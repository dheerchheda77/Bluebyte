import random
try:
    from .graph_builder import build_hetero_graph, HAS_PYG, SPECIES_METADATA
    from .model import FallbackModel
except ImportError:
    from graph_builder import build_hetero_graph, HAS_PYG, SPECIES_METADATA
    from model import FallbackModel

if HAS_PYG:
    try:
        from .model import HeteroGNN, load_pretrained
    except ImportError:
        from model import HeteroGNN, load_pretrained
    import torch


class MarineBiodiversityPredictor:
    def __init__(self, checkpoint_path="gnn_link_predictor.pt"):
        self.graph = build_hetero_graph()
        self.fallback = FallbackModel()
        self.use_gnn = HAS_PYG

        self.gnn = None
        self.gnn_trained = False
        if self.use_gnn:
            trained = load_pretrained(checkpoint_path, hidden_channels=32)
            if trained is not None:
                self.gnn = trained
                self.gnn_trained = True
            else:
                # No checkpoint found: keep an untrained model around ONLY so
                # code paths don't crash, but never present its output as a
                # real prediction. self.gnn_trained flags this explicitly.
                self.gnn = HeteroGNN(hidden_channels=32, out_channels=32)
                self.gnn.eval()
                self.gnn_trained = False

    def _x_dict(self):
        return {
            'OceanGrid': self.graph['OceanGrid'].x,
            'Species': self.graph['Species'].x,
            'eDNAMarker': self.graph['eDNAMarker'].x,
        }

    def _edge_index_dict(self):
        return {
            ('Species', 'species_occurs_in_grid', 'OceanGrid'): self.graph['Species', 'species_occurs_in_grid', 'OceanGrid'].edge_index,
            ('eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'): self.graph['eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'].edge_index,
            ('eDNAMarker', 'edna_identifies_species', 'Species'): self.graph['eDNAMarker', 'edna_identifies_species', 'Species'].edge_index,
            ('OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'): self.graph['OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'].edge_index,
        }

    def predict_species_in_grid(self, grid_id, sst, salinity, chlorophyll, do, depth=50.0, lat=15.0, lon=70.0):
        """Returns fallback (rule-based, always explainable) predictions for an
        ARBITRARY query point (sst/salinity/etc supplied directly), since the
        GNN only scores nodes that already exist in its trained graph. Use
        predict_species_in_existing_grid() to get the trained GNN's opinion on
        a real grid_id from the graph."""
        grid_features = [sst, salinity, chlorophyll, do, depth, lat, lon]
        return self.fallback.predict(grid_features)

    def predict_species_in_existing_grid(self, grid_id, top_k=None):
        """Real link-prediction path: uses the trained GNN to score every
        species against grid_id (must be an existing node index in the
        current graph). Falls back to the rule-based model, explicitly
        labelled, if no trained checkpoint is available."""
        if not (self.use_gnn and self.gnn_trained):
            if self.use_gnn:
                # torch_geometric present, but no trained checkpoint yet
                grid_features = self.graph['OceanGrid'].x[grid_id].tolist()
                source = "fallback_untrained_gnn"
            else:
                # torch_geometric not installed at all -> dict-based graph
                grid_features = self.graph["nodes"]["OceanGrid"][grid_id]
                source = "fallback_no_pyg"
            results = self.fallback.predict(grid_features)
            return {"source": source, "predictions": results}

        num_species = len(SPECIES_METADATA)
        edge_label_index = torch.tensor(
            [list(range(num_species)), [grid_id] * num_species], dtype=torch.long
        )
        with torch.no_grad():
            logits = self.gnn(self._x_dict(), self._edge_index_dict(), edge_label_index)
            probs = torch.sigmoid(logits).tolist()

        results = []
        for sp, p in zip(SPECIES_METADATA, probs):
            results.append({
                "species_name": sp["name"],
                "scientific_name": sp["scientific"],
                "confidence": p,
                "habitat_match": p > 0.6
            })
        results.sort(key=lambda x: x["confidence"], reverse=True)
        if top_k:
            results = results[:top_k]
        return {"source": "trained_gnn", "predictions": results}

    def explain_prediction(self, grid_id, species_id):
        """Returns the GNN's score for (species_id, grid_id) plus, per relation
        type, how much removing that relation's edges shifts the prediction
        (ablation-based importance). A larger shift means that relation was
        more load-bearing for this specific prediction. Requires a trained
        GNN checkpoint."""
        if not (self.use_gnn and self.gnn_trained):
            return {"error": "no trained GNN checkpoint available; run train.py first"}

        edge_label_index = torch.tensor([[species_id], [grid_id]], dtype=torch.long)
        confidence, impact_by_relation = self.gnn.explain_by_ablation(
            self._x_dict(), self._edge_index_dict(), edge_label_index
        )

        return {
            "confidence": confidence,
            "impact_by_relation": impact_by_relation
        }

    def confidence_with_support(self, grid_id, species_id):
        """Wraps explain_prediction() with a support count: how much real
        evidence backs this confidence score, not just the number itself.
        Two predictions can show '0.71 confidence' for very different
        reasons -- this surfaces that difference instead of hiding it."""
        base = self.explain_prediction(grid_id, species_id)
        if "error" in base:
            return base

        # eDNA markers actually detected in this grid
        edna_markers = self.get_edna_cross_references(grid_id)

        # Neighboring grids (from k-NN spatial edges) where this species
        # also occurs, per the graph's positive edges
        edge_index = self.graph['Species', 'species_occurs_in_grid', 'OceanGrid'].edge_index
        species_grids = set(edge_index[1][edge_index[0] == species_id].tolist())

        grid_edge_index = self.graph['OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'].edge_index
        neighbor_grids = grid_edge_index[1][grid_edge_index[0] == grid_id].tolist()
        corroborating_neighbors = sum(1 for g in neighbor_grids if g in species_grids)

        return {
            "confidence": base["confidence"],
            "impact_by_relation": base["impact_by_relation"],
            "support": {
                "edna_markers_in_grid": len(edna_markers),
                "corroborating_neighbor_grids": corroborating_neighbors,
                "total_neighbor_grids_checked": len(neighbor_grids)
            }
        }

    def seasonal_species_shift(self, species_id, top_k=5):
        """Runs the trained GNN against 3 seasonal graph snapshots (same
        model, different grid conditions) and reports the top predicted
        grids for one species in each season -- shows migration/habitat
        shift, not just a single static prediction.

        Pragmatic Tier-2 version: 3 static snapshots (pre_monsoon, monsoon,
        post_monsoon), not a true temporal GNN. Uses the SAME trained
        checkpoint across all 3 -- only the grid conditions change per
        season, via graph_builder.SEASON_SHIFTS."""
        if not (self.use_gnn and self.gnn_trained):
            return {"error": "no trained GNN checkpoint available; run train.py first"}

        results = {}
        for season in ["pre_monsoon", "monsoon", "post_monsoon"]:
            seasonal_graph = build_hetero_graph(seed=42, season=season)
            x_dict = {
                'OceanGrid': seasonal_graph['OceanGrid'].x,
                'Species': seasonal_graph['Species'].x,
                'eDNAMarker': seasonal_graph['eDNAMarker'].x,
            }
            edge_index_dict = {
                ('Species', 'species_occurs_in_grid', 'OceanGrid'): seasonal_graph['Species', 'species_occurs_in_grid', 'OceanGrid'].edge_index,
                ('eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'): seasonal_graph['eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'].edge_index,
                ('eDNAMarker', 'edna_identifies_species', 'Species'): seasonal_graph['eDNAMarker', 'edna_identifies_species', 'Species'].edge_index,
                ('OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'): seasonal_graph['OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'].edge_index,
            }
            num_grids = seasonal_graph['OceanGrid'].x.shape[0]
            edge_label_index = torch.tensor(
                [[species_id] * num_grids, list(range(num_grids))], dtype=torch.long
            )
            with torch.no_grad():
                probs = torch.sigmoid(
                    self.gnn(x_dict, edge_index_dict, edge_label_index)
                ).tolist()

            top_grids = sorted(enumerate(probs), key=lambda x: x[1], reverse=True)[:top_k]
            results[season] = [{"grid_id": g, "confidence": round(p, 3)} for g, p in top_grids]

        return results

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
            gnn_result = self.predict_species_in_existing_grid(i)
            fc["features"].append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": {
                    "grid_id": i,
                    "sst": sst,
                    "salinity": sal,
                    "prediction_source": gnn_result["source"],
                    "predictions": gnn_result["predictions"],
                    "biodiversity_score": self.get_biodiversity_score(i)
                }
            })
        return fc


if __name__ == "__main__":
    predictor = MarineBiodiversityPredictor()
    print("Mode:", "PyTorch GNN" if predictor.use_gnn else "Fallback Rule-based")
    print("GNN trained:", predictor.gnn_trained,
          "(run train.py first if False)")

    res = predictor.predict_species_in_grid(
        grid_id=0,
        sst=28.5,
        salinity=34.0,
        chlorophyll=1.5,
        do=5.5
    )
    print("\nFallback predictions for sample query (SST=28.5, DO=5.5):")
    for r in res:
        print(f"- {r['species_name']}: {r['confidence']:.2f}")

    existing = predictor.predict_species_in_existing_grid(0)
    print(f"\n[{existing['source']}] Predictions for grid 0 in the actual graph:")
    for r in existing["predictions"]:
        print(f"- {r['species_name']}: {r['confidence']:.2f}")

    print(f"\nBiodiversity Score: {predictor.get_biodiversity_score(0):.2f}")