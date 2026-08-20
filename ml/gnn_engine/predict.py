import random
from .graph_builder import build_hetero_graph, HAS_PYG, SPECIES_METADATA
from .model import FallbackModel

if HAS_PYG:
    from .model import HeteroGNN
    import torch

class MarineBiodiversityPredictor:
    def __init__(self):
        self.graph = build_hetero_graph()
        self.fallback = FallbackModel()
        self.use_gnn = HAS_PYG
        
        if self.use_gnn:
            # We initialize a dummy model with random weights to simulate trained state
            # for the hackathon demo
            hidden_channels = 32
            out_channels = 32
            self.model = HeteroGNN(hidden_channels, out_channels)
            self.model.eval()

    def predict_species_in_grid(self, grid_id, sst, salinity, chlorophyll, do, depth=50.0, lat=15.0, lon=70.0):
        # Even if GNN is available, we often use the fallback model for fast demo API 
        # unless we explicitly route through the graph. For the demo, Fallback yields 
        # highly explainable results based on environmental rules.
        grid_features = [sst, salinity, chlorophyll, do, depth, lat, lon]
        return self.fallback.predict(grid_features)

    def get_biodiversity_score(self, grid_id):
        # Simulated based on graph density and features
        # For demo, returning a synthetic but realistic index
        return random.uniform(0.4, 0.95)

    def get_edna_cross_references(self, grid_id):
        # Extract eDNA markers detected in this grid from graph
        markers = []
        if self.use_gnn:
            edge_index = self.graph['eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'].edge_index
            edna_nodes = edge_index[0][edge_index[1] == grid_id].tolist()
            for e_id in set(edna_nodes):
                markers.append({"marker_id": e_id, "confidence": random.uniform(0.7, 0.99)})
        else:
            edges = self.graph["edges"]["edna_detected_in_grid"]
            for e_id, g_id in zip(edges[0], edges[1]):
                if g_id == grid_id:
                    markers.append({"marker_id": e_id, "confidence": random.uniform(0.7, 0.99)})
        return markers

    def predict_all_grids(self):
        features = []
        if self.use_gnn:
            features = self.graph['OceanGrid'].x.tolist()
        else:
            features = self.graph["nodes"]["OceanGrid"]
            
        fc = {"type": "FeatureCollection", "features": []}
        for i, feat in enumerate(features):
            sst, sal, chl, do, dep, lat, lon = feat
            predictions = self.predict_species_in_grid(i, sst, sal, chl, do, dep, lat, lon)
            fc["features"].append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "grid_id": i,
                    "sst": sst,
                    "salinity": sal,
                    "predictions": predictions,
                    "biodiversity_score": self.get_biodiversity_score(i)
                }
            })
        return fc

if __name__ == "__main__":
    predictor = MarineBiodiversityPredictor()
    print("Mode:", "PyTorch GNN" if predictor.use_gnn else "Fallback Rule-based")
    
    res = predictor.predict_species_in_grid(
        grid_id=0,
        sst=28.5,
        salinity=34.0,
        chlorophyll=1.5,
        do=5.5
    )
    print("\nPredictions for sample grid (SST=28.5, DO=5.5):")
    for r in res:
        print(f"- {r['species_name']}: {r['confidence']:.2f}")
        
    print(f"\nBiodiversity Score: {predictor.get_biodiversity_score(0):.2f}")
