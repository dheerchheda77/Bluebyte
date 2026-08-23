"""
Training loop for HeteroGNN link prediction (Species -occurs_in-> OceanGrid).

Why this file exists:
Previously the GNN (model.py: HeteroGNN) was instantiated with random weights
and used directly for "prediction" -- it had never seen a training signal.
This script actually trains it as a link predictor: given the graph, predict
whether a (species, grid) edge should exist, using real positive edges from
graph_builder plus sampled negative edges.

Run: python train.py
Requires: torch, torch_geometric (falls back to a clear message if missing).
"""

import random

try:
    import torch
    import torch.nn.functional as F
    from sklearn.metrics import roc_auc_score
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

from graph_builder import build_hetero_graph, sample_negative_edges, HAS_PYG, SPECIES_METADATA

if HAS_PYG:
    from model import HeteroGNN


def split_edges(src, dst, test_frac=0.2, seed=42):
    random.seed(seed)
    idx = list(range(len(src)))
    random.shuffle(idx)
    n_test = int(len(idx) * test_frac)
    test_idx = set(idx[:n_test])
    train_src, train_dst, test_src, test_dst = [], [], [], []
    for i in idx:
        if i in test_idx:
            test_src.append(src[i]); test_dst.append(dst[i])
        else:
            train_src.append(src[i]); train_dst.append(dst[i])
    return (train_src, train_dst), (test_src, test_dst)


def train(num_epochs=100, hidden_channels=32, lr=0.01, seed=42):
    if not (HAS_PYG and HAS_DEPS):
        print("torch_geometric / torch / sklearn not available - cannot train. "
              "Install requirements.txt in a real environment.")
        return None

    torch.manual_seed(seed)
    data = build_hetero_graph(seed=seed)

    num_species = len(SPECIES_METADATA)
    num_grids = data['OceanGrid'].x.shape[0]

    pos_edge_index = data['Species', 'species_occurs_in_grid', 'OceanGrid'].edge_index
    pos_src = pos_edge_index[0].tolist()
    pos_dst = pos_edge_index[1].tolist()

    (train_pos_src, train_pos_dst), (test_pos_src, test_pos_dst) = split_edges(pos_src, pos_dst, seed=seed)

    # Negative sampling: separate pools for train/test so test negatives
    # are not leaked into training
    train_neg_src, train_neg_dst = sample_negative_edges(
        pos_src, pos_dst, num_species, num_grids, num_neg=len(train_pos_src), seed=seed
    )
    test_neg_src, test_neg_dst = sample_negative_edges(
        pos_src, pos_dst, num_species, num_grids, num_neg=len(test_pos_src), seed=seed + 1
    )

    model = HeteroGNN(hidden_channels=hidden_channels, out_channels=hidden_channels, dropout=0.3)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=5e-4)

    x_dict = {
        'OceanGrid': data['OceanGrid'].x,
        'Species': data['Species'].x,
        'eDNAMarker': data['eDNAMarker'].x,
    }
    edge_index_dict = {
        ('Species', 'species_occurs_in_grid', 'OceanGrid'): data['Species', 'species_occurs_in_grid', 'OceanGrid'].edge_index,
        ('eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'): data['eDNAMarker', 'edna_detected_in_grid', 'OceanGrid'].edge_index,
        ('eDNAMarker', 'edna_identifies_species', 'Species'): data['eDNAMarker', 'edna_identifies_species', 'Species'].edge_index,
        ('OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'): data['OceanGrid', 'grid_correlates_with_grid', 'OceanGrid'].edge_index,
    }

    train_edge_label_index = torch.tensor([
        train_pos_src + train_neg_src,
        train_pos_dst + train_neg_dst
    ], dtype=torch.long)
    train_labels = torch.tensor(
        [1.0] * len(train_pos_src) + [0.0] * len(train_neg_src), dtype=torch.float
    )

    test_edge_label_index = torch.tensor([
        test_pos_src + test_neg_src,
        test_pos_dst + test_neg_dst
    ], dtype=torch.long)
    test_labels = torch.tensor(
        [1.0] * len(test_pos_src) + [0.0] * len(test_neg_src), dtype=torch.float
    )

    print(f"Train edges: {len(train_labels)} ({len(train_pos_src)} pos / {len(train_neg_src)} neg)")
    print(f"Test edges:  {len(test_labels)} ({len(test_pos_src)} pos / {len(test_neg_src)} neg)")

    best_auc = -1.0
    best_state = None
    patience = 20
    epochs_since_best = 0

    model.train()
    for epoch in range(1, num_epochs + 1):
        optimizer.zero_grad()
        out = model(x_dict, edge_index_dict, train_edge_label_index)
        loss = F.binary_cross_entropy_with_logits(out, train_labels)
        loss.backward()
        optimizer.step()

        # Evaluate every epoch so we don't miss the best checkpoint between
        # print intervals, and so early stopping can react promptly.
        model.eval()
        with torch.no_grad():
            test_out = model(x_dict, edge_index_dict, test_edge_label_index)
            test_probs = torch.sigmoid(test_out).numpy()
            try:
                auc = roc_auc_score(test_labels.numpy(), test_probs)
            except ValueError:
                auc = float('nan')  # can happen if a batch is all-one-class
        model.train()

        if epoch % 10 == 0 or epoch == 1:
            print(f"Epoch {epoch:3d} | train loss {loss.item():.4f} | test AUC {auc:.4f}")

        if auc == auc and auc > best_auc:  # 'auc == auc' filters out NaN
            best_auc = auc
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            epochs_since_best = 0
        else:
            epochs_since_best += 1

        if epochs_since_best >= patience:
            print(f"Early stopping at epoch {epoch} (no test AUC improvement for {patience} epochs). "
                  f"Best test AUC: {best_auc:.4f}")
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    torch.save(model.state_dict(), "gnn_link_predictor.pt")
    print(f"Saved BEST checkpoint (test AUC {best_auc:.4f}) to gnn_link_predictor.pt")
    return model


if __name__ == "__main__":
    train()