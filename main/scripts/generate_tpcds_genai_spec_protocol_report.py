from __future__ import annotations

import csv
import json
import sys
import time
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from statistics import mean, median
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
from generate_tpcds_genai_spec_v2_report import (  # noqa: E402
    _hyperparameter_search_grid_rows,
    _hyperparameter_search_protocol_rows,
    _jaccard,
    _training_strategy_theory_rows,
)


BENCHMARK_NAME = "tpc_ds_genai_spec_protocol"
BENCHMARK_DISPLAY_NAME = "TPC-DS GenAI Spec"
REPORT_TYPE = "tpcds_genai_spec_isomera_protocol"
BENCHMARK_RUNS = 10
SCREENING_EPOCHS = 5
FULL_VALIDATION_EPOCHS = 5
TRAIN_RATIO = 0.8
SEED = 42
FORCE_RETRAIN = False

REPRESENTATIVE_SCENARIOS = [
    "graph_SOR2_D5_seed42",
    "graph_SOR4_D5_seed42",
    "graph_SOR8_D5_seed42",
    "graph_SOR16_D3_seed42",
    "graph_SOR16_D5_seed42",
]

STRATEGIES: list[dict[str, Any]] = [
    {
        "key": "weighted_bce",
        "label": "Weighted BCE",
        "model_family": "GNN GenAI Spec Protocol Weighted BCE",
        "balance_strategy": "class_weighted_loss",
        "loss_name": "bce_with_logits",
        "negative_ratio": 1,
        "training_goal": "Preserve the supervised distribution and compensate rare duplicates through pos_weight.",
    },
    {
        "key": "focal_loss",
        "label": "Focal Loss",
        "model_family": "GNN GenAI Spec Protocol Focal Loss",
        "balance_strategy": "none_real_distribution",
        "loss_name": "focal_loss",
        "negative_ratio": 1,
        "training_goal": "Keep the real distribution and concentrate gradients on hard or uncertain pairs.",
    },
    {
        "key": "hard_negatives",
        "label": "Hard Negatives",
        "model_family": "GNN GenAI Spec Protocol Hard Negatives",
        "balance_strategy": "hard_negative_mining",
        "loss_name": "bce_with_logits",
        "negative_ratio": 2,
        "training_goal": "Prefer structurally similar non-duplicates to improve the decision boundary.",
    },
]
LEARNING_RATES = [0.001, 0.005, 0.010]
HIDDEN_CHANNELS = [16, 32]
DROPOUTS = [0.0, 0.1]
THRESHOLDS = [0.4, 0.5, 0.6]
TOP_CONFIGS = 5


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(message: str) -> None:
    print(f"[tpcds_genai_spec_protocol] {message}", flush=True)


def _slug_float(value: float) -> str:
    return str(value).replace(".", "p")


def _capture_root() -> Path:
    root = MAIN_ROOT / "data" / "article_capture" / BENCHMARK_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _benchmark_root() -> Path:
    root = MAIN_ROOT / "data" / "architectures" / BENCHMARK_NAME
    for child in ("gml", "real_pairs", "validations", "models", "screening_models", "protocol"):
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


def _config_grid() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for strategy, learning_rate, hidden_channels, dropout, threshold in product(
        STRATEGIES,
        LEARNING_RATES,
        HIDDEN_CHANNELS,
        DROPOUTS,
        THRESHOLDS,
    ):
        config_id = (
            f"{strategy['key']}_lr{_slug_float(float(learning_rate))}"
            f"_h{hidden_channels}_d{_slug_float(float(dropout))}_t{_slug_float(float(threshold))}"
        )
        rows.append(
            {
                "config_id": config_id,
                "strategy_key": strategy["key"],
                "strategy_label": strategy["label"],
                "model_family": strategy["model_family"],
                "balance_strategy": strategy["balance_strategy"],
                "loss_name": strategy["loss_name"],
                "negative_ratio": strategy["negative_ratio"],
                "learning_rate": learning_rate,
                "hidden_channels": hidden_channels,
                "dropout": dropout,
                "threshold": threshold,
                "optimizer": "adam",
                "screening_epochs": SCREENING_EPOCHS,
                "full_validation_epochs": FULL_VALIDATION_EPOCHS,
                "train_ratio": TRAIN_RATIO,
                "seed": SEED,
            }
        )
    return rows


def _training_progress_logger(stage: str, scenario_name: str, config_id: str):
    def _callback(payload: dict[str, Any]) -> None:
        if payload.get("step") == "training":
            _log(
                f"{stage}/{scenario_name}/{config_id}: epoch={payload.get('current_epoch')}/{payload.get('epochs')} "
                f"train_loss={payload.get('train_loss')} val_loss={payload.get('val_loss')}"
            )
    return _callback


def _train_or_load(
    *,
    stage: str,
    config: dict[str, Any],
    scenario_name: str,
    gml_path: Path,
    labels_path: Path,
    validation_csv: Path,
    model_path: Path,
    epochs: int,
) -> tuple[dict[str, Any], bool, float]:
    metadata_path = model_path.with_suffix(".json")
    if metadata_path.exists() and model_path.exists() and not FORCE_RETRAIN:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        return metadata, True, 0.0

    start = time.perf_counter()
    metadata = train_benchmark_gnn(
        [
            ScenarioTrainingSpec(
                scenario_name=scenario_name,
                graph_path=gml_path,
                labels_path=labels_path,
                supervised_labels_path=validation_csv,
            )
        ],
        model_path=model_path,
        epochs=epochs,
        learning_rate=float(config["learning_rate"]),
        hidden_channels=int(config["hidden_channels"]),
        dropout=float(config["dropout"]),
        negative_ratio=int(config["negative_ratio"]),
        seed=int(config["seed"]),
        optimizer_name="adam",
        train_ratio=TRAIN_RATIO,
        balance_strategy=str(config["balance_strategy"]),
        loss_name=str(config["loss_name"]),
        progress_callback=_training_progress_logger(stage, scenario_name, str(config["config_id"])),
    )
    wall_seconds = time.perf_counter() - start
    metadata.update(
        {
            "config_id": config["config_id"],
            "protocol_stage": stage,
            "inference_threshold": config["threshold"],
            "wall_seconds": round(wall_seconds, 6),
            "model_family": config["model_family"],
        }
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
    return metadata, False, wall_seconds


def _evaluate_detector(
    *,
    scenario_name: str,
    graph: nx.DiGraph,
    true_pairs: list[tuple[str, str]],
    algorithm: str,
    artifact_path: str,
    artifact_role: str,
    route_mode: str,
    route_source: str,
    predictor,
    threshold: float,
    runs: int,
) -> dict[str, Any]:
    candidate_pairs = _candidate_spec_pairs(graph)
    true_set = canonical_pairs(true_pairs) & canonical_pairs(candidate_pairs)
    predictions: set[tuple[str, str]] = set()
    timings: list[float] = []
    for run_index in range(1, runs + 1):
        start = time.perf_counter()
        predictions = canonical_pairs(predictor())
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        _log(f"{scenario_name}: {algorithm} run {run_index}/{runs} {elapsed:.4f}s")
    metrics = confusion_metrics_pairs(true_set, predictions, all_pairs=candidate_pairs)
    et = float(median(timings)) if timings else 0.0
    accuracy = float(metrics["accuracy"] or 0.0)
    jaccard = _jaccard(true_set, predictions)
    evaluated_pairs = len(candidate_pairs)
    return {
        "scenario": scenario_name,
        "algorithm": algorithm,
        "artifact_path": artifact_path,
        "artifact_role": artifact_role,
        "route_mode": route_mode,
        "route_source": route_source,
        "inference_threshold": threshold,
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
        "runs": runs,
    }


def _aggregate_benchmark(per_scenario: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
                "runs": int(group["runs"].max()),
                "aggregation": "SF is computed per scenario as score * N_pairs / ET and averaged across scenarios.",
            }
        )
    return summary


def _score_config_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    df = pd.DataFrame(rows)
    summary: list[dict[str, Any]] = []
    for config_id, group in df.groupby("config_id", sort=False):
        first = group.iloc[0].to_dict()
        summary.append(
            {
                "config_id": config_id,
                "rank": None,
                "strategy_label": first["strategy_label"],
                "balance_strategy": first["balance_strategy"],
                "loss_name": first["loss_name"],
                "learning_rate": first["learning_rate"],
                "hidden_channels": first["hidden_channels"],
                "dropout": first["dropout"],
                "threshold": first["threshold"],
                "screening_scenarios": int(group["scenario"].nunique()),
                "mean_sf_jaccard": round(float(group["sf_jaccard"].mean()), 6),
                "mean_jaccard": round(float(group["jaccard"].mean()), 6),
                "mean_accuracy": round(float(group["accuracy"].mean()), 6),
                "median_ET": round(float(group["ET"].median()), 6),
                "tp": int(group["tp"].sum()),
                "fp": int(group["fp"].sum()),
                "fn": int(group["fn"].sum()),
                "tn": int(group["tn"].sum()),
            }
        )
    summary.sort(key=lambda row: (row["mean_sf_jaccard"], row["mean_jaccard"], -row["median_ET"]), reverse=True)
    for index, row in enumerate(summary, start=1):
        row["rank"] = index
    return summary


def _write_capture(payload: dict[str, Any], graph_for_figures: nx.DiGraph) -> dict[str, str]:
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
            payload["publication_tables"]["benchmark_metrics"],
            payload["publication_tables"].get("benchmark_per_scenario_metrics", []),
            capture_root,
        )
    )
    payload["capture_paths"] = paths
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    md_path.write_text(
        "\n".join(
            [
                f"# {BENCHMARK_DISPLAY_NAME} - Isomera Staged Protocol",
                "",
                f"- Screening trainings: {len(REPRESENTATIVE_SCENARIOS)} scenarios x 108 configs",
                f"- Full validation trainings: 20 scenarios x top {TOP_CONFIGS} configs",
                f"- Benchmark runs: {BENCHMARK_RUNS}",
                "",
                "```json",
                json.dumps(payload["publication_tables"]["benchmark_metrics"], indent=2, ensure_ascii=True),
                "```",
            ]
        ),
        encoding="utf-8",
    )
    return paths


def main() -> None:
    started_at = time.perf_counter()
    _log("initializing MySQL publication store")
    init_publication_store(MYSQL_URL)
    benchmark_root = _benchmark_root()
    scenario_specs = _load_manifest_index()
    scenario_specs = sorted(scenario_specs, key=lambda row: str(row.get("scenario")))
    _log(f"loaded {len(scenario_specs)} manifest scenarios")

    graphs: dict[str, nx.DiGraph] = {}
    labels: dict[str, list[tuple[str, str]]] = {}
    source_metadata_by_scenario: dict[str, dict[str, Any]] = {}
    scenario_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    lineage_rows: list[dict[str, Any]] = []
    edge_rows: list[dict[str, Any]] = []
    adjacency_rows: list[dict[str, Any]] = []
    v1_paths: dict[str, Path] = {}
    genai_v1_paths: dict[str, Path] = {}
    validation_paths: dict[str, dict[str, Path]] = {}
    publish_ids: list[dict[str, str]] = []

    filters = {
        "scope_layers": ["SPEC"],
        "constraints": ["complete_upstream_lineage", "same_layer_only", "cross_domain_allowed"],
        "same_layer_only": True,
        "same_domain_only": False,
        "candidate_generation": "all SPEC-to-SPEC combinations",
        "protocol_name": "Isomera Staged Protocol",
        "selection_metric": "SF-Jaccard",
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
        "note": "The report stores final labels, decision features, confidence, and rationale, not private chain-of-thought.",
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
        validation_paths[scenario_name] = {
            "gml": gml_path,
            "csv": validation_csv,
            "json": validation_json,
            "labels": labels_path,
        }

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
        genai_v1_path = MAIN_ROOT / "data" / "architectures" / "tpc_ds_genai_spec" / "models" / f"GNN_tpcds_genai_spec_{scenario_name}.pkl"
        if genai_v1_path.exists():
            genai_v1_paths[scenario_name] = genai_v1_path

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
                },
            )
        )

    configs = _config_grid()
    _write_rows(benchmark_root / "protocol" / "config_grid.csv", configs)
    _log(f"screening: {len(REPRESENTATIVE_SCENARIOS)} scenarios x {len(configs)} configs = {len(REPRESENTATIVE_SCENARIOS) * len(configs)} trainings")
    screening_rows: list[dict[str, Any]] = []
    training_rows: list[dict[str, Any]] = []
    training_history: list[dict[str, Any]] = []

    for config_index, config in enumerate(configs, start=1):
        _log(f"screening config {config_index}/{len(configs)}: {config['config_id']}")
        for scenario_name in REPRESENTATIVE_SCENARIOS:
            paths = validation_paths[scenario_name]
            model_path = benchmark_root / "screening_models" / str(config["config_id"]) / f"{scenario_name}.pkl"
            metadata, cached, wall_seconds = _train_or_load(
                stage="screening",
                config=config,
                scenario_name=scenario_name,
                gml_path=paths["gml"],
                labels_path=paths["labels"],
                validation_csv=paths["csv"],
                model_path=model_path,
                epochs=SCREENING_EPOCHS,
            )
            candidate_pairs = _candidate_spec_pairs(graphs[scenario_name])
            true_set = canonical_pairs(labels[scenario_name]) & canonical_pairs(candidate_pairs)
            start = time.perf_counter()
            predicted = _predict_candidate_pairs_with_pickle(graphs[scenario_name], model_path, candidate_pairs, threshold=float(config["threshold"]))
            et = time.perf_counter() - start
            metrics = confusion_metrics_pairs(true_set, predicted, all_pairs=candidate_pairs)
            accuracy = float(metrics["accuracy"] or 0.0)
            jaccard = _jaccard(true_set, canonical_pairs(predicted))
            row = {
                **config,
                "stage": "screening",
                "scenario": scenario_name,
                "model_path": str(model_path),
                "cached": cached,
                "training_wall_seconds": round(wall_seconds, 6),
                "accuracy": round(accuracy, 6),
                "jaccard": round(jaccard, 6),
                "sf_jaccard": round(success_frequency(jaccard, et, len(candidate_pairs)), 6),
                "sf_accuracy": round(success_frequency(accuracy, et, len(candidate_pairs)), 6),
                "ET": round(et, 6),
                "N_pairs": len(candidate_pairs),
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "fn": metrics["fn"],
                "tn": metrics["tn"],
            }
            screening_rows.append(row)
            for item in metadata.get("history") or []:
                training_history.append({"stage": "screening", "scenario": scenario_name, "config_id": config["config_id"], **item})

    screening_summary = _score_config_rows(screening_rows)
    selected_configs = screening_summary[:TOP_CONFIGS]
    selected_by_id = {str(row["config_id"]): row for row in selected_configs}
    _write_rows(benchmark_root / "protocol" / "screening_results.csv", screening_rows)
    _write_rows(benchmark_root / "protocol" / "screening_summary.csv", screening_summary)
    _write_rows(benchmark_root / "protocol" / "selected_top_configs.csv", selected_configs)
    _log("selected top configs: " + ", ".join(str(row["config_id"]) for row in selected_configs))

    full_model_paths: dict[str, dict[str, Path]] = {str(row["config_id"]): {} for row in selected_configs}
    for selected_index, selected in enumerate(selected_configs, start=1):
        config = next(row for row in configs if str(row["config_id"]) == str(selected["config_id"]))
        config["rank"] = selected_index
        _log(f"full validation rank {selected_index}/{TOP_CONFIGS}: {config['config_id']}")
        for scenario_name in graphs:
            paths = validation_paths[scenario_name]
            model_path = benchmark_root / "models" / f"rank{selected_index}_{config['config_id']}" / f"GNN_tpcds_genai_spec_protocol_rank{selected_index}_{scenario_name}.pkl"
            metadata, cached, wall_seconds = _train_or_load(
                stage="full_validation",
                config=config,
                scenario_name=scenario_name,
                gml_path=paths["gml"],
                labels_path=paths["labels"],
                validation_csv=paths["csv"],
                model_path=model_path,
                epochs=FULL_VALIDATION_EPOCHS,
            )
            full_model_paths[str(config["config_id"])][scenario_name] = model_path
            for row in metadata.get("dataset_summary") or []:
                training_rows.append(
                    {
                        **row,
                        "stage": "full_validation",
                        "rank": selected_index,
                        "config_id": config["config_id"],
                        "strategy_label": config["strategy_label"],
                        "model_family": f"GNN GenAI Spec Protocol rank {selected_index}",
                        "model_path": str(model_path),
                        "cached": cached,
                        "training_wall_seconds": round(wall_seconds, 6),
                    }
                )
            for item in metadata.get("history") or []:
                training_history.append({"stage": "full_validation", "rank": selected_index, "scenario": scenario_name, "config_id": config["config_id"], **item})

    _log(f"running final benchmark with {BENCHMARK_RUNS} runs per detector family")
    per_scenario_metrics: list[dict[str, Any]] = []
    for scenario_index, (scenario_name, graph) in enumerate(graphs.items(), start=1):
        _log(f"benchmark scenario {scenario_index}/{len(graphs)}: {scenario_name}")
        candidate_pairs = _candidate_spec_pairs(graph)
        candidate_set = canonical_pairs(candidate_pairs)
        detectors: list[dict[str, Any]] = [
            {
                "algorithm": "VF2",
                "artifact_path": "",
                "artifact_role": "deterministic_baseline",
                "route_mode": "not_applicable",
                "route_source": "deterministic_algorithm",
                "threshold": 0.0,
                "predictor": lambda g=graph, c=candidate_set: canonical_pairs(find_isomorphic_pairs(g, algorithm="VF2")) & c,
            },
            {
                "algorithm": "Node Match",
                "artifact_path": "",
                "artifact_role": "deterministic_baseline",
                "route_mode": "not_applicable",
                "route_source": "deterministic_algorithm",
                "threshold": 0.0,
                "predictor": lambda g=graph, c=candidate_set: canonical_pairs(find_isomorphic_pairs(g, algorithm="Node Match (Custom)")) & c,
            },
            {
                "algorithm": "GNN TPC-DS v1 cluster",
                "artifact_path": str(v1_paths[scenario_name]),
                "artifact_role": "baseline_tpcds_pickle",
                "route_mode": "scenario_specific",
                "route_source": "TPC-DS v1 pickle map",
                "threshold": 0.5,
                "predictor": lambda g=graph, p=v1_paths[scenario_name], pairs=candidate_pairs: _predict_candidate_pairs_with_pickle(g, p, pairs, threshold=0.5),
            },
        ]
        if scenario_name in genai_v1_paths:
            detectors.append(
                {
                    "algorithm": "GNN GenAI Spec v1 cluster",
                    "artifact_path": str(genai_v1_paths[scenario_name]),
                    "artifact_role": "genai_spec_v1_pickle",
                    "route_mode": "scenario_specific",
                    "route_source": "TPC-DS GenAI Spec previous cluster",
                    "threshold": 0.30,
                    "predictor": lambda g=graph, p=genai_v1_paths[scenario_name], pairs=candidate_pairs: _predict_candidate_pairs_with_pickle(g, p, pairs, threshold=0.30),
                }
            )
        for selected in selected_configs:
            rank = int(selected["rank"])
            config_id = str(selected["config_id"])
            model_path = full_model_paths[config_id][scenario_name]
            threshold = float(selected["threshold"])
            detectors.append(
                {
                    "algorithm": f"GNN GenAI Spec Protocol rank {rank}",
                    "artifact_path": str(model_path),
                    "artifact_role": f"isomera_protocol_top_{rank}",
                    "route_mode": "scenario_specific",
                    "route_source": f"Isomera Staged Protocol selected config {config_id}",
                    "threshold": threshold,
                    "predictor": lambda g=graph, p=model_path, pairs=candidate_pairs, t=threshold: _predict_candidate_pairs_with_pickle(g, p, pairs, threshold=t),
                }
            )
        for detector in detectors:
            per_scenario_metrics.append(
                _evaluate_detector(
                    scenario_name=scenario_name,
                    graph=graph,
                    true_pairs=labels[scenario_name],
                    algorithm=str(detector["algorithm"]),
                    artifact_path=str(detector["artifact_path"]),
                    artifact_role=str(detector["artifact_role"]),
                    route_mode=str(detector["route_mode"]),
                    route_source=str(detector["route_source"]),
                    predictor=detector["predictor"],
                    threshold=float(detector["threshold"]),
                    runs=BENCHMARK_RUNS,
                )
            )
    benchmark_metrics = _aggregate_benchmark(per_scenario_metrics)
    mysql_counts = _mysql_row_counts(MYSQL_URL, benchmark_name=BENCHMARK_NAME)

    routing_rows: list[dict[str, Any]] = []
    model_artifact_rows: list[dict[str, Any]] = []
    for scenario_name in graphs:
        for family, path, role, source in [
            ("GNN TPC-DS v1 cluster", v1_paths[scenario_name], "baseline_tpcds_pickle", "TPC-DS v1 pickle map"),
            ("GNN GenAI Spec v1 cluster", genai_v1_paths.get(scenario_name), "genai_spec_v1_pickle", "TPC-DS GenAI Spec previous cluster"),
        ]:
            if path:
                row = {
                    "model_family": family,
                    "scenario": scenario_name,
                    "artifact_path": str(path),
                    "artifact_role": role,
                    "route_mode": "scenario_specific",
                    "route_source": source,
                }
                routing_rows.append(row)
                model_artifact_rows.append({**row, "model_name": f"{family}::{scenario_name}"})
        for selected in selected_configs:
            rank = int(selected["rank"])
            config_id = str(selected["config_id"])
            path = full_model_paths[config_id][scenario_name]
            row = {
                "model_family": f"GNN GenAI Spec Protocol rank {rank}",
                "scenario": scenario_name,
                "artifact_path": str(path),
                "artifact_role": f"isomera_protocol_top_{rank}",
                "route_mode": "scenario_specific",
                "route_source": f"Isomera Staged Protocol selected config {config_id}",
                "config_id": config_id,
                "threshold": selected["threshold"],
            }
            routing_rows.append(row)
            model_artifact_rows.append({**row, "model_name": f"GNN GenAI Spec Protocol rank {rank}::{scenario_name}"})

    cluster_rows = [
        {"model_family": "VF2", "artifact_count": 0, "scenario_count": len(graphs), "coverage": "20/20", "reporting_rule": "deterministic baseline"},
        {"model_family": "Node Match", "artifact_count": 0, "scenario_count": len(graphs), "coverage": "20/20", "reporting_rule": "deterministic semantic baseline"},
        {"model_family": "GNN TPC-DS v1 cluster", "artifact_count": len(v1_paths), "scenario_count": len(graphs), "coverage": f"{len(v1_paths)}/{len(graphs)}", "reporting_rule": "one baseline pickle routed per scenario"},
        {"model_family": "GNN GenAI Spec v1 cluster", "artifact_count": len(genai_v1_paths), "scenario_count": len(graphs), "coverage": f"{len(genai_v1_paths)}/{len(graphs)}", "reporting_rule": "previous GenAI SPEC cluster routed per scenario"},
    ]
    for selected in selected_configs:
        rank = int(selected["rank"])
        config_id = str(selected["config_id"])
        cluster_rows.append(
            {
                "model_family": f"GNN GenAI Spec Protocol rank {rank}",
                "artifact_count": len(full_model_paths[config_id]),
                "scenario_count": len(graphs),
                "coverage": f"{len(full_model_paths[config_id])}/{len(graphs)}",
                "reporting_rule": f"Isomera staged protocol top {rank}; config={config_id}",
            }
        )

    total_pairs = sum(int(row["total_pairs"]) for row in scenario_rows)
    candidate_pairs = sum(int(row["candidate_pairs"]) for row in scenario_rows)
    duplicate_pairs = sum(int(row["positive_pairs"]) for row in scenario_rows)
    best_config = selected_configs[0]
    best_model_path = next(iter(full_model_paths[str(best_config["config_id"])].values()))
    runtime_seconds = time.perf_counter() - started_at
    source_details = [
        {"field": "benchmark_name", "value": BENCHMARK_NAME},
        {"field": "benchmark_display_name", "value": BENCHMARK_DISPLAY_NAME},
        {"field": "protocol_name", "value": "Isomera Staged Protocol"},
        {"field": "database_engine", "value": "PostgreSQL"},
        {"field": "database_name", "value": "isomera_tpcds_benchmark"},
        {"field": "database_url", "value": POSTGRES_URL},
        {"field": "publication_backend", "value": "MySQL"},
        {"field": "publication_url", "value": MYSQL_URL},
        {"field": "scenario_count", "value": len(graphs)},
        {"field": "candidate_pairs", "value": candidate_pairs},
        {"field": "duplicate_pairs", "value": duplicate_pairs},
        {"field": "screening_trainings", "value": len(REPRESENTATIVE_SCENARIOS) * len(configs)},
        {"field": "full_validation_trainings", "value": len(graphs) * TOP_CONFIGS},
        {"field": "benchmark_runs", "value": BENCHMARK_RUNS},
        {"field": "runtime_seconds", "value": round(runtime_seconds, 3)},
        {"field": "validator_model", "value": "OpenAI GPT-5.4 via Codex CLI agent"},
        {"field": "validator_reasoning_effort", "value": "xhigh"},
    ]
    training_strategy_comparison = [
        {
            "model_family": strategy["model_family"],
            "balance_strategy": strategy["balance_strategy"],
            "loss_name": strategy["loss_name"],
            "screening_epochs": SCREENING_EPOCHS,
            "full_validation_epochs": FULL_VALIDATION_EPOCHS,
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
        "model_name": "GNN_tpcds_genai_spec_isomera_protocol",
        "model_path": str(best_model_path),
        "model_family_name": "GNN (GIN Pair Classifier) v1",
        "optimizer": "Adam",
        "optimizer_label": "Adaptive gradient optimizer (torch.optim.Adam)",
        "optimizer_name": "torch.optim.Adam",
        "loss_name": str(best_config["loss_name"]),
        "resolved_hyperparameters": {
            "selected_config_id": best_config["config_id"],
            "screening_epochs": SCREENING_EPOCHS,
            "full_validation_epochs": FULL_VALIDATION_EPOCHS,
            "learning_rate": best_config["learning_rate"],
            "hidden_channels": best_config["hidden_channels"],
            "dropout": best_config["dropout"],
            "train_ratio": TRAIN_RATIO,
            "test_ratio": round(1.0 - TRAIN_RATIO, 6),
            "balance_strategy": best_config["balance_strategy"],
            "loss_name": best_config["loss_name"],
            "inference_threshold": best_config["threshold"],
            "seed": SEED,
        },
        "training_summary": {
            "scenarios": list(graphs.keys()),
            "dataset_summary": training_rows,
            "history": training_history,
            "status": "completed",
            "protocol": "Isomera Staged Protocol",
            "screening_trainings": len(REPRESENTATIVE_SCENARIOS) * len(configs),
            "full_validation_trainings": len(graphs) * TOP_CONFIGS,
            "selected_top_configs": selected_configs,
            "train_distribution": {"positive_pairs": duplicate_pairs, "negative_pairs": candidate_pairs - duplicate_pairs, "dataset_rows": candidate_pairs},
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
            {"filter": "Lineage scope", "setting": "SPEC only", "effect": "Only SPEC outputs enter candidate generation; each SPEC keeps complete upstream lineage."},
            {"filter": "Same layer", "setting": "enabled", "effect": "All reviewed pairs are SPEC-to-SPEC."},
            {"filter": "Same domain", "setting": "disabled", "effect": "Cross-domain duplicates remain eligible."},
            {"filter": "Protocol", "setting": "Isomera Staged Protocol", "effect": "Screen 108 configs on representative scenarios, then validate top 5 across all scenarios."},
        ],
        "genai_validation_protocol": [validator_protocol],
        "hyperparameter_search_grid": _hyperparameter_search_grid_rows(),
        "hyperparameter_search_protocol": _hyperparameter_search_protocol_rows(),
        "protocol_config_grid": configs,
        "protocol_screening_results": screening_rows,
        "protocol_screening_summary": screening_summary,
        "protocol_selected_top_configs": selected_configs,
        "training_strategy_comparison": training_strategy_comparison,
        "training_strategy_theory": _training_strategy_theory_rows(),
        "validation_dataset": validation_rows,
        "training_dataset": training_rows,
        "training_history": training_history,
        "model_artifact": model_artifact_rows,
        "model_cluster_summary": cluster_rows,
        "model_cluster_routing": routing_rows,
        "benchmark_metrics": benchmark_metrics,
        "benchmark_per_scenario_metrics": per_scenario_metrics,
        "benchmark_pickle_results": [row for row in per_scenario_metrics if str(row.get("artifact_path") or "")],
        "mysql_row_counts": mysql_counts,
        "formulas": [
            {"formula": "Accuracy = (TP + TN) / (TP + TN + FP + FN)"},
            {"formula": "Jaccard = TP / (TP + FP + FN)"},
            {"formula": "ET = median(t_i), i = 1..runs"},
            {"formula": "SF_accuracy = Accuracy * N_pairs / ET"},
            {"formula": "SF_jaccard = Jaccard * N_pairs / ET"},
            {"formula": "GNN prediction = 1 if sigmoid(logit) >= threshold"},
            {"formula": "Weighted BCE pos_weight = N_negative / N_positive"},
            {"formula": "FocalLoss = -alpha(1-p_t)^gamma log(p_t)"},
            {"formula": "Hard negative score = |nodes_a - nodes_b| + |edges_a - edges_b|"},
        ],
        "layers": [
            {"layer": "GIN layer 1", "operation": "neighbor aggregation over node-centered upstream lineage subgraph"},
            {"layer": "ReLU", "operation": "non-linear activation"},
            {"layer": "GIN layer 2", "operation": "second aggregation and embedding projection"},
            {"layer": "Mean pooling", "operation": "one vector embedding per subgraph"},
            {"layer": "Pair MLP with dropout", "operation": "binary duplicate logit"},
        ],
        "pipeline": [
            {"stage": "source", "input": "PostgreSQL scenario warehouse", "output": f"{len(scenario_rows)} TPC-DS scenario schemas", "details": "Each schema is materialized through the Scenario Materialization API."},
            {"stage": "normalized_graph", "input": "manifest-defined relational contract", "output": f"{sum(int(row['nodes']) for row in scenario_rows)} nodes / {sum(int(row['edges']) for row in scenario_rows)} edges", "details": "Edges are normalized to SOR -> SOT -> SPEC before validation, training, and benchmark."},
            {"stage": "validation_dataset", "input": "SPEC candidate pairs plus GenAI validation rubric", "output": f"{candidate_pairs} supervised rows", "details": "All SPEC candidate pairs receive target=1 or target=0."},
            {"stage": "screening", "input": "108 hyperparameter configurations", "output": f"{len(screening_rows)} screening result rows", "details": "Five representative scenarios select top configurations by SF-Jaccard."},
            {"stage": "full_validation_training", "input": f"top {TOP_CONFIGS} configs", "output": f"{len(graphs) * TOP_CONFIGS} scenario-specific pickles", "details": "Each selected config is retrained for every scenario."},
            {"stage": "benchmark_execution", "input": "detector families and explicit artifact routing", "output": f"{len(benchmark_metrics)} detector-family rows / {len(per_scenario_metrics)} scenario rows", "details": "Each detector is executed with 10 timing runs."},
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
            "goal": "Execute the first final benchmark reference with the real Isomera Staged Protocol on SPEC lineage candidates.",
            "graph_construction_method": "Read all PostgreSQL benchmark schemas, materialize normalized lineage graphs, create a GenAI-assisted SPEC supervised dataset, run the staged search, route scenario-specific pickles, and benchmark detector families with 10 timing runs.",
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
            "K_screening_epochs": SCREENING_EPOCHS,
            "K_full_validation_epochs": FULL_VALIDATION_EPOCHS,
            "screening_config_count": len(configs),
            "representative_scenarios": len(REPRESENTATIVE_SCENARIOS),
            "full_validation_config_count": TOP_CONFIGS,
            "benchmark_runs": BENCHMARK_RUNS,
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
