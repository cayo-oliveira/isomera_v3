from __future__ import annotations

import json
import random
import sys
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from statistics import median
from typing import Any, Callable

sys.dont_write_bytecode = True

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

import core.algorithms  # noqa: F401,E402
from core.algorithms.gnn_pickle import BoundGNNPickleAlgorithm  # noqa: E402
from core.isomorphism import find_isomorphic_pairs  # noqa: E402
from core.lineage import adjacency_matrix_dataframe, edge_dataframe, plot_adjacency_matrix, plot_lineage_graph  # noqa: E402
from core.metrics import canonical_pairs, confusion_metrics_pairs, success_frequency  # noqa: E402
from core.scenario_api import scenario_api_contract  # noqa: E402

from build_research_report_package import build_package  # noqa: E402
from generate_isomerav2_bench_report import _save_benchmark_charts, _system_architecture  # noqa: E402


BENCHMARK_RUNS = 10
SELECTION_METRIC = "sf_jaccard"
BASELINE_PICKLE_ROOT = MAIN_ROOT / "core/algorithms/pickle/gin_gnn/modelos_gnn_separados"
ISOMERAV2_MODEL_ROOT = MAIN_ROOT / "data/architectures/isomerav2_bench/models"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(message: str) -> None:
    print(f"[routing_reports] {message}", flush=True)


def _all_pairs(graph: nx.DiGraph) -> list[tuple[str, str]]:
    nodes = sorted(str(node) for node in graph.nodes)
    return [(node_a, node_b) for node_a, node_b in combinations(nodes, 2)]


def _jaccard(true_pairs: set[tuple[str, str]], predicted_pairs: set[tuple[str, str]]) -> float:
    union = true_pairs | predicted_pairs
    return 1.0 if not union else len(true_pairs & predicted_pairs) / len(union)


def _scenario_paths(architecture_name: str) -> tuple[Path, Path]:
    root = MAIN_ROOT / "data/architectures" / architecture_name
    return root / "gml", root / "real_pairs"


def _load_scenarios(architecture_name: str) -> dict[str, dict[str, Any]]:
    gml_root, real_pairs_root = _scenario_paths(architecture_name)
    scenarios: dict[str, dict[str, Any]] = {}
    for gml_path in sorted(gml_root.glob("*.gml")):
        label_path = real_pairs_root / f"{gml_path.stem}.json"
        if not label_path.exists():
            continue
        graph = nx.read_gml(gml_path)
        labels = [tuple(pair) for pair in json.loads(label_path.read_text(encoding="utf-8"))]
        scenarios[gml_path.stem] = {
            "graph": graph,
            "labels": labels,
            "gml_path": gml_path,
            "labels_path": label_path,
        }
    return scenarios


def _baseline_pickle_paths(scenario_names: list[str]) -> dict[str, Path]:
    paths = {}
    for scenario_name in scenario_names:
        pickle_path = BASELINE_PICKLE_ROOT / f"{scenario_name}.pkl"
        if pickle_path.exists():
            paths[scenario_name] = pickle_path
    return paths


def _isomerav2_pickles() -> dict[str, Path]:
    paths = {}
    for pickle_path in sorted(ISOMERAV2_MODEL_ROOT.glob("GNN_isomerav2_test_*.pkl")):
        scenario_name = pickle_path.stem.replace("GNN_isomerav2_test_", "")
        paths[scenario_name] = pickle_path
    return paths


def _predict_with_timing(predictor: Callable[[nx.DiGraph], list[tuple[str, str]]], graph: nx.DiGraph, runs: int) -> tuple[set[tuple[str, str]], list[float]]:
    predictions: set[tuple[str, str]] = set()
    timings: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        current_predictions = canonical_pairs(predictor(graph))
        timings.append(time.perf_counter() - start)
        predictions = current_predictions
    return predictions, timings


def _metric_row(
    *,
    scenario_name: str,
    graph: nx.DiGraph,
    labels: list[tuple[str, str]],
    algorithm: str,
    predicted: set[tuple[str, str]],
    timings: list[float],
    artifact_path: str = "",
    artifact_role: str = "",
    route_mode: str = "",
    route_source: str = "",
    selection_metric: str = "",
    selection_candidates: int = 0,
) -> dict[str, Any]:
    true_set = canonical_pairs(labels)
    all_pairs = _all_pairs(graph)
    metrics = confusion_metrics_pairs(true_set, predicted, all_pairs=all_pairs)
    et = float(median(timings)) if timings else 0.0
    accuracy = float(metrics["accuracy"] or 0.0)
    jaccard = _jaccard(true_set, predicted)
    evaluated_pairs = len(all_pairs)
    return {
        "scenario": scenario_name,
        "algorithm": algorithm,
        "artifact_path": artifact_path,
        "artifact_role": artifact_role,
        "route_mode": route_mode,
        "route_source": route_source,
        "selection_metric": selection_metric,
        "selection_candidates": selection_candidates,
        "accuracy": round(accuracy, 6),
        "jaccard": round(jaccard, 6),
        "sf_jaccard": round(success_frequency(jaccard, et, evaluated_pairs), 6),
        "sf_accuracy": round(success_frequency(accuracy, et, evaluated_pairs), 6),
        "ET": round(et, 6),
        "median_execution_time": round(et, 6),
        "N_pairs": evaluated_pairs,
        "tp": metrics["tp"],
        "fp": metrics["fp"],
        "fn": metrics["fn"],
        "tn": metrics["tn"],
        "precision": round(float(metrics["precision"] or 0.0), 6),
        "recall": round(float(metrics["recall"] or 0.0), 6),
        "f1": round(float(metrics["f1"] or 0.0), 6),
        "runs": len(timings),
    }


def _aggregate_metrics(per_scenario: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(per_scenario)
    rows: list[dict[str, Any]] = []
    for algorithm, group in df.groupby("algorithm", sort=False):
        tp_sum = int(group["tp"].sum())
        fp_sum = int(group["fp"].sum())
        fn_sum = int(group["fn"].sum())
        tn_sum = int(group["tn"].sum())
        accuracy_denom = tp_sum + tn_sum + fp_sum + fn_sum
        jaccard_denom = tp_sum + fp_sum + fn_sum
        rows.append(
            {
                "algorithm": algorithm,
                "accuracy": round(float((tp_sum + tn_sum) / accuracy_denom) if accuracy_denom else 0.0, 6),
                "jaccard": round(float(tp_sum / jaccard_denom) if jaccard_denom else 0.0, 6),
                "sf_jaccard": round(float(group["sf_jaccard"].mean()), 6),
                "sf_accuracy": round(float(group["sf_accuracy"].mean()), 6),
                "ET": round(float(group["ET"].median()), 6),
                "median_execution_time": round(float(group["ET"].median()), 6),
                "N_pairs": int(group["N_pairs"].sum()),
                "tp": tp_sum,
                "fp": fp_sum,
                "fn": fn_sum,
                "tn": tn_sum,
                "scenarios": int(group["scenario"].nunique()),
                "runs": BENCHMARK_RUNS,
                "aggregation": "SF columns are computed per scenario with score * N_pairs / ET and then averaged across scenarios.",
            }
        )
    return rows


def _evaluate_best_of_cluster(
    *,
    scenario_name: str,
    graph: nx.DiGraph,
    labels: list[tuple[str, str]],
    candidate_paths: list[Path],
    algorithm: str,
    artifact_role: str,
    route_source: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    selection_rows: list[dict[str, Any]] = []
    for candidate_path in candidate_paths:
        predictor = BoundGNNPickleAlgorithm(
            f"{algorithm} candidate [{candidate_path.stem}]",
            candidate_path,
            "core.algorithms.gnn_model",
        ).predict_pairs
        predicted, timings = _predict_with_timing(predictor, graph, runs=1)
        row = _metric_row(
            scenario_name=scenario_name,
            graph=graph,
            labels=labels,
            algorithm=algorithm,
            predicted=predicted,
            timings=timings,
            artifact_path=str(candidate_path),
            artifact_role=artifact_role,
            route_mode="best_of_cluster_candidate",
            route_source=route_source,
            selection_metric=SELECTION_METRIC,
            selection_candidates=len(candidate_paths),
        )
        row["candidate_rank_metric"] = row[SELECTION_METRIC]
        selection_rows.append(row)
    selected = max(
        selection_rows,
        key=lambda row: (
            float(row.get(SELECTION_METRIC, 0.0) or 0.0),
            float(row.get("jaccard", 0.0) or 0.0),
            -float(row.get("ET", 0.0) or 0.0),
        ),
    )
    selected_path = Path(str(selected["artifact_path"]))
    predictor = BoundGNNPickleAlgorithm(
        f"{algorithm} selected [{selected_path.stem}]",
        selected_path,
        "core.algorithms.gnn_model",
    ).predict_pairs
    predicted, timings = _predict_with_timing(predictor, graph, runs=BENCHMARK_RUNS)
    final_row = _metric_row(
        scenario_name=scenario_name,
        graph=graph,
        labels=labels,
        algorithm=algorithm,
        predicted=predicted,
        timings=timings,
        artifact_path=str(selected_path),
        artifact_role=artifact_role,
        route_mode="best_of_cluster",
        route_source=route_source,
        selection_metric=SELECTION_METRIC,
        selection_candidates=len(candidate_paths),
    )
    final_row["selection_rank_metric"] = selected[SELECTION_METRIC]
    return final_row, selection_rows


def _scenario_details(scenarios: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for scenario_name, payload in scenarios.items():
        graph = payload["graph"]
        rows.append(
            {
                "scenario": scenario_name,
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "total_pairs": len(_all_pairs(graph)),
                "positive_pairs": len(payload["labels"]),
                "gml_path": str(payload["gml_path"]),
                "labels_path": str(payload["labels_path"]),
            }
        )
    return rows


def _lineage_rows(scenarios: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    lineage_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    adjacency_rows: list[dict[str, Any]] = []
    for scenario_name, payload in scenarios.items():
        graph = payload["graph"]
        for node, attrs in sorted(graph.nodes(data=True), key=lambda item: str(item[0])):
            lineage_rows.append(
                {
                    "scenario": scenario_name,
                    "domain": attrs.get("domain"),
                    "layer": attrs.get("type"),
                    "node": node,
                    "in_degree": graph.in_degree(node),
                    "out_degree": graph.out_degree(node),
                }
            )
        edge_df = edge_dataframe(graph)
        edge_df.insert(0, "scenario", scenario_name)
        edge_rows.extend(edge_df.to_dict(orient="records"))
        adjacency_df = adjacency_matrix_dataframe(graph).reset_index().rename(columns={"index": "node"})
        adjacency_df.insert(0, "scenario", scenario_name)
        adjacency_rows.extend(adjacency_df.to_dict(orient="records"))
    return lineage_rows, edge_rows, adjacency_rows


def _build_capture(
    *,
    benchmark_name: str,
    report_type: str,
    architecture_name: str,
    scenarios: dict[str, dict[str, Any]],
    per_scenario_metrics: list[dict[str, Any]],
    selection_rows: list[dict[str, Any]],
    routing_rows: list[dict[str, Any]],
    cluster_rows: list[dict[str, Any]],
) -> Path:
    capture_root = MAIN_ROOT / "data/article_capture" / benchmark_name
    capture_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{stamp}_{report_type}_{benchmark_name}"
    json_path = capture_root / f"{base_name}.json"
    md_path = capture_root / f"{base_name}.md"
    lineage_png = capture_root / f"{base_name}_lineage.png"
    adjacency_png = capture_root / f"{base_name}_adjacency.png"

    first_graph = next(iter(scenarios.values()))["graph"]
    fig = plot_lineage_graph(first_graph, seed=42)
    fig.savefig(lineage_png, bbox_inches="tight", dpi=300)
    plt.close(fig)
    fig = plot_adjacency_matrix(first_graph)
    fig.savefig(adjacency_png, bbox_inches="tight", dpi=300)
    plt.close(fig)

    benchmark_metrics = _aggregate_metrics(per_scenario_metrics)
    chart_paths = _save_benchmark_charts(benchmark_metrics, per_scenario_metrics, capture_root)
    lineage_structure, lineage_edges, adjacency = _lineage_rows(scenarios)
    scenario_rows = _scenario_details(scenarios)
    total_pairs = sum(int(row["total_pairs"]) for row in scenario_rows)
    positive_pairs = sum(int(row["positive_pairs"]) for row in scenario_rows)
    source_details = [
        {"field": "benchmark_name", "value": benchmark_name},
        {"field": "architecture_name", "value": architecture_name},
        {"field": "scenario_count", "value": len(scenarios)},
        {"field": "benchmark_runs", "value": BENCHMARK_RUNS},
        {"field": "selection_metric", "value": SELECTION_METRIC},
        {"field": "routing_policy", "value": "scenario_specific, manual_random_fill, or best_of_cluster depending on cluster"},
    ]
    pipeline = [
        {"stage": "source", "input": f"{architecture_name} GML/JSON scenarios", "output": f"{len(scenarios)} scenarios", "details": "Scenarios are loaded from the Isomera architecture catalog."},
        {"stage": "normalized_graph", "input": "GML graph", "output": f"{sum(row['nodes'] for row in scenario_rows)} nodes / {sum(row['edges'] for row in scenario_rows)} edges", "details": "Graphs already follow the canonical SOR -> SOT -> SPEC contract or are consumed through the same normalized graph interface."},
        {"stage": "validation_dataset", "input": "real_pairs JSON + all pair combinations", "output": f"{total_pairs} labeled candidate rows", "details": "real_pairs are positives; all remaining node pairs are negatives."},
        {"stage": "model_routing", "input": "model clusters and routing policy", "output": f"{len(routing_rows)} scenario-artifact routes", "details": "The report records exact pickle paths and any best-of selection policy."},
        {"stage": "benchmark_execution", "input": "VF2, Node Match, GNN v1 cluster, GNN v2 cluster", "output": f"{len(per_scenario_metrics)} metric rows", "details": f"Each detector family uses {BENCHMARK_RUNS} runs after routing."},
    ]
    payload = {
        "captured_at": _utcnow(),
        "report_type": report_type,
        "summary": {
            "benchmark_name": benchmark_name,
            "scenario": f"{benchmark_name}_{len(scenarios)}_scenarios",
            "scenario_count": len(scenarios),
            "total_pairs": total_pairs,
            "positive_pairs": positive_pairs,
            "candidate_pairs": total_pairs,
            "reviewed_pairs": total_pairs,
            "duplicate_pairs": positive_pairs,
            "benchmark_runs": BENCHMARK_RUNS,
            "model_name": "routing_4_detector_families",
            "primary_metric": "sf_jaccard",
        },
        "source_metadata": {
            "architecture_name": architecture_name,
            "scenario_root": str(MAIN_ROOT / "data/architectures" / architecture_name),
        },
        "graph_summary": {
            "scenario_count": len(scenarios),
            "node_count": sum(payload["graph"].number_of_nodes() for payload in scenarios.values()),
            "edge_count": sum(payload["graph"].number_of_edges() for payload in scenarios.values()),
        },
        "system_architecture": _system_architecture(),
        "scenario_api": scenario_api_contract(),
        "formula_parameter_mapping": {
            "sf_jaccard": "jaccard * N_pairs / ET",
            "sf_accuracy": "accuracy * N_pairs / ET",
            "selection_metric": SELECTION_METRIC,
            "benchmark_runs": BENCHMARK_RUNS,
        },
        "publication_tables": {
            "source_details": source_details,
            "pipeline": pipeline,
            "scenario_details": scenario_rows,
            "lineage_structure": lineage_structure,
            "lineage_edges": lineage_edges,
            "adjacency_matrix": adjacency,
            "model_cluster_summary": cluster_rows,
            "model_cluster_routing": routing_rows,
            "benchmark_metrics": benchmark_metrics,
            "benchmark_per_scenario_metrics": per_scenario_metrics,
            "benchmark_pickle_results": [
                row for row in per_scenario_metrics if str(row.get("artifact_path") or "")
            ],
            "best_of_selection_results": selection_rows,
            "filters": [
                {
                    "setting": "all pair combinations",
                    "value": "enabled",
                    "effect": "Every node pair is labeled through ground truth positives and implicit negatives.",
                }
            ],
        },
        "capture_paths": {
            "json": str(json_path),
            "markdown": str(md_path),
            "lineage_png": str(lineage_png),
            "adjacency_png": str(adjacency_png),
            **chart_paths,
        },
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"# Isomera Routing Report: {benchmark_name}",
                "",
                f"- Scenarios: {len(scenarios)}",
                f"- Runs: {BENCHMARK_RUNS}",
                f"- Primary metric: sf_jaccard",
                "",
                "This capture was generated by the automated routing report script and is equivalent to an Article Capture evidence file.",
            ]
        ),
        encoding="utf-8",
    )
    return json_path


def _run_v1_report() -> dict[str, str | None]:
    benchmark_name = "tpcds_v1_routing_experiment"
    scenarios = _load_scenarios("tpc_ds")
    scenario_names = sorted(scenarios)
    v1_routes = _baseline_pickle_paths(scenario_names)
    v2_pickles = _isomerav2_pickles()
    if len(v1_routes) != len(scenario_names):
        missing = sorted(set(scenario_names) - set(v1_routes))
        raise FileNotFoundError(f"Missing v1 baseline pickles: {missing}")
    if len(v2_pickles) < 2:
        raise FileNotFoundError("Expected at least two Isomera v2 pickles in isomerav2_bench/models.")

    rng = random.Random(42)
    v2_candidates = [v2_pickles[key] for key in sorted(v2_pickles)]
    v2_routes: dict[str, Path] = {}
    for scenario_name in scenario_names:
        v2_routes[scenario_name] = v2_pickles.get(scenario_name) or rng.choice(v2_candidates)

    per_scenario: list[dict[str, Any]] = []
    routing_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        graph = scenarios[scenario_name]["graph"]
        labels = scenarios[scenario_name]["labels"]
        detectors = [
            ("VF2", lambda g: find_isomorphic_pairs(g, algorithm="VF2"), "", "deterministic_baseline", "not_applicable", "deterministic_algorithm"),
            ("Node Match", lambda g: find_isomorphic_pairs(g, algorithm="Node Match (Custom)"), "", "deterministic_baseline", "not_applicable", "deterministic_algorithm"),
            (
                "GNN TPC-DS v1 cluster",
                BoundGNNPickleAlgorithm(f"GNN TPC-DS v1 [{scenario_name}]", v1_routes[scenario_name], "core.algorithms.gnn_model").predict_pairs,
                str(v1_routes[scenario_name]),
                "baseline_tpcds_pickle",
                "scenario_specific",
                "script_exact_v1_mapping",
            ),
            (
                "GNN Isomera v2 cluster",
                BoundGNNPickleAlgorithm(f"GNN Isomera v2 mapped [{scenario_name}]", v2_routes[scenario_name], "core.algorithms.gnn_model").predict_pairs,
                str(v2_routes[scenario_name]),
                "new_isomerav2_pickle",
                "manual_random_fill_from_two_pickles" if scenario_name not in v2_pickles else "scenario_specific",
                "script_simulated_manual_mapping",
            ),
        ]
        _log(f"v1 evaluating {scenario_name}")
        for algorithm, predictor, artifact_path, artifact_role, route_mode, route_source in detectors:
            predicted, timings = _predict_with_timing(predictor, graph, BENCHMARK_RUNS)
            per_scenario.append(
                _metric_row(
                    scenario_name=scenario_name,
                    graph=graph,
                    labels=labels,
                    algorithm=algorithm,
                    predicted=predicted,
                    timings=timings,
                    artifact_path=artifact_path,
                    artifact_role=artifact_role,
                    route_mode=route_mode,
                    route_source=route_source,
                )
            )
        routing_rows.extend(
            [
                {
                    "model_family": "GNN TPC-DS v1 cluster",
                    "scenario": scenario_name,
                    "artifact_path": str(v1_routes[scenario_name]),
                    "artifact_role": "baseline_tpcds_pickle",
                    "route_mode": "scenario_specific",
                    "route_source": "script_exact_v1_mapping",
                },
                {
                    "model_family": "GNN Isomera v2 cluster",
                    "scenario": scenario_name,
                    "artifact_path": str(v2_routes[scenario_name]),
                    "artifact_role": "new_isomerav2_pickle",
                    "route_mode": "manual_random_fill_from_two_pickles" if scenario_name not in v2_pickles else "scenario_specific",
                    "route_source": "script_simulated_manual_mapping",
                },
            ]
        )
    cluster_rows = [
        {"model_family": "VF2", "artifact_count": 0, "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "deterministic detector"},
        {"model_family": "Node Match", "artifact_count": 0, "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "deterministic detector"},
        {"model_family": "GNN TPC-DS v1 cluster", "artifact_count": len(v1_routes), "scenario_count": len(scenario_names), "coverage": f"{len(v1_routes)}/{len(scenario_names)}", "reporting_rule": "one baseline pickle routed per scenario"},
        {"model_family": "GNN Isomera v2 cluster", "artifact_count": len(set(v2_routes.values())), "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "two new pickles manually mapped to all v1 scenarios for transfer/generalization testing"},
    ]
    capture_path = _build_capture(
        benchmark_name=benchmark_name,
        report_type="tpcds_v1_full_routing_experiment",
        architecture_name="tpc_ds",
        scenarios=scenarios,
        per_scenario_metrics=per_scenario,
        selection_rows=selection_rows,
        routing_rows=routing_rows,
        cluster_rows=cluster_rows,
    )
    return build_package(capture_path)


def _run_v2_report() -> dict[str, str | None]:
    benchmark_name = "isomerav2_bench_bestof_experiment"
    scenarios = _load_scenarios("isomerav2_bench")
    scenario_names = sorted(scenarios)
    v1_candidates = sorted(BASELINE_PICKLE_ROOT.glob("*.pkl"))
    v2_routes = _isomerav2_pickles()
    missing_v2 = sorted(set(scenario_names) - set(v2_routes))
    if missing_v2:
        raise FileNotFoundError(f"Missing Isomera v2 pickles for scenarios: {missing_v2}")

    per_scenario: list[dict[str, Any]] = []
    routing_rows: list[dict[str, Any]] = []
    selection_rows: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        graph = scenarios[scenario_name]["graph"]
        labels = scenarios[scenario_name]["labels"]
        _log(f"v2 evaluating {scenario_name}")
        for algorithm, predictor, artifact_path, artifact_role, route_mode, route_source in [
            ("VF2", lambda g: find_isomorphic_pairs(g, algorithm="VF2"), "", "deterministic_baseline", "not_applicable", "deterministic_algorithm"),
            ("Node Match", lambda g: find_isomorphic_pairs(g, algorithm="Node Match (Custom)"), "", "deterministic_baseline", "not_applicable", "deterministic_algorithm"),
        ]:
            predicted, timings = _predict_with_timing(predictor, graph, BENCHMARK_RUNS)
            per_scenario.append(
                _metric_row(
                    scenario_name=scenario_name,
                    graph=graph,
                    labels=labels,
                    algorithm=algorithm,
                    predicted=predicted,
                    timings=timings,
                    artifact_path=artifact_path,
                    artifact_role=artifact_role,
                    route_mode=route_mode,
                    route_source=route_source,
                )
            )
        best_row, candidate_rows = _evaluate_best_of_cluster(
            scenario_name=scenario_name,
            graph=graph,
            labels=labels,
            candidate_paths=v1_candidates,
            algorithm="GNN TPC-DS v1 cluster",
            artifact_role="baseline_tpcds_pickle",
            route_source="script_best_of_cluster_policy",
        )
        per_scenario.append(best_row)
        selection_rows.extend(candidate_rows)

        v2_path = v2_routes[scenario_name]
        predictor = BoundGNNPickleAlgorithm(f"GNN Isomera v2 [{scenario_name}]", v2_path, "core.algorithms.gnn_model").predict_pairs
        predicted, timings = _predict_with_timing(predictor, graph, BENCHMARK_RUNS)
        per_scenario.append(
            _metric_row(
                scenario_name=scenario_name,
                graph=graph,
                labels=labels,
                algorithm="GNN Isomera v2 cluster",
                predicted=predicted,
                timings=timings,
                artifact_path=str(v2_path),
                artifact_role="new_isomerav2_pickle",
                route_mode="scenario_specific",
                route_source="script_exact_v2_mapping",
            )
        )
        routing_rows.extend(
            [
                {
                    "model_family": "GNN TPC-DS v1 cluster",
                    "scenario": scenario_name,
                    "artifact_path": best_row["artifact_path"],
                    "artifact_role": "baseline_tpcds_pickle",
                    "route_mode": "best_of_cluster",
                    "route_source": "script_best_of_cluster_policy",
                    "selection_metric": SELECTION_METRIC,
                    "selection_candidates": len(v1_candidates),
                },
                {
                    "model_family": "GNN Isomera v2 cluster",
                    "scenario": scenario_name,
                    "artifact_path": str(v2_path),
                    "artifact_role": "new_isomerav2_pickle",
                    "route_mode": "scenario_specific",
                    "route_source": "script_exact_v2_mapping",
                },
            ]
        )
    cluster_rows = [
        {"model_family": "VF2", "artifact_count": 0, "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "deterministic detector"},
        {"model_family": "Node Match", "artifact_count": 0, "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "deterministic detector"},
        {"model_family": "GNN TPC-DS v1 cluster", "artifact_count": len(v1_candidates), "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": f"best-of-cluster selection by {SELECTION_METRIC}; every baseline pickle is tested once per scenario before selecting the final route"},
        {"model_family": "GNN Isomera v2 cluster", "artifact_count": len(v2_routes), "scenario_count": len(scenario_names), "coverage": f"{len(v2_routes)}/{len(scenario_names)}", "reporting_rule": "one newly trained pickle routed per scenario"},
    ]
    capture_path = _build_capture(
        benchmark_name=benchmark_name,
        report_type="isomerav2_two_scenario_bestof_cluster",
        architecture_name="isomerav2_bench",
        scenarios=scenarios,
        per_scenario_metrics=per_scenario,
        selection_rows=selection_rows,
        routing_rows=routing_rows,
        cluster_rows=cluster_rows,
    )
    return build_package(capture_path)


def main() -> None:
    started = time.perf_counter()
    outputs = {
        "v1": _run_v1_report(),
        "v2": _run_v2_report(),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    print(json.dumps(outputs, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
