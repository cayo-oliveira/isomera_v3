#!/usr/bin/env python3
"""Run trainable VMamba-T / VMamba-Mesh-T ablations for Isomera.

Default mode is intentionally short and safe: one scenario, two trainable
variants, small hidden size, and a small number of epochs. Increase arguments
for article-grade runs.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from pathlib import Path
from statistics import median

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "main"
if str(MAIN) not in sys.path:
    sys.path.insert(0, str(MAIN))

from core.algorithms.vmamba_mesh import load_positive_pairs  # noqa: E402
from core.algorithms.vmamba_trainable import (  # noqa: E402
    VMAMBA_TRAINABLE_MODEL_VERSION,
    VMAMBA_TRAINABLE_PRESETS,
    VMambaTrainableConfig,
    resolve_torch_device,
    save_vmamba_trainable_artifact,
    vmamba_trainable_preset_config,
)
from core.metrics import canonical_pairs  # noqa: E402


ARTICLE_SPEC_SCENARIOS = [f"graph_SOR{sor}_D{domain}_seed42" for sor in (2, 4, 8, 16) for domain in (1, 2, 3, 4, 5)]
PREVIOUS_OUTPUT_ROOT = MAIN / "data" / "article_evidence" / "vmamba_mesh_genai_benchmark"
BOOTSTRAP_SAMPLES = 2000
SEED = 42


def _scenario_paths(benchmark: str, scenario: str) -> tuple[Path, Path, Path]:
    root = MAIN / "data" / "architectures" / benchmark
    return root, root / "gml" / f"{scenario}.gml", root / "real_pairs" / f"{scenario}.json"


def _scenario_sort_key(name: str) -> tuple[int, int, str]:
    sor = domain = 0
    for part in str(name).split("_"):
        if part.startswith("SOR"):
            try:
                sor = int(part.replace("SOR", ""))
            except ValueError:
                pass
        if part.startswith("D"):
            try:
                domain = int(part.replace("D", ""))
            except ValueError:
                pass
    return sor, domain, str(name)


def _confusion(predicted: set[tuple[str, str]], truth: set[tuple[str, str]], candidate_pairs: int) -> dict[str, float]:
    tp = len(predicted & truth)
    fp = len(predicted - truth)
    fn = len(truth - predicted)
    tn = max(int(candidate_pairs) - tp - fp - fn, 0)
    denom = tp + fp + fn
    jaccard = tp / denom if denom else 0.0
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    accuracy = (tp + tn) / candidate_pairs if candidate_pairs else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "jaccard": jaccard,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _channels_for_variant(variant: str) -> tuple[str, ...]:
    if variant == "vmamba_t":
        return ("C0", "C1")
    return ("C0", "C1", "C2", "C3", "C4", "C5")


def _channel_contract_for_variant(variant: str) -> list[dict[str, str]]:
    base = [
        {"channel": "C0", "name": "Forward adjacency", "role": "edges in canonical lineage direction"},
        {"channel": "C1", "name": "Reverse adjacency", "role": "reverse edges for bidirectional scan context"},
    ]
    if variant == "vmamba_t":
        return base
    return [
        *base,
        {"channel": "C2", "name": "Layer diagonal", "role": "SOR/SOT/SPEC layer identity on the diagonal"},
        {"channel": "C3", "name": "Degree fingerprint", "role": "local structural degree signature on the diagonal"},
        {"channel": "C4", "name": "Lineage route bias", "role": "route prior for SOR -> SOT -> SPEC traversal"},
        {"channel": "C5", "name": "Sparse mask", "role": "occupied cells so sparse zeros are not treated as missing evidence"},
    ]


def _parse_int_tuple(value: str | None, fallback: tuple[int, ...]) -> tuple[int, ...]:
    if not value:
        return fallback
    return tuple(int(part.strip()) for part in str(value).split(",") if part.strip())


def _scope_nodes(graph: nx.DiGraph, scope_layers: list[str]) -> list[str]:
    scope = {layer.upper() for layer in scope_layers}
    nodes = []
    for node in graph.nodes:
        upper = str(node).upper()
        if not scope:
            nodes.append(str(node))
        elif any(layer in upper for layer in scope):
            nodes.append(str(node))
    return sorted(nodes)


def _candidate_pair_count(graph: nx.DiGraph, scope_layers: list[str]) -> int:
    n_nodes = len(_scope_nodes(graph, scope_layers))
    return int(n_nodes * (n_nodes - 1) / 2)


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _config_columns() -> list[str]:
    return [
        "family",
        "variant",
        "preset",
        "resolution",
        "patch_size",
        "depths",
        "dims",
        "hidden_dim",
        "embedding_dim",
        "epochs",
        "batch_size",
        "learning_rate",
        "loss",
        "optimizer",
        "dropout",
        "drop_path_rate",
        "weight_decay",
        "hard_negative_mining",
        "hard_negative_strategy",
        "hard_negative_manifest_id",
        "false_positive_replay_rounds",
        "threshold_policy",
        "threshold_precision_floor",
        "experiment_tag",
    ]


def _aggregate_dataframe(df: pd.DataFrame, group_fields: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if df.empty:
        return pd.DataFrame(rows)
    for key, group in df.groupby(group_fields, dropna=False, sort=False):
        key_values = key if isinstance(key, tuple) else (key,)
        base = dict(zip(group_fields, key_values))
        tp = int(group["tp"].sum())
        fp = int(group["fp"].sum())
        fn = int(group["fn"].sum())
        tn = int(group["tn"].sum())
        n_pairs = int(group["N_pairs"].sum())
        precision = tp / max(tp + fp, 1)
        recall = tp / max(tp + fn, 1)
        rows.append(
            {
                **base,
                "algorithm": str(group["algorithm"].iloc[0]),
                "jaccard": tp / (tp + fp + fn) if (tp + fp + fn) else 0.0,
                "sf_jaccard": float(group["sf_jaccard"].mean()),
                "ET": float(group["ET"].median()),
                "accuracy": (tp + tn) / n_pairs if n_pairs else 0.0,
                "precision": precision,
                "recall": recall,
                "f1": (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0,
                "N_pairs": n_pairs,
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "scenarios": int(group["scenario"].nunique()),
                "runs": int(group.shape[0]),
            }
        )
    return pd.DataFrame(rows)


def _row_config_id(row: pd.Series | dict[str, object]) -> str:
    return "|".join(str(row.get(column, "")) for column in _config_columns())


def _select_best_per_family(metrics_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if metrics_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    config_summary = _aggregate_dataframe(metrics_df, _config_columns())
    if config_summary.empty:
        return pd.DataFrame(), pd.DataFrame()
    best_rows = []
    selected_ids: set[str] = set()
    for family, group in config_summary.groupby("family", sort=False):
        complete = group[group["scenarios"] == metrics_df["scenario"].nunique()]
        ranked = complete if not complete.empty else group
        best = ranked.sort_values(["sf_jaccard", "jaccard", "f1"], ascending=False).iloc[0]
        best_rows.append(best.to_dict())
        selected_ids.add(_row_config_id(best))
    tagged = metrics_df.copy()
    tagged["_config_id"] = tagged.apply(_row_config_id, axis=1)
    best_per_scenario = tagged[tagged["_config_id"].isin(selected_ids)].drop(columns=["_config_id"])
    return pd.DataFrame(best_rows), best_per_scenario


def _bootstrap_summary(df: pd.DataFrame, algorithm: str) -> dict[str, float | str]:
    subset = df[df["algorithm"] == algorithm].copy()
    rows = subset.to_dict("records")
    rng = random.Random(SEED)
    boot_jaccard: list[float] = []
    boot_sf: list[float] = []
    boot_et: list[float] = []
    boot_acc: list[float] = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = [rng.choice(rows) for _ in rows]
        tp = sum(int(row.get("tp", 0)) for row in sample)
        fp = sum(int(row.get("fp", 0)) for row in sample)
        fn = sum(int(row.get("fn", 0)) for row in sample)
        tn = sum(int(row.get("tn", 0)) for row in sample)
        n_pairs = sum(int(row.get("N_pairs", row.get("candidate_pairs", 0))) for row in sample)
        boot_jaccard.append(tp / (tp + fp + fn) if (tp + fp + fn) else 0.0)
        boot_sf.append(sum(float(row.get("sf_jaccard", 0.0)) for row in sample) / max(len(sample), 1))
        boot_et.append(median(float(row.get("ET", row.get("elapsed_seconds", 0.0))) for row in sample))
        boot_acc.append((tp + tn) / n_pairs if n_pairs else 0.0)
    boot_jaccard.sort()
    boot_sf.sort()
    boot_et.sort()
    boot_acc.sort()
    lo_idx = int(0.025 * len(boot_jaccard))
    hi_idx = min(int(0.975 * len(boot_jaccard)), len(boot_jaccard) - 1)
    return {
        "algorithm": algorithm,
        "ci_level": 0.95,
        "ci_unit": "scenario bootstrap",
        "jaccard_ci_low": boot_jaccard[lo_idx],
        "jaccard_ci_high": boot_jaccard[hi_idx],
        "sf_jaccard_ci_low": boot_sf[lo_idx],
        "sf_jaccard_ci_high": boot_sf[hi_idx],
        "ET_ci_low": boot_et[lo_idx],
        "ET_ci_high": boot_et[hi_idx],
        "accuracy_ci_low": boot_acc[lo_idx],
        "accuracy_ci_high": boot_acc[hi_idx],
    }


def _paired_delta(df: pd.DataFrame, left: str, right: str) -> dict[str, object] | None:
    left_df = df[df["algorithm"] == left][["scenario", "jaccard", "sf_jaccard", "ET", "accuracy"]].rename(
        columns={"jaccard": "jaccard_left", "sf_jaccard": "sf_left", "ET": "ET_left", "accuracy": "acc_left"}
    )
    right_df = df[df["algorithm"] == right][["scenario", "jaccard", "sf_jaccard", "ET", "accuracy"]].rename(
        columns={"jaccard": "jaccard_right", "sf_jaccard": "sf_right", "ET": "ET_right", "accuracy": "acc_right"}
    )
    merged = left_df.merge(right_df, on="scenario", how="inner")
    if merged.empty:
        return None
    rng = random.Random(SEED)
    rows = merged.to_dict("records")
    deltas_j = []
    deltas_sf = []
    for _ in range(BOOTSTRAP_SAMPLES):
        sample = [rng.choice(rows) for _ in rows]
        deltas_j.append(sum(float(row["jaccard_right"]) - float(row["jaccard_left"]) for row in sample) / len(sample))
        deltas_sf.append(sum(float(row["sf_right"]) - float(row["sf_left"]) for row in sample) / len(sample))
    deltas_j.sort()
    deltas_sf.sort()
    lo_idx = int(0.025 * len(deltas_j))
    hi_idx = min(int(0.975 * len(deltas_j)), len(deltas_j) - 1)
    return {
        "left_algorithm": left,
        "right_algorithm": right,
        "scenarios": len(rows),
        "mean_delta_jaccard": sum(float(row["jaccard_right"]) - float(row["jaccard_left"]) for row in rows) / len(rows),
        "mean_delta_jaccard_ci_low": deltas_j[lo_idx],
        "mean_delta_jaccard_ci_high": deltas_j[hi_idx],
        "mean_delta_sf_jaccard": sum(float(row["sf_right"]) - float(row["sf_left"]) for row in rows) / len(rows),
        "mean_delta_sf_jaccard_ci_low": deltas_sf[lo_idx],
        "mean_delta_sf_jaccard_ci_high": deltas_sf[hi_idx],
        "wins_right_on_jaccard": int((merged["jaccard_right"] > merged["jaccard_left"]).sum()),
        "wins_right_on_sf_jaccard": int((merged["sf_right"] > merged["sf_left"]).sum()),
    }


def _load_previous_combined(benchmark: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    root = PREVIOUS_OUTPUT_ROOT / benchmark
    summary_path = root / "combined_summary_metrics.csv"
    per_path = root / "combined_per_scenario_metrics.csv"
    if not summary_path.exists() or not per_path.exists():
        return pd.DataFrame(), pd.DataFrame()
    return pd.read_csv(summary_path), pd.read_csv(per_path)


def _write_dataframe(df: pd.DataFrame, path: Path) -> str:
    df.to_csv(path, index=False)
    return str(path)


def _plot_combined_article_results(
    *,
    benchmark: str,
    report_dir: Path,
    combined_summary: pd.DataFrame,
    combined_per: pd.DataFrame,
) -> dict[str, str]:
    figures_dir = report_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    if combined_summary.empty:
        return {}
    figures: dict[str, str] = {}
    palette = {
        "VF2": "#8E8F89",
        "Node Match": "#A7B8A8",
        "GNN TPC-DS v1 cluster": "#86A3C3",
        "GNN GenAI SPEC v1 cluster": "#6D8FB3",
        "GNN Best-of-all cluster selector": "#B58C5A",
        "Vanilla VMamba graph-image proxy": "#E0A64B",
        "VMamba-Mesh Isomera adapter": "#5D7F68",
        "VMamba-T": "#C47B32",
        "VMamba-Mesh-T": "#2F6F73",
        "VMamba-T (hardneg-mps-spec)": "#B95C2B",
        "VMamba-Mesh-T (hardneg-mps-spec)": "#1F6D78",
    }

    def colors(labels: list[str]) -> list[str]:
        resolved = []
        for label in labels:
            if label in palette:
                resolved.append(palette[label])
            elif str(label).startswith("VMamba-Mesh-T"):
                resolved.append("#1F6D78")
            elif str(label).startswith("VMamba-T"):
                resolved.append("#B95C2B")
            else:
                resolved.append("#A6A6A6")
        return resolved

    ordered = combined_summary.sort_values("sf_jaccard", ascending=False)
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.bar(ordered["algorithm"], ordered["sf_jaccard"], color=colors(ordered["algorithm"].tolist()))
    ax.set_ylabel("SF-Jaccard (correct duplicate-pair evidence per second)")
    ax.set_title(f"{benchmark}: Isomera models with trainable VMamba family")
    ax.set_xticks(range(len(ordered)))
    ax.set_xticklabels(ordered["algorithm"], rotation=35, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "combined_sf_jaccard_with_trainable.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    figures["combined_sf_jaccard_with_trainable"] = str(path)

    metrics = ["jaccard", "accuracy", "ET"]
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for ax, metric in zip(axes, metrics):
        metric_ordered = combined_summary.sort_values(metric, ascending=(metric == "ET"))
        ax.barh(metric_ordered["algorithm"], metric_ordered[metric], color=colors(metric_ordered["algorithm"].tolist()))
        ax.set_title(metric)
        ax.grid(axis="x", alpha=0.25)
    fig.suptitle(f"{benchmark}: quality and runtime diagnostics", fontsize=14, weight="bold")
    fig.tight_layout()
    path = figures_dir / "combined_quality_runtime_with_trainable.png"
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    figures["combined_quality_runtime_with_trainable"] = str(path)

    selected = [
        "VF2",
        "Node Match",
        "GNN GenAI SPEC v1 cluster",
        "GNN Best-of-all cluster selector",
        "Vanilla VMamba graph-image proxy",
        "VMamba-Mesh Isomera adapter",
    ]
    selected.extend(
        label
        for label in combined_per["algorithm"].dropna().unique()
        if str(label).startswith("VMamba-T") or str(label).startswith("VMamba-Mesh-T")
    )
    selected_df = combined_per[combined_per["algorithm"].isin(selected)].copy()
    if not selected_df.empty:
        fig, ax = plt.subplots(figsize=(16, 6))
        for algorithm, group in selected_df.groupby("algorithm", sort=False):
            group = group.sort_values("scenario", key=lambda s: s.map(_scenario_sort_key))
            ax.plot(group["scenario"], group["sf_jaccard"], marker="o", linewidth=1.4, label=algorithm, color=colors([algorithm])[0])
        ax.set_ylabel("SF-Jaccard")
        ax.set_title(f"{benchmark}: per-scenario trend with trainable VMamba")
        ax.set_xticks(range(len(sorted(selected_df["scenario"].unique(), key=_scenario_sort_key))))
        ax.set_xticklabels(sorted(selected_df["scenario"].unique(), key=_scenario_sort_key), rotation=45, ha="right", fontsize=7)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8, ncol=2)
        fig.tight_layout()
        path = figures_dir / "combined_sf_jaccard_line_with_trainable.png"
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        figures["combined_sf_jaccard_line_with_trainable"] = str(path)
    return figures


def _write_article_outputs(report_dir: Path, metrics_df: pd.DataFrame, figures: dict[str, str]) -> dict[str, object]:
    artifacts: dict[str, object] = {}
    if metrics_df.empty:
        return artifacts
    ablation_summary = _aggregate_dataframe(metrics_df, _config_columns())
    best_summary, best_per = _select_best_per_family(metrics_df)
    previous_summary, previous_per = _load_previous_combined(str(metrics_df["benchmark"].iloc[0]))
    trainable_summary = _aggregate_dataframe(best_per, ["algorithm"]) if not best_per.empty else pd.DataFrame()
    combined_summary = pd.concat([previous_summary, trainable_summary], ignore_index=True, sort=False)
    combined_per = pd.concat([previous_per, best_per], ignore_index=True, sort=False)
    artifacts["ablation_summary_metrics"] = _write_dataframe(ablation_summary, report_dir / "ablation_summary_metrics.csv")
    artifacts["best_trainable_summary_metrics"] = _write_dataframe(best_summary, report_dir / "best_trainable_summary_metrics.csv")
    artifacts["best_trainable_per_scenario_metrics"] = _write_dataframe(best_per, report_dir / "best_trainable_per_scenario_metrics.csv")
    if not combined_summary.empty:
        artifacts["combined_summary_with_trainable"] = _write_dataframe(combined_summary, report_dir / "combined_summary_with_trainable.csv")
    if not combined_per.empty:
        artifacts["combined_per_scenario_with_trainable"] = _write_dataframe(combined_per, report_dir / "combined_per_scenario_with_trainable.csv")
        ci_df = pd.DataFrame([_bootstrap_summary(combined_per, algorithm) for algorithm in combined_per["algorithm"].dropna().unique()])
        artifacts["confidence_intervals_with_trainable"] = _write_dataframe(ci_df, report_dir / "confidence_intervals_with_trainable.csv")
        trainable_labels = [str(label) for label in best_per["algorithm"].dropna().unique()] if not best_per.empty else []
        vmamba_t_label = next((label for label in trainable_labels if label.startswith("VMamba-T")), "VMamba-T")
        vmamba_mesh_t_label = next((label for label in trainable_labels if label.startswith("VMamba-Mesh-T")), "VMamba-Mesh-T")
        delta_candidates = [
            ("Vanilla VMamba graph-image proxy", vmamba_t_label),
            ("VMamba-Mesh Isomera adapter", vmamba_mesh_t_label),
            (vmamba_t_label, vmamba_mesh_t_label),
        ]
        deltas = [item for item in (_paired_delta(combined_per, left, right) for left, right in delta_candidates) if item]
        if deltas:
            artifacts["paired_deltas_with_trainable"] = _write_dataframe(pd.DataFrame(deltas), report_dir / "paired_deltas_with_trainable.csv")
    figures.update(
        _plot_combined_article_results(
            benchmark=str(metrics_df["benchmark"].iloc[0]),
            report_dir=report_dir,
            combined_summary=combined_summary,
            combined_per=combined_per,
        )
    )
    return artifacts


def _plot_results(rows: list[dict[str, object]], report_dir: Path) -> dict[str, str]:
    figures_dir = report_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    if not rows:
        return {}
    figures: dict[str, str] = {}
    labels = [
        f"{row['family']}\n{row['scenario'].replace('graph_', '')}\n{row['preset']}/{row['loss']}"
        for row in rows
    ]
    x_values = list(range(len(rows)))

    for metric, ylabel, filename in [
        ("sf_jaccard", "SF-Jaccard", "vmamba_t_ablation_sf_jaccard.png"),
        ("jaccard", "Jaccard", "vmamba_t_ablation_jaccard.png"),
        ("elapsed_seconds", "ET (s)", "vmamba_t_ablation_elapsed_time.png"),
    ]:
        width = max(10, min(26, len(rows) * 1.2))
        fig, ax = plt.subplots(figsize=(width, 6))
        values = [_safe_float(row.get(metric)) for row in rows]
        colors = ["#5D7F68" if str(row.get("variant")) == "vmamba_mesh_t" else "#E0A64B" for row in rows]
        ax.bar(x_values, values, color=colors)
        ax.set_ylabel(ylabel)
        ax.set_title(f"Trainable VMamba ablation - {ylabel}")
        ax.set_xticks(x_values)
        ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        path = figures_dir / filename
        fig.savefig(path, dpi=220, bbox_inches="tight")
        plt.close(fig)
        figures[metric] = str(path)

    top_rows = sorted(rows, key=lambda row: (_safe_float(row.get("sf_jaccard")), _safe_float(row.get("jaccard"))), reverse=True)[:10]
    fig, ax = plt.subplots(figsize=(12, 6))
    top_labels = [f"{row['family']} {row['scenario'].replace('graph_', '')}" for row in top_rows]
    top_values = [_safe_float(row.get("sf_jaccard")) for row in top_rows]
    ax.barh(list(range(len(top_rows))), top_values, color="#6C7A89")
    ax.set_yticks(list(range(len(top_rows))))
    ax.set_yticklabels(top_labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("SF-Jaccard")
    ax.set_title("Top trainable VMamba configurations")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    path = figures_dir / "vmamba_t_ablation_top_configs.png"
    fig.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(fig)
    figures["top_configs"] = str(path)
    return figures


def _write_article_addendum(report_dir: Path, rows: list[dict[str, object]], figures: dict[str, str], article_artifacts: dict[str, object]) -> Path:
    best = sorted(rows, key=lambda row: (_safe_float(row.get("sf_jaccard")), _safe_float(row.get("jaccard"))), reverse=True)
    best_row = best[0] if best else {}
    path = report_dir / "article_iv_trainable_vmamba_addendum.md"
    lines = [
        "# Article IV Trainable VMamba Addendum",
        "",
        "## Scope",
        "",
        "This report documents trainable VMamba-T and VMamba-Mesh-T runs. The deterministic adapters remain as baselines; the `-T` rows are neural models trained from Isomera tensors.",
        "",
        "## Processing Contract",
        "",
        "1. Read the lineage graph and the labeled duplicate pairs.",
        "2. CanonSort defines a stable node order for each context subgraph.",
        "3. Tensorization creates the model input before the neural network.",
        "4. VMamba-T uses C0 forward adjacency and C1 reverse adjacency.",
        "5. VMamba-Mesh-T uses C0 forward adjacency, C1 reverse adjacency, C2 layer diagonal, C3 degree fingerprint, C4 lineage route bias, and C5 sparse mask.",
        "6. The tensor enters a VMamba-style neural backbone: patch embedding, staged VSS-style blocks, bidirectional row/column SS2D-style scans, stochastic depth/dropout, and a pair head.",
        "7. The pair head also receives an auditable structural feature vector for calibration; the final logit is still learned by the neural head.",
        "8. Sigmoid converts the logit to a continuous duplicate score; the calibrated threshold converts the score into `predict_pairs(graph)`.",
        "",
        "## Best Configuration",
        "",
        json.dumps(best_row, indent=2, ensure_ascii=True),
        "",
        "## Figures",
        "",
    ]
    for key, value in figures.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Article Artifacts", ""])
    for key, value in article_artifacts.items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Suggested Article Wording",
            "",
            "VMamba-T and VMamba-Mesh-T instantiate the trainable neural version of the VMamba family inside Isomera. VMamba-T is the neural baseline over the two adjacency channels. VMamba-Mesh-T keeps the same neural backbone but changes the input contract to the full six-channel lineage tensor, allowing DiagFP, lineage route bias and SparseGate information to be learned by the VSS/SS2D blocks. Both expose `predict_pairs(graph)` for fair comparison against VF2, Node Match, GNN clusters, Vanilla VMamba adapter and VMamba-Mesh adapter.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(args: argparse.Namespace) -> Path:
    stamp = f"{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}_{time.time_ns() % 1_000_000_000:09d}"
    report_dir = MAIN / "data" / "research_reports" / f"{stamp}_vmamba_trainable_ablation"
    report_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    manifest: dict[str, object] = {
        "created_at": stamp,
        "model_version": VMAMBA_TRAINABLE_MODEL_VERSION,
        "benchmark": args.benchmark,
        "scenarios": args.scenario,
        "variants": args.variant,
        "epochs": args.epochs,
        "presets": args.preset,
        "resolution": args.resolution,
        "learning_rate": args.learning_rate,
        "negative_ratio": args.negative_ratio,
        "hard_negative_mining": bool(args.hard_negative_mining),
        "hard_negative_strategy": args.hard_negative_strategy,
        "hard_negative_agent": args.hard_negative_agent,
        "hard_negative_manifest_path": args.hard_negative_manifest_path,
        "hard_negative_manifest_id": args.hard_negative_manifest_id,
        "false_positive_replay_rounds": args.false_positive_replay_rounds,
        "false_positive_replay_top_k": args.false_positive_replay_top_k,
        "false_positive_replay_weight": args.false_positive_replay_weight,
        "false_positive_replay_epochs": args.false_positive_replay_epochs,
        "threshold_policy": args.threshold_policy,
        "threshold_precision_floor": args.threshold_precision_floor,
        "experiment_tag": args.experiment_tag,
        "batch_size": args.batch_size,
        "inference_batch_size": args.inference_batch_size,
        "encoder_batch_size": args.encoder_batch_size,
        "requested_device": args.device,
        "initial_device_probe": resolve_torch_device(args.device),
        "pipeline_contract": [
            "networkx lineage graph",
            "CanonSort canonical node order",
            "context subgraph tensorization",
            "VMamba-T channels C0-C1 or VMamba-Mesh-T channels C0-C5",
            "patch embedding",
            "staged VSS-style blocks with bidirectional row/column SS2D-style scans",
            "auditable structural pair-feature vector",
            "pair embedding head over [left, right, abs(left-right), left*right, auxiliary_features]",
            "sigmoid score",
            "calibrated threshold",
            "predict_pairs(graph)",
        ],
        "artifacts": [],
    }
    for scenario in args.scenario:
        benchmark_root, graph_path, labels_path = _scenario_paths(args.benchmark, scenario)
        graph = nx.read_gml(graph_path)
        graph.graph["benchmark"] = args.benchmark
        graph.graph["scenario"] = scenario
        graph.graph["scenario_name"] = scenario
        truth_pairs = set(canonical_pairs(load_positive_pairs(labels_path)))
        for variant in args.variant:
            family_base = "VMamba-Mesh-T" if variant == "vmamba_mesh_t" else "VMamba-T"
            family = f"{family_base} ({args.experiment_tag})" if args.experiment_tag else family_base
            model_dir = benchmark_root / "models" / variant
            model_dir.mkdir(parents=True, exist_ok=True)
            for resolution in args.resolution:
                for preset in args.preset:
                    preset_cfg = vmamba_trainable_preset_config(preset)
                    depths = _parse_int_tuple(args.depths, tuple(preset_cfg["depths"]))
                    dims = _parse_int_tuple(args.dims, tuple(preset_cfg["dims"]))
                    hidden_dim = int(args.hidden_dim or preset_cfg["hidden_dim"])
                    embedding_dim = int(args.embedding_dim or preset_cfg["embedding_dim"])
                    for loss_name in args.loss:
                        for learning_rate in args.learning_rate:
                            model_name = (
                                f"{family_base.replace('-', '').replace(' ', '')}_{scenario}_"
                                f"{preset}_r{resolution}_d{'-'.join(map(str, depths))}_"
                                f"w{'-'.join(map(str, dims))}_loss{loss_name}_"
                                f"nr{args.negative_ratio}_"
                                f"{'hardneg_' if args.hard_negative_mining else ''}"
                                f"{str(args.experiment_tag).replace('-', '_') + '_' if args.experiment_tag else ''}"
                                f"lr{str(learning_rate).replace('.', 'p')}_seed{args.seed}"
                            )
                            model_path = model_dir / f"{model_name}.pkl"
                            metadata_path = model_dir / f"{model_name}.json"
                            config = VMambaTrainableConfig(
                                variant=variant,
                                scope_layers=tuple(args.scope_layers),
                                resolution=int(resolution),
                                channels=_channels_for_variant(variant),
                                architecture="vss_torch",
                                preset=str(preset),
                                patch_size=int(args.patch_size or preset_cfg["patch_size"]),
                                depths=depths,
                                dims=dims,
                                hidden_dim=hidden_dim,
                                embedding_dim=embedding_dim,
                                mlp_ratio=float(args.mlp_ratio),
                                dropout=float(args.dropout),
                                drop_path_rate=float(args.drop_path_rate if args.drop_path_rate is not None else preset_cfg["drop_path_rate"]),
                                negative_ratio=int(args.negative_ratio),
                                hard_negative_mining=bool(args.hard_negative_mining),
                                hard_negative_strategy=str(args.hard_negative_strategy),
                                hard_negative_agent=str(args.hard_negative_agent),
                                hard_negative_manifest_path=str(args.hard_negative_manifest_path),
                                hard_negative_manifest_id=str(args.hard_negative_manifest_id),
                                false_positive_replay_rounds=int(args.false_positive_replay_rounds),
                                false_positive_replay_top_k=int(args.false_positive_replay_top_k),
                                false_positive_replay_weight=int(args.false_positive_replay_weight),
                                false_positive_replay_epochs=int(args.false_positive_replay_epochs),
                                batch_size=int(args.batch_size),
                                inference_batch_size=int(args.inference_batch_size),
                                encoder_batch_size=int(args.encoder_batch_size),
                                seed=int(args.seed),
                                epochs=int(args.epochs),
                                learning_rate=float(learning_rate),
                                loss_name=str(loss_name),
                                threshold_policy=str(args.threshold_policy),
                                threshold_precision_floor=float(args.threshold_precision_floor),
                                optimizer_name=str(args.optimizer),
                                weight_decay=float(args.weight_decay),
                                forward_type=str(args.forward_type),
                                device=str(args.device),
                            )
                            metadata = save_vmamba_trainable_artifact(
                                graph=graph,
                                positive_pairs=sorted(truth_pairs),
                                model_path=model_path,
                                metadata_path=metadata_path,
                                config=config,
                                benchmark_name=args.benchmark,
                                scenario_name=scenario,
                                source_graph_path=graph_path,
                                source_labels_path=labels_path,
                            )
                            import pickle

                            with model_path.open("rb") as handle:
                                model = pickle.load(handle)
                            started = time.perf_counter()
                            predicted = set(canonical_pairs(model.predict_pairs(graph)))
                            try:
                                import torch

                                if str(model.training_summary.get("device", {}).get("resolved_device")) == "mps" and hasattr(torch, "mps"):
                                    torch.mps.synchronize()
                            except Exception:
                                pass
                            elapsed = time.perf_counter() - started
                            n_pairs = _candidate_pair_count(graph, args.scope_layers)
                            metrics = _confusion(predicted, truth_pairs, n_pairs)
                            row = {
                                "benchmark": args.benchmark,
                                "scenario": scenario,
                                "algorithm": family,
                                "family": family,
                                "family_base": family_base,
                                "variant": variant,
                                "experiment_tag": args.experiment_tag,
                                "channel_contract": json.dumps(_channel_contract_for_variant(variant), ensure_ascii=True),
                                "preset": preset,
                                "resolution": resolution,
                                "patch_size": config.patch_size,
                                "depths": "-".join(map(str, depths)),
                                "dims": "-".join(map(str, dims)),
                                "hidden_dim": hidden_dim,
                                "embedding_dim": embedding_dim,
                                "epochs": args.epochs,
                                "batch_size": args.batch_size,
                                "inference_batch_size": args.inference_batch_size,
                                "encoder_batch_size": args.encoder_batch_size,
                                "learning_rate": learning_rate,
                                "loss": loss_name,
                                "negative_ratio": args.negative_ratio,
                                "hard_negative_mining": bool(args.hard_negative_mining),
                                "hard_negative_strategy": args.hard_negative_strategy,
                                "hard_negative_agent": args.hard_negative_agent,
                                "hard_negative_manifest_path": args.hard_negative_manifest_path,
                                "hard_negative_manifest_id": args.hard_negative_manifest_id,
                                "false_positive_replay_rounds": args.false_positive_replay_rounds,
                                "false_positive_replay_top_k": args.false_positive_replay_top_k,
                                "false_positive_replay_weight": args.false_positive_replay_weight,
                                "false_positive_replay_epochs": args.false_positive_replay_epochs,
                                "threshold_policy": args.threshold_policy,
                                "threshold_precision_floor": args.threshold_precision_floor,
                                "optimizer": args.optimizer,
                                "dropout": args.dropout,
                                "drop_path_rate": config.drop_path_rate,
                                "weight_decay": args.weight_decay,
                                "requested_device": args.device,
                                "resolved_device": metadata["training_summary"].get("device", {}).get("resolved_device", "cpu"),
                                "mps_available": metadata["training_summary"].get("device", {}).get("mps_available"),
                                "mps_fallback_reason": metadata["training_summary"].get("device", {}).get("fallback_reason"),
                                "threshold": metadata["training_summary"]["selected_threshold"],
                                "candidate_pairs": n_pairs,
                                "N_pairs": n_pairs,
                                "elapsed_seconds": elapsed,
                                "ET": elapsed,
                                "sf_jaccard": metrics["jaccard"] * n_pairs / elapsed if elapsed > 0 else 0.0,
                                "tp_per_second": metrics["tp"] / elapsed if elapsed > 0 else 0.0,
                                "pickle_path": str(model_path),
                                "metadata_path": str(metadata_path),
                                **metrics,
                            }
                            rows.append(row)
                            manifest["artifacts"].append(row)
                            print(json.dumps(row, ensure_ascii=True))
    figures = _plot_results(rows, report_dir)
    metrics_df = pd.DataFrame(rows)
    article_artifacts = _write_article_outputs(report_dir, metrics_df, figures)
    best_rows = sorted(rows, key=lambda row: (_safe_float(row.get("sf_jaccard")), _safe_float(row.get("jaccard"))), reverse=True)
    manifest["figures"] = figures
    manifest["article_artifacts"] = article_artifacts
    manifest["best_by_sf_jaccard"] = best_rows[0] if best_rows else None
    manifest["article_addendum"] = str(_write_article_addendum(report_dir, rows, figures, article_artifacts))
    metrics_path = report_dir / "metrics.csv"
    with metrics_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["status"])
        writer.writeheader()
        writer.writerows(rows)
    (report_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    md_lines = [
        "# VMamba Trainable Ablation",
        "",
        f"- Benchmark: `{args.benchmark}`",
        f"- Scenarios: `{', '.join(args.scenario)}`",
        f"- Variants: `{', '.join(args.variant)}`",
        f"- Presets: `{', '.join(args.preset)}`",
        f"- Experiment tag: `{args.experiment_tag or 'default'}`",
        f"- Hard-negative mining: `{bool(args.hard_negative_mining)}` via `{args.hard_negative_agent}`",
        f"- Hard-negative strategy: `{args.hard_negative_strategy}`",
        f"- Hard-negative manifest: `{args.hard_negative_manifest_path or 'none'}`",
        f"- False-positive replay rounds: `{args.false_positive_replay_rounds}`",
        f"- False-positive replay top-k: `{args.false_positive_replay_top_k or 'auto'}`",
        f"- False-positive replay weight: `{args.false_positive_replay_weight}`",
        f"- Threshold policy: `{args.threshold_policy}`",
        f"- Threshold precision floor: `{args.threshold_precision_floor}`",
        f"- Metrics CSV: `{metrics_path}`",
        f"- Best by SF-Jaccard: `{json.dumps(manifest['best_by_sf_jaccard'], ensure_ascii=True)}`",
        "",
        "## Pipeline",
        "",
        "The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding and VSS-style SS2D scan blocks. The pair head combines the learned embeddings with an auditable structural calibration vector, emits a sigmoid score, and applies the calibrated threshold to produce `predict_pairs(graph)`.",
        "",
        "Hard-negative mining, when enabled, selects difficult non-duplicate candidate pairs. The structural miner ranks pairs by Isomera features; the LLM-manifest strategy prioritizes an auditable Codex/GPT-5 JSON list and then falls back to the structural miner.",
        "",
        "False-positive replay, when enabled, scores the selected negative rows after the initial training pass, reinforces the highest-scoring false-positive-like negatives, and continues training. Precision-aware thresholding can then select the best Jaccard threshold under a minimum precision floor.",
        "",
        "## Article Outputs",
        "",
        *[f"- {key}: `{value}`" for key, value in article_artifacts.items()],
        "",
        "The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.",
    ]
    (report_dir / "README.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return report_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="tpc_ds_genai_spec_v2")
    parser.add_argument("--scenario", nargs="+", default=["graph_SOR2_D1_seed42"])
    parser.add_argument("--article-scenarios", action="store_true", help="Use all 20 SOR/domain scenarios.")
    parser.add_argument("--variant", nargs="+", default=["vmamba_t", "vmamba_mesh_t"])
    parser.add_argument("--scope-layers", nargs="+", default=["SPEC"])
    parser.add_argument("--resolution", nargs="+", type=int, default=[32])
    parser.add_argument("--preset", nargs="+", choices=sorted(VMAMBA_TRAINABLE_PRESETS), default=["small"])
    parser.add_argument("--depths", default=None, help="Override preset depths, e.g. 2,2,8,2.")
    parser.add_argument("--dims", default=None, help="Override preset dims, e.g. 96,192,384,768.")
    parser.add_argument("--hidden-dim", type=int, default=None)
    parser.add_argument("--embedding-dim", type=int, default=None)
    parser.add_argument("--patch-size", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--inference-batch-size", type=int, default=4096)
    parser.add_argument("--encoder-batch-size", type=int, default=64)
    parser.add_argument("--learning-rate", nargs="+", type=float, default=[1e-3])
    parser.add_argument("--mlp-ratio", type=float, default=4.0)
    parser.add_argument("--dropout", type=float, default=0.10)
    parser.add_argument("--drop-path-rate", type=float, default=None)
    parser.add_argument("--negative-ratio", type=int, default=4)
    parser.add_argument("--hard-negative-mining", action="store_true")
    parser.add_argument("--hard-negative-strategy", default="structural_similarity")
    parser.add_argument("--hard-negative-agent", default="isomera_structural_hard_negative_miner")
    parser.add_argument("--hard-negative-manifest-path", default="")
    parser.add_argument("--hard-negative-manifest-id", default="")
    parser.add_argument("--false-positive-replay-rounds", type=int, default=0)
    parser.add_argument("--false-positive-replay-top-k", type=int, default=0)
    parser.add_argument("--false-positive-replay-weight", type=int, default=2)
    parser.add_argument("--false-positive-replay-epochs", type=int, default=2)
    parser.add_argument("--threshold-policy", choices=["jaccard", "precision_guard", "precision", "f1"], default="jaccard")
    parser.add_argument("--threshold-precision-floor", type=float, default=0.0)
    parser.add_argument("--experiment-tag", default="")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--loss", nargs="+", default=["weighted_bce"])
    parser.add_argument("--optimizer", default="adamw")
    parser.add_argument("--weight-decay", type=float, default=0.05)
    parser.add_argument("--forward-type", default="v05")
    parser.add_argument("--device", choices=["auto", "cpu", "mps"], default="auto")
    args = parser.parse_args()
    if args.article_scenarios:
        args.scenario = ARTICLE_SPEC_SCENARIOS
    if args.benchmark == "full_lineage":
        args.benchmark = "tpc_ds_genai_full_lineage"
        args.scope_layers = ["SOR", "SOT", "SPEC"]
    if args.benchmark in {"spec", "spec_v2"}:
        args.benchmark = "tpc_ds_genai_spec_v2"
    return args


if __name__ == "__main__":
    output = run(parse_args())
    print(f"saved={output}")
