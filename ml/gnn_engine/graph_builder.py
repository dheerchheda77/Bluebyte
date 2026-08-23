import random
import numpy as np

try:
    import torch
    from torch_geometric.data import HeteroData
    HAS_PYG = True
except ImportError:
    HAS_PYG = False
    HeteroData = object  # dummy for type hints

SPECIES_METADATA = [
    {"id": 0, "name": "Indian Mackerel", "scientific": "Rastrelliger kanagurta", "min_sst": 26.0, "max_sst": 29.0, "min_depth": 10, "max_depth": 70, "comm": 0.9, "risk": 0.2},
    {"id": 1, "name": "Oil Sardine", "scientific": "Sardinella longiceps", "min_sst": 25.0, "max_sst": 28.5, "min_depth": 0, "max_depth": 40, "comm": 0.8, "risk": 0.3},
    {"id": 2, "name": "Hilsa", "scientific": "Tenualosa ilisha", "min_sst": 24.0, "max_sst": 30.0, "min_depth": 0, "max_depth": 50, "comm": 0.95, "risk": 0.6},
    {"id": 3, "name": "Bombay Duck", "scientific": "Harpadon nehereus", "min_sst": 24.5, "max_sst": 28.0, "min_depth": 10, "max_depth": 60, "comm": 0.7, "risk": 0.4},
    {"id": 4, "name": "Yellowfin Tuna", "scientific": "Thunnus albacares", "min_sst": 22.0, "max_sst": 28.0, "min_depth": 0, "max_depth": 250, "comm": 1.0, "risk": 0.7},
    {"id": 5, "name": "Penaeid Shrimp", "scientific": "Penaeus indicus", "min_sst": 26.0, "max_sst": 31.0, "min_depth": 2, "max_depth": 30, "comm": 0.85, "risk": 0.2}
]

# NOTE: this is a PLACEHOLDER data-generation function. It exists so the GNN
# training pipeline has a structured (not purely random) signal to learn from
# while real INCOIS/CMFRI/NCBI data integration is pending. The occurrence
# rule below (species present if grid SST/depth fall inside the species'
# known tolerance range) mirrors the same logic already used in
# FallbackModel.score_habitat, so both paths agree on what "ground truth"
# looks like for demo purposes.


def _species_occurs(sp, sst, depth):
    """Ground-truth-ish rule used only for synthetic label generation.
    High probability if within tolerance range, low otherwise -> gives the
    GNN an actual pattern to discover instead of pure noise."""
    sst_ok = sp["min_sst"] <= sst <= sp["max_sst"]
    depth_ok = sp["min_depth"] <= depth <= sp["max_depth"]
    if sst_ok and depth_ok:
        return random.random() < 0.85
    elif sst_ok or depth_ok:
        return random.random() < 0.25
    else:
        return random.random() < 0.05

def _build_grid_adjacency(grid_features, num_grids, k=6):
    """Grid <-> Grid spatial adjacency. Currently: sklearn BallTree k-NN on
    haversine distance (placeholder). TODO: swap for Dheer's KD-tree spatial
    indexing module when ready — same interface, return (src_list, dst_list)."""
    from sklearn.neighbors import BallTree
    latlon_rad = np.radians([[gf[5], gf[6]] for gf in grid_features])
    tree = BallTree(latlon_rad, metric='haversine')
    _, neighbor_idx = tree.query(latlon_rad, k=min(k + 1, num_grids))

    src, dst = [], []
    for g1, neighbors in enumerate(neighbor_idx):
        for g2 in neighbors:
            g2 = int(g2)
            if g1 != g2:
                src.append(g1)
                dst.append(g2)
    return src, dst

# Seasonal SST/chlorophyll offsets used by build_hetero_graph(season=...).
# Pragmatic Tier-2 version: 3 static snapshots with shifted grid conditions,
# not a true temporal GNN. Species occurrence naturally shifts per season
# because _species_occurs reads sst/depth off these season-adjusted grids.
SEASON_SHIFTS = {
    "pre_monsoon": {"sst_offset": 1.5, "chl_offset": -0.5},
    "monsoon": {"sst_offset": -1.0, "chl_offset": 1.5},
    "post_monsoon": {"sst_offset": 0.0, "chl_offset": 0.3},
}


def build_hetero_graph(num_grids=200, num_edna=150, seed=None, season="post_monsoon"):
    if seed is not None:
        random.seed(seed)

    num_species = len(SPECIES_METADATA)
    shift = SEASON_SHIFTS.get(season, SEASON_SHIFTS["post_monsoon"])

    # Grid nodes
    grid_features = []
    for i in range(num_grids):
        lat = random.uniform(5.0, 25.0)
        lon = random.uniform(65.0, 95.0)
        sst = random.uniform(22.0, 31.0) + shift["sst_offset"]
        salinity = random.uniform(32.0, 36.0)
        chlorophyll = max(0.05, random.uniform(0.1, 5.0) + shift["chl_offset"])
        do = random.uniform(3.0, 7.0)
        depth = random.uniform(0.0, 300.0)
        grid_features.append([sst, salinity, chlorophyll, do, depth, lat, lon])

    # Species nodes
    species_features = []
    for sp in SPECIES_METADATA:
        species_features.append([
            sp["min_sst"], sp["max_sst"], sp["min_depth"], sp["max_depth"],
            sp["comm"], sp["risk"]
        ])

    # eDNA nodes
    edna_features = []
    for i in range(num_edna):
        confidence = random.uniform(0.5, 1.0)
        marker_type = random.choice([0, 1, 2])
        edna_features.append([confidence, marker_type])

    # --- Species -> Grid edges: STRUCTURED (rule-biased), not flat 20% ---
    species_grid_src, species_grid_dst = [], []
    for sp_id, sp in enumerate(SPECIES_METADATA):
        for g_id in range(num_grids):
            sst, salinity, chlorophyll, do, depth, lat, lon = grid_features[g_id]
            if _species_occurs(sp, sst, depth):
                species_grid_src.append(sp_id)
                species_grid_dst.append(g_id)

    # eDNA -> Grid: keep as-is (sampling location is inherently arbitrary)
    edna_grid_src, edna_grid_dst = [], []
    for e_id in range(num_edna):
        g_id = random.randint(0, num_grids - 1)
        edna_grid_src.append(e_id)
        edna_grid_dst.append(g_id)

    # eDNA -> Species: bias towards species that DO occur in that eDNA's grid,
    # so the edna_identifies_species signal is consistent with occurrence,
    # not just random noise the GNN has to fight against.
    edna_species_src, edna_species_dst = [], []
    occurs_by_grid = {}
    for sp_id, g_id in zip(species_grid_src, species_grid_dst):
        occurs_by_grid.setdefault(g_id, []).append(sp_id)

    for e_id in range(num_edna):
        g_id = edna_grid_dst[e_id]
        candidates = occurs_by_grid.get(g_id, [])
        if candidates and random.random() < 0.8:
            sp_id = random.choice(candidates)
        else:
            sp_id = random.randint(0, num_species - 1)
        edna_species_src.append(e_id)
        edna_species_dst.append(sp_id)

    # Grid <-> Grid: k-NN spatial adjacency (see _build_grid_adjacency).
    grid_grid_src, grid_grid_dst = _build_grid_adjacency(grid_features, num_grids)

    if HAS_PYG:
        data = HeteroData()
        data['OceanGrid'].x = torch.tensor(grid_features, dtype=torch.float)
        data['Species'].x = torch.tensor(species_features, dtype=torch.float)
        data['eDNAMarker'].x = torch.tensor(edna_features, dtype=torch.float)

        data['Species', 'species_occurs_in_grid', 'OceanGrid'].edge_index = torch.tensor([species_grid_src, species_grid_dst], dtype=torch.long)
        data['eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'].edge_index = torch.tensor([edna_grid_src, edna_grid_dst], dtype=torch.long)
        data['eDNAMarker', 'edna_identifies_species', 'Species'].edge_index = torch.tensor([edna_species_src, edna_species_dst], dtype=torch.long)
        data['OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'].edge_index = torch.tensor([grid_grid_src, grid_grid_dst], dtype=torch.long)
        return data
    else:
        return {
            "nodes": {
                "OceanGrid": grid_features,
                "Species": species_features,
                "eDNAMarker": edna_features
            },
            "edges": {
                "species_occurs_in_grid": (species_grid_src, species_grid_dst),
                "edna_detected_in_grid": (edna_grid_src, edna_grid_dst),
                "edna_identifies_species": (edna_species_src, edna_species_dst),
                "grid_correlates_with_grid": (grid_grid_src, grid_grid_dst)
            }
        }


def sample_negative_edges(pos_src, pos_dst, num_src_nodes, num_dst_nodes, num_neg=None, seed=None):
    """Generate negative (non-occurrence) species-grid edges for link prediction
    training. Excludes any pair already present as a positive edge.
    Returns (neg_src, neg_dst) lists, same length as positives by default."""
    if seed is not None:
        random.seed(seed)

    pos_set = set(zip(pos_src, pos_dst))
    if num_neg is None:
        num_neg = len(pos_src)

    neg_src, neg_dst = [], []
    attempts = 0
    max_attempts = num_neg * 50  # safety valve for dense/small graphs
    while len(neg_src) < num_neg and attempts < max_attempts:
        s = random.randint(0, num_src_nodes - 1)
        d = random.randint(0, num_dst_nodes - 1)
        attempts += 1
        if (s, d) not in pos_set:
            neg_src.append(s)
            neg_dst.append(d)
            pos_set.add((s, d))  # avoid duplicate negatives too
    return neg_src, neg_dst


if __name__ == "__main__":
    graph = build_hetero_graph(seed=42)
    print("Graph built successfully.")
    if HAS_PYG:
        print(graph)
    else:
        print("Using dict fallback.")