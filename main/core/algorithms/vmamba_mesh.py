"""VMamba-Mesh prototype adapter for Isomera benchmarks.

This module intentionally separates two concerns:

1. The official VMamba runtime can be installed and studied from the UI.
2. The Isomera-compatible VMamba-Mesh adapter produces a benchmarkable pickle.

The adapter is a lightweight, deterministic prototype. It keeps the same
external contract as the other Isomera pickle models by exposing
``predict_pairs(graph)``. That makes it safe to route through the current
benchmark engine while the full neural VMamba-Mesh backbone is developed.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from itertools import combinations
import json
import math
import pickle
import random
import re
import shutil
import subprocess
import time
import zipfile
from pathlib import Path
from typing import Any, Iterable

import networkx as nx


VMAMBA_REPOSITORY_URL = "https://github.com/MzeroMiko/VMamba.git"
VMAMBA_PAPER_URL = "https://arxiv.org/abs/2401.10166"
MAMBA_PAPER_URL = "https://arxiv.org/abs/2312.00752"
VMAMBA_MESH_MODEL_VERSION = "vmamba_mesh_isomera_adapter_v0.1"


@dataclass(frozen=True)
class VMambaMeshConfig:
    """Serializable configuration for the Isomera VMamba-Mesh adapter."""

    scope_layers: tuple[str, ...] = ("SPEC",)
    canon_sort: bool = True
    diag_fp: bool = True
    mesh_ss2d: bool = True
    hier_init: bool = True
    sparse_gate: bool = True
    threshold: float = 0.62
    negative_ratio: int = 4
    seed: int = 42
    resolution: int = 32
    notes: str = (
        "Prototype adapter: canonical lineage features are calibrated to the "
        "validated duplicate-pair table and exported as an Isomera-compatible pickle."
    )


@dataclass
class VMambaMeshPickle:
    """Pickle object consumed by ``core.algorithms.gnn_pickle``.

    The object is deliberately small and stable. Full VMamba-Mesh can later
    replace the scoring internals while preserving this public pickle contract.
    """

    config: VMambaMeshConfig
    feature_weights: dict[str, float]
    feature_names: list[str]
    training_summary: dict[str, Any] = field(default_factory=dict)

    def score_pair(self, graph: nx.DiGraph, node_a: str, node_b: str) -> float:
        features = pair_features(graph, node_a, node_b, config=self.config)
        weight_sum = sum(abs(weight) for weight in self.feature_weights.values()) or 1.0
        weighted = sum(features.get(name, 0.0) * weight for name, weight in self.feature_weights.items())
        return max(0.0, min(1.0, weighted / weight_sum))

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        scope = {layer.upper() for layer in self.config.scope_layers}
        nodes = [
            str(node)
            for node in graph.nodes
            if not scope or _node_layer(str(node)) in scope
        ]
        if self.config.canon_sort:
            nodes = canonical_node_order(nodes)
        predicted: list[tuple[str, str]] = []
        for node_a, node_b in combinations(nodes, 2):
            if self.score_pair(graph, node_a, node_b) >= self.config.threshold:
                predicted.append(tuple(sorted((node_a, node_b))))
        return predicted


def _node_layer(node: str) -> str:
    upper = str(node).upper()
    if "SPEC" in upper:
        return "SPEC"
    if "SOT" in upper:
        return "SOT"
    if "SOR" in upper:
        return "SOR"
    return "OTHER"


def _node_domain(node: str) -> str:
    match = re.search(r"_D(\d+)\b", str(node), flags=re.IGNORECASE)
    return f"D{match.group(1)}" if match else "UNKNOWN"


def _tokenize(node: str) -> set[str]:
    tokens = re.split(r"[^A-Za-z0-9]+", str(node).lower())
    return {token for token in tokens if token and token not in {"sor", "sot", "spec"}}


def _jaccard(left: Iterable[Any], right: Iterable[Any]) -> float:
    left_set = set(left)
    right_set = set(right)
    union = left_set | right_set
    if not union:
        return 1.0
    return len(left_set & right_set) / len(union)


def _size_similarity(left: int, right: int) -> float:
    max_value = max(left, right, 1)
    return 1.0 - (abs(left - right) / max_value)


def canonical_node_order(nodes: Iterable[str]) -> list[str]:
    layer_rank = {"SOR": 0, "SOT": 1, "SPEC": 2, "OTHER": 3}
    return sorted(
        [str(node) for node in nodes],
        key=lambda node: (layer_rank.get(_node_layer(node), 9), _node_domain(node), node.lower()),
    )


def _preserve_node_order(nodes: Iterable[str], graph: nx.DiGraph) -> list[str]:
    graph_order = [str(item) for item in graph.nodes]
    keep = {str(item) for item in nodes}
    ordered = [item for item in graph_order if item in keep]
    leftovers = [item for item in keep if item not in ordered]
    ordered.extend(sorted(leftovers))
    return ordered


def _sequence_jaccard(left: Iterable[Any], right: Iterable[Any]) -> float:
    left_list = list(left)
    right_list = list(right)
    if not left_list and not right_list:
        return 1.0
    if not left_list or not right_list:
        return 0.0
    left_set = set(left_list)
    right_set = set(right_list)
    return len(left_set & right_set) / len(left_set | right_set)


def _adjacent_pairs(values: Iterable[str]) -> list[tuple[str, str]]:
    sequence = list(values)
    return [(sequence[idx], sequence[idx + 1]) for idx in range(len(sequence) - 1)]


def context_subgraph(graph: nx.DiGraph, node: str, *, canonical: bool = True) -> nx.DiGraph:
    """Return the same local context contract used by Isomera pair review."""
    layer = _node_layer(node)
    if layer == "SPEC":
        context_nodes = set(nx.ancestors(graph, node)) | {node}
    elif layer == "SOR":
        context_nodes = set(nx.descendants(graph, node)) | {node}
    else:
        context_nodes = set(nx.ancestors(graph, node)) | {node} | set(nx.descendants(graph, node))
    ordered_nodes = canonical_node_order(context_nodes) if canonical else _preserve_node_order(context_nodes, graph)
    return graph.subgraph(ordered_nodes).copy()


def _signature(graph: nx.DiGraph, node: str, *, config: VMambaMeshConfig) -> dict[str, Any]:
    subgraph = context_subgraph(graph, node, canonical=config.canon_sort)
    nodes = [str(item) for item in subgraph.nodes]
    edges = [(str(src), str(dst)) for src, dst in subgraph.edges]
    layers = [_node_layer(item) for item in nodes]
    domains = [_node_domain(item) for item in nodes]
    parents = [str(item) for item in graph.predecessors(node)]
    children = [str(item) for item in graph.successors(node)]
    return {
        "node": node,
        "layer": _node_layer(node),
        "domain": _node_domain(node),
        "tokens": _tokenize(node),
        "context_nodes": nodes,
        "context_edges": edges,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "layers": layers,
        "domains": domains,
        "ordered_layer_domain": [f"{_node_layer(item)}:{_node_domain(item)}" for item in nodes],
        "ordered_layer_pairs": [f"{left}->{right}" for left, right in _adjacent_pairs(layers)],
        "ordered_domain_pairs": [f"{left}->{right}" for left, right in _adjacent_pairs(domains)],
        "parents": parents,
        "children": children,
        "parent_layer_domain": [f"{_node_layer(item)}:{_node_domain(item)}" for item in parents],
        "child_layer_domain": [f"{_node_layer(item)}:{_node_domain(item)}" for item in children],
    }


def pair_features(
    graph: nx.DiGraph,
    node_a: str,
    node_b: str,
    *,
    config: VMambaMeshConfig | None = None,
) -> dict[str, float]:
    cfg = config or VMambaMeshConfig()
    sig_a = _signature(graph, node_a, config=cfg)
    sig_b = _signature(graph, node_b, config=cfg)
    feature_map = {
        "same_layer": 1.0 if sig_a["layer"] == sig_b["layer"] else 0.0,
        "same_domain": 1.0 if sig_a["domain"] == sig_b["domain"] else 0.0,
        "name_token_jaccard": _jaccard(sig_a["tokens"], sig_b["tokens"]),
        "context_node_similarity": _size_similarity(sig_a["node_count"], sig_b["node_count"]),
        "context_edge_similarity": _size_similarity(sig_a["edge_count"], sig_b["edge_count"]),
        "layer_hist_jaccard": _jaccard(sig_a["layers"], sig_b["layers"]),
        "domain_hist_jaccard": _jaccard(sig_a["domains"], sig_b["domains"]),
        "parent_signature_jaccard": _jaccard(sig_a["parent_layer_domain"], sig_b["parent_layer_domain"]),
        "child_signature_jaccard": _jaccard(sig_a["child_layer_domain"], sig_b["child_layer_domain"]),
        "exact_parent_jaccard": _jaccard(sig_a["parents"], sig_b["parents"]),
        "exact_child_jaccard": _jaccard(sig_a["children"], sig_b["children"]),
        "canonsort_route_alignment": 0.0,
    }
    if cfg.canon_sort:
        feature_map["canonsort_route_alignment"] = _sequence_jaccard(
            sig_a["ordered_layer_domain"], sig_b["ordered_layer_domain"]
        )
    if cfg.diag_fp:
        feature_map["diag_fingerprint_similarity"] = (
            0.55 * feature_map["name_token_jaccard"]
            + 0.25 * feature_map["same_domain"]
            + 0.20 * feature_map["same_layer"]
        )
    else:
        feature_map["diag_fingerprint_similarity"] = 0.0
    if cfg.mesh_ss2d:
        feature_map["meshss2d_route_similarity"] = (
            0.45 * _sequence_jaccard(sig_a["ordered_layer_pairs"], sig_b["ordered_layer_pairs"])
            + 0.35 * _sequence_jaccard(sig_a["ordered_domain_pairs"], sig_b["ordered_domain_pairs"])
            + 0.20 * feature_map["canonsort_route_alignment"]
        )
    else:
        feature_map["meshss2d_route_similarity"] = 0.0
    if cfg.hier_init:
        upstream = feature_map["parent_signature_jaccard"]
        downstream = feature_map["child_signature_jaccard"]
        feature_map["hierarchical_context_match"] = (upstream + downstream) / 2.0
    else:
        feature_map["hierarchical_context_match"] = 0.0
    if cfg.sparse_gate:
        density_a = sig_a["edge_count"] / max(sig_a["node_count"] * sig_a["node_count"], 1)
        density_b = sig_b["edge_count"] / max(sig_b["node_count"] * sig_b["node_count"], 1)
        feature_map["sparse_density_similarity"] = _size_similarity(
            int(density_a * 10_000),
            int(density_b * 10_000),
        )
    else:
        feature_map["sparse_density_similarity"] = 0.0
    return feature_map


DEFAULT_FEATURE_WEIGHTS = {
    "same_layer": 1.20,
    "same_domain": 0.85,
    "name_token_jaccard": 0.55,
    "context_node_similarity": 0.90,
    "context_edge_similarity": 0.90,
    "layer_hist_jaccard": 0.75,
    "domain_hist_jaccard": 0.45,
    "parent_signature_jaccard": 1.05,
    "child_signature_jaccard": 1.05,
    "exact_parent_jaccard": 0.35,
    "exact_child_jaccard": 0.35,
    "canonsort_route_alignment": 0.70,
    "diag_fingerprint_similarity": 0.80,
    "meshss2d_route_similarity": 0.95,
    "hierarchical_context_match": 1.35,
    "sparse_density_similarity": 0.50,
}


def canonical_pair(node_a: str, node_b: str) -> tuple[str, str]:
    return tuple(sorted((str(node_a), str(node_b))))


def load_positive_pairs(labels_path: Path) -> list[tuple[str, str]]:
    if not labels_path.exists():
        return []
    payload = json.loads(labels_path.read_text(encoding="utf-8"))
    pairs: list[tuple[str, str]] = []
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                pairs.append(canonical_pair(str(item[0]), str(item[1])))
            elif isinstance(item, dict) and item.get("target", 1):
                node_a = item.get("node_a") or item.get("source") or item.get("left")
                node_b = item.get("node_b") or item.get("target_node") or item.get("right")
                if node_a and node_b:
                    pairs.append(canonical_pair(str(node_a), str(node_b)))
    return sorted(set(pairs))


def _training_dataset(
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    *,
    config: VMambaMeshConfig,
) -> list[tuple[tuple[str, str], int]]:
    scope = {layer.upper() for layer in config.scope_layers}
    nodes = [
        str(node)
        for node in graph.nodes
        if not scope or _node_layer(str(node)) in scope
    ]
    nodes = canonical_node_order(nodes) if config.canon_sort else sorted(nodes)
    all_pairs = [canonical_pair(node_a, node_b) for node_a, node_b in combinations(nodes, 2)]
    positive_set = {pair for pair in positive_pairs if pair[0] in nodes and pair[1] in nodes}
    negatives = [pair for pair in all_pairs if pair not in positive_set]
    rng = random.Random(config.seed)
    rng.shuffle(negatives)
    negative_limit = min(len(negatives), max(len(positive_set) * max(config.negative_ratio, 1), 1))
    selected_negatives = negatives[:negative_limit]
    dataset = [(pair, 1) for pair in sorted(positive_set)]
    dataset.extend((pair, 0) for pair in selected_negatives)
    return dataset


def _evaluate_threshold(
    scores: list[tuple[float, int]],
    threshold: float,
) -> dict[str, float]:
    tp = fp = fn = tn = 0
    for score, target in scores:
        pred = 1 if score >= threshold else 0
        if pred == 1 and target == 1:
            tp += 1
        elif pred == 1 and target == 0:
            fp += 1
        elif pred == 0 and target == 1:
            fn += 1
        else:
            tn += 1
    denom = tp + fp + fn
    jaccard = (tp / denom) if denom else 0.0
    accuracy = ((tp + tn) / max(tp + fp + fn + tn, 1))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    return {
        "threshold": threshold,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "jaccard": jaccard,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
    }


def fit_vmamba_mesh_model(
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    *,
    config: VMambaMeshConfig,
    feature_weights: dict[str, float] | None = None,
) -> VMambaMeshPickle:
    weights = dict(feature_weights or DEFAULT_FEATURE_WEIGHTS)
    model = VMambaMeshPickle(
        config=config,
        feature_weights=weights,
        feature_names=sorted(weights),
    )
    dataset = _training_dataset(graph, positive_pairs, config=config)
    if not dataset:
        raise ValueError("VMamba-Mesh training dataset is empty. Validate at least one positive duplicate pair first.")
    scores = [(model.score_pair(graph, pair[0], pair[1]), target) for pair, target in dataset]
    threshold_grid = [round(0.30 + idx * 0.025, 3) for idx in range(25)]
    evaluations = [_evaluate_threshold(scores, threshold) for threshold in threshold_grid]
    best = max(
        evaluations,
        key=lambda row: (
            float(row["jaccard"]),
            float(row["recall"]),
            float(row["precision"]),
            -abs(float(row["threshold"]) - config.threshold),
        ),
    )
    calibrated_config = VMambaMeshConfig(
        scope_layers=config.scope_layers,
        canon_sort=config.canon_sort,
        diag_fp=config.diag_fp,
        mesh_ss2d=config.mesh_ss2d,
        hier_init=config.hier_init,
        sparse_gate=config.sparse_gate,
        threshold=float(best["threshold"]),
        negative_ratio=config.negative_ratio,
        seed=config.seed,
        resolution=config.resolution,
        notes=config.notes,
    )
    model.config = calibrated_config
    positives = sum(1 for _, target in dataset if target == 1)
    negatives = len(dataset) - positives
    model.training_summary = {
        "model_version": VMAMBA_MESH_MODEL_VERSION,
        "dataset_pairs": len(dataset),
        "positive_pairs": positives,
        "negative_pairs": negatives,
        "threshold_candidates": threshold_grid,
        "selected_threshold": calibrated_config.threshold,
        "selected_metrics": best,
        "scope_layers": list(calibrated_config.scope_layers),
        "feature_weights": weights,
        "official_vmamba_reference": VMAMBA_REPOSITORY_URL,
        "vmamba_paper": VMAMBA_PAPER_URL,
        "mamba_paper": MAMBA_PAPER_URL,
    }
    return model


def save_vmamba_mesh_artifact(
    *,
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    model_path: Path,
    metadata_path: Path,
    config: VMambaMeshConfig,
    benchmark_name: str,
    scenario_name: str,
    source_graph_path: Path,
    source_labels_path: Path,
) -> dict[str, Any]:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    model = fit_vmamba_mesh_model(graph, positive_pairs, config=config)
    with model_path.open("wb") as handle:
        pickle.dump(model, handle)
    elapsed = time.perf_counter() - started
    metadata = {
        "model_name": model_path.stem,
        "model_family": "VMamba-Mesh Isomera adapter",
        "model_family_name": "VMamba-Mesh Isomera adapter",
        "model_version": VMAMBA_MESH_MODEL_VERSION,
        "pickle_module": "core.algorithms.vmamba_mesh",
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
            "input": "networkx.DiGraph with SOR/SOT/SPEC lineage nodes",
            "output": "list[tuple[str, str]] predicted duplicate pairs",
            "comparison_metrics": ["jaccard", "sf_jaccard", "accuracy", "ET"],
        },
    }
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
    return metadata


def vmamba_runtime_status(runtime_root: Path) -> dict[str, Any]:
    torch_available = False
    torch_version = None
    try:
        import torch  # type: ignore

        torch_available = True
        torch_version = str(torch.__version__)
    except Exception:
        pass
    return {
        "runtime_root": str(runtime_root),
        "repository_present": runtime_root.exists(),
        "git_present": shutil.which("git") is not None,
        "pip_present": shutil.which("pip") is not None,
        "torch_available": torch_available,
        "torch_version": torch_version,
        "vmamba_reference_file_present": (runtime_root / "classification").exists()
        or (runtime_root / "vmamba.py").exists(),
    }


def install_or_update_vmamba_runtime(runtime_root: Path, python_executable: str) -> tuple[bool, str]:
    runtime_root.parent.mkdir(parents=True, exist_ok=True)
    logs: list[str] = []
    if not runtime_root.exists():
        command = ["git", "clone", "--depth", "1", VMAMBA_REPOSITORY_URL, str(runtime_root)]
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=900)
        logs.extend([result.stdout.strip(), result.stderr.strip()])
        if result.returncode != 0:
            return False, "\n".join(part for part in logs if part)
    else:
        command = ["git", "-C", str(runtime_root), "pull", "--ff-only"]
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=600)
        logs.extend([result.stdout.strip(), result.stderr.strip()])
        if result.returncode != 0:
            return False, "\n".join(part for part in logs if part)
    requirements = runtime_root / "requirements.txt"
    if requirements.exists():
        command = [python_executable, "-m", "pip", "install", "-r", str(requirements)]
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=1800)
        logs.extend([result.stdout.strip(), result.stderr.strip()])
        if result.returncode != 0:
            return False, "\n".join(part for part in logs if part)
    return True, "\n".join(part for part in logs if part) or "VMamba runtime is present."


def _latex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def build_vmamba_mesh_study_package(
    *,
    reports_root: Path,
    metadata: dict[str, Any],
    compile_pdf: bool = True,
) -> dict[str, str]:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    scenario = str((metadata.get("scenarios") or ["scenario"])[0])
    package_name = f"{stamp}_{scenario}_vmamba_mesh_study"
    package_dir = reports_root / package_name
    package_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = package_dir / "package_manifest.json"
    md_path = package_dir / f"{package_name}.md"
    tex_path = package_dir / f"{package_name}.tex"
    pdf_path = package_dir / f"{package_name}.pdf"
    zip_path = reports_root / f"{package_name}.zip"

    summary = metadata.get("training_summary") or {}
    selected_metrics = summary.get("selected_metrics") or {}
    markdown = f"""# VMamba-Mesh Study Report

## Purpose

This report records a VMamba-Mesh study/training run inside Isomera. The official VMamba architecture is treated as the reference backbone, while this first Isomera adapter exports a benchmark-compatible `.pkl` through a stable `predict_pairs(graph)` contract.

## Source

- Benchmark: `{metadata.get('benchmark_name')}`
- Scenario: `{scenario}`
- Graph: `{metadata.get('source_graph_path')}`
- Labels: `{metadata.get('source_labels_path')}`
- Pickle: `{metadata.get('pickle_path')}`
- Inference module: `{metadata.get('pickle_module')}`

## VMamba to VMamba-Mesh Delta

| Component | VMamba | VMamba-Mesh |
|---|---|---|
| Input | Natural image patches | Canonical lineage pair tensors |
| Scan | SS2D over image rows/columns | Lineage-aware scan over SOR -> SOT -> SPEC blocks |
| Identity | Pixel channels | DiagFP schema/table fingerprint channel |
| State | Visual context memory | HierInit upstream lineage memory |
| Sparsity | Dense image assumption | SparseGate for sparse adjacency matrices |
| Output | Image class/logits | Duplicate-pair score and benchmarkable pair set |

## Training Summary

- Model version: `{metadata.get('model_version')}`
- Dataset pairs: `{summary.get('dataset_pairs')}`
- Positive pairs: `{summary.get('positive_pairs')}`
- Negative pairs: `{summary.get('negative_pairs')}`
- Selected threshold: `{summary.get('selected_threshold')}`
- Jaccard on calibration set: `{selected_metrics.get('jaccard')}`
- Accuracy on calibration set: `{selected_metrics.get('accuracy')}`
- Precision: `{selected_metrics.get('precision')}`
- Recall: `{selected_metrics.get('recall')}`

## Reproducibility Contract

The saved pickle expects a directed `networkx.DiGraph` with lineage table nodes. It returns predicted duplicate pairs as `list[tuple[str, str]]`. The benchmark layer then computes TP, FP, FN, TN, Jaccard, SF-Jaccard and ET exactly like the other Isomera models.

```json
{json.dumps(metadata, indent=2, ensure_ascii=True)}
```
"""
    md_path.write_text(markdown, encoding="utf-8")

    tex = rf"""\documentclass[11pt]{{article}}
\usepackage[margin=1in]{{geometry}}
\usepackage{{booktabs}}
\usepackage{{hyperref}}
\usepackage{{longtable}}
\title{{VMamba-Mesh Study Report}}
\author{{Isomera Study Lab}}
\date{{{_latex_escape(time.strftime("%Y-%m-%d %H:%M:%S"))}}}
\begin{{document}}
\maketitle
\section{{Purpose}}
This report records a VMamba-Mesh study/training run inside Isomera. VMamba is the reference backbone, and the Isomera adapter exports a benchmark-compatible pickle through a stable \texttt{{predict\_pairs(graph)}} contract.

\section{{Source and Artifact Contract}}
\begin{{longtable}}{{p{{0.28\linewidth}}p{{0.66\linewidth}}}}
\toprule
Field & Value\\
\midrule
Benchmark & {_latex_escape(metadata.get('benchmark_name'))}\\
Scenario & {_latex_escape(scenario)}\\
Graph & {_latex_escape(metadata.get('source_graph_path'))}\\
Labels & {_latex_escape(metadata.get('source_labels_path'))}\\
Pickle & {_latex_escape(metadata.get('pickle_path'))}\\
Inference module & {_latex_escape(metadata.get('pickle_module'))}\\
\bottomrule
\end{{longtable}}

\section{{VMamba to VMamba-Mesh Delta}}
\begin{{longtable}}{{p{{0.18\linewidth}}p{{0.35\linewidth}}p{{0.35\linewidth}}}}
\toprule
Component & VMamba & VMamba-Mesh\\
\midrule
Input & Natural image patches & Canonical lineage pair tensors\\
Scan & SS2D over image rows/columns & Lineage-aware scan over SOR--SOT--SPEC blocks\\
Identity & Pixel channels & DiagFP schema/table fingerprint channel\\
State & Visual context memory & HierInit upstream lineage memory\\
Sparsity & Dense image assumption & SparseGate for sparse adjacency matrices\\
Output & Image class/logits & Duplicate-pair score and benchmarkable pair set\\
\bottomrule
\end{{longtable}}

\section{{Training Summary}}
\begin{{longtable}}{{p{{0.42\linewidth}}p{{0.48\linewidth}}}}
\toprule
Metric & Value\\
\midrule
Model version & {_latex_escape(metadata.get('model_version'))}\\
Dataset pairs & {_latex_escape(summary.get('dataset_pairs'))}\\
Positive pairs & {_latex_escape(summary.get('positive_pairs'))}\\
Negative pairs & {_latex_escape(summary.get('negative_pairs'))}\\
Selected threshold & {_latex_escape(summary.get('selected_threshold'))}\\
Calibration Jaccard & {_latex_escape(selected_metrics.get('jaccard'))}\\
Calibration accuracy & {_latex_escape(selected_metrics.get('accuracy'))}\\
Calibration precision & {_latex_escape(selected_metrics.get('precision'))}\\
Calibration recall & {_latex_escape(selected_metrics.get('recall'))}\\
\bottomrule
\end{{longtable}}

\section{{Reproducibility}}
The saved pickle expects a directed \texttt{{networkx.DiGraph}} with lineage table nodes and returns predicted duplicate pairs as a list of string tuples. The benchmark layer computes TP, FP, FN, TN, Jaccard, SF-Jaccard and ET using the same evaluator used by VF2, Node Match and GNN pickle clusters.
\end{{document}}
"""
    tex_path.write_text(tex, encoding="utf-8")

    pdf_status = "not_requested"
    if compile_pdf and shutil.which("tectonic"):
        result = subprocess.run(
            ["tectonic", str(tex_path.name)],
            cwd=str(package_dir),
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        pdf_status = "compiled" if result.returncode == 0 and pdf_path.exists() else "failed"
        if result.returncode != 0:
            (package_dir / "tectonic_error.log").write_text(
                "\n".join([result.stdout, result.stderr]),
                encoding="utf-8",
            )
    manifest = {
        "name": package_name,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "report_type": "vmamba_mesh_study",
        "metadata": metadata,
        "markdown": str(md_path),
        "tex": str(tex_path),
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "pdf_status": pdf_status,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(package_dir.iterdir()):
            if file_path.is_file():
                archive.write(file_path, arcname=f"{package_name}/{file_path.name}")
    return {
        "package_dir": str(package_dir),
        "manifest": str(manifest_path),
        "markdown": str(md_path),
        "tex": str(tex_path),
        "pdf": str(pdf_path) if pdf_path.exists() else "",
        "zip": str(zip_path),
    }


__all__ = [
    "DEFAULT_FEATURE_WEIGHTS",
    "MAMBA_PAPER_URL",
    "VMAMBA_MESH_MODEL_VERSION",
    "VMAMBA_PAPER_URL",
    "VMAMBA_REPOSITORY_URL",
    "VMambaMeshConfig",
    "VMambaMeshPickle",
    "build_vmamba_mesh_study_package",
    "fit_vmamba_mesh_model",
    "install_or_update_vmamba_runtime",
    "load_positive_pairs",
    "pair_features",
    "save_vmamba_mesh_artifact",
    "vmamba_runtime_status",
]
