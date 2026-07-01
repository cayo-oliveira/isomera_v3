"""Declarative article reproducibility registry and lightweight runners."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from itertools import combinations
import json
import time
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd

from core.algorithms.gnn_pickle import BoundGNNPickleAlgorithm
from core.algorithms.vmamba_mesh import load_positive_pairs
from core.metrics import canonical_pairs, confusion_metrics_pairs, success_frequency


VANILLA_VMAMBA_BASELINE = "Vanilla VMamba baseline"
LEGACY_VANILLA_VMAMBA_LABEL = "Vanilla VMamba graph-image proxy"


@dataclass(frozen=True)
class ExpectedMetric:
    benchmark: str
    algorithm: str
    metric: str
    value: float
    tolerance: float


@dataclass(frozen=True)
class ArticleReproducibilitySpec:
    article_id: str
    title: str
    status: str
    summary: str
    benchmarks: tuple[str, ...]
    models: tuple[str, ...]
    scenarios: tuple[str, ...]
    runs: int
    seeds: tuple[int, ...]
    source_files: tuple[str, ...]
    expected_metrics: tuple[ExpectedMetric, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)


def _article_iv_spec() -> ArticleReproducibilitySpec:
    return ArticleReproducibilitySpec(
        article_id="article_iv_vmamba_mesh_operational",
        title="Article IV - VMamba-Mesh operational study",
        status="ready",
        summary=(
            "Reproduces the operational VMamba/VMamba-Mesh evidence from the TeXLab "
            "journal package using the Isomera benchmark catalogs and stored model pickles."
        ),
        benchmarks=("tpc_ds_genai_spec_v2", "tpc_ds_genai_full_lineage"),
        models=(
            VANILLA_VMAMBA_BASELINE,
            "VMamba-Mesh Isomera adapter",
        ),
        scenarios=("graph_SOR2_D1_seed42", "graph_SOR16_D1_seed42"),
        runs=10,
        seeds=(42,),
        source_files=(
            "main/data/article_evidence/vmamba_mesh_genai_benchmark",
            "main/data/architectures/tpc_ds_genai_spec_v2",
            "main/data/architectures/tpc_ds_genai_full_lineage",
            "main/data/research_reports",
            "main/docs/presentations/vmamba_mesh_assets",
        ),
        expected_metrics=(
            ExpectedMetric(
                "tpc_ds_genai_spec_v2",
                VANILLA_VMAMBA_BASELINE,
                "jaccard",
                0.255548,
                0.02,
            ),
            ExpectedMetric(
                "tpc_ds_genai_spec_v2",
                "VMamba-Mesh Isomera adapter",
                "jaccard",
                0.274798,
                0.02,
            ),
            ExpectedMetric(
                "tpc_ds_genai_full_lineage",
                VANILLA_VMAMBA_BASELINE,
                "jaccard",
                0.111757,
                0.02,
            ),
            ExpectedMetric(
                "tpc_ds_genai_full_lineage",
                "VMamba-Mesh Isomera adapter",
                "jaccard",
                0.090915,
                0.02,
            ),
        ),
        notes=(
            "Execution time is hardware-sensitive and should be interpreted with a tolerance.",
            "The current VMamba-Mesh artifact is an operational Isomera adapter, not the final CUDA neural model.",
        ),
    )


def list_article_specs() -> list[ArticleReproducibilitySpec]:
    """Return the installed reproducibility registry."""
    return [
        _article_iv_spec(),
        ArticleReproducibilitySpec(
            article_id="article_ii_gnn_duplicate_detector",
            title="Article II - GNN duplicate detector",
            status="planned",
            summary="Manifest placeholder. Enable after expected metrics and routes are consolidated.",
            benchmarks=("tpc_ds",),
            models=("GNN TPC-DS v1 cluster", "VF2", "Node Match"),
            scenarios=("graph_SOR2_D1_seed42", "graph_SOR16_D1_seed42"),
            runs=10,
            seeds=(42,),
            source_files=("main/docs/tech_hub/05_Algorithms_and_Models.md",),
        ),
        ArticleReproducibilitySpec(
            article_id="article_iii_isomera_v2_benchmark",
            title="Article III - Isomera v2 benchmark",
            status="planned",
            summary="Manifest placeholder. Enable after the article benchmark package is frozen.",
            benchmarks=("tpc_ds_genai_spec", "tpc_ds_genai_full_lineage"),
            models=("VF2", "Node Match", "GNN clusters"),
            scenarios=("graph_SOR2_D1_seed42", "graph_SOR16_D1_seed42"),
            runs=10,
            seeds=(42,),
            source_files=("main/docs/tpcds_benchmark.md",),
        ),
    ]


def get_article_spec(article_id: str) -> ArticleReproducibilitySpec:
    for spec in list_article_specs():
        if spec.article_id == article_id:
            return spec
    raise KeyError(f"Unknown article reproducibility spec: {article_id}")


def compare_metric(actual: float | None, expected: float, tolerance: float) -> str:
    """Classify an actual metric against an expected value."""
    if actual is None:
        return "not_available"
    delta = abs(float(actual) - float(expected))
    if delta == 0:
        return "match"
    if delta <= float(tolerance):
        return "within_tolerance"
    return "mismatch"


def _load_expected_summary(repo_root: Path, benchmark: str) -> pd.DataFrame:
    path = (
        repo_root / "main" / "data" / "article_evidence" / "vmamba_mesh_genai_benchmark"
        / benchmark
        / "combined_summary_metrics.csv"
    )
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _algorithm_lookup_names(display_name: str) -> tuple[str, ...]:
    if display_name == VANILLA_VMAMBA_BASELINE:
        return (VANILLA_VMAMBA_BASELINE, LEGACY_VANILLA_VMAMBA_LABEL)
    return (display_name,)


def evidence_comparison_rows(repo_root: Path, spec: ArticleReproducibilitySpec) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for expected in spec.expected_metrics:
        df = _load_expected_summary(repo_root, expected.benchmark)
        actual: float | None = None
        source_path = (
            repo_root / "main" / "data" / "article_evidence" / "vmamba_mesh_genai_benchmark"
            / expected.benchmark
            / "combined_summary_metrics.csv"
        )
        if not df.empty and "algorithm" in df.columns and expected.metric in df.columns:
            match = df[df["algorithm"].astype(str).isin(_algorithm_lookup_names(expected.algorithm))]
            if not match.empty:
                actual = float(match.iloc[0][expected.metric])
        status = compare_metric(actual, expected.value, expected.tolerance)
        rows.append(
            {
                "step": "compare_expected_metric",
                "article_id": spec.article_id,
                "benchmark": expected.benchmark,
                "algorithm": expected.algorithm,
                "metric": expected.metric,
                "expected": expected.value,
                "actual": actual,
                "tolerance": expected.tolerance,
                "delta": None if actual is None else abs(actual - expected.value),
                "status": status,
                "source": str(source_path),
            }
        )
    return rows


def _candidate_model_path(repo_root: Path, benchmark: str, model_family: str, scenario: str) -> Path | None:
    root = repo_root / "main" / "data" / "architectures" / benchmark / "models"
    if "VMamba-Mesh" in model_family:
        pattern = f"vmamba_mesh/*{scenario}.pkl"
    elif "Vanilla VMamba" in model_family:
        pattern = f"vanilla_vmamba/*{scenario}.pkl"
    elif "GNN" in model_family:
        baseline = (
            repo_root
            / "main"
            / "core"
            / "algorithms"
            / "pickle"
            / "gin_gnn"
            / "modelos_gnn_separados"
            / f"{scenario}.pkl"
        )
        return baseline if baseline.exists() else None
    else:
        return None
    candidates = sorted(root.glob(pattern))
    return candidates[0] if candidates else None


def run_quick_scenario(
    repo_root: Path,
    *,
    benchmark: str,
    scenario: str,
    model_family: str,
    runs: int = 1,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run one scenario through a stored model pickle and return metrics plus trace."""
    trace: list[dict[str, Any]] = []
    arch_root = repo_root / "main" / "data" / "architectures" / benchmark
    graph_path = arch_root / "gml" / f"{scenario}.gml"
    labels_path = arch_root / "real_pairs" / f"{scenario}.json"
    model_path = _candidate_model_path(repo_root, benchmark, model_family, scenario)
    trace.append(
        {
            "step": "resolve_inputs",
            "benchmark": benchmark,
            "scenario": scenario,
            "model_family": model_family,
            "graph_path": str(graph_path),
            "labels_path": str(labels_path),
            "model_path": str(model_path) if model_path else "",
            "status": "match" if graph_path.exists() and labels_path.exists() and model_path else "not_available",
        }
    )
    if not graph_path.exists() or not labels_path.exists() or not model_path:
        return {
            "benchmark": benchmark,
            "scenario": scenario,
            "algorithm": model_family,
            "status": "not_available",
        }, trace

    graph = nx.read_gml(graph_path)
    positive_pairs = load_positive_pairs(labels_path)
    nodes = [str(node) for node in graph.nodes]
    all_pairs = [(nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))]
    pickle_module = "core.algorithms.gnn_model" if "GNN" in model_family else "core.algorithms.vmamba_mesh"
    algorithm = BoundGNNPickleAlgorithm(model_family, model_path, pickle_module)

    predicted_pairs: list[tuple[str, str]] = []
    times: list[float] = []
    for run_index in range(max(int(runs), 1)):
        started = time.perf_counter()
        predicted_pairs = algorithm.predict_pairs(graph)
        elapsed = time.perf_counter() - started
        times.append(elapsed)
        trace.append(
            {
                "step": "predict_pairs",
                "run": run_index + 1,
                "elapsed_seconds": elapsed,
                "predicted_pairs": len(predicted_pairs),
                "status": "match",
            }
        )
    metrics = confusion_metrics_pairs(positive_pairs, predicted_pairs, all_pairs=all_pairs)
    tp = int(metrics["tp"] or 0)
    fp = int(metrics["fp"] or 0)
    fn = int(metrics["fn"] or 0)
    denom = tp + fp + fn
    jaccard = tp / denom if denom else 0.0
    et = float(pd.Series(times).median()) if times else 0.0
    sf_jaccard = success_frequency(jaccard, et, len(all_pairs))
    row = {
        "benchmark": benchmark,
        "scenario": scenario,
        "algorithm": model_family,
        "runs": max(int(runs), 1),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": metrics["tn"],
        "accuracy": metrics["accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "jaccard": jaccard,
        "ET": et,
        "sf_jaccard": sf_jaccard,
        "N_pairs": len(all_pairs),
        "status": "match",
    }
    trace.append(
        {
            "step": "compute_metrics",
            "metric": "jaccard",
            "actual": jaccard,
            "ET": et,
            "sf_jaccard": sf_jaccard,
            "status": "match",
        }
    )
    return row, trace


def create_reproduction_package(
    repo_root: Path,
    *,
    spec: ArticleReproducibilitySpec,
    mode: str,
    benchmark: str | None = None,
    scenario: str | None = None,
    model_family: str | None = None,
    runs: int | None = None,
) -> dict[str, str]:
    """Create a reproducibility package under main/data/research_reports."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    package_name = f"{stamp}_article_reproduction_{spec.article_id}"
    package_dir = repo_root / "main" / "data" / "research_reports" / package_name
    package_dir.mkdir(parents=True, exist_ok=True)

    trace_rows: list[dict[str, Any]] = [
        {
            "step": "load_article_spec",
            "article_id": spec.article_id,
            "title": spec.title,
            "mode": mode,
            "runs": runs or spec.runs,
            "status": "match" if spec.status == "ready" else "not_available",
        }
    ]
    metric_rows: list[dict[str, Any]] = []
    if mode == "quick":
        selected_benchmark = benchmark or spec.benchmarks[0]
        selected_scenario = scenario or spec.scenarios[0]
        selected_model = model_family or spec.models[0]
        row, quick_trace = run_quick_scenario(
            repo_root,
            benchmark=selected_benchmark,
            scenario=selected_scenario,
            model_family=selected_model,
            runs=runs or 1,
        )
        metric_rows.append(row)
        trace_rows.extend(quick_trace)
    else:
        trace_rows.extend(evidence_comparison_rows(repo_root, spec))
        metric_rows.extend(
            {
                "benchmark": row["benchmark"],
                "algorithm": row["algorithm"],
                "metric": row["metric"],
                "expected": row["expected"],
                "actual": row["actual"],
                "status": row["status"],
            }
            for row in trace_rows
            if row.get("step") == "compare_expected_metric"
        )

    metrics_path = package_dir / "metrics.csv"
    trace_path = package_dir / "reproducibility_trace.csv"
    manifest_path = package_dir / "package_manifest.json"
    markdown_path = package_dir / f"{package_name}.md"

    pd.DataFrame(metric_rows).to_csv(metrics_path, index=False)
    pd.DataFrame(trace_rows).to_csv(trace_path, index=False)
    manifest = {
        "package_name": package_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "article": asdict(spec),
        "metrics_csv": str(metrics_path),
        "trace_csv": str(trace_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    markdown_path.write_text(
        "\n".join(
            [
                f"# Article Reproduction - {spec.title}",
                "",
                f"- Article ID: `{spec.article_id}`",
                f"- Mode: `{mode}`",
                f"- Generated at: `{manifest['generated_at']}`",
                f"- Metrics: `{metrics_path.name}`",
                f"- Trace: `{trace_path.name}`",
                "",
                "The trace records operational steps, parameters, files and metric comparisons.",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "package_name": package_name,
        "dir": str(package_dir),
        "manifest": str(manifest_path),
        "markdown": str(markdown_path),
        "metrics": str(metrics_path),
        "trace": str(trace_path),
    }
