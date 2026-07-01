"""Training helpers for benchmark-specific GNN pickle artifacts."""
from __future__ import annotations

import json
import csv
import os
import pickle
import random
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import networkx as nx

from core.lineage import normalize_lineage_direction


TRAINING_OPTIMIZER_OPTIONS: dict[str, dict[str, str]] = {
    "adam": {
        "label": "Adaptive gradient optimizer (torch.optim.Adam)",
        "technical_name": "torch.optim.Adam",
        "formula": "m_t = beta_1 m_{t-1} + (1 - beta_1) g_t; v_t = beta_2 v_{t-1} + (1 - beta_2) g_t^2",
        "description": "Default optimizer for the GNN. It adapts the learning rate per parameter using first and second gradient moments.",
    },
    "adamw": {
        "label": "Adam with decoupled weight decay (torch.optim.AdamW)",
        "technical_name": "torch.optim.AdamW",
        "formula": "theta_t = theta_{t-1} - eta (AdamGradient + lambda theta_{t-1})",
        "description": "Adam variant with decoupled weight decay. Useful when later experiments add explicit regularization.",
    },
    "sgd": {
        "label": "Stochastic gradient descent (torch.optim.SGD)",
        "technical_name": "torch.optim.SGD",
        "formula": "theta_t = theta_{t-1} - eta * grad_theta L",
        "description": "Simple gradient descent baseline. It is slower but useful as a methodological control.",
    },
}


TRAINING_LOSS_OPTIONS: dict[str, dict[str, str]] = {
    "bce_with_logits": {
        "label": "Binary cross entropy on logits (torch.nn.BCEWithLogitsLoss)",
        "technical_name": "torch.nn.BCEWithLogitsLoss",
        "formula": "L = -[y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))]",
        "description": "Default binary classification loss. It receives raw logits and applies the sigmoid internally in a numerically stable way.",
    },
    "weighted_bce_with_logits": {
        "label": "Weighted binary cross entropy (torch.nn.BCEWithLogitsLoss(pos_weight))",
        "technical_name": "torch.nn.BCEWithLogitsLoss(pos_weight)",
        "formula": "L = -[pos_weight * y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))]",
        "description": "Same BCE loss, but positive duplicate pairs receive a larger weight when the dataset has many more negatives.",
    },
    "focal_loss": {
        "label": "Focal loss for rare duplicates (custom sigmoid focal loss)",
        "technical_name": "custom sigmoid focal loss",
        "formula": "FL(p_t) = -alpha * (1 - p_t)^gamma * log(p_t)",
        "description": "Focuses training on hard examples by down-weighting easy negatives. Useful when almost every pair is non-duplicate.",
    },
}


TRAINING_BALANCE_OPTIONS: dict[str, dict[str, str]] = {
    "class_weighted_loss": {
        "label": "Weight duplicate class in the loss (torch.nn.BCEWithLogitsLoss(pos_weight))",
        "technical_name": "torch.nn.BCEWithLogitsLoss(pos_weight=N_negative/N_positive)",
        "formula": "pos_weight = N_negative / N_positive",
        "description": "Recommended default for article-grade training. It keeps the supervised dataset intact and increases the penalty for missing rare duplicate pairs.",
    },
    "negative_sampling": {
        "label": "Sample negatives by ratio (negative_sampling)",
        "technical_name": "negative_sampling with negative_ratio",
        "formula": "N_negative_sampled = N_positive * negative_ratio",
        "description": "Legacy-compatible path. Positives come from curated labels and negatives are sampled from non-labeled graph pairs.",
    },
    "none_real_distribution": {
        "label": "Use real distribution without balancing (no sampler/no class weight)",
        "technical_name": "no balancing",
        "formula": "D_train = D_train_original",
        "description": "Keeps the imbalanced distribution exactly as produced by the supervised table. Useful as a baseline, but can hide duplicate failures behind high accuracy.",
    },
    "undersample_negatives": {
        "label": "Reduce non-duplicates in training (random undersampling)",
        "technical_name": "random undersampling of target=0",
        "formula": "N_negative_kept <= N_positive * negative_ratio",
        "description": "Keeps all positives and randomly reduces negatives. Faster, but may discard useful negative diversity.",
    },
    "oversample_positives": {
        "label": "Repeat duplicate pairs in training (random oversampling)",
        "technical_name": "random oversampling of target=1",
        "formula": "N_positive_repeated ~= N_negative",
        "description": "Duplicates positive rows so the model sees rare duplicate evidence more often. Can overfit if positives are too few.",
    },
    "balanced_batch_sampler": {
        "label": "Balanced training batches (balanced batch sampler)",
        "technical_name": "balanced positive/negative epoch sampler",
        "formula": "batch ~= 50% target=1 + 50% target=0",
        "description": "Approximates balanced batches by oversampling positives before each epoch. This stabilizes gradients in highly imbalanced training.",
    },
    "hard_negative_mining": {
        "label": "Prefer difficult non-duplicates (hard negative mining)",
        "technical_name": "structural hard-negative sampler",
        "formula": "score = |nodes_a - nodes_b| + |edges_a - edges_b|",
        "description": "Keeps negatives whose subgraphs have similar size/edge profiles to positives. These are harder examples than random non-duplicates.",
    },
}


class _GraphBatch(SimpleNamespace):
    def to(self, device: Any) -> "_GraphBatch":
        payload = _GraphBatch(
            x=self.x.to(device),
            edge_index=self.edge_index.to(device),
            num_nodes=self.num_nodes,
        )
        if hasattr(self, "batch"):
            payload.batch = self.batch.to(device)
        return payload


@dataclass(frozen=True)
class ScenarioTrainingSpec:
    scenario_name: str
    graph_path: Path
    labels_path: Path
    supervised_labels_path: Path | None = None


def _resolve_torch() -> tuple[Any, Any, Any]:
    import torch
    import torch.nn as nn

    from core.algorithms.gnn_model import PairClassifier, SubgraphGNN

    return torch, nn, (SubgraphGNN, PairClassifier)


def resolve_gnn_torch_device(torch: Any, requested: str | None = None) -> tuple[Any, dict[str, Any]]:
    requested_device = str(requested or os.environ.get("ISOMERA_GNN_DEVICE") or "auto").lower()
    accelerator_enabled = os.environ.get("ISOMERA_ENABLE_ACCELERATOR") == "1"
    summary: dict[str, Any] = {
        "requested_device": requested_device,
        "accelerator_enabled": accelerator_enabled,
        "resolved_device": "cpu",
        "torch_version": getattr(torch, "__version__", "unknown"),
        "cuda_available": bool(torch.cuda.is_available()),
        "mps_built": False,
        "mps_available": False,
        "mps_device_count": None,
        "fallback_reason": None,
    }
    mps_backend = getattr(torch.backends, "mps", None)
    if mps_backend is not None:
        summary["mps_built"] = bool(mps_backend.is_built())
        summary["mps_available"] = bool(mps_backend.is_available())
    if hasattr(torch, "mps"):
        try:
            summary["mps_device_count"] = int(torch.mps.device_count())
        except Exception as exc:  # noqa: BLE001
            summary["mps_device_count"] = None
            summary["fallback_reason"] = f"mps_device_count_error: {type(exc).__name__}: {exc}"

    if requested_device == "cpu":
        return torch.device("cpu"), summary
    if not accelerator_enabled:
        summary["fallback_reason"] = "ISOMERA_ENABLE_ACCELERATOR is not enabled"
        return torch.device("cpu"), summary
    if requested_device in {"cuda", "auto"} and torch.cuda.is_available():
        summary["resolved_device"] = "cuda"
        return torch.device("cuda"), summary
    if requested_device in {"mps", "auto"} and bool(summary["mps_available"]):
        try:
            probe = torch.ones(1, device="mps")
            del probe
            summary["resolved_device"] = "mps"
            return torch.device("mps"), summary
        except Exception as exc:  # noqa: BLE001
            summary["fallback_reason"] = f"{type(exc).__name__}: {exc}"
            return torch.device("cpu"), summary
    if requested_device not in {"auto", "cpu", "cuda", "mps"}:
        summary["fallback_reason"] = f"unknown requested device: {requested_device}"
    elif requested_device == "mps":
        summary["fallback_reason"] = "MPS requested but not available"
    elif requested_device == "cuda":
        summary["fallback_reason"] = "CUDA requested but not available"
    else:
        summary["fallback_reason"] = "no accelerator backend available"
    return torch.device("cpu"), summary


def _resolve_torch_device(torch: Any) -> Any:
    device, _ = resolve_gnn_torch_device(torch)
    return device


def extract_subgraphs(graph: nx.DiGraph) -> dict[str, nx.DiGraph]:
    subgraphs: dict[str, nx.DiGraph] = {}
    for node in graph.nodes:
        upper = str(node).upper()
        if "SPEC" in upper:
            context_nodes = set(nx.ancestors(graph, node)) | {node}
        elif "SOR" in upper:
            context_nodes = set(nx.descendants(graph, node)) | {node}
        else:
            context_nodes = set(nx.ancestors(graph, node)) | {node} | set(nx.descendants(graph, node))
        subgraphs[node] = graph.subgraph(sorted(context_nodes)).copy()
    return subgraphs


def graph_to_batch(graph: nx.DiGraph, torch: Any) -> _GraphBatch:
    mapping = {node: idx for idx, node in enumerate(graph.nodes)}
    if graph.number_of_edges() == 0:
        edge_index = torch.empty((2, 0), dtype=torch.long)
    else:
        edge_index = torch.tensor(
            [[mapping[source], mapping[target]] for source, target in graph.edges],
            dtype=torch.long,
        ).t().contiguous()
    x = torch.ones((len(graph.nodes), 1), dtype=torch.float32)
    return _GraphBatch(x=x, edge_index=edge_index, num_nodes=len(graph.nodes))


def collate_graph_batches(graphs: list[_GraphBatch], torch: Any) -> _GraphBatch:
    """Concatenate variable-size graph batches without requiring torch-geometric."""
    if not graphs:
        return _GraphBatch(
            x=torch.empty((0, 1), dtype=torch.float32),
            edge_index=torch.empty((2, 0), dtype=torch.long),
            num_nodes=0,
            batch=torch.empty((0,), dtype=torch.long),
        )
    xs = []
    edge_indices = []
    batch_parts = []
    offset = 0
    for graph_idx, graph in enumerate(graphs):
        xs.append(graph.x)
        if graph.edge_index.numel() > 0:
            edge_indices.append(graph.edge_index + offset)
        batch_parts.append(torch.full((graph.num_nodes,), graph_idx, dtype=torch.long))
        offset += int(graph.num_nodes)
    edge_index = (
        torch.cat(edge_indices, dim=1)
        if edge_indices
        else torch.empty((2, 0), dtype=torch.long)
    )
    return _GraphBatch(
        x=torch.cat(xs, dim=0),
        edge_index=edge_index,
        num_nodes=offset,
        batch=torch.cat(batch_parts, dim=0),
    )


def iter_training_batches(
    rows: list[tuple[_GraphBatch, _GraphBatch, float]],
    batch_size: int,
) -> Any:
    safe_batch_size = max(int(batch_size), 1)
    for start in range(0, len(rows), safe_batch_size):
        yield rows[start : start + safe_batch_size]


def _canonical_pair(node_a: str, node_b: str) -> tuple[str, str]:
    return tuple(sorted((node_a, node_b)))


def create_training_dataset(
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    *,
    negative_ratio: int,
    seed: int,
) -> tuple[list[tuple[_GraphBatch, _GraphBatch, float]], dict[str, int]]:
    torch, _, _ = _resolve_torch()
    subgraphs = extract_subgraphs(graph)
    valid_positive_pairs = []
    for node_a, node_b in sorted({_canonical_pair(*pair) for pair in positive_pairs}):
        if node_a not in subgraphs or node_b not in subgraphs:
            continue
        batch_a = graph_to_batch(subgraphs[node_a], torch)
        batch_b = graph_to_batch(subgraphs[node_b], torch)
        if batch_a.edge_index.numel() == 0 or batch_b.edge_index.numel() == 0:
            continue
        valid_positive_pairs.append((node_a, node_b, batch_a, batch_b))

    rng = random.Random(seed)
    nodes = list(subgraphs.keys())
    positive_set = {_canonical_pair(node_a, node_b) for node_a, node_b, _, _ in valid_positive_pairs}
    negative_target = max(len(valid_positive_pairs) * max(negative_ratio, 1), len(valid_positive_pairs))
    negative_pairs: list[tuple[str, str, _GraphBatch, _GraphBatch]] = []
    negative_seen: set[tuple[str, str]] = set()
    all_pairs = [_canonical_pair(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]
    rng.shuffle(all_pairs)
    for node_a, node_b in all_pairs:
        if len(negative_pairs) >= negative_target:
            break
        if (node_a, node_b) in positive_set or (node_a, node_b) in negative_seen:
            continue
        batch_a = graph_to_batch(subgraphs[node_a], torch)
        batch_b = graph_to_batch(subgraphs[node_b], torch)
        if batch_a.edge_index.numel() == 0 or batch_b.edge_index.numel() == 0:
            continue
        negative_pairs.append((node_a, node_b, batch_a, batch_b))
        negative_seen.add((node_a, node_b))

    dataset: list[tuple[_GraphBatch, _GraphBatch, float]] = []
    for _, _, batch_a, batch_b in valid_positive_pairs:
        dataset.append((batch_a, batch_b, 1.0))
    for _, _, batch_a, batch_b in negative_pairs:
        dataset.append((batch_a, batch_b, 0.0))
    rng.shuffle(dataset)
    return dataset, {
        "positive_pairs": len(valid_positive_pairs),
        "negative_pairs": len(negative_pairs),
        "dataset_rows": len(dataset),
        "dataset_source": "positive_pairs_with_negative_sampling",
    }


def _load_supervised_pair_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("rows") or payload.get("validation_dataset") or payload.get("pairs") or []
    else:
        rows = payload
    return [dict(row) for row in rows if isinstance(row, dict)]


def create_training_dataset_from_supervised_rows(
    graph: nx.DiGraph,
    rows: list[dict[str, Any]],
) -> tuple[list[tuple[_GraphBatch, _GraphBatch, float]], dict[str, int | str]]:
    torch, _, _ = _resolve_torch()
    subgraphs = extract_subgraphs(graph)
    dataset: list[tuple[_GraphBatch, _GraphBatch, float]] = []
    seen: set[tuple[str, str]] = set()
    skipped_rows = 0
    for row in rows:
        node_a = str(row.get("node_a") or row.get("source") or "").strip()
        node_b = str(row.get("node_b") or row.get("target") or "").strip()
        if not node_a or not node_b:
            skipped_rows += 1
            continue
        canonical = _canonical_pair(node_a, node_b)
        if canonical in seen or canonical[0] not in subgraphs or canonical[1] not in subgraphs:
            skipped_rows += 1
            continue
        try:
            label = float(row.get("target", 1 if str(row.get("decision", "")).lower() == "duplicate" else 0))
        except (TypeError, ValueError):
            label = 1.0 if str(row.get("decision", "")).lower() == "duplicate" else 0.0
        label = 1.0 if label >= 0.5 else 0.0
        batch_a = graph_to_batch(subgraphs[canonical[0]], torch)
        batch_b = graph_to_batch(subgraphs[canonical[1]], torch)
        if batch_a.edge_index.numel() == 0 or batch_b.edge_index.numel() == 0:
            skipped_rows += 1
            continue
        dataset.append((batch_a, batch_b, label))
        seen.add(canonical)
    counts = _label_counts(dataset)
    return dataset, {
        **counts,
        "skipped_rows": skipped_rows,
        "dataset_source": "supervised_validation_dataset",
    }


def _load_training_specs(
    specs: list[ScenarioTrainingSpec],
    *,
    negative_ratio: int,
    seed: int,
) -> tuple[list[tuple[_GraphBatch, _GraphBatch, float]], list[dict[str, int | str]]]:
    dataset: list[tuple[_GraphBatch, _GraphBatch, float]] = []
    dataset_summary: list[dict[str, int | str]] = []
    for spec in specs:
        raw_graph = nx.read_gml(spec.graph_path)
        graph, _ = normalize_lineage_direction(raw_graph)
        if spec.supervised_labels_path and spec.supervised_labels_path.exists():
            scenario_dataset, counts = create_training_dataset_from_supervised_rows(
                graph,
                _load_supervised_pair_rows(spec.supervised_labels_path),
            )
            if not scenario_dataset:
                continue
            dataset.extend(scenario_dataset)
            dataset_summary.append({"scenario": spec.scenario_name, **counts})
            continue
        positive_pairs = [tuple(pair) for pair in json.loads(spec.labels_path.read_text(encoding="utf-8"))]
        scenario_dataset, counts = create_training_dataset(
            graph,
            positive_pairs,
            negative_ratio=negative_ratio,
            seed=seed,
        )
        if not scenario_dataset:
            continue
        dataset.extend(scenario_dataset)
        dataset_summary.append({"scenario": spec.scenario_name, **counts})
    return dataset, dataset_summary


def _normalize_option_key(value: str, options: dict[str, dict[str, str]], aliases: dict[str, str], default: str) -> str:
    raw = str(value or "").strip()
    lowered = raw.lower()
    if raw in options:
        return raw
    if lowered in options:
        return lowered
    if lowered in aliases:
        return aliases[lowered]
    for key, meta in options.items():
        if lowered in {str(meta.get("label", "")).lower(), str(meta.get("technical_name", "")).lower()}:
            return key
    return default


def _label_counts(dataset: list[tuple[_GraphBatch, _GraphBatch, float]]) -> dict[str, int]:
    positive = sum(1 for _, _, label in dataset if float(label) >= 0.5)
    negative = len(dataset) - positive
    return {"positive_pairs": positive, "negative_pairs": negative, "dataset_rows": len(dataset)}


def _stratified_split_dataset(
    dataset: list[tuple[_GraphBatch, _GraphBatch, float]],
    *,
    train_ratio: float,
    seed: int,
) -> tuple[list[tuple[_GraphBatch, _GraphBatch, float]], list[tuple[_GraphBatch, _GraphBatch, float]]]:
    rng = random.Random(seed)
    positives = [row for row in dataset if float(row[2]) >= 0.5]
    negatives = [row for row in dataset if float(row[2]) < 0.5]
    rng.shuffle(positives)
    rng.shuffle(negatives)

    def split_bucket(bucket: list[tuple[_GraphBatch, _GraphBatch, float]]) -> tuple[list[tuple[_GraphBatch, _GraphBatch, float]], list[tuple[_GraphBatch, _GraphBatch, float]]]:
        if len(bucket) <= 1:
            return list(bucket), []
        split = int(len(bucket) * train_ratio)
        split = min(max(1, split), len(bucket) - 1)
        return bucket[:split], bucket[split:]

    train_pos, val_pos = split_bucket(positives)
    train_neg, val_neg = split_bucket(negatives)
    train_dataset = [*train_pos, *train_neg]
    val_dataset = [*val_pos, *val_neg]
    if not val_dataset and len(train_dataset) > 1:
        val_dataset = [train_dataset.pop()]
    rng.shuffle(train_dataset)
    rng.shuffle(val_dataset)
    return train_dataset, val_dataset


def _graph_signature_score(row: tuple[_GraphBatch, _GraphBatch, float]) -> int:
    graph_a, graph_b, _ = row
    edge_count_a = int(graph_a.edge_index.size(1)) if graph_a.edge_index is not None else 0
    edge_count_b = int(graph_b.edge_index.size(1)) if graph_b.edge_index is not None else 0
    return abs(int(graph_a.num_nodes) - int(graph_b.num_nodes)) + abs(edge_count_a - edge_count_b)


def _rebalance_training_dataset(
    train_dataset: list[tuple[_GraphBatch, _GraphBatch, float]],
    *,
    balance_strategy: str,
    negative_ratio: int,
    seed: int,
) -> tuple[list[tuple[_GraphBatch, _GraphBatch, float]], dict[str, Any]]:
    rng = random.Random(seed)
    positives = [row for row in train_dataset if float(row[2]) >= 0.5]
    negatives = [row for row in train_dataset if float(row[2]) < 0.5]
    before = _label_counts(train_dataset)
    strategy = balance_strategy

    if not positives or not negatives or strategy in {"none_real_distribution", "negative_sampling", "class_weighted_loss"}:
        return list(train_dataset), {"strategy": strategy, "before": before, "after": _label_counts(train_dataset), "operation": "kept_original_training_rows"}

    if strategy == "undersample_negatives":
        target_negative_count = min(len(negatives), max(len(positives) * max(int(negative_ratio), 1), len(positives)))
        sampled_negatives = rng.sample(negatives, target_negative_count) if target_negative_count < len(negatives) else negatives
        balanced = [*positives, *sampled_negatives]
        operation = f"kept_all_positives_and_{len(sampled_negatives)}_sampled_negatives"
    elif strategy in {"oversample_positives", "balanced_batch_sampler"}:
        repeated_positives = list(positives)
        while len(repeated_positives) < len(negatives):
            repeated_positives.append(rng.choice(positives))
        balanced = [*repeated_positives, *negatives]
        operation = f"oversampled_positives_from_{len(positives)}_to_{len(repeated_positives)}"
    elif strategy == "hard_negative_mining":
        target_negative_count = min(len(negatives), max(len(positives) * max(int(negative_ratio), 1), len(positives)))
        scored_negatives = sorted(negatives, key=_graph_signature_score)
        balanced = [*positives, *scored_negatives[:target_negative_count]]
        operation = f"kept_{target_negative_count}_structurally_similar_negatives"
    else:
        balanced = list(train_dataset)
        operation = "unknown_strategy_kept_original_training_rows"

    rng.shuffle(balanced)
    return balanced, {"strategy": strategy, "before": before, "after": _label_counts(balanced), "operation": operation}


def _build_loss_function(
    *,
    torch: Any,
    nn: Any,
    device: Any,
    loss_name: str,
    balance_strategy: str,
    train_counts: dict[str, int],
) -> tuple[Callable[[Any, Any], Any], dict[str, Any]]:
    loss_key = _normalize_option_key(
        loss_name,
        TRAINING_LOSS_OPTIONS,
        aliases={"bcewithlogitsloss": "bce_with_logits", "bce": "bce_with_logits"},
        default="bce_with_logits",
    )
    positive_count = max(int(train_counts.get("positive_pairs", 0)), 0)
    negative_count = max(int(train_counts.get("negative_pairs", 0)), 0)
    pos_weight_value = float(negative_count / positive_count) if positive_count else 1.0
    use_pos_weight = loss_key == "weighted_bce_with_logits" or balance_strategy == "class_weighted_loss"

    if loss_key == "focal_loss":
        alpha = 0.25 if positive_count and negative_count else 0.5
        gamma = 2.0

        def focal_loss(logits: Any, target: Any) -> Any:
            bce = nn.functional.binary_cross_entropy_with_logits(logits, target, reduction="none")
            probability = torch.sigmoid(logits)
            pt = probability * target + (1 - probability) * (1 - target)
            alpha_factor = alpha * target + (1 - alpha) * (1 - target)
            return (alpha_factor * ((1 - pt) ** gamma) * bce).mean()

        return focal_loss, {
            "loss_key": loss_key,
            "loss_name": TRAINING_LOSS_OPTIONS[loss_key]["technical_name"],
            "loss_label": TRAINING_LOSS_OPTIONS[loss_key]["label"],
            "formula": TRAINING_LOSS_OPTIONS[loss_key]["formula"],
            "alpha": alpha,
            "gamma": gamma,
            "pos_weight": None,
        }

    pos_weight_tensor = torch.tensor([pos_weight_value], dtype=torch.float32, device=device) if use_pos_weight else None
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight_tensor)
    effective_loss_key = "weighted_bce_with_logits" if use_pos_weight else "bce_with_logits"
    return criterion, {
        "loss_key": effective_loss_key,
        "loss_name": TRAINING_LOSS_OPTIONS[effective_loss_key]["technical_name"],
        "loss_label": TRAINING_LOSS_OPTIONS[effective_loss_key]["label"],
        "formula": TRAINING_LOSS_OPTIONS[effective_loss_key]["formula"],
        "pos_weight": round(pos_weight_value, 6) if use_pos_weight else None,
    }


def train_benchmark_gnn(
    specs: list[ScenarioTrainingSpec],
    *,
    model_path: Path,
    epochs: int,
    learning_rate: float,
    hidden_channels: int,
    dropout: float,
    negative_ratio: int,
    seed: int,
    optimizer_name: str,
    train_ratio: float = 0.8,
    balance_strategy: str = "negative_sampling",
    loss_name: str = "bce_with_logits",
    batch_size: int = 1,
    batched_inference: bool = False,
    inference_batch_size: int = 4096,
    encoder_batch_size: int = 64,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    stop_flag_path: Path | None = None,
) -> dict[str, Any]:
    if not specs:
        raise ValueError("No scenarios selected for GNN training.")

    torch, nn, (SubgraphGNN, PairClassifier) = _resolve_torch()
    random.seed(seed)
    torch.manual_seed(seed)
    optimizer_key = _normalize_option_key(
        optimizer_name,
        TRAINING_OPTIMIZER_OPTIONS,
        aliases={"adam": "adam", "adamw": "adamw", "sgd": "sgd"},
        default="adam",
    )
    balance_key = _normalize_option_key(
        balance_strategy,
        TRAINING_BALANCE_OPTIONS,
        aliases={
            "none": "none_real_distribution",
            "no_balancing": "none_real_distribution",
            "class_weighted": "class_weighted_loss",
            "weighted_bce": "class_weighted_loss",
        },
        default="negative_sampling",
    )
    configured_loss_key = _normalize_option_key(
        loss_name,
        TRAINING_LOSS_OPTIONS,
        aliases={"bcewithlogitsloss": "bce_with_logits", "bce": "bce_with_logits"},
        default="bce_with_logits",
    )
    safe_batch_size = max(int(batch_size), 1)

    if progress_callback:
        progress_callback(
            {
                "status": "running",
                "step": "loading_scenarios",
                "step_detail": "Loading curated scenarios and labels.",
                "epochs": int(epochs),
                "current_epoch": 0,
                "progress": 0.02,
            }
        )
    dataset, dataset_summary = _load_training_specs(specs, negative_ratio=negative_ratio, seed=seed)
    if not dataset:
        raise ValueError("Training dataset is empty. Check the curated duplicate pairs for the selected scenarios.")

    train_ratio = min(max(float(train_ratio), 0.1), 0.95)
    train_dataset, val_dataset = _stratified_split_dataset(dataset, train_ratio=train_ratio, seed=seed)
    train_dataset, balance_summary = _rebalance_training_dataset(
        train_dataset,
        balance_strategy=balance_key,
        negative_ratio=negative_ratio,
        seed=seed,
    )
    train_counts = _label_counts(train_dataset)
    val_counts = _label_counts(val_dataset)

    if progress_callback:
        progress_callback(
            {
                "status": "running",
                "step": "initializing_model",
                "step_detail": "Building GNN layers, classifier head, optimizer, and loss.",
                "epochs": int(epochs),
                "current_epoch": 0,
                "progress": 0.08,
                "train_size": len(train_dataset),
                "val_size": len(val_dataset),
                "train_distribution": train_counts,
                "val_distribution": val_counts,
                "balance_summary": balance_summary,
                "dataset_summary": dataset_summary,
                "optimizer": TRAINING_OPTIMIZER_OPTIONS[optimizer_key]["technical_name"],
                "configured_loss": TRAINING_LOSS_OPTIONS[configured_loss_key]["technical_name"],
                "balance_strategy": TRAINING_BALANCE_OPTIONS[balance_key]["technical_name"],
                "batch_size": safe_batch_size,
            }
        )
    device, device_summary = resolve_gnn_torch_device(torch)
    gnn = SubgraphGNN(hidden_channels=int(hidden_channels), out_channels=int(hidden_channels)).to(device)
    clf = PairClassifier(emb_size=int(hidden_channels), dropout=float(dropout)).to(device)

    optimizer_cls = {
        "adam": torch.optim.Adam,
        "adamw": torch.optim.AdamW,
        "sgd": torch.optim.SGD,
    }.get(optimizer_key)
    if optimizer_cls is None:
        raise ValueError(f"Unsupported optimizer: {optimizer_name}")
    optimizer = optimizer_cls(list(gnn.parameters()) + list(clf.parameters()), lr=float(learning_rate))
    criterion, loss_summary = _build_loss_function(
        torch=torch,
        nn=nn,
        device=device,
        loss_name=configured_loss_key,
        balance_strategy=balance_key,
        train_counts=train_counts,
    )
    history: list[dict[str, float | int]] = []
    status = "completed"
    for epoch in range(int(epochs)):
        if stop_flag_path and stop_flag_path.exists():
            status = "stopped"
            break
        epoch_wall_start = time.perf_counter()
        random.shuffle(train_dataset)
        total_loss = 0.0
        correct = 0
        total = 0
        for batch_rows in iter_training_batches(train_dataset, safe_batch_size):
            batch_a = collate_graph_batches([row[0] for row in batch_rows], torch).to(device)
            batch_b = collate_graph_batches([row[1] for row in batch_rows], torch).to(device)
            batch_a.batch = batch_a.batch.to(device)
            batch_b.batch = batch_b.batch.to(device)
            logits = clf(
                gnn(batch_a.x, batch_a.edge_index, batch_a.batch),
                gnn(batch_b.x, batch_b.edge_index, batch_b.batch),
            )
            target = torch.tensor([row[2] for row in batch_rows], dtype=torch.float32, device=device)
            loss = criterion(logits, target)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            row_count = len(batch_rows)
            total_loss += float(loss.item()) * row_count
            predicted_labels = torch.sigmoid(logits) >= 0.5
            targets = target >= 0.5
            correct += int((predicted_labels == targets).sum().item())
            total += row_count
        gnn.eval()
        clf.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for batch_rows in iter_training_batches(val_dataset, safe_batch_size):
                batch_a = collate_graph_batches([row[0] for row in batch_rows], torch).to(device)
                batch_b = collate_graph_batches([row[1] for row in batch_rows], torch).to(device)
                batch_a.batch = batch_a.batch.to(device)
                batch_b.batch = batch_b.batch.to(device)
                logits = clf(
                    gnn(batch_a.x, batch_a.edge_index, batch_a.batch),
                    gnn(batch_b.x, batch_b.edge_index, batch_b.batch),
                )
                target = torch.tensor([row[2] for row in batch_rows], dtype=torch.float32, device=device)
                current_val_loss = criterion(logits, target)
                row_count = len(batch_rows)
                val_loss += float(current_val_loss.item()) * row_count
                predicted_labels = torch.sigmoid(logits) >= 0.5
                targets = target >= 0.5
                val_correct += int((predicted_labels == targets).sum().item())
                val_total += row_count
        gnn.train()
        clf.train()
        epoch_payload = {
            "epoch": epoch + 1,
            "train_loss": round(total_loss / max(len(train_dataset), 1), 6),
            "train_accuracy": round(correct / total if total else 0.0, 6),
            "val_loss": round(val_loss / max(len(val_dataset), 1), 6),
            "val_accuracy": round(val_correct / val_total if val_total else 0.0, 6),
            "epoch_seconds": round(time.perf_counter() - epoch_wall_start, 6),
        }
        history.append(
            epoch_payload
        )
        if progress_callback:
            progress_callback(
                {
                    "status": "running",
                    "step": "training",
                    "step_detail": f"Running epoch {epoch + 1} of {int(epochs)}.",
                    "current_epoch": epoch + 1,
                    "epochs": int(epochs),
                    "progress": (epoch + 1) / max(int(epochs), 1),
                    "train_size": len(train_dataset),
                    "val_size": len(val_dataset),
                    "history": history,
                    "loss": loss_summary,
                    "balance_summary": balance_summary,
                    "batch_size": safe_batch_size,
                    **epoch_payload,
                }
            )

    model_path.parent.mkdir(parents=True, exist_ok=True)
    with model_path.open("wb") as handle:
        pickle.dump((gnn.cpu(), clf.cpu()), handle)

    metadata_path = model_path.with_suffix(".json")
    metadata = {
        "model_path": str(model_path),
        "scenarios": [spec.scenario_name for spec in specs],
        "dataset_summary": dataset_summary,
        "epochs": int(epochs),
        "learning_rate": float(learning_rate),
        "hidden_channels": int(hidden_channels),
        "dropout": float(dropout),
        "negative_ratio": int(negative_ratio),
        "batch_size": safe_batch_size,
        "batched_inference": bool(batched_inference),
        "inference_batch_size": max(int(inference_batch_size), 1),
        "encoder_batch_size": max(int(encoder_batch_size), 1),
        "train_ratio": float(train_ratio),
        "test_ratio": round(1.0 - float(train_ratio), 6),
        "balance_strategy": balance_key,
        "balance_strategy_label": TRAINING_BALANCE_OPTIONS[balance_key]["label"],
        "balance_summary": balance_summary,
        "seed": int(seed),
        "optimizer": optimizer_key,
        "optimizer_label": TRAINING_OPTIMIZER_OPTIONS[optimizer_key]["label"],
        "optimizer_name": TRAINING_OPTIMIZER_OPTIONS[optimizer_key]["technical_name"],
        "configured_loss": configured_loss_key,
        "configured_loss_label": TRAINING_LOSS_OPTIONS[configured_loss_key]["label"],
        "loss": loss_summary,
        "loss_name": loss_summary["loss_name"],
        "train_distribution": train_counts,
        "val_distribution": val_counts,
        "history": history,
        "train_size": len(train_dataset),
        "val_size": len(val_dataset),
        "status": status,
        "device": device_summary,
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


__all__ = [
    "ScenarioTrainingSpec",
    "TRAINING_BALANCE_OPTIONS",
    "TRAINING_LOSS_OPTIONS",
    "TRAINING_OPTIMIZER_OPTIONS",
    "collate_graph_batches",
    "create_training_dataset",
    "iter_training_batches",
    "resolve_gnn_torch_device",
    "train_benchmark_gnn",
]
