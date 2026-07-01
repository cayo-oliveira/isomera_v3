from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from statistics import median
from typing import Any

sys.dont_write_bytecode = True

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

import core.algorithms  # noqa: F401,E402
from core.algorithms.gnn_pickle import BoundGNNPickleAlgorithm  # noqa: E402
from core.algorithms.gnn_training import ScenarioTrainingSpec, train_benchmark_gnn  # noqa: E402
from core.database import create_database_engine  # noqa: E402
from core.isomorphism import find_isomorphic_pairs  # noqa: E402
from core.lineage import adjacency_matrix_dataframe, edge_dataframe, plot_adjacency_matrix, plot_lineage_graph  # noqa: E402
from core.metrics import canonical_pairs, confusion_metrics_pairs, success_frequency  # noqa: E402
from core.publication_store import init_publication_store, publish_curated_scenario  # noqa: E402
from core.scenario_api import materialize_database_scenario, scenario_api_contract  # noqa: E402

from build_research_report_package import build_package  # noqa: E402


POSTGRES_URL = "postgresql+psycopg://localhost:5432/isomera_tpcds_benchmark"
MYSQL_URL = "mysql+pymysql://root@localhost/isomera_publication?unix_socket=/tmp/mysql.sock"
BENCHMARK_NAME = "isomerav2_bench"
REPORT_TYPE = "isomerav2_two_scenario_full_pipeline"
BENCHMARK_RUNS = 10
TRAIN_EPOCHS = 2
TRAIN_RATIO = 0.8
HIDDEN_CHANNELS = 16
DROPOUT = 0.2
LEARNING_RATE = 0.005
NEGATIVE_RATIO = 1
SEED = 42

SCENARIOS = [
    {"scenario": "graph_SOR2_D5_seed42", "schema": "scenario_sor2_d5_seed42"},
    {"scenario": "graph_SOR8_D5_seed42", "schema": "scenario_sor8_d5_seed42"},
]


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(message: str) -> None:
    print(f"[isomerav2_bench] {message}", flush=True)


def _training_progress_logger(scenario_name: str):
    def _callback(payload: dict[str, Any]) -> None:
        step = payload.get("step", "training")
        epoch = payload.get("current_epoch", 0)
        epochs = payload.get("epochs", "-")
        detail = payload.get("step_detail", "")
        metrics = ""
        if payload.get("train_loss") is not None:
            metrics = (
                f" train_loss={payload.get('train_loss')} val_loss={payload.get('val_loss')} "
                f"train_acc={payload.get('train_accuracy')} val_acc={payload.get('val_accuracy')}"
            )
        _log(f"{scenario_name}: {step} epoch={epoch}/{epochs} {detail}{metrics}")

    return _callback


def _capture_root() -> Path:
    root = MAIN_ROOT / "data" / "article_capture" / BENCHMARK_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _benchmark_root() -> Path:
    root = MAIN_ROOT / "data" / "architectures" / BENCHMARK_NAME
    for child in ("gml", "real_pairs", "models"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def _load_positive_pairs(scenario_name: str) -> list[tuple[str, str]]:
    labels_path = MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "real_pairs" / f"{scenario_name}.json"
    return [tuple(pair) for pair in json.loads(labels_path.read_text(encoding="utf-8"))]


def _all_pairs(graph: nx.DiGraph) -> list[tuple[str, str]]:
    nodes = sorted(str(node) for node in graph.nodes)
    return [(node_a, node_b) for node_a, node_b in combinations(nodes, 2)]


def _validation_rows(
    graph: nx.DiGraph,
    positive_pairs: list[tuple[str, str]],
    *,
    scenario_name: str,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    positive_set = canonical_pairs(positive_pairs)
    rows: list[dict[str, Any]] = []
    reviewed_pairs: dict[tuple[str, str], dict[str, Any]] = {}
    for index, (node_a, node_b) in enumerate(_all_pairs(graph), start=1):
        canonical = tuple(sorted((node_a, node_b)))
        target = 1 if canonical in positive_set else 0
        decision = "duplicate" if target else "not_duplicate"
        row = {
            "scenario": scenario_name,
            "pair_index": index,
            "node_a": node_a,
            "node_b": node_b,
            "layer_a": str(graph.nodes[node_a].get("type") or node_a.split("_", 1)[0]),
            "layer_b": str(graph.nodes[node_b].get("type") or node_b.split("_", 1)[0]),
            "domain_a": str(graph.nodes[node_a].get("domain") or node_a.rsplit("_", 1)[-1]),
            "domain_b": str(graph.nodes[node_b].get("domain") or node_b.rsplit("_", 1)[-1]),
            "decision": decision,
            "target": target,
            "reviewed_at": _utcnow(),
        }
        rows.append(row)
        reviewed_pairs[canonical] = {"decision": decision, "timestamp": row["reviewed_at"]}
    return rows, reviewed_pairs


def _mysql_row_counts(database_url: str, *, benchmark_name: str) -> list[dict[str, object]]:
    engine = create_database_engine(database_url)
    with engine.connect() as conn:
        return [
            {
                "table": "publication_benchmarks",
                "rows": int(
                    conn.execute(
                        text("SELECT COUNT(*) FROM publication_benchmarks WHERE benchmark_id = :benchmark_id"),
                        {"benchmark_id": benchmark_name},
                    ).scalar_one()
                ),
            },
            {
                "table": "publication_scenarios",
                "rows": int(
                    conn.execute(
                        text("SELECT COUNT(*) FROM publication_scenarios WHERE benchmark_id = :benchmark_id"),
                        {"benchmark_id": benchmark_name},
                    ).scalar_one()
                ),
            },
            {
                "table": "publication_nodes",
                "rows": int(
                    conn.execute(
                        text(
                            "SELECT COUNT(*) FROM publication_nodes WHERE scenario_id IN "
                            "(SELECT scenario_id FROM publication_scenarios WHERE benchmark_id = :benchmark_id)"
                        ),
                        {"benchmark_id": benchmark_name},
                    ).scalar_one()
                ),
            },
            {
                "table": "publication_edges",
                "rows": int(
                    conn.execute(
                        text(
                            "SELECT COUNT(*) FROM publication_edges WHERE scenario_id IN "
                            "(SELECT scenario_id FROM publication_scenarios WHERE benchmark_id = :benchmark_id)"
                        ),
                        {"benchmark_id": benchmark_name},
                    ).scalar_one()
                ),
            },
            {
                "table": "publication_pairs",
                "rows": int(
                    conn.execute(
                        text(
                            "SELECT COUNT(*) FROM publication_pairs WHERE scenario_id IN "
                            "(SELECT scenario_id FROM publication_scenarios WHERE benchmark_id = :benchmark_id)"
                        ),
                        {"benchmark_id": benchmark_name},
                    ).scalar_one()
                ),
            },
            {
                "table": "publication_reports",
                "rows": int(
                    conn.execute(
                        text("SELECT COUNT(*) FROM publication_reports WHERE benchmark_id = :benchmark_id"),
                        {"benchmark_id": benchmark_name},
                    ).scalar_one()
                ),
            },
        ]


def _graph_summary(graphs: dict[str, nx.DiGraph]) -> dict[str, Any]:
    layer_counts: dict[str, int] = {}
    for graph in graphs.values():
        for _, attrs in graph.nodes(data=True):
            layer = str(attrs.get("type") or "UNK")
            layer_counts[layer] = layer_counts.get(layer, 0) + 1
    return {
        "node_count": sum(graph.number_of_nodes() for graph in graphs.values()),
        "edge_count": sum(graph.number_of_edges() for graph in graphs.values()),
        "scenario_count": len(graphs),
        "layer_counts": layer_counts,
    }


def _system_architecture() -> dict[str, object]:
    return {
        "overview": (
            "Isomera v2 is a layered research system for transforming relational benchmark schemas into "
            "normalized lineage graphs, creating supervised duplicate-pair datasets, training scenario-specific "
            "GNN artifacts, and publishing reproducible benchmark evidence."
        ),
        "layers": [
            {"layer": "Presentation Layer", "responsibility": "Streamlit modules expose source selection, validation, training, benchmark execution, admin inspection, and report export."},
            {"layer": "Scenario Materialization API", "responsibility": "Converts PostgreSQL schemas, GML files, or future connectors into the same graph, edge table, adjacency matrix, and metadata contract."},
            {"layer": "Lineage Normalization Layer", "responsibility": "Normalizes directed edges to the canonical SOR -> SOT -> SPEC flow when layer semantics are available."},
            {"layer": "Validation Dataset Layer", "responsibility": "Stores reviewed pair decisions as a supervised table with binary target values."},
            {"layer": "Training and Benchmark Layer", "responsibility": "Trains Graph Isomorphism Network Pair Classifier artifacts and evaluates detector families with repeated timing runs."},
            {"layer": "Publication and Research Package Layer", "responsibility": "Writes MySQL publication rows plus Markdown, JSON, CSV, image, pickle, LaTeX, PDF, and ZIP evidence."},
        ],
        "stores": [
            {"store": "Scenario Warehouse", "technology": "PostgreSQL", "purpose": "External relational benchmark source. Each scenario is one schema, and manifests map tables to domains, SOR/SOT/SPEC layers, and lineage edges."},
            {"store": "Publication Backend", "technology": "MySQL", "purpose": "Operational and research backend for published benchmarks, scenarios, nodes, edges, reviewed pairs, reports, and future logs/artifacts."},
            {"store": "Portable Scenario Files", "technology": "GML/JSON", "purpose": "Reproducible graph, label, manifest, and benchmark metadata files for DOI/data sharing."},
            {"store": "Model Artifacts", "technology": "Pickle/JSON", "purpose": "Scenario-specific GNN artifacts plus metadata describing input contract and training hyperparameters."},
            {"store": "Research Reports", "technology": "LaTeX/PDF/ZIP", "purpose": "Article-ready package containing narrative, figures, metrics, tables, source data, and model references."},
        ],
    }


def _pipeline_rows(scenario_rows: list[dict[str, Any]], training_rows: list[dict[str, Any]], model_paths: dict[str, Path]) -> list[dict[str, object]]:
    return [
        {
            "stage": "source",
            "input": "PostgreSQL scenario warehouse",
            "output": f"{len(scenario_rows)} scenario schemas",
            "details": "Each selected schema is read through the Scenario Materialization API.",
        },
        {
            "stage": "normalized_graph",
            "input": "Warehouse manifest contract",
            "output": f"{sum(int(row['nodes']) for row in scenario_rows)} nodes / {sum(int(row['edges']) for row in scenario_rows)} edges",
            "details": "Edges are normalized to SOR -> SOT -> SPEC before validation, training, or benchmarking.",
        },
        {
            "stage": "validation_dataset",
            "input": "Ground-truth duplicate labels and all node-pair combinations",
            "output": f"{sum(int(row['total_pairs']) for row in scenario_rows)} labeled rows",
            "details": "For this full test, TPC-DS real_pairs are treated as positive labels and all other pairs are negative labels.",
        },
        {
            "stage": "training_dataset",
            "input": "Normalized graph + positive duplicate labels",
            "output": f"{sum(int(row['dataset_rows']) for row in training_rows)} sampled rows",
            "details": f"negative_ratio={NEGATIVE_RATIO}, train_ratio={TRAIN_RATIO}, balancing=negative_sampling.",
        },
        {
            "stage": "model_artifact",
            "input": "GIN pair training loop per scenario",
            "output": f"{len(model_paths)} new Isomera v2 GNN pickles",
            "details": "Each scenario routes to its own pickle inside the same detector family/cluster.",
        },
        {
            "stage": "benchmark_execution",
            "input": "Detector families + scenario-specific artifact routing",
            "output": f"4 detector families, {BENCHMARK_RUNS} runs each",
            "details": "VF2, Node Match, TPC-DS GNN v1 cluster, and Isomera v2 GNN cluster.",
        },
    ]


def _jaccard(true_pairs: set[tuple[str, str]], predicted_pairs: set[tuple[str, str]]) -> float:
    union = true_pairs | predicted_pairs
    return 1.0 if not union else len(true_pairs & predicted_pairs) / len(union)


def _predict_with_timing(graph: nx.DiGraph, predictor, runs: int) -> tuple[set[tuple[str, str]], list[float]]:
    predictions: set[tuple[str, str]] = set()
    times: list[float] = []
    for _ in range(runs):
        start = time.perf_counter()
        current_predictions = canonical_pairs(predictor(graph))
        times.append(time.perf_counter() - start)
        predictions = current_predictions
    return predictions, times


def _run_benchmark(
    graphs: dict[str, nx.DiGraph],
    labels: dict[str, list[tuple[str, str]]],
    v1_paths: dict[str, Path],
    v2_paths: dict[str, Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    per_scenario: list[dict[str, Any]] = []
    for scenario_name, graph in graphs.items():
        true_set = canonical_pairs(labels[scenario_name])
        all_pairs = _all_pairs(graph)
        detectors = [
            {
                "algorithm": "VF2",
                "predictor": lambda g: find_isomorphic_pairs(g, algorithm="VF2"),
                "artifact_path": "",
                "artifact_role": "deterministic_baseline",
                "route_mode": "not_applicable",
                "route_source": "deterministic_algorithm",
            },
            {
                "algorithm": "Node Match",
                "predictor": lambda g: find_isomorphic_pairs(g, algorithm="Node Match (Custom)"),
                "artifact_path": "",
                "artifact_role": "deterministic_baseline",
                "route_mode": "not_applicable",
                "route_source": "deterministic_algorithm",
            },
            {
                "algorithm": "GNN TPC-DS v1 cluster",
                "predictor": BoundGNNPickleAlgorithm(
                    f"GNN TPC-DS v1 [{scenario_name}]",
                    v1_paths[scenario_name],
                    "core.algorithms.gnn_model",
                ).predict_pairs,
                "artifact_path": str(v1_paths[scenario_name]),
                "artifact_role": "baseline_tpcds_pickle",
                "route_mode": "scenario_specific",
                "route_source": "script_explicit_mapping",
            },
            {
                "algorithm": "GNN Isomera v2 cluster",
                "predictor": BoundGNNPickleAlgorithm(
                    f"GNN Isomera v2 [{scenario_name}]",
                    v2_paths[scenario_name],
                    "core.algorithms.gnn_model",
                ).predict_pairs,
                "artifact_path": str(v2_paths[scenario_name]),
                "artifact_role": "new_isomerav2_pickle",
                "route_mode": "scenario_specific",
                "route_source": "script_explicit_mapping",
            },
        ]
        for detector in detectors:
            algorithm = str(detector["algorithm"])
            predictor = detector["predictor"]
            predicted, timings = _predict_with_timing(graph, predictor, BENCHMARK_RUNS)
            metrics = confusion_metrics_pairs(true_set, predicted, all_pairs=all_pairs)
            et = float(median(timings)) if timings else 0.0
            accuracy = float(metrics["accuracy"] or 0.0)
            jaccard = _jaccard(true_set, predicted)
            evaluated_pairs = len(all_pairs)
            accuracy_out = round(accuracy, 6)
            jaccard_out = round(jaccard, 6)
            et_out = round(et, 6)
            per_scenario.append(
                {
                    "scenario": scenario_name,
                    "algorithm": algorithm,
                    "artifact_path": detector.get("artifact_path", ""),
                    "artifact_role": detector.get("artifact_role", ""),
                    "route_mode": detector.get("route_mode", ""),
                    "route_source": detector.get("route_source", ""),
                    "accuracy": accuracy_out,
                    "jaccard": jaccard_out,
                    "sf_jaccard": round(success_frequency(jaccard_out, et_out, evaluated_pairs), 6),
                    "sf_accuracy": round(success_frequency(accuracy_out, et_out, evaluated_pairs), 6),
                    "ET": et_out,
                    "median_execution_time": et_out,
                    "N_pairs": evaluated_pairs,
                    "tp": metrics["tp"],
                    "fp": metrics["fp"],
                    "fn": metrics["fn"],
                    "tn": metrics["tn"],
                    "precision": round(float(metrics["precision"] or 0.0), 6),
                    "recall": round(float(metrics["recall"] or 0.0), 6),
                    "f1": round(float(metrics["f1"] or 0.0), 6),
                    "runs": BENCHMARK_RUNS,
                }
            )

    summary: list[dict[str, Any]] = []
    df = pd.DataFrame(per_scenario)
    for algorithm, group in df.groupby("algorithm", sort=False):
        tp_sum = int(group["tp"].sum())
        fp_sum = int(group["fp"].sum())
        fn_sum = int(group["fn"].sum())
        tn_sum = int(group["tn"].sum())
        accuracy_denom = tp_sum + tn_sum + fp_sum + fn_sum
        jaccard_denom = tp_sum + fp_sum + fn_sum
        summary.append(
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
    return summary, per_scenario


def _save_benchmark_charts(
    metrics: list[dict[str, Any]],
    per_scenario_metrics: list[dict[str, Any]],
    output_root: Path,
) -> dict[str, str]:
    df = pd.DataFrame(metrics)
    charts = {
        "benchmark_accuracy_png": ("accuracy", "Benchmark accuracy by detector family"),
        "benchmark_jaccard_png": ("jaccard", "Benchmark Jaccard by detector family"),
        "benchmark_sf_jaccard_png": ("sf_jaccard", "Benchmark SF-Jaccard by detector family"),
        "benchmark_runtime_png": ("ET", "Benchmark ET by detector family"),
    }
    paths: dict[str, str] = {}
    for key, (column, title) in charts.items():
        path = output_root / f"{key}.png"
        fig, ax = plt.subplots(figsize=(9, 4.8))
        ax.bar(df["algorithm"], df[column], color=["#6C7A62", "#9AA28D", "#C0A36E", "#5F7F70"])
        ax.set_title(title)
        ax.set_ylabel(column)
        ax.tick_params(axis="x", rotation=20)
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        paths[key] = str(path)
    per_df = pd.DataFrame(per_scenario_metrics)
    if not per_df.empty and {"scenario", "algorithm", "sf_jaccard"}.issubset(per_df.columns):
        per_df = per_df.sort_values(["scenario", "algorithm"]).copy()
        line_path = output_root / "benchmark_sf_jaccard_line_by_scenario_png.png"
        fig, ax = plt.subplots(figsize=(10.5, 5.2))
        for algorithm, group in per_df.groupby("algorithm", sort=False):
            ax.plot(group["scenario"], group["sf_jaccard"], marker="o", linewidth=2, label=algorithm)
        ax.set_title("SF-Jaccard by scenario")
        ax.set_ylabel("sf_jaccard")
        ax.set_xlabel("scenario")
        ax.tick_params(axis="x", rotation=18)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(line_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        paths["benchmark_sf_jaccard_line_by_scenario_png"] = str(line_path)

        bar_path = output_root / "benchmark_sf_jaccard_bar_by_scenario_png.png"
        pivot = per_df.pivot_table(index="scenario", columns="algorithm", values="sf_jaccard", aggfunc="mean")
        fig, ax = plt.subplots(figsize=(10.5, 5.2))
        pivot.plot(kind="bar", ax=ax, color=["#6C7A62", "#9AA28D", "#C0A36E", "#5F7F70"])
        ax.set_title("SF-Jaccard by scenario and detector family")
        ax.set_ylabel("sf_jaccard")
        ax.set_xlabel("scenario")
        ax.tick_params(axis="x", rotation=18)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(bar_path, dpi=300, bbox_inches="tight")
        plt.close(fig)
        paths["benchmark_sf_jaccard_bar_by_scenario_png"] = str(bar_path)
    return paths


def _write_capture(payload: dict[str, object], graph_for_figures: nx.DiGraph) -> dict[str, str]:
    capture_root = _capture_root()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{stamp}_{REPORT_TYPE}_{BENCHMARK_NAME}"
    json_path = capture_root / f"{base_name}.json"
    md_path = capture_root / f"{base_name}.md"
    lineage_png = capture_root / f"{base_name}_lineage.png"
    adjacency_png = capture_root / f"{base_name}_adjacency.png"

    fig = plot_lineage_graph(graph_for_figures, seed=42)
    fig.savefig(lineage_png, bbox_inches="tight", dpi=300)
    plt.close(fig)
    fig = plot_adjacency_matrix(graph_for_figures)
    fig.savefig(adjacency_png, bbox_inches="tight", dpi=300)
    plt.close(fig)

    paths = {
        "json": str(json_path),
        "markdown": str(md_path),
        "lineage_png": str(lineage_png),
        "adjacency_png": str(adjacency_png),
    }
    paths.update(
        _save_benchmark_charts(
            payload["publication_tables"]["benchmark_metrics"],  # type: ignore[index]
            payload["publication_tables"].get("benchmark_per_scenario_metrics", []),  # type: ignore[union-attr]
            capture_root,
        )
    )
    payload["capture_paths"] = paths
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    md_path.write_text(_markdown_from_payload(payload), encoding="utf-8")
    return paths


def _markdown_from_payload(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    lines = [
        f"# Isomera v2 Report: {summary.get('benchmark_name')}",
        "",
        f"- Captured at: {payload.get('captured_at')}",
        f"- Scenarios: {summary.get('scenario_count')}",
        f"- Benchmark runs: {BENCHMARK_RUNS}",
        "",
        "## Methods for Paper",
        "",
        "This run uses two PostgreSQL scenario schemas from the TPC-DS warehouse. Each schema is materialized through the Scenario Materialization API into a normalized directed graph. The ground-truth validation dataset is built from the TPC-DS real_pairs files: listed pairs are duplicates and all remaining node pairs are negatives.",
        "",
        "The benchmark reports detector families, not individual pickle files. VF2 and Node Match are deterministic detector families. GNN TPC-DS v1 and GNN Isomera v2 are cluster families with scenario-specific pickle routing.",
        "",
        "## Benchmark Summary",
        "",
        "```json",
        json.dumps((payload.get("publication_tables") or {}).get("benchmark_metrics"), indent=2, ensure_ascii=True),
        "```",
    ]
    return "\n".join(lines)


def main() -> None:
    _log("initializing MySQL publication store")
    init_publication_store(MYSQL_URL)
    benchmark_root = _benchmark_root()
    graphs: dict[str, nx.DiGraph] = {}
    labels: dict[str, list[tuple[str, str]]] = {}
    source_metadata_by_scenario: dict[str, dict[str, Any]] = {}
    scenario_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    training_rows: list[dict[str, Any]] = []
    training_history: list[dict[str, Any]] = []
    v1_paths: dict[str, Path] = {}
    v2_paths: dict[str, Path] = {}
    publish_ids: list[dict[str, str]] = []

    filters = {
        "scope_sor": True,
        "scope_sot": True,
        "scope_spec": True,
        "same_layer_only": False,
        "same_domain_only": False,
        "same_input_count": False,
        "same_output_count": False,
        "same_parent_signature": False,
        "same_child_signature": False,
        "ground_truth_source": "TPC-DS real_pairs positives plus all remaining node pairs as negatives",
    }

    for scenario_spec in SCENARIOS:
        scenario_name = scenario_spec["scenario"]
        schema_name = scenario_spec["schema"]
        _log(f"materializing {schema_name} from PostgreSQL")
        materialized = materialize_database_scenario(
            POSTGRES_URL,
            schema_name,
            manifests_root=MAIN_ROOT / "data" / "tpcds_postgres",
        )
        graph = materialized.graph
        graphs[scenario_name] = graph
        positive_pairs = _load_positive_pairs(scenario_name)
        labels[scenario_name] = positive_pairs

        gml_path = benchmark_root / "gml" / f"{scenario_name}.gml"
        labels_path = benchmark_root / "real_pairs" / f"{scenario_name}.json"
        nx.write_gml(graph, gml_path)
        labels_path.write_text(json.dumps(positive_pairs, indent=2), encoding="utf-8")

        source_metadata = {
            **materialized.source_metadata,
            "mode": "Scenario Warehouse",
            "database_name": "isomera_tpcds_benchmark",
            "schema": schema_name,
            "database_url": POSTGRES_URL,
            "gml_path": str(gml_path),
            "labels_path": str(labels_path),
        }
        source_metadata_by_scenario[scenario_name] = source_metadata

        current_validation_rows, reviewed_pairs = _validation_rows(graph, positive_pairs, scenario_name=scenario_name)
        validation_rows.extend(current_validation_rows)

        model_path = benchmark_root / "models" / f"GNN_isomerav2_test_{scenario_name}.pkl"
        _log(f"training GNN Isomera v2 artifact for {scenario_name}")
        torch_start = time.perf_counter()
        import torch  # noqa: F401

        _log(f"{scenario_name}: torch import ready in {time.perf_counter() - torch_start:.2f}s")
        training_metadata = train_benchmark_gnn(
            [
                ScenarioTrainingSpec(
                    scenario_name=scenario_name,
                    graph_path=gml_path,
                    labels_path=labels_path,
                )
            ],
            model_path=model_path,
            epochs=TRAIN_EPOCHS,
            learning_rate=LEARNING_RATE,
            hidden_channels=HIDDEN_CHANNELS,
            dropout=DROPOUT,
            negative_ratio=NEGATIVE_RATIO,
            seed=SEED,
            optimizer_name="adam",
            train_ratio=TRAIN_RATIO,
            balance_strategy="negative_sampling",
            progress_callback=_training_progress_logger(scenario_name),
        )
        v2_paths[scenario_name] = model_path
        baseline_path = MAIN_ROOT / "core" / "algorithms" / "pickle" / "gin_gnn" / "modelos_gnn_separados" / f"{scenario_name}.pkl"
        if not baseline_path.exists():
            raise FileNotFoundError(f"TPC-DS baseline pickle not found: {baseline_path}")
        v1_paths[scenario_name] = baseline_path

        for row in training_metadata.get("dataset_summary") or []:
            training_rows.append({**row, "model_path": str(model_path)})
        for row in training_metadata.get("history") or []:
            training_history.append({"scenario": scenario_name, **row})

        scenario_rows.append(
            {
                "scenario": scenario_name,
                "schema": schema_name,
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "total_pairs": len(_all_pairs(graph)),
                "positive_pairs": len(positive_pairs),
                "validation_rows": len(current_validation_rows),
                "gml_path": str(gml_path),
                "labels_path": str(labels_path),
                "manifest_path": source_metadata.get("manifest_path"),
            }
        )

        _log(f"publishing {scenario_name} to MySQL")
        publish_ids.append(
            publish_curated_scenario(
                MYSQL_URL,
                benchmark_name=BENCHMARK_NAME,
                scenario_name=scenario_name,
                graph=graph,
                source_metadata=source_metadata,
                gml_path=str(gml_path),
                labels_path=str(labels_path),
                reviewed_pairs=reviewed_pairs,
                filters=filters,
                summary={
                    "benchmark_name": BENCHMARK_NAME,
                    "scenario": scenario_name,
                    "total_pairs": len(_all_pairs(graph)),
                    "candidate_pairs": len(current_validation_rows),
                    "reviewed_pairs": len(current_validation_rows),
                    "duplicate_pairs": len(positive_pairs),
                    "filters": filters,
                },
            )
        )

    _log(f"running benchmark with {BENCHMARK_RUNS} runs per detector family")
    benchmark_metrics, per_scenario_metrics = _run_benchmark(graphs, labels, v1_paths, v2_paths)
    mysql_counts = _mysql_row_counts(MYSQL_URL, benchmark_name=BENCHMARK_NAME)

    lineage_rows = []
    edge_rows = []
    adjacency_rows = []
    for scenario_name, graph in graphs.items():
        for node, attrs in sorted(graph.nodes(data=True), key=lambda item: str(item[0])):
            lineage_rows.append(
                {
                    "scenario": scenario_name,
                    "domain": attrs.get("domain"),
                    "layer": attrs.get("type"),
                    "node": node,
                    "table_name": attrs.get("table_name"),
                    "semantic_name": attrs.get("semantic_name"),
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

    model_artifact_rows = []
    routing_rows = []
    for scenario_name in graphs:
        for family, path, role in (
            ("GNN TPC-DS v1 cluster", v1_paths[scenario_name], "baseline_tpcds_pickle"),
            ("GNN Isomera v2 cluster", v2_paths[scenario_name], "new_isomerav2_pickle"),
        ):
            row = {
                "model_family": family,
                "scenario": scenario_name,
                "artifact_path": str(path),
                "artifact_role": role,
                "route_mode": "scenario_specific",
                "route_source": "script_explicit_mapping",
            }
            routing_rows.append(row)
            model_artifact_rows.append(
                {
                    "model_name": f"{family}::{scenario_name}",
                    "artifact_path": str(path),
                    "artifact_role": role,
                    "route_mode": "scenario_specific",
                    "route_source": "script_explicit_mapping",
                    "scenario": scenario_name,
                }
            )

    cluster_rows = [
        {"model_family": "VF2", "artifact_count": 0, "scenario_count": len(graphs), "reporting_rule": "one deterministic detector family"},
        {"model_family": "Node Match", "artifact_count": 0, "scenario_count": len(graphs), "reporting_rule": "one deterministic semantic node-matching family"},
        {"model_family": "GNN TPC-DS v1 cluster", "artifact_count": len(v1_paths), "scenario_count": len(graphs), "coverage": f"{len(v1_paths)}/{len(graphs)}", "reporting_rule": "one detector family with one baseline pickle routed per scenario"},
        {"model_family": "GNN Isomera v2 cluster", "artifact_count": len(v2_paths), "scenario_count": len(graphs), "coverage": f"{len(v2_paths)}/{len(graphs)}", "reporting_rule": "one detector family with one newly trained pickle routed per scenario"},
    ]

    first_scenario = SCENARIOS[0]["scenario"]
    source_details = [
        {"field": "benchmark_name", "value": BENCHMARK_NAME},
        {"field": "database_engine", "value": "PostgreSQL"},
        {"field": "database_name", "value": "isomera_tpcds_benchmark"},
        {"field": "database_url", "value": POSTGRES_URL},
        {"field": "publication_backend", "value": "MySQL"},
        {"field": "publication_url", "value": MYSQL_URL},
        {"field": "scenario_count", "value": len(graphs)},
        {"field": "benchmark_runs", "value": BENCHMARK_RUNS},
    ]
    summary = {
        "benchmark_name": BENCHMARK_NAME,
        "scenario": f"{BENCHMARK_NAME}_2_scenarios",
        "scenario_count": len(graphs),
        "total_pairs": sum(int(row["total_pairs"]) for row in scenario_rows),
        "candidate_pairs": sum(int(row["validation_rows"]) for row in scenario_rows),
        "reviewed_pairs": sum(int(row["validation_rows"]) for row in scenario_rows),
        "duplicate_pairs": sum(int(row["positive_pairs"]) for row in scenario_rows),
        "published_to_benchmark": True,
        "filters": filters,
        "publication_ids": publish_ids,
        "mysql_row_counts": mysql_counts,
        "model_name": "GNN_isomerav2_test_cluster",
        "model_path": str(next(iter(v2_paths.values()))),
        "model_family_name": "GNN (GIN Pair Classifier) v1",
        "optimizer": "Adam",
        "loss_name": "BCEWithLogitsLoss",
        "resolved_hyperparameters": {
            "epochs": TRAIN_EPOCHS,
            "learning_rate": LEARNING_RATE,
            "hidden_channels": HIDDEN_CHANNELS,
            "dropout": DROPOUT,
            "negative_ratio": NEGATIVE_RATIO,
            "train_ratio": TRAIN_RATIO,
            "test_ratio": round(1.0 - TRAIN_RATIO, 6),
            "balance_strategy": "negative_sampling",
            "seed": SEED,
        },
        "training_summary": {
            "scenarios": list(graphs.keys()),
            "dataset_summary": training_rows,
            "history": training_history,
            "train_size": sum(int(row.get("dataset_rows", 0) * TRAIN_RATIO) for row in training_rows),
            "val_size": sum(max(1, int(row.get("dataset_rows", 0) * (1.0 - TRAIN_RATIO))) for row in training_rows),
            "status": "completed",
        },
        "benchmark_metrics": benchmark_metrics,
    }
    publication_tables = {
        "source_details": source_details,
        "scenario_details": scenario_rows,
        "lineage_structure": lineage_rows,
        "lineage_edges": edge_rows,
        "adjacency_matrix": adjacency_rows,
        "filters": [
            {"filter": "Lineage scope", "setting": "SOR, SOT, SPEC", "effect": "All graph layers are included in full benchmark validation."},
            {"filter": "Ground-truth source", "setting": "TPC-DS real_pairs", "effect": "Listed pairs are positives; all remaining node-pair combinations are negatives for this reproducible test."},
            {"filter": "Same layer only", "setting": "disabled", "effect": "The full gold-standard table keeps all node-pair combinations."},
        ],
        "validation_dataset": validation_rows,
        "training_dataset": training_rows,
        "training_history": training_history,
        "model_artifact": model_artifact_rows,
        "model_cluster_summary": cluster_rows,
        "model_cluster_routing": routing_rows,
        "benchmark_metrics": benchmark_metrics,
        "benchmark_per_scenario_metrics": per_scenario_metrics,
        "benchmark_pickle_results": [
            row for row in per_scenario_metrics if str(row.get("artifact_path") or "")
        ],
        "pipeline": _pipeline_rows(scenario_rows, training_rows, v2_paths),
        "mysql_row_counts": mysql_counts,
        "formulas": [
            {"formula": "Accuracy = (TP + TN) / (TP + TN + FP + FN)"},
            {"formula": "Jaccard = TP / (TP + FP + FN)"},
            {"formula": "ET = median(t_i), i = 1..runs"},
            {"formula": "SF_accuracy = Accuracy * N_pairs / ET"},
            {"formula": "SF_jaccard = Jaccard * N_pairs / ET"},
            {"formula": "h_v^(k) = MLP^(k)((1 + eps^(k)) h_v^(k-1) + sum_{u in N(v)} h_u^(k-1))"},
            {"formula": "z_G = mean_pool({h_v^(K)})"},
            {"formula": "y_hat = sigmoid(MLP([z_G1 || z_G2]))"},
            {"formula": "L = BCEWithLogitsLoss(logit, y)"},
        ],
        "layers": [
            {"layer": "GIN layer 1: neighborhood aggregation over node-centered subgraph"},
            {"layer": "ReLU: non-linear hidden activation"},
            {"layer": "GIN layer 2: second aggregation and projection"},
            {"layer": "Mean pooling: one embedding per subgraph"},
            {"layer": "Pair MLP with dropout: binary duplicate logit"},
        ],
    }

    payload: dict[str, Any] = {
        "report_type": REPORT_TYPE,
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system_architecture": _system_architecture(),
        "scenario_api": scenario_api_contract(),
        "storytelling": {
            "module": "Research Reports",
            "goal": "Execute a real two-scenario Isomera v2 benchmark and document the article-grade pipeline.",
            "graph_construction_method": "Read two PostgreSQL benchmark schemas, materialize each into a normalized graph, train one Isomera v2 GNN pickle per scenario, route detector families by scenario, and benchmark with 10 timing runs.",
        },
        "environment": {
            "python_executable": sys.executable,
            "project_root": str(REPO_ROOT),
            "scenarios_db_url": POSTGRES_URL,
            "publication_db_url": MYSQL_URL,
            "streamlit_reason": "Streamlit was selected for the v2 research prototype because it exposes each intermediate artifact quickly in a single interactive workflow.",
            "api_reason": "The Scenario Materialization API separates database connectivity from UI, training, benchmark, and reporting so the graph contract is reproducible.",
        },
        "source_metadata": source_metadata_by_scenario[first_scenario],
        "graph_summary": _graph_summary(graphs),
        "publication_tables": publication_tables,
        "formula_parameter_mapping": {
            "K / epochs": TRAIN_EPOCHS,
            "hidden_channels / embedding dimension": HIDDEN_CHANNELS,
            "dropout": DROPOUT,
            "learning_rate": LEARNING_RATE,
            "negative_ratio": NEGATIVE_RATIO,
            "train_ratio": TRAIN_RATIO,
            "benchmark_runs": BENCHMARK_RUNS,
            "detector_family_count": 4,
            "new_isomerav2_artifacts": len(v2_paths),
        },
        "summary": summary,
    }
    _log("writing article capture, figures, and package")
    capture_paths = _write_capture(payload, graphs[first_scenario])
    package = build_package(Path(capture_paths["json"]))
    print(json.dumps({"capture_paths": capture_paths, "package": package, "benchmark_metrics": benchmark_metrics}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
