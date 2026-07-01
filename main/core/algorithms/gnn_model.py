"""GNN model definitions for pickle compatibility."""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def global_mean_pool(x: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
    """Minimal replacement for torch_geometric.nn.global_mean_pool."""
    if batch.numel() == 0:
        return x.new_zeros((0, x.size(-1)))

    batch = batch.to(dtype=torch.long, device=x.device)
    num_graphs = int(batch.max().item()) + 1
    pooled = x.new_zeros((num_graphs, x.size(-1)))
    counts = x.new_zeros((num_graphs, 1))

    pooled.index_add_(0, batch, x)
    counts.index_add_(0, batch, torch.ones((x.size(0), 1), device=x.device, dtype=x.dtype))
    counts = counts.clamp_min_(1)
    return pooled / counts


class GINLayer(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.eps = nn.Parameter(torch.zeros(1))
        self.mlp = nn.Sequential(
            nn.Linear(in_channels, out_channels),
            nn.ReLU(),
            nn.Linear(out_channels, out_channels),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        row, col = edge_index
        agg = torch.zeros_like(x)
        agg.index_add_(0, row, x[col])
        out = self.mlp((1 + self.eps) * x + agg)
        return out


class SubgraphGNN(nn.Module):
    def __init__(self, in_channels: int = 1, hidden_channels: int = 64, out_channels: int = 64) -> None:
        super().__init__()
        self.gin1 = GINLayer(in_channels, hidden_channels)
        self.gin2 = GINLayer(hidden_channels, out_channels)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, batch: torch.Tensor) -> torch.Tensor:
        x = self.gin1(x, edge_index)
        x = F.relu(x)
        x = self.gin2(x, edge_index)
        return global_mean_pool(x, batch)


class PairClassifier(nn.Module):
    def __init__(self, emb_size: int = 64, dropout: float = 0.0) -> None:
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(emb_size * 2, 128),
            nn.ReLU(),
            nn.Dropout(p=float(dropout)),
            nn.Linear(128, 1),
        )

    def forward(self, emb1: torch.Tensor, emb2: torch.Tensor) -> torch.Tensor:
        if emb1.dim() == 1:
            emb1 = emb1.view(1, -1)
        if emb2.dim() == 1:
            emb2 = emb2.view(1, -1)
        x = torch.cat([emb1, emb2], dim=1)
        return self.fc(x).squeeze(1)


__all__ = ["GINLayer", "SubgraphGNN", "PairClassifier"]
