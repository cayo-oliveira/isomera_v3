from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime
from itertools import combinations
from pathlib import Path
from statistics import median
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

import core.algorithms  # noqa: F401,E402 - registers VF2/Node Match/GNN adapters
from core.isomorphism import find_isomorphic_pairs  # noqa: E402
from core.metrics import canonical_pairs, confusion_metrics_pairs, success_frequency  # noqa: E402
from build_research_report_package import build_package  # noqa: E402
from generate_tpcds_genai_spec_report import _predict_candidate_pairs_with_pickle  # noqa: E402


ARCH_ROOT = MAIN_ROOT / "data" / "architectures"
REPORT_IMG_ROOT = REPO_ROOT / "research" / "img"
ARTICLE_CAPTURE_ROOT = MAIN_ROOT / "data" / "article_capture"
TPCDS_V1_MODEL_ROOT = MAIN_ROOT / "core" / "algorithms" / "pickle" / "gin_gnn" / "modelos_gnn_separados"


BENCHMARKS: dict[str, dict[str, Any]] = {
    "smoke_operational": {
        "display": "Smoke Operational",
        "source_arch": "smoke_operational",
        "candidate_scope": "all",
        "scenario_limit": None,
        "description": "Small operational example benchmark registered in Isomera to validate routing, metrics, figures, and report generation.",
    },
    "tpc_ds_default": {
        "display": "TPC-DS (Default)",
        "source_arch": "tpc_ds",
        "candidate_scope": "all",
        "scenario_limit": None,
        "description": "Original TPC-DS benchmark using the default curated duplicate pairs.",
    },
    "tpc_ds_genai_spec": {
        "display": "TPC-DS GenAI SPEC",
        "source_arch": "tpc_ds_genai_spec",
        "candidate_scope": "spec",
        "scenario_limit": None,
        "description": "GenAI-assisted SPEC-level benchmark using SPEC candidate pairs.",
    },
    "tpc_ds_genai_sot_spec": {
        "display": "TPC-DS GenAI SOT + SPEC",
        "source_arch": "tpc_ds_genai_sot_spec",
        "candidate_scope": "sot_spec",
        "scenario_limit": None,
        "description": "Combined SOT and SPEC benchmark that merges default SOT positives with GenAI SPEC positives.",
    },
    "tpc_ds_genai_sor_sot": {
        "display": "TPC-DS GenAI SOR + SOT",
        "source_arch": "tpc_ds_genai_sor_sot",
        "candidate_scope": "sor_sot",
        "scenario_limit": None,
        "description": "Operational-layer benchmark with SOR and SOT candidates. This isolates source and transformation structures before final SPEC products.",
    },
    "tpc_ds_genai_full_lineage": {
        "display": "TPC-DS GenAI Full Lineage",
        "source_arch": "tpc_ds_genai_full_lineage",
        "candidate_scope": "all",
        "scenario_limit": None,
        "description": "Full lineage benchmark across SOR, SOT, and SPEC candidates with default labels merged with GenAI SPEC labels.",
    },
}


def _log(message: str) -> None:
    print(f"[isomera-benchmark] {message}", flush=True)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def _scenario_sort_key(path: Path) -> tuple[int, int, str]:
    name = path.stem
    sor = 0
    domain = 0
    for part in name.split("_"):
        if part.startswith("SOR"):
            try:
                sor = int(part.replace("SOR", ""))
            except ValueError:
                sor = 0
        if part.startswith("D"):
            try:
                domain = int(part.replace("D", ""))
            except ValueError:
                domain = 0
    return sor, domain, name


def _copy_scenario(source_arch: str, target_arch: str, scenario: str) -> None:
    source = ARCH_ROOT / source_arch
    target = ARCH_ROOT / target_arch
    for subdir, suffix in [("gml", ".gml"), ("real_pairs", ".json")]:
        src = source / subdir / f"{scenario}{suffix}"
        dst = target / subdir / f"{scenario}{suffix}"
        if src.exists() and not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)


def ensure_smoke_benchmark() -> Path:
    """Register a small benchmark so it appears in the Isomera catalog."""
    target = ARCH_ROOT / "smoke_operational"
    source = ARCH_ROOT / "tpc_ds"
    scenarios = [path.stem for path in sorted((source / "gml").glob("*.gml"), key=_scenario_sort_key)[:2]]
    for scenario in scenarios:
        _copy_scenario("tpc_ds", "smoke_operational", scenario)
    manifest = {
        "benchmark_name": "smoke_operational",
        "display_name": "Smoke Operational",
        "description": "Operational smoke benchmark automatically maintained by Isomera. It is intentionally small and should be used only to validate that benchmark execution, model routing, plots, and reports are working.",
        "benchmark_kind": "smoke_example",
        "candidate_scope": "all",
        "scenarios": {
            scenario: {
                "gml_path": str((target / "gml" / f"{scenario}.gml").resolve()),
                "labels_path": str((target / "real_pairs" / f"{scenario}.json").resolve()),
                "source_benchmark": "tpc_ds",
            }
            for scenario in scenarios
        },
        "model_clusters": {
            "GNN TPC-DS v1 cluster": {
                "source": "baseline_tpcds_pickle_dir",
                "route_policy": "explicit_map",
                "routes": {
                    scenario: {
                        "pickle_path": str((TPCDS_V1_MODEL_ROOT / f"{scenario}.pkl").resolve()),
                        "artifact_role": "baseline_tpcds_pickle",
                    }
                    for scenario in scenarios
                },
            }
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_json(target / "benchmark_manifest.json", manifest)
    return target / "benchmark_manifest.json"


def ensure_sot_spec_benchmark() -> Path:
    """Build a benchmark that combines default SOT positives with GenAI SPEC positives."""
    target = ARCH_ROOT / "tpc_ds_genai_sot_spec"
    target_gml = target / "gml"
    target_labels = target / "real_pairs"
    source_gml = ARCH_ROOT / "tpc_ds" / "gml"
    default_labels = ARCH_ROOT / "tpc_ds" / "real_pairs"
    spec_labels = ARCH_ROOT / "tpc_ds_genai_spec" / "real_pairs"
    scenarios = [path.stem for path in sorted(source_gml.glob("*.gml"), key=_scenario_sort_key)]
    for scenario in scenarios:
        target_gml.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_gml / f"{scenario}.gml", target_gml / f"{scenario}.gml")
        merged = canonical_pairs([tuple(pair) for pair in _load_json(default_labels / f"{scenario}.json")])
        spec_path = spec_labels / f"{scenario}.json"
        if spec_path.exists():
            merged |= canonical_pairs([tuple(pair) for pair in _load_json(spec_path)])
        target_labels.mkdir(parents=True, exist_ok=True)
        _write_json(target_labels / f"{scenario}.json", [list(pair) for pair in sorted(merged)])
    manifest = {
        "benchmark_name": "tpc_ds_genai_sot_spec",
        "display_name": "TPC-DS GenAI SOT + SPEC",
        "description": "Combined benchmark scope with SOT and SPEC candidates. Positives are the union of TPC-DS default SOT labels and GenAI SPEC labels.",
        "benchmark_kind": "article_benchmark",
        "candidate_scope": "sot_spec",
        "scenarios": {
            scenario: {
                "gml_path": str((target_gml / f"{scenario}.gml").resolve()),
                "labels_path": str((target_labels / f"{scenario}.json").resolve()),
                "source_benchmark": "tpc_ds + tpc_ds_genai_spec",
            }
            for scenario in scenarios
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_json(target / "benchmark_manifest.json", manifest)
    return target / "benchmark_manifest.json"


def ensure_sor_sot_benchmark() -> Path:
    """Build a benchmark focused on source and transformation lineage layers."""
    target = ARCH_ROOT / "tpc_ds_genai_sor_sot"
    target_gml = target / "gml"
    target_labels = target / "real_pairs"
    source_gml = ARCH_ROOT / "tpc_ds" / "gml"
    default_labels = ARCH_ROOT / "tpc_ds" / "real_pairs"
    scenarios = [path.stem for path in sorted(source_gml.glob("*.gml"), key=_scenario_sort_key)]
    for scenario in scenarios:
        target_gml.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_gml / f"{scenario}.gml", target_gml / f"{scenario}.gml")
        labels = canonical_pairs([tuple(pair) for pair in _load_json(default_labels / f"{scenario}.json")])
        target_labels.mkdir(parents=True, exist_ok=True)
        _write_json(target_labels / f"{scenario}.json", [list(pair) for pair in sorted(labels)])
    manifest = {
        "benchmark_name": "tpc_ds_genai_sor_sot",
        "display_name": "TPC-DS GenAI SOR + SOT",
        "description": "Operational-layer benchmark over SOR and SOT candidates. Positives come from the default curated TPC-DS duplicate contract and are scoped at metric time.",
        "benchmark_kind": "article_benchmark",
        "candidate_scope": "sor_sot",
        "scenarios": {
            scenario: {
                "gml_path": str((target_gml / f"{scenario}.gml").resolve()),
                "labels_path": str((target_labels / f"{scenario}.json").resolve()),
                "source_benchmark": "tpc_ds",
            }
            for scenario in scenarios
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_json(target / "benchmark_manifest.json", manifest)
    return target / "benchmark_manifest.json"


def ensure_full_lineage_benchmark() -> Path:
    """Build a full SOR/SOT/SPEC benchmark with merged default and GenAI SPEC labels."""
    target = ARCH_ROOT / "tpc_ds_genai_full_lineage"
    target_gml = target / "gml"
    target_labels = target / "real_pairs"
    source_gml = ARCH_ROOT / "tpc_ds" / "gml"
    default_labels = ARCH_ROOT / "tpc_ds" / "real_pairs"
    spec_labels = ARCH_ROOT / "tpc_ds_genai_spec" / "real_pairs"
    scenarios = [path.stem for path in sorted(source_gml.glob("*.gml"), key=_scenario_sort_key)]
    for scenario in scenarios:
        target_gml.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_gml / f"{scenario}.gml", target_gml / f"{scenario}.gml")
        merged = canonical_pairs([tuple(pair) for pair in _load_json(default_labels / f"{scenario}.json")])
        spec_path = spec_labels / f"{scenario}.json"
        if spec_path.exists():
            merged |= canonical_pairs([tuple(pair) for pair in _load_json(spec_path)])
        target_labels.mkdir(parents=True, exist_ok=True)
        _write_json(target_labels / f"{scenario}.json", [list(pair) for pair in sorted(merged)])
    manifest = {
        "benchmark_name": "tpc_ds_genai_full_lineage",
        "display_name": "TPC-DS GenAI Full Lineage",
        "description": "Full lineage benchmark across SOR, SOT, and SPEC candidates. Positives are the union of default TPC-DS labels and GenAI SPEC labels.",
        "benchmark_kind": "article_benchmark",
        "candidate_scope": "all",
        "scenarios": {
            scenario: {
                "gml_path": str((target_gml / f"{scenario}.gml").resolve()),
                "labels_path": str((target_labels / f"{scenario}.json").resolve()),
                "source_benchmark": "tpc_ds + tpc_ds_genai_spec",
            }
            for scenario in scenarios
        },
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _write_json(target / "benchmark_manifest.json", manifest)
    return target / "benchmark_manifest.json"


def _node_layer(graph: nx.DiGraph, node: str) -> str:
    return str(graph.nodes[node].get("type") or node.split("_", 1)[0]).upper()


def _candidate_pairs(graph: nx.DiGraph, scope: str) -> list[tuple[str, str]]:
    nodes = sorted(str(node) for node in graph.nodes)
    if scope == "spec":
        nodes = [node for node in nodes if _node_layer(graph, node).startswith("SPEC")]
    elif scope == "sot_spec":
        nodes = [node for node in nodes if _node_layer(graph, node).startswith(("SOT", "SPEC"))]
    elif scope == "sor_sot":
        nodes = [node for node in nodes if _node_layer(graph, node).startswith(("SOR", "SOT"))]
    return [(a, b) for a, b in combinations(nodes, 2)]


def _load_graphs_and_labels(arch_name: str, limit: int | None = None) -> tuple[dict[str, nx.DiGraph], dict[str, list[tuple[str, str]]], list[dict[str, Any]]]:
    root = ARCH_ROOT / arch_name
    gml_paths = sorted((root / "gml").glob("*.gml"), key=_scenario_sort_key)
    if limit:
        gml_paths = gml_paths[:limit]
    graphs: dict[str, nx.DiGraph] = {}
    labels: dict[str, list[tuple[str, str]]] = {}
    scenario_rows: list[dict[str, Any]] = []
    for path in gml_paths:
        scenario = path.stem
        graph = nx.read_gml(path)
        label_path = root / "real_pairs" / f"{scenario}.json"
        pairs = [tuple(pair) for pair in _load_json(label_path)] if label_path.exists() else []
        graphs[scenario] = graph
        labels[scenario] = pairs
        scenario_rows.append(
            {
                "scenario": scenario,
                "schema": f"scenario_{scenario.replace('graph_', '').lower()}",
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "positive_pairs": len(pairs),
                "gml_path": str(path.resolve()),
                "labels_path": str(label_path.resolve()),
            }
        )
    if not graphs:
        raise FileNotFoundError(f"No scenarios found in {root / 'gml'}")
    return graphs, labels, scenario_rows


def _model_path_maps() -> dict[str, dict[str, Path]]:
    return {
        "GNN TPC-DS v1 cluster": {path.stem: path for path in TPCDS_V1_MODEL_ROOT.glob("*.pkl")},
        "GNN GenAI SPEC v1 cluster": {
            path.name.replace("GNN_tpcds_genai_spec_", "").replace(".pkl", ""): path
            for path in (ARCH_ROOT / "tpc_ds_genai_spec" / "models").glob("*.pkl")
        },
        **{
            f"GNN GenAI SPEC Protocol rank {rank}": {
                path.name.replace(f"GNN_tpcds_genai_spec_protocol_rank{rank}_", "").replace(".pkl", ""): path
                for path in (ARCH_ROOT / "tpc_ds_genai_spec_protocol" / "models" / folder).glob("*.pkl")
            }
            for rank, folder in [
                (1, "rank1_weighted_bce_lr0p005_h16_d0p1_t0p5"),
                (2, "rank2_weighted_bce_lr0p001_h16_d0p0_t0p4"),
                (3, "rank3_weighted_bce_lr0p005_h16_d0p1_t0p4"),
                (4, "rank4_weighted_bce_lr0p001_h16_d0p1_t0p4"),
                (5, "rank5_weighted_bce_lr0p001_h16_d0p1_t0p5"),
            ]
        },
    }


def _threshold_for(family: str, path: Path | None) -> float:
    if "TPC-DS v1" in family:
        return 0.5
    if "GenAI SPEC v1" in family:
        return 0.3
    if path:
        name = path.parent.name
        if "_t0p4" in name:
            return 0.4
        if "_t0p6" in name:
            return 0.6
    return 0.5


def _predict_with_timing(predictor: Callable[[], set[tuple[str, str]]], runs: int) -> tuple[set[tuple[str, str]], list[float]]:
    predictions: set[tuple[str, str]] = set()
    timings: list[float] = []
    for run in range(1, runs + 1):
        start = time.perf_counter()
        predictions = canonical_pairs(predictor())
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        _log(f"    run {run}/{runs}: {elapsed:.4f}s")
    return predictions, timings


def _jaccard(true_pairs: set[tuple[str, str]], predicted_pairs: set[tuple[str, str]]) -> float:
    union = true_pairs | predicted_pairs
    return 1.0 if not union else len(true_pairs & predicted_pairs) / len(union)


def _evaluate_one(
    *,
    scenario: str,
    graph: nx.DiGraph,
    true_pairs: list[tuple[str, str]],
    candidate_pairs: list[tuple[str, str]],
    algorithm: str,
    predictor: Callable[[], set[tuple[str, str]]],
    artifact_path: str = "",
    artifact_role: str = "",
    route_mode: str = "",
    route_source: str = "",
    threshold: float = 0.0,
    runs: int,
) -> dict[str, Any]:
    _log(f"{scenario}: {algorithm} ({runs} runs)")
    candidate_set = canonical_pairs(candidate_pairs)
    true_set = canonical_pairs(true_pairs) & candidate_set
    predicted, timings = _predict_with_timing(lambda: canonical_pairs(predictor()) & candidate_set, runs)
    metrics = confusion_metrics_pairs(true_set, predicted, all_pairs=candidate_pairs)
    et = float(median(timings)) if timings else 0.0
    accuracy = float(metrics["accuracy"] or 0.0)
    jaccard = _jaccard(true_set, predicted)
    n_pairs = len(candidate_pairs)
    return {
        "scenario": scenario,
        "algorithm": algorithm,
        "artifact_path": artifact_path,
        "artifact_role": artifact_role,
        "route_mode": route_mode,
        "route_source": route_source,
        "inference_threshold": threshold,
        "accuracy": round(accuracy, 6),
        "jaccard": round(jaccard, 6),
        "sf_jaccard": round(success_frequency(jaccard, et, n_pairs), 6),
        "sf_accuracy": round(success_frequency(accuracy, et, n_pairs), 6),
        "ET": round(et, 6),
        "median_execution_time": round(et, 6),
        "N_pairs": n_pairs,
        "tp": metrics["tp"],
        "fp": metrics["fp"],
        "fn": metrics["fn"],
        "tn": metrics["tn"],
        "precision": round(float(metrics["precision"] or 0.0), 6),
        "recall": round(float(metrics["recall"] or 0.0), 6),
        "f1": round(float(metrics["f1"] or 0.0), 6),
        "runs": runs,
    }


def _aggregate(rows: list[dict[str, Any]], runs: int) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary: list[dict[str, Any]] = []
    for algorithm, group in df.groupby("algorithm", sort=False):
        tp = int(group["tp"].sum())
        fp = int(group["fp"].sum())
        fn = int(group["fn"].sum())
        tn = int(group["tn"].sum())
        j_denom = tp + fp + fn
        a_denom = tp + fp + fn + tn
        summary.append(
            {
                "algorithm": algorithm,
                "sf_jaccard": round(float(group["sf_jaccard"].mean()), 6),
                "jaccard": round(float(tp / j_denom) if j_denom else 0.0, 6),
                "ET": round(float(group["ET"].median()), 6),
                "accuracy": round(float((tp + tn) / a_denom) if a_denom else 0.0, 6),
                "sf_accuracy": round(float(group["sf_accuracy"].mean()), 6),
                "N_pairs": int(group["N_pairs"].sum()),
                "tp": tp,
                "fp": fp,
                "fn": fn,
                "tn": tn,
                "scenarios": int(group["scenario"].nunique()),
                "runs": runs,
                "aggregation": "SF is computed per scenario as score * N_pairs / ET and averaged across scenarios.",
            }
        )
    return summary


def _save_figures(base: Path, benchmark_key: str, benchmark_display: str, summary: list[dict[str, Any]], per_rows: list[dict[str, Any]]) -> dict[str, str]:
    base.mkdir(parents=True, exist_ok=True)
    REPORT_IMG_ROOT.mkdir(parents=True, exist_ok=True)
    summary_df = pd.DataFrame(summary)
    per_df = pd.DataFrame(per_rows)
    fig_paths: dict[str, str] = {}

    def save(fig_name: str) -> str:
        package_path = base / fig_name
        research_path = REPORT_IMG_ROOT / f"{benchmark_key}_{fig_name}"
        plt.tight_layout()
        plt.savefig(package_path, dpi=260, bbox_inches="tight")
        plt.savefig(research_path, dpi=300, bbox_inches="tight")
        plt.close()
        return str(package_path)

    for metric, ylabel, filename in [
        ("sf_jaccard", "SF-Jaccard", "benchmark_sf_jaccard.png"),
        ("jaccard", "Jaccard", "benchmark_jaccard.png"),
        ("accuracy", "Accuracy", "benchmark_accuracy.png"),
        ("ET", "ET (seconds)", "benchmark_runtime.png"),
    ]:
        plt.figure(figsize=(12, 5))
        plot_df = summary_df.sort_values(metric, ascending=False)
        plt.bar(plot_df["algorithm"], plot_df[metric], color="#5B7F6F")
        plt.title(f"{benchmark_display}: {ylabel} by detector family")
        plt.ylabel(ylabel)
        plt.xticks(rotation=35, ha="right", fontsize=8)
        plt.grid(axis="y", alpha=0.25)
        fig_paths[filename.replace(".png", "_png")] = save(filename)

    plt.figure(figsize=(14, 6))
    for algorithm, group in per_df.groupby("algorithm", sort=False):
        ordered = group.sort_values("scenario")
        plt.plot(ordered["scenario"], ordered["sf_jaccard"], marker="o", linewidth=1.4, label=algorithm)
    plt.title(f"{benchmark_display}: SF-Jaccard by scenario")
    plt.ylabel("SF-Jaccard")
    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.grid(axis="y", alpha=0.25)
    plt.legend(fontsize=7, ncol=2)
    fig_paths["benchmark_sf_jaccard_line_by_scenario_png"] = save("benchmark_sf_jaccard_line_by_scenario.png")

    pivot = per_df.pivot_table(index="scenario", columns="algorithm", values="sf_jaccard", aggfunc="mean")
    pivot = pivot.sort_index()
    ax = pivot.plot(kind="bar", figsize=(15, 6), width=0.85, color=plt.cm.Set2.colors)
    ax.set_title(f"{benchmark_display}: grouped SF-Jaccard by scenario")
    ax.set_ylabel("SF-Jaccard")
    ax.tick_params(axis="x", labelrotation=45, labelsize=7)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=7, ncol=2)
    fig_paths["benchmark_sf_jaccard_bar_by_scenario_png"] = save("benchmark_sf_jaccard_bar_by_scenario.png")
    return fig_paths


def _write_markdown(path: Path, benchmark_display: str, summary: list[dict[str, Any]], package: dict[str, str | None] | None = None) -> None:
    lines = [
        f"# {benchmark_display}",
        "",
        "Operational benchmark run generated by Isomera Article Capture.",
        "",
        "## Summary",
        "",
        pd.DataFrame(summary).to_markdown(index=False),
        "",
    ]
    if package:
        lines.extend(["## Package", "", f"- PDF: `{package.get('pdf')}`", f"- TEX: `{package.get('tex')}`", f"- ZIP: `{package.get('zip')}`", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _simple_architecture() -> dict[str, Any]:
    return {
        "overview": "Isomera v2 separates source scenario materialization, curation, model training, benchmark execution, and publication packaging.",
        "layers": [
            {"layer": "Source Warehouse", "responsibility": "PostgreSQL/GML scenarios used as reproducible lineage sources."},
            {"layer": "Scenario Materialization API", "responsibility": "Normalizes each scenario into graph, edge table, matrix, and metadata."},
            {"layer": "Curation and Validation", "responsibility": "Produces supervised duplicate-pair datasets with filters and target labels."},
            {"layer": "Training and Benchmark", "responsibility": "Routes detector families and model clusters to each evaluated scenario."},
            {"layer": "Research Reports", "responsibility": "Exports JSON, CSV, figures, LaTeX, PDF, ZIP, and model references."},
        ],
        "stores": [
            {"store": "PostgreSQL Scenario Warehouse", "technology": "PostgreSQL", "purpose": "Relational benchmark source schemas."},
            {"store": "MySQL Publication Backend", "technology": "MySQL", "purpose": "Publication/backend evidence, logs, reports, and curated scenario metadata."},
            {"store": "GML/JSON", "technology": "Files", "purpose": "Portable graphs, labels, manifests, and model routing."},
            {"store": "Research Packages", "technology": "LaTeX/PDF/ZIP", "purpose": "Article-ready reproducibility package."},
        ],
    }


def _simple_api() -> dict[str, Any]:
    return {
        "purpose": "Expose a reproducible source-to-graph transformation contract used by the UI, training code, benchmark runner, and report builder.",
        "functions": [
            {"function": "load_source", "input": "benchmark architecture or database schema", "output": "scenario graph and labels"},
            {"function": "normalize_lineage", "input": "SOR/SOT/SPEC node metadata and edges", "output": "directed graph normalized to SOR -> SOT -> SPEC when semantics are available"},
            {"function": "candidate_scope", "input": "all, SPEC, or SOT+SPEC", "output": "evaluated candidate-pair universe"},
            {"function": "route_models", "input": "scenario name and detector cluster", "output": "scenario-specific pickle path or post-hoc best-of selector"},
        ],
        "limits": [
            "Generic databases without a manifest or SOR/SOT/SPEC semantics cannot be normalized semantically; they require a mapping contract.",
            "Best-of-all routing is a diagnostic selector and must be reported as post-hoc/oracle-style evidence unless the selection policy is fixed before execution.",
            "Accuracy is retained but SF-Jaccard is the primary metric under pair-imbalance.",
        ],
    }


def run_benchmark(benchmark_key: str, *, runs: int, include_best_of_all: bool, limit: int | None = None) -> dict[str, Any]:
    if benchmark_key == "smoke_operational":
        ensure_smoke_benchmark()
    if benchmark_key == "tpc_ds_genai_sot_spec":
        ensure_sot_spec_benchmark()
    if benchmark_key == "tpc_ds_genai_sor_sot":
        ensure_sor_sot_benchmark()
    if benchmark_key == "tpc_ds_genai_full_lineage":
        ensure_full_lineage_benchmark()
    config = BENCHMARKS[benchmark_key]
    arch_name = str(config["source_arch"])
    scope = str(config["candidate_scope"])
    graphs, labels, scenario_rows = _load_graphs_and_labels(arch_name, limit=limit or config.get("scenario_limit"))
    model_maps = _model_path_maps()
    per_rows: list[dict[str, Any]] = []
    routing_rows: list[dict[str, Any]] = []

    total_jobs = len(graphs) * (2 + sum(1 for paths in model_maps.values() if paths))
    _log(f"{config['display']}: {len(graphs)} scenarios, scope={scope}, runs={runs}, detector jobs~{total_jobs}")
    for scenario_index, (scenario, graph) in enumerate(graphs.items(), start=1):
        _log(f"scenario {scenario_index}/{len(graphs)}: {scenario}")
        candidate_pairs = _candidate_pairs(graph, scope)
        deterministic = [
            ("VF2", "VF2"),
            ("Node Match", "Node Match (Custom)"),
        ]
        for label, algo in deterministic:
            per_rows.append(
                _evaluate_one(
                    scenario=scenario,
                    graph=graph,
                    true_pairs=labels[scenario],
                    candidate_pairs=candidate_pairs,
                    algorithm=label,
                    predictor=lambda g=graph, a=algo: canonical_pairs(find_isomorphic_pairs(g, algorithm=a)),
                    artifact_role="deterministic_baseline",
                    route_mode="not_applicable",
                    route_source="deterministic_algorithm",
                    runs=runs,
                )
            )
        for family, path_map in model_maps.items():
            model_path = path_map.get(scenario)
            if not model_path or not model_path.exists():
                routing_rows.append(
                    {
                        "model_family": family,
                        "scenario": scenario,
                        "artifact_path": "",
                        "artifact_role": "missing_pickle",
                        "route_mode": "missing",
                        "route_source": "cluster map",
                    }
                )
                continue
            threshold = _threshold_for(family, model_path)
            routing_rows.append(
                {
                    "model_family": family,
                    "scenario": scenario,
                    "artifact_path": str(model_path.resolve()),
                    "artifact_role": "scenario_specific_pickle",
                    "route_mode": "scenario_specific",
                    "route_source": "explicit scenario pickle map",
                    "inference_threshold": threshold,
                }
            )
            per_rows.append(
                _evaluate_one(
                    scenario=scenario,
                    graph=graph,
                    true_pairs=labels[scenario],
                    candidate_pairs=candidate_pairs,
                    algorithm=family,
                    artifact_path=str(model_path.resolve()),
                    artifact_role="scenario_specific_pickle",
                    route_mode="scenario_specific",
                    route_source="explicit scenario pickle map",
                    threshold=threshold,
                    predictor=lambda g=graph, p=model_path, pairs=candidate_pairs, t=threshold: _predict_candidate_pairs_with_pickle(g, p, pairs, threshold=t),
                    runs=runs,
                )
            )

    if include_best_of_all:
        _log("building post-hoc best-of-all GNN selector rows")
        by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in per_rows:
            if str(row.get("artifact_path") or ""):
                by_scenario[str(row["scenario"])].append(row)
        for scenario, rows in by_scenario.items():
            best = max(rows, key=lambda row: (float(row.get("sf_jaccard") or 0), float(row.get("jaccard") or 0), -float(row.get("ET") or 0)))
            synthetic = dict(best)
            synthetic["algorithm"] = "GNN Best-of-all cluster selector"
            synthetic["artifact_role"] = "posthoc_best_pickle"
            synthetic["route_mode"] = "best_of_all_posthoc"
            synthetic["route_source"] = f"selected from {len(rows)} GNN cluster candidates by sf_jaccard"
            per_rows.append(synthetic)
            routing_rows.append(
                {
                    "model_family": "GNN Best-of-all cluster selector",
                    "scenario": scenario,
                    "artifact_path": best.get("artifact_path", ""),
                    "artifact_role": "posthoc_best_pickle",
                    "route_mode": "best_of_all_posthoc",
                    "route_source": f"selected {best.get('algorithm')} by sf_jaccard",
                    "selection_metric": "sf_jaccard",
                }
            )

    summary = _aggregate(per_rows, runs)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    capture_dir = ARTICLE_CAPTURE_ROOT / benchmark_key
    capture_dir.mkdir(parents=True, exist_ok=True)
    report_stem = f"{stamp}_{benchmark_key}_article_benchmark"
    report_dir = MAIN_ROOT / "data" / "research_reports" / f"{stamp}_{benchmark_key}_article_benchmark"
    raw_img_dir = report_dir / "raw_images"
    fig_paths = _save_figures(raw_img_dir, benchmark_key, str(config["display"]), summary, per_rows)

    csv_dir = capture_dir / "exports"
    csv_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary).to_csv(csv_dir / f"{report_stem}_benchmark_metrics.csv", index=False)
    pd.DataFrame(per_rows).to_csv(csv_dir / f"{report_stem}_per_scenario_metrics.csv", index=False)
    pd.DataFrame(routing_rows).to_csv(csv_dir / f"{report_stem}_model_routing.csv", index=False)

    total_candidate_pairs = sum(len(_candidate_pairs(graph, scope)) for graph in graphs.values())
    positive_pairs = sum(len(canonical_pairs(labels[name]) & canonical_pairs(_candidate_pairs(graphs[name], scope))) for name in graphs)
    model_cluster_summary = []
    for family, path_map in model_maps.items():
        covered = sum(1 for scenario in graphs if scenario in path_map and path_map[scenario].exists())
        model_cluster_summary.append(
            {
                "model_family": family,
                "artifact_count": covered,
                "scenario_count": len(graphs),
                "coverage": f"{covered}/{len(graphs)}",
                "reporting_rule": "detector family with scenario-specific pickle routing",
            }
        )
    if include_best_of_all:
        model_cluster_summary.append(
            {
                "model_family": "GNN Best-of-all cluster selector",
                "artifact_count": len(graphs),
                "scenario_count": len(graphs),
                "coverage": f"{len(graphs)}/{len(graphs)}",
                "reporting_rule": "post-hoc diagnostic selector; cite separately from fixed detector families",
            }
        )

    capture = {
        "captured_at": datetime.now().isoformat(timespec="seconds"),
        "report_type": f"{benchmark_key}_article_benchmark",
        "summary": {
            "benchmark_name": benchmark_key,
            "benchmark_display_name": config["display"],
            "scenario": f"{benchmark_key}_{len(graphs)}_scenarios",
            "model_name": "all_detector_families",
            "model_family_name": "VF2_NodeMatch_GNN_clusters",
            "total_pairs": total_candidate_pairs,
            "candidate_pairs": total_candidate_pairs,
            "reviewed_pairs": total_candidate_pairs,
            "duplicate_pairs": positive_pairs,
            "benchmark_metrics": summary,
            "resolved_hyperparameters": {
                "runs": runs,
                "candidate_scope": scope,
                "best_of_all": include_best_of_all,
            },
        },
        "source_metadata": {
            "mode": "file_architecture_catalog",
            "architecture": arch_name,
            "candidate_scope": scope,
            "scenario_count": len(graphs),
        },
        "graph_summary": {
            "node_count": sum(graph.number_of_nodes() for graph in graphs.values()),
            "edge_count": sum(graph.number_of_edges() for graph in graphs.values()),
            "scenario_count": len(graphs),
        },
        "system_architecture": _simple_architecture(),
        "scenario_api": _simple_api(),
        "publication_tables": {
            "source_details": [
                {"field": "benchmark", "value": benchmark_key},
                {"field": "display_name", "value": config["display"]},
                {"field": "architecture_root", "value": str((ARCH_ROOT / arch_name).resolve())},
                {"field": "candidate_scope", "value": scope},
                {"field": "runs", "value": runs},
                {"field": "best_of_all", "value": include_best_of_all},
            ],
            "pipeline": [
                {"stage": "source", "input": arch_name, "output": f"{len(graphs)} GML scenarios", "details": config["description"]},
                {"stage": "normalized graph", "input": "GML + node layer metadata", "output": "NetworkX directed graph", "details": "Edges and nodes are evaluated under the selected candidate scope."},
                {"stage": "validation dataset", "input": "real_pairs JSON", "output": f"{positive_pairs} positives inside {total_candidate_pairs} candidates", "details": "Pairs outside the selected candidate scope are excluded from metric denominators."},
                {"stage": "model routing", "input": "scenario name + cluster map", "output": "pickle path per scenario", "details": "Best-of-all is post-hoc diagnostic routing when enabled."},
                {"stage": "benchmark execution", "input": "detector families", "output": f"{len(summary)} family rows", "details": f"{runs} runs per detector family per scenario."},
            ],
            "filters": [
                {"filter": "candidate_scope", "setting": scope, "effect": "Defines the candidate-pair universe used by metrics."},
            ],
            "scenario_details": scenario_rows,
            "model_cluster_summary": model_cluster_summary,
            "model_cluster_routing": routing_rows,
            "benchmark_metrics": summary,
            "benchmark_per_scenario_metrics": per_rows,
            "benchmark_pickle_results": [row for row in per_rows if str(row.get("artifact_path") or "")],
            "benchmark_interpretation": [],
            "training_dataset": [
                {
                    "scenario": row["scenario"],
                    "positive_pairs": row["positive_pairs"],
                    "negative_pairs": max(0, len(_candidate_pairs(graphs[row["scenario"]], scope)) - int(row["positive_pairs"])),
                    "dataset_rows": len(_candidate_pairs(graphs[row["scenario"]], scope)),
                }
                for row in scenario_rows
            ],
        },
        "capture_paths": {
            "benchmark_accuracy_png": fig_paths.get("benchmark_accuracy_png"),
            "benchmark_jaccard_png": fig_paths.get("benchmark_jaccard_png"),
            "benchmark_sf_jaccard_png": fig_paths.get("benchmark_sf_jaccard_png"),
            "benchmark_sf_jaccard_line_by_scenario_png": fig_paths.get("benchmark_sf_jaccard_line_by_scenario_png"),
            "benchmark_sf_jaccard_bar_by_scenario_png": fig_paths.get("benchmark_sf_jaccard_bar_by_scenario_png"),
            "benchmark_runtime_png": fig_paths.get("benchmark_runtime_png"),
        },
    }
    capture_path = capture_dir / f"{report_stem}.json"
    _write_json(capture_path, capture)
    markdown_path = capture_dir / f"{report_stem}.md"
    _write_markdown(markdown_path, str(config["display"]), summary)
    capture["capture_paths"]["markdown"] = str(markdown_path)
    _write_json(capture_path, capture)
    package = build_package(capture_path)
    _write_markdown(markdown_path, str(config["display"]), summary, package)
    _log(f"{config['display']}: report package generated at {package.get('package_dir')}")
    return {"capture_path": str(capture_path), "package": package, "benchmark_metrics": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Isomera article benchmark batches.")
    parser.add_argument("--benchmark", choices=sorted(BENCHMARKS), required=True)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-best-of-all", action="store_true")
    args = parser.parse_args()
    result = run_benchmark(
        args.benchmark,
        runs=args.runs,
        include_best_of_all=not args.no_best_of_all,
        limit=args.limit,
    )
    print(json.dumps(result, indent=2, ensure_ascii=True), flush=True)


if __name__ == "__main__":
    main()
