from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any

sys.dont_write_bytecode = True

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

import core.algorithms  # noqa: F401,E402
from core.algorithms.gnn_training import ScenarioTrainingSpec, train_benchmark_gnn  # noqa: E402
from core.isomorphism import find_isomorphic_pairs  # noqa: E402
from core.lineage import adjacency_matrix_dataframe, edge_dataframe, plot_adjacency_matrix, plot_lineage_graph  # noqa: E402
from core.metrics import canonical_pairs, confusion_metrics_pairs, success_frequency  # noqa: E402
from core.publication_store import init_publication_store, publish_curated_scenario  # noqa: E402
from core.scenario_api import materialize_database_scenario, scenario_api_contract  # noqa: E402

from build_research_report_package import build_package  # noqa: E402
from generate_isomerav2_bench_report import _save_benchmark_charts, _system_architecture  # noqa: E402
from generate_tpcds_genai_spec_report import (  # noqa: E402
    MYSQL_URL,
    POSTGRES_URL,
    _all_nodes_pairs,
    _candidate_spec_pairs,
    _create_validation_dataset,
    _graph_summary,
    _load_manifest_index,
    _mysql_row_counts,
    _predict_candidate_pairs_with_pickle,
)


BENCHMARK_NAME = "tpc_ds_genai_spec_v2"
BENCHMARK_DISPLAY_NAME = "TPC-DS GenAI Spec v2"
REPORT_TYPE = "tpcds_genai_spec_v2_strategy_benchmark"
BENCHMARK_RUNS = 10
TRAIN_EPOCHS = 5
TRAIN_RATIO = 0.8
HIDDEN_CHANNELS = 16
DROPOUT = 0.10
LEARNING_RATE = 0.005
SEED = 42
INFERENCE_THRESHOLD = 0.50

STRATEGIES: list[dict[str, Any]] = [
    {
        "key": "weighted_bce",
        "model_family": "GNN GenAI v2 Weighted BCE",
        "balance_strategy": "class_weighted_loss",
        "loss_name": "bce_with_logits",
        "negative_ratio": 1,
        "training_goal": "Keep the supervised distribution intact and compensate rare duplicates through pos_weight.",
    },
    {
        "key": "focal_loss",
        "model_family": "GNN GenAI v2 Focal Loss",
        "balance_strategy": "none_real_distribution",
        "loss_name": "focal_loss",
        "negative_ratio": 1,
        "training_goal": "Keep the real distribution and focus gradients on hard or misclassified examples.",
    },
    {
        "key": "hard_negatives",
        "model_family": "GNN GenAI v2 Hard Negatives",
        "balance_strategy": "hard_negative_mining",
        "loss_name": "bce_with_logits",
        "negative_ratio": 2,
        "training_goal": "Keep positives and structurally similar negatives to reduce easy-negative dominance.",
    },
]


def _training_strategy_theory_rows() -> list[dict[str, Any]]:
    return [
        {
            "strategy": "Weighted BCE",
            "technical_function": "torch.nn.BCEWithLogitsLoss(pos_weight)",
            "formula": "L = -[w_p y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))]",
            "interpretation": "The rare duplicate class receives a larger penalty. In this benchmark this tests whether preserving every validated negative while weighting positives is enough to improve duplicate recall.",
        },
        {
            "strategy": "Focal Loss",
            "technical_function": "custom sigmoid focal loss",
            "formula": "FL(p_t) = -alpha(1-p_t)^gamma log(p_t)",
            "interpretation": "Easy examples contribute less to the gradient. This tests whether the classifier benefits from concentrating on misclassified or uncertain pairs under strong class imbalance.",
        },
        {
            "strategy": "Hard Negative Mining",
            "technical_function": "structural hard-negative sampler + BCEWithLogitsLoss",
            "formula": "score = |nodes_a-nodes_b| + |edges_a-edges_b|",
            "interpretation": "The training set keeps negatives whose subgraphs are structurally close to candidate positives. This tests decision-boundary quality against near-duplicate non-matches.",
        },
    ]


def _hyperparameter_search_grid_rows() -> list[dict[str, Any]]:
    return [
        {"parameter": "training strategy", "values": "Weighted BCE; Focal Loss; Hard Negatives", "count": 3, "reason": "Compare the three imbalance-handling families."},
        {"parameter": "learning rate", "values": "0.001; 0.005; 0.010", "count": 3, "reason": "Control optimizer step size."},
        {"parameter": "hidden channels", "values": "16; 32", "count": 2, "reason": "Compare compact and higher-capacity embeddings."},
        {"parameter": "dropout", "values": "0.0; 0.1", "count": 2, "reason": "Test regularization in scarce-positive training."},
        {"parameter": "inference threshold", "values": "0.4; 0.5; 0.6", "count": 3, "reason": "Compare conservative and recall-oriented duplicate decisions."},
    ]


def _hyperparameter_search_protocol_rows() -> list[dict[str, Any]]:
    return [
        {
            "stage": "screening_5_scenarios",
            "scope": "3 benchmarks x 5 representative scenarios x 108 configs",
            "trainings": 1620,
            "selection_rule": "Select top 5 configurations per benchmark by SF-Jaccard.",
            "protocol_output": "Efficient model-selection evidence before full execution.",
        },
        {
            "stage": "full_validation_20_scenarios",
            "scope": "3 benchmarks x 20 scenarios x top 5 configs",
            "trainings": 300,
            "selection_rule": "Retrain selected configurations on every scenario.",
            "protocol_output": "Final model-selection validation with complete scenario coverage.",
        },
        {
            "stage": "benchmark_final",
            "scope": "Best configurations vs VF2, Node Match, GNN TPC-DS v1, GNN GenAI v1, and GNN GenAI v2",
            "trainings": 0,
            "selection_rule": "Report detector-family metrics, per-scenario metrics, and pickle routing.",
            "protocol_output": "Final comparison table and figures.",
        },
    ]


def _log(message: str) -> None:
    print(f"[tpcds_genai_spec_v2] {message}", flush=True)


def _capture_root() -> Path:
    root = MAIN_ROOT / "data" / "article_capture" / BENCHMARK_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _benchmark_root() -> Path:
    root = MAIN_ROOT / "data" / "architectures" / BENCHMARK_NAME
    for child in ("gml", "real_pairs", "validations", "models"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _training_progress_logger(scenario_name: str, strategy_key: str):
    def _callback(payload: dict[str, Any]) -> None:
        if payload.get("step") == "training":
            _log(
                f"{scenario_name}/{strategy_key}: epoch={payload.get('current_epoch')}/{payload.get('epochs')} "
                f"train_loss={payload.get('train_loss')} val_loss={payload.get('val_loss')} "
                f"train_acc={payload.get('train_accuracy')} val_acc={payload.get('val_accuracy')}"
            )
        else:
            _log(f"{scenario_name}/{strategy_key}: {payload.get('step')} {payload.get('step_detail', '')}")

    return _callback


def _predict_with_timing(predictor, runs: int) -> tuple[set[tuple[str, str]], list[float]]:
    predictions: set[tuple[str, str]] = set()
    times: list[float] = []
    for run_index in range(1, runs + 1):
        start = time.perf_counter()
        predictions = canonical_pairs(predictor())
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        _log(f"benchmark run {run_index}/{runs}: {elapsed:.4f}s")
    return predictions, times


def _jaccard(true_pairs: set[tuple[str, str]], predicted_pairs: set[tuple[str, str]]) -> float:
    union = true_pairs | predicted_pairs
    return 1.0 if not union else len(true_pairs & predicted_pairs) / len(union)


def _run_benchmark(
    graphs: dict[str, nx.DiGraph],
    labels: dict[str, list[tuple[str, str]]],
    v1_paths: dict[str, Path],
    strategy_paths: dict[str, dict[str, Path]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    per_scenario: list[dict[str, Any]] = []
    strategy_by_key = {str(item["key"]): item for item in STRATEGIES}
    for scenario_index, (scenario_name, graph) in enumerate(graphs.items(), start=1):
        _log(f"benchmark scenario {scenario_index}/{len(graphs)}: {scenario_name}")
        candidate_pairs = _candidate_spec_pairs(graph)
        candidate_set = canonical_pairs(candidate_pairs)
        true_set = canonical_pairs(labels[scenario_name]) & candidate_set
        detectors: list[dict[str, Any]] = [
            {
                "algorithm": "VF2",
                "artifact_path": "",
                "artifact_role": "deterministic_baseline",
                "route_mode": "not_applicable",
                "route_source": "deterministic_algorithm",
                "predictor": lambda g=graph, c=candidate_set: canonical_pairs(find_isomorphic_pairs(g, algorithm="VF2")) & c,
            },
            {
                "algorithm": "Node Match",
                "artifact_path": "",
                "artifact_role": "deterministic_baseline",
                "route_mode": "not_applicable",
                "route_source": "deterministic_algorithm",
                "predictor": lambda g=graph, c=candidate_set: canonical_pairs(find_isomorphic_pairs(g, algorithm="Node Match (Custom)")) & c,
            },
            {
                "algorithm": "GNN TPC-DS v1 cluster",
                "artifact_path": str(v1_paths[scenario_name]),
                "artifact_role": "baseline_tpcds_pickle",
                "route_mode": "scenario_specific",
                "route_source": "TPC-DS v1 pickle map",
                "predictor": lambda g=graph, p=v1_paths[scenario_name], pairs=candidate_pairs: _predict_candidate_pairs_with_pickle(
                    g,
                    p,
                    pairs,
                    threshold=INFERENCE_THRESHOLD,
                ),
            },
        ]
        for strategy_key, scenario_paths in strategy_paths.items():
            strategy = strategy_by_key[strategy_key]
            detectors.append(
                {
                    "algorithm": strategy["model_family"],
                    "artifact_path": str(scenario_paths[scenario_name]),
                    "artifact_role": f"genai_spec_v2_{strategy_key}",
                    "route_mode": "scenario_specific",
                    "route_source": f"{BENCHMARK_DISPLAY_NAME} explicit routing",
                    "predictor": lambda g=graph, p=scenario_paths[scenario_name], pairs=candidate_pairs: _predict_candidate_pairs_with_pickle(
                        g,
                        p,
                        pairs,
                        threshold=INFERENCE_THRESHOLD,
                    ),
                }
            )

        for detector in detectors:
            _log(f"{scenario_name}: running {detector['algorithm']} ({BENCHMARK_RUNS} runs, threshold={INFERENCE_THRESHOLD})")
            predicted, timings = _predict_with_timing(detector["predictor"], BENCHMARK_RUNS)
            metrics = confusion_metrics_pairs(true_set, predicted, all_pairs=candidate_pairs)
            et = float(median(timings)) if timings else 0.0
            accuracy = float(metrics["accuracy"] or 0.0)
            jaccard = _jaccard(true_set, predicted)
            evaluated_pairs = len(candidate_pairs)
            per_scenario.append(
                {
                    "scenario": scenario_name,
                    "algorithm": detector["algorithm"],
                    "artifact_path": detector["artifact_path"],
                    "artifact_role": detector["artifact_role"],
                    "route_mode": detector["route_mode"],
                    "route_source": detector["route_source"],
                    "inference_threshold": INFERENCE_THRESHOLD,
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
                    "runs": BENCHMARK_RUNS,
                }
            )

    df = pd.DataFrame(per_scenario)
    summary: list[dict[str, Any]] = []
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
                "sf_jaccard": round(float(group["sf_jaccard"].mean()), 6),
                "jaccard": round(float(tp_sum / jaccard_denom) if jaccard_denom else 0.0, 6),
                "ET": round(float(group["ET"].median()), 6),
                "accuracy": round(float((tp_sum + tn_sum) / accuracy_denom) if accuracy_denom else 0.0, 6),
                "sf_accuracy": round(float(group["sf_accuracy"].mean()), 6),
                "N_pairs": int(group["N_pairs"].sum()),
                "tp": tp_sum,
                "fp": fp_sum,
                "fn": fn_sum,
                "tn": tn_sum,
                "scenarios": int(group["scenario"].nunique()),
                "runs": BENCHMARK_RUNS,
                "inference_threshold": INFERENCE_THRESHOLD,
                "aggregation": "SF is computed per scenario as score * N_pairs / ET and averaged across scenarios.",
            }
        )
    return summary, per_scenario


def _pipeline_rows(scenario_rows: list[dict[str, Any]], training_rows: list[dict[str, Any]], strategy_paths: dict[str, dict[str, Path]]) -> list[dict[str, object]]:
    return [
        {
            "stage": "source",
            "input": "PostgreSQL scenario warehouse",
            "output": f"{len(scenario_rows)} TPC-DS scenario schemas",
            "details": "Each schema is materialized through the Scenario Materialization API.",
        },
        {
            "stage": "normalized_graph",
            "input": "manifest-defined relational contract",
            "output": f"{sum(int(row['nodes']) for row in scenario_rows)} nodes / {sum(int(row['edges']) for row in scenario_rows)} edges",
            "details": "Edges are normalized to SOR -> SOT -> SPEC before validation, training, and benchmark.",
        },
        {
            "stage": "validation_dataset",
            "input": "SPEC candidate pairs plus GenAI documented validation rubric",
            "output": f"{sum(int(row['candidate_pairs']) for row in scenario_rows)} supervised rows",
            "details": "The same ground truth is reused across all v2 training strategies.",
        },
        {
            "stage": "strategy_training",
            "input": "validation_dataset.csv per scenario",
            "output": f"{len(STRATEGIES)} strategy clusters / {sum(len(paths) for paths in strategy_paths.values())} pickles",
            "details": "Weighted BCE, focal loss, and hard-negative mining are trained and reported separately.",
        },
        {
            "stage": "benchmark_execution",
            "input": f"detector families with explicit threshold={INFERENCE_THRESHOLD}",
            "output": f"{BENCHMARK_RUNS} runs per detector family per scenario",
            "details": "The primary article metric is SF-Jaccard; Accuracy remains diagnostic.",
        },
    ]


def _write_capture(payload: dict[str, object], graph_for_figures: nx.DiGraph) -> dict[str, str]:
    capture_root = _capture_root()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{stamp}_{REPORT_TYPE}_{BENCHMARK_NAME}"
    json_path = capture_root / f"{base_name}.json"
    md_path = capture_root / f"{base_name}.md"
    lineage_png = capture_root / f"{base_name}_lineage.png"
    adjacency_png = capture_root / f"{base_name}_adjacency.png"

    fig = plot_lineage_graph(graph_for_figures, seed=42)
    fig.savefig(lineage_png, bbox_inches="tight", dpi=360)
    plt.close(fig)
    fig = plot_adjacency_matrix(graph_for_figures)
    fig.savefig(adjacency_png, bbox_inches="tight", dpi=360)
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
    md_path.write_text(
        "\n".join(
            [
                f"# {BENCHMARK_DISPLAY_NAME}",
                "",
                f"- Runs: {BENCHMARK_RUNS}",
                f"- Epochs: {TRAIN_EPOCHS}",
                f"- Threshold: {INFERENCE_THRESHOLD}",
                f"- Strategies: {', '.join(str(item['model_family']) for item in STRATEGIES)}",
                "",
                "```json",
                json.dumps(payload["publication_tables"]["benchmark_metrics"], indent=2, ensure_ascii=True),  # type: ignore[index]
                "```",
            ]
        ),
        encoding="utf-8",
    )
    return paths


def main() -> None:
    _log("initializing MySQL publication store")
    init_publication_store(MYSQL_URL)
    benchmark_root = _benchmark_root()
    scenario_specs = _load_manifest_index()
    _log(f"loaded {len(scenario_specs)} manifest scenarios")

    graphs: dict[str, nx.DiGraph] = {}
    labels: dict[str, list[tuple[str, str]]] = {}
    source_metadata_by_scenario: dict[str, dict[str, Any]] = {}
    scenario_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    training_rows: list[dict[str, Any]] = []
    training_history: list[dict[str, Any]] = []
    lineage_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    adjacency_rows: list[dict[str, Any]] = []
    v1_paths: dict[str, Path] = {}
    strategy_paths: dict[str, dict[str, Path]] = {str(item["key"]): {} for item in STRATEGIES}
    publish_ids: list[dict[str, str]] = []

    filters = {
        "scope_layers": ["SPEC"],
        "constraints": ["complete_upstream_lineage", "cross_domain_allowed"],
        "same_layer_only": True,
        "same_domain_only": False,
        "candidate_generation": "all SPEC-to-SPEC combinations",
        "ground_truth_source": "GenAI-assisted validation rubric reused from v1 protocol",
        "inference_threshold": INFERENCE_THRESHOLD,
    }
    validator_protocol = {
        "validator_provider": "OpenAI",
        "validator_environment": "Codex CLI agent",
        "validator_model_id": "gpt-5.4",
        "reasoning_effort": "xhigh",
        "rubric_version": "genai_spec_v1",
        "private_chain_of_thought_saved": False,
        "decision_scope": "SPEC node pairs with complete upstream lineage context",
        "same_domain_filter": "disabled",
        "v2_change": "Training/benchmark comparison only; the supervised labels are kept stable across strategies.",
    }

    for index, scenario_spec in enumerate(scenario_specs, start=1):
        scenario_name = str(scenario_spec["scenario"])
        schema_name = str(scenario_spec["schema"])
        _log(f"[{index}/{len(scenario_specs)}] materializing {schema_name}")
        materialized = materialize_database_scenario(POSTGRES_URL, schema_name, manifests_root=MAIN_ROOT / "data" / "tpcds_postgres")
        graph = materialized.graph
        graphs[scenario_name] = graph
        gml_path = benchmark_root / "gml" / f"{scenario_name}.gml"
        nx.write_gml(graph, gml_path)

        rows, positive_pairs, reviewed_pairs, validation_csv, validation_json, labels_path = _create_validation_dataset(
            graph,
            scenario_name=scenario_name,
            benchmark_root=benchmark_root,
        )
        labels[scenario_name] = positive_pairs
        validation_rows.extend(rows)

        source_metadata = {
            **materialized.source_metadata,
            "mode": "Scenario Warehouse",
            "database_name": "isomera_tpcds_benchmark",
            "database_url": POSTGRES_URL,
            "schema": schema_name,
            "gml_path": str(gml_path),
            "labels_path": str(labels_path),
            "validation_dataset_path": str(validation_csv),
        }
        source_metadata_by_scenario[scenario_name] = source_metadata
        baseline_path = MAIN_ROOT / "core" / "algorithms" / "pickle" / "gin_gnn" / "modelos_gnn_separados" / f"{scenario_name}.pkl"
        if not baseline_path.exists():
            raise FileNotFoundError(f"TPC-DS baseline pickle not found: {baseline_path}")
        v1_paths[scenario_name] = baseline_path

        for strategy in STRATEGIES:
            strategy_key = str(strategy["key"])
            model_path = benchmark_root / "models" / strategy_key / f"GNN_tpcds_genai_spec_v2_{strategy_key}_{scenario_name}.pkl"
            _log(f"{scenario_name}: training {strategy['model_family']} for {TRAIN_EPOCHS} epochs")
            training_metadata = train_benchmark_gnn(
                [
                    ScenarioTrainingSpec(
                        scenario_name=scenario_name,
                        graph_path=gml_path,
                        labels_path=labels_path,
                        supervised_labels_path=validation_csv,
                    )
                ],
                model_path=model_path,
                epochs=TRAIN_EPOCHS,
                learning_rate=LEARNING_RATE,
                hidden_channels=HIDDEN_CHANNELS,
                dropout=DROPOUT,
                negative_ratio=int(strategy["negative_ratio"]),
                seed=SEED,
                optimizer_name="adam",
                train_ratio=TRAIN_RATIO,
                balance_strategy=str(strategy["balance_strategy"]),
                loss_name=str(strategy["loss_name"]),
                progress_callback=_training_progress_logger(scenario_name, strategy_key),
            )
            strategy_paths[strategy_key][scenario_name] = model_path
            for row in training_metadata.get("dataset_summary") or []:
                training_rows.append(
                    {
                        **row,
                        "model_family": strategy["model_family"],
                        "strategy_key": strategy_key,
                        "model_path": str(model_path),
                        "validation_dataset_path": str(validation_csv),
                    }
                )
            for row in training_metadata.get("history") or []:
                training_history.append({"scenario": scenario_name, "model_family": strategy["model_family"], "strategy_key": strategy_key, **row})

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

        scenario_rows.append(
            {
                "scenario": scenario_name,
                "schema": schema_name,
                "nodes": graph.number_of_nodes(),
                "edges": graph.number_of_edges(),
                "total_pairs": len(_all_nodes_pairs(graph)),
                "candidate_pairs": len(rows),
                "positive_pairs": len(positive_pairs),
                "negative_pairs": len(rows) - len(positive_pairs),
                "validation_rows": len(rows),
                "gml_path": str(gml_path),
                "labels_path": str(labels_path),
                "validation_dataset_path": str(validation_csv),
                "validation_json_path": str(validation_json),
                "manifest_path": source_metadata.get("manifest_path"),
            }
        )

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
                    "benchmark_display_name": BENCHMARK_DISPLAY_NAME,
                    "scenario": scenario_name,
                    "total_pairs": len(_all_nodes_pairs(graph)),
                    "candidate_pairs": len(rows),
                    "reviewed_pairs": len(rows),
                    "duplicate_pairs": len(positive_pairs),
                    "filters": filters,
                    "validator_protocol": validator_protocol,
                    "training_strategies": STRATEGIES,
                },
            )
        )

    _log(f"running benchmark with {BENCHMARK_RUNS} runs and threshold={INFERENCE_THRESHOLD}")
    benchmark_metrics, per_scenario_metrics = _run_benchmark(graphs, labels, v1_paths, strategy_paths)
    mysql_counts = _mysql_row_counts(MYSQL_URL, benchmark_name=BENCHMARK_NAME)

    model_artifact_rows: list[dict[str, Any]] = []
    routing_rows: list[dict[str, Any]] = []
    for scenario_name in graphs:
        routing_rows.append(
            {
                "model_family": "GNN TPC-DS v1 cluster",
                "scenario": scenario_name,
                "artifact_path": str(v1_paths[scenario_name]),
                "artifact_role": "baseline_tpcds_pickle",
                "route_mode": "scenario_specific",
                "route_source": "TPC-DS v1 pickle map",
            }
        )
        model_artifact_rows.append({**routing_rows[-1], "model_name": f"GNN TPC-DS v1 cluster::{scenario_name}"})
        for strategy in STRATEGIES:
            path = strategy_paths[strategy["key"]][scenario_name]
            row = {
                "model_family": strategy["model_family"],
                "scenario": scenario_name,
                "artifact_path": str(path),
                "artifact_role": f"genai_spec_v2_{strategy['key']}",
                "route_mode": "scenario_specific",
                "route_source": f"{BENCHMARK_DISPLAY_NAME} explicit routing",
            }
            routing_rows.append(row)
            model_artifact_rows.append({**row, "model_name": f"{strategy['model_family']}::{scenario_name}"})

    cluster_rows = [
        {"model_family": "VF2", "artifact_count": 0, "scenario_count": len(graphs), "coverage": "20/20", "reporting_rule": "one deterministic detector family"},
        {"model_family": "Node Match", "artifact_count": 0, "scenario_count": len(graphs), "coverage": "20/20", "reporting_rule": "one deterministic semantic node-matching family"},
        {"model_family": "GNN TPC-DS v1 cluster", "artifact_count": len(v1_paths), "scenario_count": len(graphs), "coverage": f"{len(v1_paths)}/{len(graphs)}", "reporting_rule": "one baseline pickle routed per scenario"},
    ]
    for strategy in STRATEGIES:
        cluster_rows.append(
            {
                "model_family": strategy["model_family"],
                "artifact_count": len(strategy_paths[strategy["key"]]),
                "scenario_count": len(graphs),
                "coverage": f"{len(strategy_paths[strategy['key']])}/{len(graphs)}",
                "reporting_rule": f"one v2 pickle routed per scenario; balance={strategy['balance_strategy']}; loss={strategy['loss_name']}",
            }
        )

    source_details = [
        {"field": "benchmark_name", "value": BENCHMARK_NAME},
        {"field": "benchmark_display_name", "value": BENCHMARK_DISPLAY_NAME},
        {"field": "database_engine", "value": "PostgreSQL"},
        {"field": "database_name", "value": "isomera_tpcds_benchmark"},
        {"field": "database_url", "value": POSTGRES_URL},
        {"field": "publication_backend", "value": "MySQL"},
        {"field": "publication_url", "value": MYSQL_URL},
        {"field": "scenario_count", "value": len(graphs)},
        {"field": "benchmark_runs", "value": BENCHMARK_RUNS},
        {"field": "training_epochs", "value": TRAIN_EPOCHS},
        {"field": "inference_threshold", "value": INFERENCE_THRESHOLD},
        {"field": "strategy_count", "value": len(STRATEGIES)},
        {"field": "validator_model", "value": "OpenAI GPT-5.4 via Codex CLI agent"},
        {"field": "validator_reasoning_effort", "value": "xhigh"},
    ]
    total_pairs = sum(int(row["total_pairs"]) for row in scenario_rows)
    candidate_pairs = sum(int(row["candidate_pairs"]) for row in scenario_rows)
    duplicate_pairs = sum(int(row["positive_pairs"]) for row in scenario_rows)
    primary_strategy = STRATEGIES[0]
    primary_path = next(iter(strategy_paths[primary_strategy["key"]].values()))
    training_summary = {
        "scenarios": list(graphs.keys()),
        "dataset_summary": training_rows,
        "history": training_history,
        "train_size": sum(int(row.get("dataset_rows", 0) * TRAIN_RATIO) for row in training_rows),
        "val_size": sum(max(1, int(row.get("dataset_rows", 0) * (1.0 - TRAIN_RATIO))) for row in training_rows),
        "status": "completed",
        "loss": {"loss_name": "strategy dependent: BCEWithLogitsLoss(pos_weight), focal loss, or BCEWithLogitsLoss"},
        "balance_summary": {"operation": "strategy comparison; see training_strategy_comparison.csv"},
        "train_distribution": {"positive_pairs": duplicate_pairs, "negative_pairs": candidate_pairs - duplicate_pairs, "dataset_rows": candidate_pairs},
    }
    training_strategy_comparison = [
        {
            "model_family": strategy["model_family"],
            "balance_strategy": strategy["balance_strategy"],
            "loss_name": strategy["loss_name"],
            "epochs": TRAIN_EPOCHS,
            "threshold": INFERENCE_THRESHOLD,
            "training_goal": strategy["training_goal"],
        }
        for strategy in STRATEGIES
    ]
    summary = {
        "benchmark_name": BENCHMARK_NAME,
        "benchmark_display_name": BENCHMARK_DISPLAY_NAME,
        "scenario": f"{BENCHMARK_NAME}_20_scenarios",
        "scenario_count": len(graphs),
        "total_pairs": total_pairs,
        "candidate_pairs": candidate_pairs,
        "reviewed_pairs": candidate_pairs,
        "duplicate_pairs": duplicate_pairs,
        "published_to_benchmark": True,
        "filters": filters,
        "publication_ids": publish_ids,
        "mysql_row_counts": mysql_counts,
        "model_name": "GNN_tpcds_genai_spec_v2_strategy_clusters",
        "model_path": str(primary_path),
        "model_family_name": "GNN (GIN Pair Classifier) v1",
        "optimizer": "Adam",
        "optimizer_label": "Adaptive gradient optimizer (torch.optim.Adam)",
        "optimizer_name": "torch.optim.Adam",
        "loss_name": "strategy dependent",
        "resolved_hyperparameters": {
            "epochs": TRAIN_EPOCHS,
            "learning_rate": LEARNING_RATE,
            "hidden_channels": HIDDEN_CHANNELS,
            "dropout": DROPOUT,
            "train_ratio": TRAIN_RATIO,
            "test_ratio": round(1.0 - TRAIN_RATIO, 6),
            "balance_strategy": "strategy_comparison",
            "balance_strategy_label": "Weighted BCE vs Focal Loss vs Hard Negative Mining",
            "inference_threshold": INFERENCE_THRESHOLD,
            "seed": SEED,
        },
        "training_summary": training_summary,
        "benchmark_metrics": benchmark_metrics,
    }
    publication_tables = {
        "source_details": source_details,
        "scenario_details": scenario_rows,
        "lineage_structure": lineage_rows,
        "lineage_edges": edge_rows,
        "adjacency_matrix": adjacency_rows,
        "filters": [
            {"filter": "Lineage scope", "setting": "SPEC only", "effect": "Only SPEC outputs enter candidate generation; each SPEC keeps complete upstream lineage."},
            {"filter": "Same layer", "setting": "enabled", "effect": "All reviewed pairs are SPEC-to-SPEC."},
            {"filter": "Same domain", "setting": "disabled", "effect": "Cross-domain duplicates remain eligible."},
            {"filter": "Inference threshold", "setting": str(INFERENCE_THRESHOLD), "effect": "GNN logits are converted to duplicate predictions only when sigmoid(score) >= threshold."},
        ],
        "genai_validation_protocol": [validator_protocol],
        "training_strategy_comparison": training_strategy_comparison,
        "training_strategy_theory": _training_strategy_theory_rows(),
        "hyperparameter_search_grid": _hyperparameter_search_grid_rows(),
        "hyperparameter_search_protocol": _hyperparameter_search_protocol_rows(),
        "validation_dataset": validation_rows,
        "training_dataset": training_rows,
        "training_history": training_history,
        "model_artifact": model_artifact_rows,
        "model_cluster_summary": cluster_rows,
        "model_cluster_routing": routing_rows,
        "benchmark_metrics": benchmark_metrics,
        "benchmark_per_scenario_metrics": per_scenario_metrics,
        "benchmark_pickle_results": [row for row in per_scenario_metrics if str(row.get("artifact_path") or "")],
        "pipeline": _pipeline_rows(scenario_rows, training_rows, strategy_paths),
        "mysql_row_counts": mysql_counts,
        "formulas": [
            {"formula": "Accuracy = (TP + TN) / (TP + TN + FP + FN)"},
            {"formula": "Jaccard = TP / (TP + FP + FN)"},
            {"formula": "ET = median(t_i), i = 1..runs"},
            {"formula": "SF_accuracy = Accuracy * N_pairs / ET"},
            {"formula": "SF_jaccard = Jaccard * N_pairs / ET"},
            {"formula": "GNN prediction = 1 if sigmoid(logit) >= 0.50"},
            {"formula": "Weighted BCE pos_weight = N_negative / N_positive"},
            {"formula": "FocalLoss = -alpha(1-p_t)^gamma log(p_t)"},
        ],
        "layers": [
            {"layer": "GIN layer 1", "operation": "neighbor aggregation over node-centered upstream lineage subgraph"},
            {"layer": "ReLU", "operation": "non-linear activation"},
            {"layer": "GIN layer 2", "operation": "second aggregation and embedding projection"},
            {"layer": "Mean pooling", "operation": "one vector embedding per subgraph"},
            {"layer": "Pair MLP with dropout", "operation": "binary duplicate logit"},
        ],
    }
    first_scenario = next(iter(graphs))
    payload: dict[str, Any] = {
        "report_type": REPORT_TYPE,
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system_architecture": _system_architecture(),
        "scenario_api": scenario_api_contract(),
        "storytelling": {
            "module": "Research Reports",
            "goal": "Compare reproducible GNN training strategies on the same GenAI-curated SPEC benchmark.",
            "graph_construction_method": "Read all PostgreSQL benchmark schemas, materialize normalized lineage graphs, reuse the GenAI SPEC supervised dataset, train strategy-specific GNN clusters, and benchmark detector families with 10 timing runs.",
        },
        "environment": {
            "python_executable": sys.executable,
            "project_root": str(REPO_ROOT),
            "scenarios_db_url": POSTGRES_URL,
            "publication_db_url": MYSQL_URL,
            "streamlit_reason": "Streamlit exposes the same curation, training, benchmark, and report workflow interactively.",
            "api_reason": "The Scenario Materialization API keeps database connectivity separate from UI, training, benchmark, and reporting.",
        },
        "source_metadata": source_metadata_by_scenario[first_scenario],
        "graph_summary": _graph_summary(graphs),
        "publication_tables": publication_tables,
        "formula_parameter_mapping": {
            "K / epochs": TRAIN_EPOCHS,
            "hidden_channels / embedding dimension": HIDDEN_CHANNELS,
            "dropout": DROPOUT,
            "learning_rate": LEARNING_RATE,
            "train_ratio": TRAIN_RATIO,
            "benchmark_runs": BENCHMARK_RUNS,
            "inference_threshold": INFERENCE_THRESHOLD,
            "strategy_count": len(STRATEGIES),
            "candidate_scope": "SPEC-to-SPEC pairs",
            "sf_jaccard": "Jaccard * N_pairs / ET",
        },
        "summary": summary,
    }
    _log("writing article capture, figures, and package")
    capture_paths = _write_capture(payload, graphs[first_scenario])
    package = build_package(Path(capture_paths["json"]))
    print(json.dumps({"capture_paths": capture_paths, "package": package, "benchmark_metrics": benchmark_metrics, "mysql_counts": mysql_counts}, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
