"""Metrics and timing utilities for isomorphism analysis."""
from __future__ import annotations

from collections.abc import Iterable
from time import perf_counter

import networkx as nx
import pandas as pd

from core.isomorphism import find_isomorphic_pairs


def _canonical_pair(node_a: str, node_b: str) -> tuple[str, str]:
    return tuple(sorted((node_a, node_b)))


def canonical_pairs(pairs: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    return {_canonical_pair(node_a, node_b) for node_a, node_b in pairs}


def confusion_metrics_pairs(
    true_pairs: Iterable[tuple[str, str]],
    predicted_pairs: Iterable[tuple[str, str]],
    all_pairs: Iterable[tuple[str, str]] | None = None,
) -> dict[str, float | None]:
    """Compute confusion matrix metrics for pair-level classification."""
    true_set = canonical_pairs(true_pairs)
    pred_set = canonical_pairs(predicted_pairs)

    tp = len(true_set & pred_set)
    fp = len(pred_set - true_set)
    fn = len(true_set - pred_set)

    tn = None
    # TN is only valid when the dataset is fully labeled (gold standard).
    if all_pairs is not None:
        all_set = canonical_pairs(all_pairs)
        tn = len(all_set - (true_set | pred_set))

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    accuracy = None
    if tn is not None:
        denom = tp + tn + fp + fn
        accuracy = (tp + tn) / denom if denom else 0.0

    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def jaccard_pairs(
    true_pairs: Iterable[tuple[str, str]],
    predicted_pairs: Iterable[tuple[str, str]],
) -> float:
    """Return pair-level Jaccard: TP / (TP + FP + FN)."""
    true_set = canonical_pairs(true_pairs)
    pred_set = canonical_pairs(predicted_pairs)
    union = true_set | pred_set
    if not union:
        return 1.0
    return len(true_set & pred_set) / len(union)


def success_frequency(score: float | None, et_seconds: float | None, evaluated_pairs: int) -> float:
    """Return the Isomera SF throughput score: score * N_pairs / ET."""
    if score is None or et_seconds is None or et_seconds <= 0 or evaluated_pairs <= 0:
        return 0.0
    return float(score) * float(evaluated_pairs) / float(et_seconds)


def metrics_table(
    graph: nx.DiGraph,
    true_pairs: Iterable[tuple[str, str]],
    algorithms: Iterable[str],
    all_pairs: Iterable[tuple[str, str]] | None = None,
) -> pd.DataFrame:
    """Return a metrics table for each algorithm."""
    rows = []
    for algo in algorithms:
        predicted_pairs = find_isomorphic_pairs(graph, algorithm=algo)
        metrics = confusion_metrics_pairs(true_pairs, predicted_pairs, all_pairs=all_pairs)
        rows.append(
            {
                "algorithm": algo,
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "fn": metrics["fn"],
                "tn": metrics["tn"],
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "accuracy": metrics["accuracy"],
            }
        )
    return pd.DataFrame(rows)


def execution_times(
    graph: nx.DiGraph,
    algorithms: Iterable[str],
    runs: int = 25,
) -> dict[str, list[float]]:
    """Measure execution times for each algorithm."""
    times: dict[str, list[float]] = {algo: [] for algo in algorithms}

    for algo in algorithms:
        for _ in range(runs):
            start = perf_counter()
            find_isomorphic_pairs(graph, algorithm=algo)
            times[algo].append(perf_counter() - start)
    return times


def error_rate(metrics: dict[str, float | None]) -> float:
    """Compute error rate from confusion metrics."""
    tn = metrics.get("tn")
    if tn is None:
        total = metrics["tp"] + metrics["fp"] + metrics["fn"]
    else:
        total = metrics["tp"] + tn + metrics["fp"] + metrics["fn"]
    if total == 0:
        return 0.0
    return (metrics["fp"] + metrics["fn"]) / total
