"""Trainable VMamba-style tensor models for Isomera benchmarks.

The deterministic VMamba adapters in ``vmamba_mesh.py`` are intentionally
transparent. This module adds the next contract: neural pickle artifacts that
still expose ``predict_pairs(graph)`` so Benchmark & Examples can route them
like the existing GNN and VMamba-Mesh pickles.

These models are Isomera trainable baselines with VMamba-like hyperparameters.
They do not claim to be the official CUDA/Triton VMamba implementation. The
architecture uses patch embedding, staged VSS-style blocks, native PyTorch
cross-scan SS2D-style cumulative routes, stochastic-depth-style residual
dropout, and a duplicate-pair head.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import combinations
import json
import math
import os
import platform
import pickle
import random
import sys
import time
from pathlib import Path
from typing import Any

import networkx as nx

from core.algorithms.vmamba_mesh import (
    DEFAULT_FEATURE_WEIGHTS,
    VMambaMeshConfig,
    canonical_node_order,
    canonical_pair,
    context_subgraph,
    load_positive_pairs,
    pair_features,
)


VMAMBA_TRAINABLE_MODEL_VERSION = "vmamba_trainable_tensor_v0.1"

VMAMBA_TRAINABLE_PRESETS: dict[str, dict[str, Any]] = {
    "tiny": {
        "depths": (1, 1, 2, 1),
        "dims": (32, 64, 128, 256),
        "hidden_dim": 128,
        "embedding_dim": 128,
        "patch_size": 2,
        "drop_path_rate": 0.05,
        "description": "Fast sanity-check preset. Not article-grade.",
    },
    "article_cpu": {
        "depths": (2, 2, 8, 2),
        "dims": (16, 32, 64, 128),
        "hidden_dim": 128,
        "embedding_dim": 128,
        "patch_size": 2,
        "drop_path_rate": 0.15,
        "description": "Article CPU preset: base-depth VSS/SS2D topology with CPU-feasible width for all 20 scenarios.",
    },
    "small": {
        "depths": (2, 2, 4, 2),
        "dims": (64, 128, 256, 512),
        "hidden_dim": 256,
        "embedding_dim": 256,
        "patch_size": 2,
        "drop_path_rate": 0.10,
        "description": "Practical local ablation preset for SPEC screening.",
    },
    "base": {
        "depths": (2, 2, 8, 2),
        "dims": (96, 192, 384, 768),
        "hidden_dim": 384,
        "embedding_dim": 384,
        "patch_size": 2,
        "drop_path_rate": 0.20,
        "description": "VMamba-like base depth/width for article-grade runs.",
    },
}


VMAMBA_CHANNEL_CONTRACT: dict[str, dict[str, str]] = {
    "C0": {
        "name": "Forward adjacency",
        "role": "canonical directed lineage edges",
    },
    "C1": {
        "name": "Reverse adjacency",
        "role": "reverse lineage edges for bidirectional structural context",
    },
    "C2": {
        "name": "Layer diagonal",
        "role": "SOR/SOT/SPEC identity injected on the tensor diagonal",
    },
    "C3": {
        "name": "Degree fingerprint",
        "role": "normalized local in/out degree signature on the diagonal",
    },
    "C4": {
        "name": "Lineage route bias",
        "role": "route prior for the SOR -> SOT -> SPEC direction",
    },
    "C5": {
        "name": "Sparse mask",
        "role": "occupied-cell mask so structural zeros are explicitly represented",
    },
}


@dataclass(frozen=True)
class VMambaTrainableConfig:
    variant: str = "vmamba_mesh_t"
    scope_layers: tuple[str, ...] = ("SPEC",)
    resolution: int = 32
    channels: tuple[str, ...] = ("C0", "C1", "C2", "C3", "C4", "C5")
    architecture: str = "vss_torch"
    preset: str = "small"
    patch_size: int = 2
    depths: tuple[int, ...] = (2, 2, 4, 2)
    dims: tuple[int, ...] = (64, 128, 256, 512)
    hidden_dim: int = 64
    embedding_dim: int = 64
    mlp_ratio: float = 4.0
    dropout: float = 0.10
    drop_path_rate: float = 0.10
    threshold: float = 0.50
    negative_ratio: int = 4
    hard_negative_mining: bool = False
    hard_negative_strategy: str = "structural_similarity"
    hard_negative_agent: str = "isomera_structural_hard_negative_miner"
    hard_negative_manifest_path: str = ""
    hard_negative_manifest_id: str = ""
    false_positive_replay_rounds: int = 0
    false_positive_replay_top_k: int = 0
    false_positive_replay_weight: int = 2
    false_positive_replay_epochs: int = 2
    batch_size: int = 16
    inference_batch_size: int = 4096
    encoder_batch_size: int = 64
    auxiliary_features: bool = True
    auxiliary_feature_names: tuple[str, ...] = tuple(DEFAULT_FEATURE_WEIGHTS)
    seed: int = 42
    epochs: int = 10
    learning_rate: float = 1e-3
    train_ratio: float = 0.80
    loss_name: str = "weighted_bce"
    threshold_policy: str = "jaccard"
    threshold_precision_floor: float = 0.0
    optimizer_name: str = "adamw"
    weight_decay: float = 0.05
    forward_type: str = "v05"
    device: str = "auto"
    notes: str = "Trainable VMamba-style tensor pair model for Isomera."


def vmamba_trainable_preset_config(preset: str) -> dict[str, Any]:
    return dict(VMAMBA_TRAINABLE_PRESETS.get(str(preset).lower(), VMAMBA_TRAINABLE_PRESETS["small"]))


def _node_layer(node: str) -> str:
    upper = str(node).upper()
    if "SPEC" in upper:
        return "SPEC"
    if "SOT" in upper:
        return "SOT"
    if "SOR" in upper:
        return "SOR"
    return "OTHER"


def _layer_value(node: str) -> float:
    return {"SOR": 1.0 / 3.0, "SOT": 2.0 / 3.0, "SPEC": 1.0}.get(_node_layer(node), 0.0)


def _layer_rank(node: str) -> int:
    return {"SOR": 0, "SOT": 1, "SPEC": 2}.get(_node_layer(node), 3)


def _scope_nodes(graph: nx.DiGraph, scope_layers: tuple[str, ...]) -> list[str]:
    scope = {layer.upper() for layer in scope_layers}
    return [
        str(node)
        for node in graph.nodes
        if not scope or _node_layer(str(node)) in scope
    ]


def _channel_index(channels: tuple[str, ...], name: str) -> int | None:
    try:
        return channels.index(name)
    except ValueError:
        return None


def _resize_index(index: int, n_items: int, resolution: int) -> int:
    if n_items <= 1:
        return 0
    return min(resolution - 1, int(round(index * (resolution - 1) / (n_items - 1))))


def graph_context_tensor(
    graph: nx.DiGraph,
    node: str,
    *,
    config: VMambaTrainableConfig,
) -> Any:
    """Build a C x R x R tensor for one node context.

    The import of torch is intentionally local so the rest of the app can load
    even when optional neural dependencies are absent.

    Channel semantics:
    C0 forward adjacency, C1 reverse adjacency, C2 layer diagonal, C3 degree
    fingerprint, C4 lineage route bias, and C5 sparse mask. The selected
    channels are the neural input; the VSS/SS2D blocks operate after this
    tensorization step.
    """
    import torch

    subgraph = context_subgraph(graph, str(node), canonical=True)
    nodes = canonical_node_order([str(item) for item in subgraph.nodes])
    resolution = int(config.resolution)
    channels = tuple(config.channels)
    tensor = torch.zeros((len(channels), resolution, resolution), dtype=torch.float32)
    if not nodes:
        return tensor

    positions = {
        node_name: _resize_index(idx, len(nodes), resolution)
        for idx, node_name in enumerate(nodes)
    }
    max_degree = max(
        [subgraph.in_degree(item) + subgraph.out_degree(item) for item in nodes] or [1]
    )

    c0 = _channel_index(channels, "C0")
    c1 = _channel_index(channels, "C1")
    c2 = _channel_index(channels, "C2")
    c3 = _channel_index(channels, "C3")
    c4 = _channel_index(channels, "C4")
    c5 = _channel_index(channels, "C5")

    for node_name in nodes:
        pos = positions[node_name]
        if c2 is not None:
            tensor[c2, pos, pos] = _layer_value(node_name)
        if c3 is not None:
            degree = subgraph.in_degree(node_name) + subgraph.out_degree(node_name)
            tensor[c3, pos, pos] = float(degree) / max(float(max_degree), 1.0)
        if c5 is not None:
            tensor[c5, pos, pos] = 1.0

    for src, dst in subgraph.edges:
        src_name = str(src)
        dst_name = str(dst)
        if src_name not in positions or dst_name not in positions:
            continue
        i = positions[src_name]
        j = positions[dst_name]
        if c0 is not None:
            tensor[c0, i, j] = 1.0
        if c1 is not None:
            tensor[c1, j, i] = 1.0
        if c4 is not None:
            route_direction = 1.0 if _layer_rank(src_name) <= _layer_rank(dst_name) else 0.5
            tensor[c4, i, j] = route_direction
        if c5 is not None:
            tensor[c5, i, j] = 1.0
            tensor[c5, j, i] = 1.0
    return tensor


def pair_auxiliary_tensor(
    graph: nx.DiGraph,
    node_a: str,
    node_b: str,
    *,
    config: VMambaTrainableConfig,
) -> Any:
    import torch

    if not bool(_config_get(config, "auxiliary_features", True)):
        return torch.zeros((0,), dtype=torch.float32)
    is_mesh = str(_config_get(config, "variant", "")).lower() == "vmamba_mesh_t"
    mesh_cfg = VMambaMeshConfig(
        scope_layers=tuple(_config_get(config, "scope_layers", ("SPEC",))),
        canon_sort=is_mesh,
        diag_fp=is_mesh,
        mesh_ss2d=is_mesh,
        hier_init=is_mesh,
        sparse_gate=is_mesh,
        threshold=float(_config_get(config, "threshold", 0.5)),
        negative_ratio=int(_config_get(config, "negative_ratio", 4)),
        seed=int(_config_get(config, "seed", 42)),
        resolution=int(_config_get(config, "resolution", 32)),
    )
    features = pair_features(graph, node_a, node_b, config=mesh_cfg)
    names = tuple(_config_get(config, "auxiliary_feature_names", tuple(DEFAULT_FEATURE_WEIGHTS)))
    return torch.tensor([float(features.get(name, 0.0)) for name in names], dtype=torch.float32)


class VMambaStyleTensorEncoder:  # placeholder for type checkers; actual class built below
    pass


def _config_get(config: VMambaTrainableConfig, name: str, default: Any) -> Any:
    return getattr(config, name, default)


def resolve_torch_device(requested: str = "auto") -> dict[str, Any]:
    """Resolve the execution device and keep an auditable fallback reason."""
    import torch

    requested = str(requested or "auto").lower()
    summary: dict[str, Any] = {
        "requested_device": requested,
        "resolved_device": "cpu",
        "torch_version": getattr(torch, "__version__", "unknown"),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "mps_built": bool(torch.backends.mps.is_built()),
        "mps_available": bool(torch.backends.mps.is_available()),
        "mps_device_count": None,
        "fallback_reason": None,
    }
    if hasattr(torch, "mps"):
        try:
            summary["mps_device_count"] = int(torch.mps.device_count())
        except Exception as exc:  # noqa: BLE001
            summary["mps_device_count"] = None
            summary["fallback_reason"] = f"mps_device_count_error: {type(exc).__name__}: {exc}"
    if requested == "cpu":
        return summary
    if requested not in {"auto", "mps"}:
        summary["fallback_reason"] = f"unknown requested device: {requested}"
        return summary
    try:
        if bool(torch.backends.mps.is_available()):
            probe = torch.ones(1, device="mps")
            del probe
            summary["resolved_device"] = "mps"
            return summary
        summary["fallback_reason"] = "torch.backends.mps.is_available() returned False"
    except Exception as exc:  # noqa: BLE001
        summary["fallback_reason"] = f"{type(exc).__name__}: {exc}"
    return summary


def _drop_path(x: Any, drop_prob: float, training: bool) -> Any:
    if drop_prob <= 0.0 or not training:
        return x
    keep_prob = 1.0 - float(drop_prob)
    shape = (x.shape[0],) + (1,) * (x.ndim - 1)
    random_tensor = keep_prob + x.new_empty(shape).bernoulli_(keep_prob)
    return x.div(keep_prob) * random_tensor


def _build_modules_from_config(config: VMambaTrainableConfig) -> tuple[Any, Any]:
    return _build_modules(
        input_channels=len(tuple(_config_get(config, "channels", ("C0", "C1")))),
        hidden_dim=int(_config_get(config, "hidden_dim", 64)),
        embedding_dim=int(_config_get(config, "embedding_dim", 64)),
        dropout=float(_config_get(config, "dropout", 0.1)),
        patch_size=int(_config_get(config, "patch_size", 2)),
        depths=tuple(int(item) for item in _config_get(config, "depths", (2, 2, 4, 2))),
        dims=tuple(int(item) for item in _config_get(config, "dims", (64, 128, 256, 512))),
        mlp_ratio=float(_config_get(config, "mlp_ratio", 4.0)),
        drop_path_rate=float(_config_get(config, "drop_path_rate", 0.1)),
        aux_feature_dim=len(tuple(_config_get(config, "auxiliary_feature_names", ()))) if bool(_config_get(config, "auxiliary_features", True)) else 0,
    )


def _build_modules(
    input_channels: int,
    hidden_dim: int,
    embedding_dim: int,
    dropout: float,
    patch_size: int = 2,
    depths: tuple[int, ...] = (2, 2, 4, 2),
    dims: tuple[int, ...] = (64, 128, 256, 512),
    mlp_ratio: float = 4.0,
    drop_path_rate: float = 0.10,
    aux_feature_dim: int = 0,
) -> tuple[Any, Any]:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    class LayerNorm2d(nn.Module):
        def __init__(self, channels: int) -> None:
            super().__init__()
            self.norm = nn.LayerNorm(channels)

        def forward(self, x: Any) -> Any:
            x_nhwc = x.permute(0, 2, 3, 1)
            x_nhwc = self.norm(x_nhwc)
            return x_nhwc.permute(0, 3, 1, 2).contiguous()

    class TorchSS2D(nn.Module):
        """Native-PyTorch SS2D-style row/column selective scan.

        This is not the CUDA selective-scan kernel. It keeps the VMamba idea
        operational in Isomera by learning four cross-scan routes over a 2D
        tensor: left-to-right, right-to-left, top-to-bottom and bottom-to-top.
        """

        def __init__(self, dim: int) -> None:
            super().__init__()
            self.in_proj = nn.Conv2d(dim, dim * 2, kernel_size=1)
            self.dwconv = nn.Conv2d(dim, dim, kernel_size=3, padding=1, groups=dim)
            self.route_gate = nn.Conv2d(dim, 4, kernel_size=1)
            self.route_scale = nn.Parameter(torch.ones(4, dim, 1, 1))
            self.out_proj = nn.Conv2d(dim, dim, kernel_size=1)

        @staticmethod
        def _scan_average(x: Any, dim: int) -> Any:
            scanned = torch.cumsum(x, dim=dim)
            if dim == 3:
                denom = torch.arange(1, x.shape[3] + 1, device=x.device, dtype=x.dtype).view(1, 1, 1, -1)
            else:
                denom = torch.arange(1, x.shape[2] + 1, device=x.device, dtype=x.dtype).view(1, 1, -1, 1)
            return scanned / denom

        def forward(self, x: Any) -> Any:
            x = x.contiguous()
            projected = self.in_proj(x)
            u, z = projected.chunk(2, dim=1)
            u = F.silu(self.dwconv(u.contiguous()))
            left_right = self._scan_average(u, dim=3)
            right_left = torch.flip(self._scan_average(torch.flip(u, dims=[3]), dim=3), dims=[3])
            top_bottom = self._scan_average(u, dim=2)
            bottom_top = torch.flip(self._scan_average(torch.flip(u, dims=[2]), dim=2), dims=[2])
            routes = torch.stack([left_right, right_left, top_bottom, bottom_top], dim=1)
            routes = routes * self.route_scale.unsqueeze(0)
            gate = torch.softmax(self.route_gate(u), dim=1).unsqueeze(2)
            mixed = (gate * routes).sum(dim=1).contiguous()
            return self.out_proj((mixed * F.silu(z)).contiguous())

    class VSSStyleBlock(nn.Module):
        def __init__(self, dim: int, drop_path: float) -> None:
            super().__init__()
            mlp_hidden = max(int(dim * float(mlp_ratio)), dim)
            self.norm1 = LayerNorm2d(dim)
            self.ss2d = TorchSS2D(dim)
            self.norm2 = LayerNorm2d(dim)
            self.mlp = nn.Sequential(
                nn.Conv2d(dim, mlp_hidden, kernel_size=1),
                nn.GELU(),
                nn.Dropout(float(dropout)),
                nn.Conv2d(mlp_hidden, dim, kernel_size=1),
            )
            self.drop_path = float(drop_path)

        def forward(self, x: Any) -> Any:
            x = x + _drop_path(self.ss2d(self.norm1(x)), self.drop_path, self.training)
            x = x + _drop_path(self.mlp(self.norm2(x)), self.drop_path, self.training)
            return x

    class PatchEmbed(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            first_dim = int(dims[0])
            self.proj = nn.Sequential(
                nn.Conv2d(input_channels, first_dim, kernel_size=patch_size, stride=patch_size),
                LayerNorm2d(first_dim),
            )

        def forward(self, x: Any) -> Any:
            return self.proj(x.contiguous())

    class Downsample(nn.Module):
        def __init__(self, in_dim: int, out_dim: int) -> None:
            super().__init__()
            self.channel_proj = nn.Sequential(LayerNorm2d(in_dim), nn.Conv2d(in_dim, out_dim, kernel_size=1))
            self.proj = nn.Sequential(
                LayerNorm2d(in_dim),
                nn.Conv2d(in_dim, out_dim, kernel_size=2, stride=2),
            )

        def forward(self, x: Any) -> Any:
            if x.shape[-1] < 2 or x.shape[-2] < 2:
                return self.channel_proj(x)
            return self.proj(x)

    class TensorEncoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.patch_embed = PatchEmbed()
            total_depth = max(sum(depths), 1)
            dpr = torch.linspace(0, float(drop_path_rate), total_depth).tolist()
            dpr_idx = 0
            stages: list[nn.Module] = []
            for stage_idx, (dim, depth) in enumerate(zip(dims, depths)):
                blocks = [
                    VSSStyleBlock(int(dim), float(dpr[dpr_idx + block_idx]))
                    for block_idx in range(int(depth))
                ]
                dpr_idx += int(depth)
                stages.append(nn.Sequential(*blocks))
                if stage_idx < len(dims) - 1:
                    stages.append(Downsample(int(dim), int(dims[stage_idx + 1])))
            self.stages = nn.Sequential(*stages)
            self.norm = LayerNorm2d(int(dims[-1]))
            self.proj = nn.Sequential(
                nn.Linear(int(dims[-1]), embedding_dim),
                nn.GELU(),
                nn.Dropout(float(dropout)),
            )

        def forward(self, x: Any) -> Any:
            feat = self.patch_embed(x)
            feat = self.stages(feat)
            feat = self.norm(feat)
            pooled = F.adaptive_avg_pool2d(feat.contiguous(), 1).flatten(1)
            return self.proj(pooled)

    class PairHead(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(embedding_dim * 4 + int(aux_feature_dim), hidden_dim),
                nn.GELU(),
                nn.Dropout(float(dropout)),
                nn.Linear(hidden_dim, 1),
            )

        def forward(self, left: Any, right: Any, aux: Any | None = None) -> Any:
            features = torch.cat([left, right, torch.abs(left - right), left * right], dim=1)
            if int(aux_feature_dim) > 0:
                if aux is None:
                    aux = left.new_zeros((left.shape[0], int(aux_feature_dim)))
                features = torch.cat([features, aux.to(features.device)], dim=1)
            return self.net(features).squeeze(1)

    return TensorEncoder(), PairHead()


@dataclass
class VMambaTrainablePickle:
    config: VMambaTrainableConfig
    encoder_state: dict[str, Any]
    head_state: dict[str, Any]
    training_summary: dict[str, Any] = field(default_factory=dict)

    def _modules(self) -> tuple[Any, Any, Any]:
        import torch

        device_summary = resolve_torch_device(str(_config_get(self.config, "device", "auto")))
        device = torch.device(str(device_summary["resolved_device"]))
        encoder, head = _build_modules_from_config(self.config)
        encoder.load_state_dict(self.encoder_state)
        head.load_state_dict(self.head_state)
        encoder.to(device)
        head.to(device)
        encoder.eval()
        head.eval()
        return torch, encoder, head

    def score_pair(self, graph: nx.DiGraph, node_a: str, node_b: str) -> float:
        torch, encoder, head = self._modules()
        device = next(encoder.parameters()).device
        with torch.no_grad():
            left = graph_context_tensor(graph, node_a, config=self.config).unsqueeze(0).to(device)
            right = graph_context_tensor(graph, node_b, config=self.config).unsqueeze(0).to(device)
            aux = pair_auxiliary_tensor(graph, node_a, node_b, config=self.config).unsqueeze(0).to(device)
            logit = head(encoder(left), encoder(right), aux)
            return float(torch.sigmoid(logit).item())

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        torch, encoder, head = self._modules()
        device = next(encoder.parameters()).device
        nodes = canonical_node_order(_scope_nodes(graph, tuple(_config_get(self.config, "scope_layers", ("SPEC",)))))
        predicted: list[tuple[str, str]] = []
        try:
            chunk_size = max(
                int(os.environ.get("ISOMERA_VMAMBA_T_BATCH_SIZE") or _config_get(self.config, "inference_batch_size", 4096)),
                1,
            )
        except (TypeError, ValueError):
            chunk_size = 4096
        try:
            encoder_batch_size = max(
                int(os.environ.get("ISOMERA_VMAMBA_T_ENCODER_BATCH_SIZE") or _config_get(self.config, "encoder_batch_size", 64)),
                1,
            )
        except (TypeError, ValueError):
            encoder_batch_size = 64
        with torch.no_grad():
            tensor_cache = {
                node: graph_context_tensor(graph, node, config=self.config).unsqueeze(0)
                for node in nodes
            }
            emb_cache: dict[str, Any] = {}
            for start in range(0, len(nodes), encoder_batch_size):
                node_chunk = nodes[start : start + encoder_batch_size]
                tensor_batch = torch.cat([tensor_cache[node] for node in node_chunk], dim=0).to(device)
                embeddings = encoder(tensor_batch)
                for node, embedding in zip(node_chunk, embeddings):
                    emb_cache[node] = embedding.unsqueeze(0)
            candidate_pairs = list(combinations(nodes, 2))
            for start in range(0, len(candidate_pairs), chunk_size):
                chunk = candidate_pairs[start : start + chunk_size]
                left = torch.cat([emb_cache[node_a] for node_a, _ in chunk], dim=0)
                right = torch.cat([emb_cache[node_b] for _, node_b in chunk], dim=0)
                aux = torch.cat(
                    [
                        pair_auxiliary_tensor(graph, node_a, node_b, config=self.config).unsqueeze(0)
                        for node_a, node_b in chunk
                    ],
                    dim=0,
                ).to(device)
                scores = torch.sigmoid(head(left, right, aux))
                mask = (scores >= float(_config_get(self.config, "threshold", 0.5))).detach().cpu().tolist()
                predicted.extend(canonical_pair(node_a, node_b) for (node_a, node_b), keep in zip(chunk, mask) if bool(keep))
        return sorted(set(predicted))


def _negative_pair_score(graph: nx.DiGraph, node_a: str, node_b: str, *, config: VMambaTrainableConfig) -> float:
    mesh_cfg = VMambaMeshConfig(
        scope_layers=tuple(_config_get(config, "scope_layers", ("SPEC",))),
        canon_sort=True,
        diag_fp=True,
        mesh_ss2d=True,
        hier_init=True,
        sparse_gate=True,
        threshold=float(_config_get(config, "threshold", 0.5)),
        negative_ratio=int(_config_get(config, "negative_ratio", 4)),
        seed=int(_config_get(config, "seed", 42)),
        resolution=int(_config_get(config, "resolution", 32)),
    )
    features = pair_features(graph, node_a, node_b, config=mesh_cfg)
    feature_names = tuple(_config_get(config, "auxiliary_feature_names", tuple(DEFAULT_FEATURE_WEIGHTS)))
    if not feature_names:
        feature_names = tuple(DEFAULT_FEATURE_WEIGHTS)
    return sum(float(features.get(name, 0.0)) for name in feature_names) / max(len(feature_names), 1)


def _load_hard_negative_manifest(config: VMambaTrainableConfig) -> dict[str, Any]:
    manifest_path = str(_config_get(config, "hard_negative_manifest_path", "") or "").strip()
    if not manifest_path:
        return {}
    path = Path(manifest_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        return {"_load_error": f"manifest_not_found: {path}"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {"_load_error": f"{type(exc).__name__}: {exc}", "_path": str(path)}


def _manifest_pairs_for_graph(
    manifest: dict[str, Any],
    graph: nx.DiGraph,
    *,
    config: VMambaTrainableConfig,
) -> dict[tuple[str, str], dict[str, Any]]:
    if not manifest or manifest.get("_load_error"):
        return {}
    benchmark = str(graph.graph.get("benchmark") or graph.graph.get("name") or "")
    scenario = str(graph.graph.get("scenario") or graph.graph.get("scenario_name") or graph.graph.get("name") or "")
    scope_key = ",".join(tuple(_config_get(config, "scope_layers", ("SPEC",))))
    entries = manifest.get("entries", [])
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in entries:
        if benchmark and str(entry.get("benchmark", "")) not in {"", benchmark}:
            continue
        if scenario and str(entry.get("scenario", "")) not in {"", scenario}:
            continue
        if str(entry.get("scope_layers", "")) not in {"", scope_key}:
            continue
        pair = canonical_pair(str(entry.get("node_a", "")), str(entry.get("node_b", "")))
        if pair[0] and pair[1]:
            selected[pair] = dict(entry)
    return selected


def _dataset(
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    *,
    config: VMambaTrainableConfig,
) -> tuple[list[tuple[str, str, float]], dict[str, Any]]:
    nodes = canonical_node_order(_scope_nodes(graph, config.scope_layers))
    positive_set = {
        canonical_pair(a, b)
        for a, b in positive_pairs
        if a in nodes and b in nodes
    }
    all_pairs = [canonical_pair(a, b) for a, b in combinations(nodes, 2)]
    negatives = [pair for pair in all_pairs if pair not in positive_set]
    rng = random.Random(int(config.seed))
    rng.shuffle(negatives)
    hard_negative_mining = bool(_config_get(config, "hard_negative_mining", False))
    strategy = str(_config_get(config, "hard_negative_strategy", "structural_similarity"))
    manifest = _load_hard_negative_manifest(config) if "llm_manifest" in strategy else {}
    manifest_pairs = _manifest_pairs_for_graph(manifest, graph, config=config)
    negative_scores: dict[tuple[str, str], float] = {}
    if hard_negative_mining:
        negative_scores = {
            pair: _negative_pair_score(graph, pair[0], pair[1], config=config)
            for pair in negatives
        }
        if "llm_manifest" in strategy:
            negatives.sort(
                key=lambda pair: (
                    1 if pair in manifest_pairs else 0,
                    float(manifest_pairs.get(pair, {}).get("llm_priority", 0.0)),
                    negative_scores.get(pair, 0.0),
                    pair[0],
                    pair[1],
                ),
                reverse=True,
            )
        else:
            negatives.sort(key=lambda pair: (negative_scores.get(pair, 0.0), pair[0], pair[1]), reverse=True)
    negative_limit = min(len(negatives), max(len(positive_set) * int(config.negative_ratio), 1))
    selected_negatives = negatives[:negative_limit]
    rows = [(a, b, 1.0) for a, b in sorted(positive_set)]
    rows.extend((a, b, 0.0) for a, b in selected_negatives)
    rng.shuffle(rows)
    summary: dict[str, Any] = {
        "negative_sampling": "hard_negative_mining" if hard_negative_mining else "random_negative_sampling",
        "hard_negative_mining": hard_negative_mining,
        "hard_negative_strategy": strategy,
        "hard_negative_agent": str(_config_get(config, "hard_negative_agent", "isomera_structural_hard_negative_miner")),
        "hard_negative_manifest_path": str(_config_get(config, "hard_negative_manifest_path", "")),
        "hard_negative_manifest_id": str(_config_get(config, "hard_negative_manifest_id", "")),
        "hard_negative_manifest_error": manifest.get("_load_error") if manifest else None,
        "hard_negative_manifest_agent": manifest.get("agent", {}).get("name") if manifest else None,
        "hard_negative_manifest_model": manifest.get("agent", {}).get("model") if manifest else None,
        "hard_negative_manifest_pairs_available": len(manifest_pairs),
        "positive_pairs": len(positive_set),
        "candidate_negatives": len(negatives),
        "selected_negatives": len(selected_negatives),
        "negative_ratio": int(_config_get(config, "negative_ratio", 4)),
        "selected_negative_preview": [
            {
                "node_a": pair[0],
                "node_b": pair[1],
                "hardness_score": round(float(negative_scores.get(pair, 0.0)), 6) if hard_negative_mining else None,
                "llm_suggested": pair in manifest_pairs,
                "llm_priority": manifest_pairs.get(pair, {}).get("llm_priority") if pair in manifest_pairs else None,
                "llm_reason": manifest_pairs.get(pair, {}).get("reason") if pair in manifest_pairs else None,
            }
            for pair in selected_negatives[:50]
        ],
    }
    return rows, summary


def _split_rows(rows: list[tuple[str, str, float]], *, train_ratio: float, seed: int) -> tuple[list[tuple[str, str, float]], list[tuple[str, str, float]]]:
    rng = random.Random(seed)
    positives = [row for row in rows if row[2] >= 0.5]
    negatives = [row for row in rows if row[2] < 0.5]
    rng.shuffle(positives)
    rng.shuffle(negatives)

    def split_bucket(bucket: list[tuple[str, str, float]]) -> tuple[list[tuple[str, str, float]], list[tuple[str, str, float]]]:
        if len(bucket) <= 1:
            return list(bucket), []
        split = int(len(bucket) * train_ratio)
        split = min(max(1, split), len(bucket) - 1)
        return bucket[:split], bucket[split:]

    train_pos, val_pos = split_bucket(positives)
    train_neg, val_neg = split_bucket(negatives)
    train_rows = [*train_pos, *train_neg]
    val_rows = [*val_pos, *val_neg]
    if not val_rows and len(train_rows) > 1:
        val_rows = [train_rows.pop()]
    rng.shuffle(train_rows)
    rng.shuffle(val_rows)
    return train_rows, val_rows


def _counts(rows: list[tuple[str, str, float]]) -> dict[str, int]:
    positives = sum(1 for _, _, label in rows if label >= 0.5)
    return {"rows": len(rows), "positive": positives, "negative": len(rows) - positives}


def _evaluate_scores(scores: list[tuple[float, float]], threshold: float) -> dict[str, float]:
    tp = fp = fn = tn = 0
    for score, label in scores:
        pred = score >= threshold
        target = label >= 0.5
        if pred and target:
            tp += 1
        elif pred and not target:
            fp += 1
        elif not pred and target:
            fn += 1
        else:
            tn += 1
    jaccard = tp / max(tp + fp + fn, 1)
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / max(tp + fp + fn + tn, 1)
    return {
        "threshold": float(threshold),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "jaccard": jaccard,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def _select_threshold(evaluations: list[dict[str, float]], config: VMambaTrainableConfig) -> tuple[dict[str, float], dict[str, Any]]:
    policy = str(_config_get(config, "threshold_policy", "jaccard") or "jaccard").lower()
    precision_floor = max(float(_config_get(config, "threshold_precision_floor", 0.0) or 0.0), 0.0)
    candidates = list(evaluations)
    selected_pool = candidates
    fallback = False
    if policy in {"precision_guard", "precision_floor", "jaccard_precision_guard"} and precision_floor > 0:
        eligible = [item for item in candidates if float(item.get("precision", 0.0)) >= precision_floor]
        if eligible:
            selected_pool = eligible
        else:
            fallback = True
    if policy in {"f1", "f1_score"}:
        best = max(selected_pool, key=lambda item: (float(item.get("f1", 0.0)), float(item.get("jaccard", 0.0)), float(item.get("precision", 0.0))))
    elif policy in {"precision", "precision_first"}:
        best = max(selected_pool, key=lambda item: (float(item.get("precision", 0.0)), float(item.get("jaccard", 0.0)), float(item.get("recall", 0.0))))
    else:
        best = max(selected_pool, key=lambda item: (float(item.get("jaccard", 0.0)), float(item.get("precision", 0.0)), float(item.get("recall", 0.0))))
    return best, {
        "policy": policy,
        "precision_floor": precision_floor,
        "eligible_thresholds": len(selected_pool),
        "fallback_to_all_thresholds": fallback,
    }


def _loss_function(config: VMambaTrainableConfig, train_rows: list[tuple[str, str, float]], torch: Any, nn: Any) -> tuple[Any, dict[str, Any]]:
    positives = sum(1 for _, _, label in train_rows if label >= 0.5)
    negatives = max(len(train_rows) - positives, 0)
    loss_name = str(config.loss_name).lower()
    if loss_name in {"weighted_bce", "weighted_bce_with_logits"}:
        pos_weight = float(negatives / positives) if positives else 1.0
        return nn.BCEWithLogitsLoss(pos_weight=torch.tensor([pos_weight], dtype=torch.float32)), {
            "loss_name": "torch.nn.BCEWithLogitsLoss(pos_weight)",
            "pos_weight": pos_weight,
        }
    if loss_name in {"focal", "focal_loss"}:
        alpha = 0.25 if positives and negatives else 0.5
        gamma = 2.0

        def focal_loss(logits: Any, target: Any) -> Any:
            bce = nn.functional.binary_cross_entropy_with_logits(logits, target, reduction="none")
            probability = torch.sigmoid(logits)
            pt = probability * target + (1 - probability) * (1 - target)
            alpha_factor = alpha * target + (1 - alpha) * (1 - target)
            return (alpha_factor * ((1 - pt) ** gamma) * bce).mean()

        return focal_loss, {
            "loss_name": "custom sigmoid focal loss",
            "alpha": alpha,
            "gamma": gamma,
            "pos_weight": None,
        }
    return nn.BCEWithLogitsLoss(), {"loss_name": "torch.nn.BCEWithLogitsLoss", "pos_weight": None}


def fit_vmamba_trainable_model(
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    *,
    config: VMambaTrainableConfig,
) -> VMambaTrainablePickle:
    import torch
    import torch.nn as nn

    random.seed(int(config.seed))
    torch.manual_seed(int(config.seed))
    device_summary = resolve_torch_device(str(_config_get(config, "device", "auto")))
    device = torch.device(str(device_summary["resolved_device"]))
    rows, dataset_sampling_summary = _dataset(graph, positive_pairs, config=config)
    if not rows:
        raise ValueError("VMamba trainable dataset is empty.")
    train_ratio = min(max(float(config.train_ratio), 0.1), 0.95)
    train_rows, val_rows = _split_rows(rows, train_ratio=train_ratio, seed=int(config.seed))
    encoder, head = _build_modules_from_config(config)
    encoder.to(device)
    head.to(device)
    params = list(encoder.parameters()) + list(head.parameters())
    optimizer_cls = torch.optim.AdamW if str(config.optimizer_name).lower() == "adamw" else torch.optim.Adam
    optimizer_kwargs = {"lr": float(config.learning_rate)}
    if optimizer_cls is torch.optim.AdamW:
        optimizer_kwargs["weight_decay"] = float(_config_get(config, "weight_decay", 0.05))
    optimizer = optimizer_cls(params, **optimizer_kwargs)
    criterion, loss_summary = _loss_function(config, train_rows, torch, nn)
    if hasattr(criterion, "to"):
        criterion = criterion.to(device)
    tensor_cache = {
        node: graph_context_tensor(graph, node, config=config).unsqueeze(0)
        for row in rows
        for node in (row[0], row[1])
    }

    def iter_batches(batch_rows: list[tuple[str, str, float]], batch_size: int) -> Any:
        for start in range(0, len(batch_rows), batch_size):
            yield batch_rows[start : start + batch_size]

    aux_cache = {
        canonical_pair(node_a, node_b): pair_auxiliary_tensor(graph, node_a, node_b, config=config).unsqueeze(0)
        for node_a, node_b, _ in rows
    }

    def batch_tensors(batch_rows: list[tuple[str, str, float]]) -> tuple[Any, Any, Any, Any]:
        left = torch.cat([tensor_cache[node_a] for node_a, _, _ in batch_rows], dim=0).to(device)
        right = torch.cat([tensor_cache[node_b] for _, node_b, _ in batch_rows], dim=0).to(device)
        aux = torch.cat([aux_cache[canonical_pair(node_a, node_b)] for node_a, node_b, _ in batch_rows], dim=0).to(device)
        target = torch.tensor([label for _, _, label in batch_rows], dtype=torch.float32, device=device)
        return left, right, aux, target

    batch_size = max(int(_config_get(config, "batch_size", 16)), 1)
    history: list[dict[str, float | int]] = []
    replay_history: list[dict[str, Any]] = []
    started = time.perf_counter()
    for epoch in range(int(config.epochs)):
        encoder.train()
        head.train()
        random.shuffle(train_rows)
        total_loss = 0.0
        correct = 0
        seen = 0
        for batch_rows in iter_batches(train_rows, batch_size):
            left, right, aux, target = batch_tensors(batch_rows)
            logit = head(encoder(left), encoder(right), aux)
            loss = criterion(logit, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            batch_len = len(batch_rows)
            total_loss += float(loss.item()) * batch_len
            preds = torch.sigmoid(logit) >= 0.5
            correct += int((preds == (target >= 0.5)).sum().item())
            seen += batch_len
        encoder.eval()
        head.eval()
        val_scores: list[tuple[float, float]] = []
        with torch.no_grad():
            for batch_rows in iter_batches(val_rows, batch_size):
                left, right, aux, target = batch_tensors(batch_rows)
                logits = head(encoder(left), encoder(right), aux)
                probabilities = torch.sigmoid(logits).detach().cpu().tolist()
                labels = target.detach().cpu().tolist()
                val_scores.extend((float(score), float(label)) for score, label in zip(probabilities, labels))
        val_eval = _evaluate_scores(val_scores, 0.5) if val_scores else {}
        history.append(
            {
                "epoch": epoch + 1,
                "train_loss": round(total_loss / max(seen, 1), 6),
                "train_accuracy": round(correct / max(seen, 1), 6),
                "val_jaccard_at_0_5": round(float(val_eval.get("jaccard", 0.0)), 6),
                "val_accuracy_at_0_5": round(float(val_eval.get("accuracy", 0.0)), 6),
            }
        )
    replay_rounds = max(int(_config_get(config, "false_positive_replay_rounds", 0) or 0), 0)
    replay_weight = max(int(_config_get(config, "false_positive_replay_weight", 2) or 2), 1)
    replay_epochs = max(int(_config_get(config, "false_positive_replay_epochs", 2) or 2), 1)
    replay_top_k = max(int(_config_get(config, "false_positive_replay_top_k", 0) or 0), 0)
    if replay_rounds:
        negative_rows = [row for row in rows if row[2] < 0.5]
        for replay_round in range(replay_rounds):
            encoder.eval()
            head.eval()
            scored_negatives: list[tuple[float, tuple[str, str, float]]] = []
            with torch.no_grad():
                for batch_rows in iter_batches(negative_rows, batch_size):
                    left, right, aux, _target = batch_tensors(batch_rows)
                    scores = torch.sigmoid(head(encoder(left), encoder(right), aux)).detach().cpu().tolist()
                    scored_negatives.extend((float(score), row) for score, row in zip(scores, batch_rows))
            scored_negatives.sort(key=lambda item: item[0], reverse=True)
            limit = replay_top_k or max(_counts(rows)["positive"] * 2, 1)
            selected_replay = [row for score, row in scored_negatives[: min(limit, len(scored_negatives))] if score >= 0.5]
            if not selected_replay:
                selected_replay = [row for _score, row in scored_negatives[: min(limit, len(scored_negatives))]]
            reinforced_rows = list(selected_replay) * replay_weight
            train_rows.extend(reinforced_rows)
            replay_history.append(
                {
                    "round": replay_round + 1,
                    "selected_pairs": len(selected_replay),
                    "reinforced_rows": len(reinforced_rows),
                    "max_negative_score": round(scored_negatives[0][0], 6) if scored_negatives else 0.0,
                    "min_selected_score": round(scored_negatives[min(len(selected_replay), len(scored_negatives)) - 1][0], 6) if selected_replay and scored_negatives else 0.0,
                    "preview": [
                        {"node_a": row[0], "node_b": row[1], "score": round(float(score), 6)}
                        for score, row in scored_negatives[:10]
                    ],
                }
            )
            for replay_epoch in range(replay_epochs):
                encoder.train()
                head.train()
                random.shuffle(train_rows)
                total_loss = 0.0
                correct = 0
                seen = 0
                for batch_rows in iter_batches(train_rows, batch_size):
                    left, right, aux, target = batch_tensors(batch_rows)
                    logit = head(encoder(left), encoder(right), aux)
                    loss = criterion(logit, target)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    batch_len = len(batch_rows)
                    total_loss += float(loss.item()) * batch_len
                    preds = torch.sigmoid(logit) >= 0.5
                    correct += int((preds == (target >= 0.5)).sum().item())
                    seen += batch_len
                history.append(
                    {
                        "epoch": int(config.epochs) + replay_round * replay_epochs + replay_epoch + 1,
                        "replay_round": replay_round + 1,
                        "train_loss": round(total_loss / max(seen, 1), 6),
                        "train_accuracy": round(correct / max(seen, 1), 6),
                        "val_jaccard_at_0_5": 0.0,
                        "val_accuracy_at_0_5": 0.0,
                    }
                )
    encoder.eval()
    head.eval()
    val_scores = []
    with torch.no_grad():
        for batch_rows in iter_batches((val_rows or train_rows), batch_size):
            left, right, aux, target = batch_tensors(batch_rows)
            logits = head(encoder(left), encoder(right), aux)
            probabilities = torch.sigmoid(logits).detach().cpu().tolist()
            labels = target.detach().cpu().tolist()
            val_scores.extend((float(score), float(label)) for score, label in zip(probabilities, labels))
    threshold_grid = [round(0.10 + idx * 0.025, 3) for idx in range(33)]
    evaluations = [_evaluate_scores(val_scores, threshold) for threshold in threshold_grid]
    best, threshold_summary = _select_threshold(evaluations, config)
    calibrated_config = VMambaTrainableConfig(
        **{
            **asdict(config),
            "threshold": float(best["threshold"]),
        }
    )
    model = VMambaTrainablePickle(
        config=calibrated_config,
        encoder_state={key: value.detach().cpu() for key, value in encoder.state_dict().items()},
        head_state={key: value.detach().cpu() for key, value in head.state_dict().items()},
    )
    model.training_summary = {
        "model_version": VMAMBA_TRAINABLE_MODEL_VERSION,
        "variant": calibrated_config.variant,
        "dataset": _counts(rows),
        "dataset_sampling": dataset_sampling_summary,
        "train": _counts(train_rows),
        "validation": _counts(val_rows),
        "selected_threshold": calibrated_config.threshold,
        "selected_metrics": best,
        "threshold_candidates": threshold_grid,
        "threshold_selection": threshold_summary,
        "history": history,
        "false_positive_replay": {
            "rounds": replay_rounds,
            "top_k": replay_top_k,
            "weight": replay_weight,
            "epochs_per_round": replay_epochs,
            "history": replay_history,
        },
        "loss": loss_summary,
        "device": device_summary,
        "architecture": {
            "architecture": _config_get(calibrated_config, "architecture", "vss_torch"),
            "preset": _config_get(calibrated_config, "preset", "custom"),
            "patch_size": _config_get(calibrated_config, "patch_size", 2),
            "depths": list(_config_get(calibrated_config, "depths", ())),
            "dims": list(_config_get(calibrated_config, "dims", ())),
            "mlp_ratio": _config_get(calibrated_config, "mlp_ratio", 4.0),
            "drop_path_rate": _config_get(calibrated_config, "drop_path_rate", 0.1),
            "forward_type": _config_get(calibrated_config, "forward_type", "v05"),
            "batch_size": _config_get(calibrated_config, "batch_size", batch_size),
            "inference_batch_size": _config_get(calibrated_config, "inference_batch_size", 4096),
            "encoder_batch_size": _config_get(calibrated_config, "encoder_batch_size", 64),
            "auxiliary_features": bool(_config_get(calibrated_config, "auxiliary_features", True)),
            "auxiliary_feature_names": list(_config_get(calibrated_config, "auxiliary_feature_names", ())),
        },
        "input_contract": {
            "pipeline": [
                "CanonSort context ordering",
                "six-channel lineage tensorization when VMamba-Mesh-T is selected",
                "patch embedding",
                "staged VSS-style blocks",
                "bidirectional row/column SS2D-style scans",
                "auditable pair-feature calibration vector",
                "global pooling",
                "pair head over left/right/absolute-difference/product features",
                "sigmoid score",
                "calibrated threshold",
            ],
            "channels": {
                channel: VMAMBA_CHANNEL_CONTRACT[channel]
                for channel in tuple(_config_get(calibrated_config, "channels", ()))
                if channel in VMAMBA_CHANNEL_CONTRACT
            },
        },
        "elapsed_seconds": round(time.perf_counter() - started, 6),
        "contract": "predict_pairs(graph)",
        "note": "Trainable VMamba-like VSS/SS2D-style tensor model implemented in native PyTorch; official CUDA/Triton kernels remain the external VMamba reference.",
    }
    if str(device) == "mps" and hasattr(torch, "mps"):
        torch.mps.synchronize()
        model.training_summary["elapsed_seconds"] = round(time.perf_counter() - started, 6)
    return model


def save_vmamba_trainable_artifact(
    *,
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    model_path: Path,
    metadata_path: Path,
    config: VMambaTrainableConfig,
    benchmark_name: str,
    scenario_name: str,
    source_graph_path: Path,
    source_labels_path: Path,
) -> dict[str, Any]:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    graph.graph["benchmark"] = benchmark_name
    graph.graph["scenario"] = scenario_name
    graph.graph["scenario_name"] = scenario_name
    started = time.perf_counter()
    model = fit_vmamba_trainable_model(graph, positive_pairs, config=config)
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    elapsed = time.perf_counter() - started
    family = "VMamba-Mesh-T" if config.variant == "vmamba_mesh_t" else "VMamba-T"
    metadata = {
        "model_name": model_path.stem,
        "model_family": family,
        "model_family_name": family,
        "model_version": VMAMBA_TRAINABLE_MODEL_VERSION,
        "pickle_module": "core.algorithms.vmamba_trainable",
        "pickle_path": str(model_path),
        "benchmark_name": benchmark_name,
        "scenarios": [scenario_name],
        "source_scenarios": [scenario_name],
        "source_graph_path": str(source_graph_path),
        "source_labels_path": str(source_labels_path),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_seconds": elapsed,
        "config": asdict(model.config),
        "training_summary": model.training_summary,
        "benchmark_contract": {
            "input": "networkx.DiGraph",
            "output": "list[tuple[str, str]] predicted duplicate pairs",
            "comparison_metrics": ["jaccard", "sf_jaccard", "accuracy", "ET"],
            "neural_input": "C x R x R lineage tensor built before the VMamba-style backbone",
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
    return metadata


def load_vmamba_trainable_artifact(model_path: Path) -> VMambaTrainablePickle:
    """Load a trainable VMamba pickle with a typed return value."""
    with Path(model_path).open("rb") as handle:
        model = pickle.load(handle)
    if not isinstance(model, VMambaTrainablePickle):
        raise TypeError(f"Expected VMambaTrainablePickle, got {type(model).__name__}")
    return model


def explain_vmamba_trainable_pair(
    *,
    model_path: Path,
    graph: nx.DiGraph,
    node_a: str,
    node_b: str,
) -> dict[str, Any]:
    """Return an auditable input-gradient explanation for one pair.

    The explanation is intentionally scoped to observable model internals:
    input tensors, logit, sigmoid score, calibrated threshold, channel-level
    saliency and the resolved device. It does not attempt to expose hidden
    reasoning; it records what the trained PyTorch modules actually computed.
    """
    import torch

    model = load_vmamba_trainable_artifact(Path(model_path))
    torch_mod, encoder, head = model._modules()
    device = next(encoder.parameters()).device
    left = graph_context_tensor(graph, node_a, config=model.config).unsqueeze(0).to(device)
    right = graph_context_tensor(graph, node_b, config=model.config).unsqueeze(0).to(device)
    aux = pair_auxiliary_tensor(graph, node_a, node_b, config=model.config).unsqueeze(0).to(device)
    left.requires_grad_(True)
    right.requires_grad_(True)

    encoder.zero_grad(set_to_none=True)
    head.zero_grad(set_to_none=True)
    logit = head(encoder(left), encoder(right), aux)
    score = torch.sigmoid(logit)
    score.backward(torch.ones_like(score))

    left_tensor = left.detach().cpu().squeeze(0)
    right_tensor = right.detach().cpu().squeeze(0)
    left_saliency = (left.grad.detach().abs().cpu().squeeze(0) * left_tensor.abs()).float()
    right_saliency = (right.grad.detach().abs().cpu().squeeze(0) * right_tensor.abs()).float()
    saliency = left_saliency + right_saliency
    total_saliency = float(saliency.sum().item())
    channel_names = tuple(_config_get(model.config, "channels", ("C0", "C1")))
    channel_rows = []
    for idx, channel in enumerate(channel_names):
        raw_value = float(saliency[idx].sum().item()) if idx < saliency.shape[0] else 0.0
        channel_rows.append(
            {
                "channel": str(channel),
                "name": VMAMBA_CHANNEL_CONTRACT.get(str(channel), {}).get("name", str(channel)),
                "role": VMAMBA_CHANNEL_CONTRACT.get(str(channel), {}).get("role", ""),
                "saliency": raw_value,
                "saliency_share": raw_value / total_saliency if total_saliency > 0 else 0.0,
            }
        )

    threshold = float(_config_get(model.config, "threshold", 0.5))
    score_value = float(score.detach().cpu().item())
    return {
        "model_path": str(model_path),
        "variant": str(_config_get(model.config, "variant", "")),
        "channels": list(channel_names),
        "config": asdict(model.config),
        "training_summary": dict(model.training_summary or {}),
        "resolved_device": str(device),
        "node_a": str(node_a),
        "node_b": str(node_b),
        "logit": float(logit.detach().cpu().item()),
        "score": score_value,
        "threshold": threshold,
        "decision": "duplicate" if score_value >= threshold else "not_duplicate",
        "left_tensor": left_tensor.numpy(),
        "right_tensor": right_tensor.numpy(),
        "left_saliency": left_saliency.numpy(),
        "right_saliency": right_saliency.numpy(),
        "saliency": saliency.numpy(),
        "channel_saliency": channel_rows,
    }


__all__ = [
    "VMAMBA_CHANNEL_CONTRACT",
    "VMAMBA_TRAINABLE_MODEL_VERSION",
    "VMambaTrainableConfig",
    "VMambaTrainablePickle",
    "explain_vmamba_trainable_pair",
    "fit_vmamba_trainable_model",
    "graph_context_tensor",
    "load_vmamba_trainable_artifact",
    "load_positive_pairs",
    "pair_auxiliary_tensor",
    "resolve_torch_device",
    "save_vmamba_trainable_artifact",
]
