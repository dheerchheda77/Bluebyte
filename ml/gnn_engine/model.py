import math

try:
    import torch
    import torch.nn.functional as F
    from torch_geometric.nn import HeteroConv, GATConv
    HAS_PYG = True
except ImportError:
    HAS_PYG = False
    
from .graph_builder import SPECIES_METADATA

if HAS_PYG:
    class HeteroGNN(torch.nn.Module):
        def __init__(self, hidden_channels, out_channels):
            super().__init__()
            # A simple 2-layer HeteroGAT
            self.conv1 = HeteroConv({
                ('Species', 'species_occurs_in_grid', 'OceanGrid'): GATConv((-1, -1), hidden_channels),
                ('eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'): GATConv((-1, -1), hidden_channels),
                ('eDNAMarker', 'edna_identifies_species', 'Species'): GATConv((-1, -1), hidden_channels),
                ('OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'): GATConv(-1, hidden_channels),
            }, aggr='sum')
            self.conv2 = HeteroConv({
                ('Species', 'species_occurs_in_grid', 'OceanGrid'): GATConv((-1, -1), hidden_channels),
                ('eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'): GATConv((-1, -1), hidden_channels),
                ('eDNAMarker', 'edna_identifies_species', 'Species'): GATConv((-1, -1), hidden_channels),
                ('OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'): GATConv(-1, hidden_channels),
            }, aggr='sum')

            # Link prediction head for species -> grid
            self.lin = torch.nn.Linear(hidden_channels * 2, 1)

        def forward(self, x_dict, edge_index_dict, edge_label_index):
            x_dict = self.conv1(x_dict, edge_index_dict)
            x_dict = {key: F.relu(x) for key, x in x_dict.items()}
            x_dict = self.conv2(x_dict, edge_index_dict)
            
            # Predict edges for ('Species', 'species_occurs_in_grid', 'OceanGrid')
            z_src = x_dict['Species'][edge_label_index[0]]
            z_dst = x_dict['OceanGrid'][edge_label_index[1]]
            z = torch.cat([z_src, z_dst], dim=-1)
            return self.lin(z).squeeze(-1)

class FallbackModel:
    def __init__(self):
        self.species_meta = SPECIES_METADATA
        
    def score_habitat(self, grid_features, sp):
        # grid_features = [sst, salinity, chlorophyll, do, depth, lat, lon]
        sst, salinity, chlorophyll, do, depth, lat, lon = grid_features
        
        opt_sst = (sp["min_sst"] + sp["max_sst"]) / 2
        sst_sigma = (sp["max_sst"] - sp["min_sst"]) / 2 if sp["max_sst"] != sp["min_sst"] else 1.0
        
        # Gaussian similarity for SST
        sst_score = math.exp(-0.5 * ((sst - opt_sst) / sst_sigma)**2)
        
        opt_depth = (sp["min_depth"] + sp["max_depth"]) / 2
        depth_sigma = (sp["max_depth"] - sp["min_depth"]) / 2 if sp["max_depth"] != sp["min_depth"] else 1.0
        depth_score = math.exp(-0.5 * ((depth - opt_depth) / depth_sigma)**2)
        
        # Salinity optimal is roughly 34 PSU for marine fish
        salinity_score = math.exp(-0.5 * ((salinity - 34.0) / 2.0)**2)
        
        # Combining
        score = (0.5 * sst_score) + (0.3 * depth_score) + (0.2 * salinity_score)
        
        # DO influence - below 3.0 is hypoxic
        if do < 3.0:
            score *= 0.2
            
        return max(0.0, min(1.0, score))
        
    def predict(self, grid_features):
        results = []
        for sp in self.species_meta:
            score = self.score_habitat(grid_features, sp)
            results.append({
                "species_name": sp["name"],
                "scientific_name": sp["scientific"],
                "confidence": score,
                "habitat_match": score > 0.6
            })
        results.sort(key=lambda x: x["confidence"], reverse=True)
        return results
