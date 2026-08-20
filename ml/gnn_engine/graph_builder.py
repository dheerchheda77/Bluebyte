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

def build_hetero_graph():
    num_grids = 20
    num_species = len(SPECIES_METADATA)
    num_edna = 15

    # Grid nodes
    grid_features = []
    for i in range(num_grids):
        lat = random.uniform(5.0, 25.0)
        lon = random.uniform(65.0, 95.0)
        sst = random.uniform(22.0, 31.0)
        salinity = random.uniform(32.0, 36.0)
        chlorophyll = random.uniform(0.1, 5.0)
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

    # Edges
    species_grid_src, species_grid_dst = [], []
    for sp_id in range(num_species):
        for g_id in range(num_grids):
            if random.random() < 0.2:
                species_grid_src.append(sp_id)
                species_grid_dst.append(g_id)
                
    edna_grid_src, edna_grid_dst = [], []
    for e_id in range(num_edna):
        g_id = random.randint(0, num_grids - 1)
        edna_grid_src.append(e_id)
        edna_grid_dst.append(g_id)

    edna_species_src, edna_species_dst = [], []
    for e_id in range(num_edna):
        sp_id = random.randint(0, num_species - 1)
        edna_species_src.append(e_id)
        edna_species_dst.append(sp_id)

    grid_grid_src, grid_grid_dst = [], []
    for g1 in range(num_grids):
        for g2 in range(num_grids):
            if g1 != g2 and random.random() < 0.1:
                grid_grid_src.append(g1)
                grid_grid_dst.append(g2)

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
        # Fallback dict-based graph
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

if __name__ == "__main__":
    graph = build_hetero_graph()
    print("Graph built successfully.")
    if HAS_PYG:
        print(graph)
    else:
        print("Using dict fallback.")
