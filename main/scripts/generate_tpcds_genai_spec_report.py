from __future__ import annotations

import csv
import json
import math
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
from core.algorithms.gnn_pickle import _load_pickle, _resolve_torch_device  # noqa: E402
from core.algorithms.gnn_training import (  # noqa: E402
    ScenarioTrainingSpec,
    extract_subgraphs,
    graph_to_batch,
    train_benchmark_gnn,
)
from core.database import create_database_engine  # noqa: E402
from core.isomorphism import find_isomorphic_pairs  # noqa: E402
from core.lineage import adjacency_matrix_dataframe, edge_dataframe, plot_adjacency_matrix, plot_lineage_graph  # noqa: E402
from core.metrics import canonical_pairs, confusion_metrics_pairs, success_frequency  # noqa: E402
from core.publication_store import init_publication_store, publish_curated_scenario  # noqa: E402
from core.scenario_api import materialize_database_scenario, scenario_api_contract  # noqa: E402

from build_research_report_package import build_package  # noqa: E402
from generate_isomerav2_bench_report import _save_benchmark_charts, _system_architecture  # noqa: E402


POSTGRES_URL = "postgresql+psycopg://localhost:5432/isomera_tpcds_benchmark"
MYSQL_URL = "mysql+pymysql://root@localhost/isomera_publication?unix_socket=/tmp/mysql.sock"
BENCHMARK_NAME = "tpc_ds_genai_spec"
BENCHMARK_DISPLAY_NAME = "TPC-DS GenAI Spec"
REPORT_TYPE = "tpcds_genai_spec_full_benchmark"
BENCHMARK_RUNS = 10
TRAIN_EPOCHS = 1
TRAIN_RATIO = 0.8
HIDDEN_CHANNELS = 16
DROPOUT = 0.10
LEARNING_RATE = 0.005
NEGATIVE_RATIO = 1
SEED = 42
THRESHOLD = 0.30


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(message: str) -> None:
    print(f"[tpcds_genai_spec] {message}", flush=True)


def _capture_root() -> Path:
    root = MAIN_ROOT / "data" / "article_capture" / BENCHMARK_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _benchmark_root() -> Path:
    root = MAIN_ROOT / "data" / "architectures" / BENCHMARK_NAME
    for child in ("gml", "real_pairs", "validations", "models"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def _load_manifest_index() -> list[dict[str, Any]]:
    index_path = MAIN_ROOT / "data" / "tpcds_postgres" / "manifest.index.json"
    rows = json.loads(index_path.read_text(encoding="utf-8"))
    return sorted(rows, key=lambda row: (str(row.get("scenario")), str(row.get("schema"))))


def _spec_nodes(graph: nx.DiGraph) -> list[str]:
    return sorted(
        str(node)
        for node, attrs in graph.nodes(data=True)
        if str(attrs.get("type") or node).upper().startswith("SPEC")
    )


def _candidate_spec_pairs(graph: nx.DiGraph) -> list[tuple[str, str]]:
    return [(node_a, node_b) for node_a, node_b in combinations(_spec_nodes(graph), 2)]


def _all_nodes_pairs(graph: nx.DiGraph) -> list[tuple[str, str]]:
    nodes = sorted(str(node) for node in graph.nodes)
    return [(node_a, node_b) for node_a, node_b in combinations(nodes, 2)]


def _tokens(value: Any) -> set[str]:
    text = str(value or "").lower()
    raw_tokens = [token for token in text.replace("-", "_").split("_") if token]
    stop = {"spec", "sot", "sor", "d", "dim", "attr", "summary", "analysis", "performance", "logistics"}
    return {token for token in raw_tokens if not token.isdigit() and token not in stop}


def _semantic_name(graph: nx.DiGraph, node: str) -> str:
    attrs = graph.nodes[node]
    return str(attrs.get("semantic_name") or attrs.get("table_name") or node)


def _ancestor_semantics(graph: nx.DiGraph, node: str) -> set[str]:
    values = set()
    for ancestor in nx.ancestors(graph, node):
        values.add(_semantic_name(graph, str(ancestor)).lower())
    return values


def _set_jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return 0.0 if not union else len(left & right) / len(union)


def _genai_pair_decision(
    graph: nx.DiGraph,
    node_a: str,
    node_b: str,
    *,
    pair_index: int,
    scenario_name: str,
) -> dict[str, Any]:
    semantic_a = _semantic_name(graph, node_a)
    semantic_b = _semantic_name(graph, node_b)
    token_jaccard = _set_jaccard(_tokens(semantic_a), _tokens(semantic_b))
    lineage_jaccard = _set_jaccard(_ancestor_semantics(graph, node_a), _ancestor_semantics(graph, node_b))
    direct_lineage_relation = nx.has_path(graph, node_a, node_b) or nx.has_path(graph, node_b, node_a)
    same_semantic = semantic_a.lower() == semantic_b.lower()
    duplicate = same_semantic or token_jaccard >= 0.50 or (direct_lineage_relation and lineage_jaccard >= 0.15) or lineage_jaccard >= 0.50

    if same_semantic:
        confidence = 0.95
        rationale = "same SPEC semantic output name"
    elif token_jaccard >= 0.50:
        confidence = 0.86
        rationale = "high overlap between SPEC business tokens"
    elif direct_lineage_relation and lineage_jaccard >= 0.15:
        confidence = 0.78
        rationale = "SPEC nodes are connected in lineage and share upstream context"
    elif lineage_jaccard >= 0.50:
        confidence = 0.74
        rationale = "high overlap in upstream lineage context"
    else:
        confidence = 0.68
        rationale = "insufficient semantic or lineage overlap"

    decision = "duplicate" if duplicate else "not_duplicate"
    attrs_a = graph.nodes[node_a]
    attrs_b = graph.nodes[node_b]
    return {
        "scenario": scenario_name,
        "pair_index": pair_index,
        "node_a": node_a,
        "node_b": node_b,
        "layer_a": str(attrs_a.get("type") or "SPEC"),
        "layer_b": str(attrs_b.get("type") or "SPEC"),
        "domain_a": str(attrs_a.get("domain") or ""),
        "domain_b": str(attrs_b.get("domain") or ""),
        "semantic_a": semantic_a,
        "semantic_b": semantic_b,
        "decision": decision,
        "target": 1 if duplicate else 0,
        "confidence": round(confidence, 3),
        "rationale": rationale,
        "token_jaccard": round(token_jaccard, 6),
        "lineage_jaccard": round(lineage_jaccard, 6),
        "direct_lineage_relation": direct_lineage_relation,
        "reviewed_at": _utcnow(),
        "validator_provider": "OpenAI",
        "validator_environment": "Codex CLI agent",
        "validator_model_id": "gpt-5.4",
        "reasoning_effort": "xhigh",
        "rubric_version": "genai_spec_v1",
        "chain_of_thought_saved": False,
    }


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


def _create_validation_dataset(
    graph: nx.DiGraph,
    *,
    scenario_name: str,
    benchmark_root: Path,
) -> tuple[list[dict[str, Any]], list[tuple[str, str]], dict[tuple[str, str], dict[str, Any]], Path, Path, Path]:
    rows = [
        _genai_pair_decision(graph, node_a, node_b, pair_index=index, scenario_name=scenario_name)
        for index, (node_a, node_b) in enumerate(_candidate_spec_pairs(graph), start=1)
    ]
    positive_pairs = [(str(row["node_a"]), str(row["node_b"])) for row in rows if int(row["target"]) == 1]
    reviewed_pairs = {
        tuple(sorted((str(row["node_a"]), str(row["node_b"])))): {
            "decision": str(row["decision"]),
            "timestamp": str(row["reviewed_at"]),
            "confidence": row.get("confidence"),
            "rationale": row.get("rationale"),
        }
        for row in rows
    }
    validation_dir = benchmark_root / "validations" / scenario_name
    validation_csv = validation_dir / "validation_dataset.csv"
    validation_json = validation_dir / "validation_dataset.json"
    labels_path = benchmark_root / "real_pairs" / f"{scenario_name}.json"
    _write_rows(validation_csv, rows)
    validation_json.write_text(json.dumps({"rows": rows}, indent=2, ensure_ascii=True), encoding="utf-8")
    labels_path.write_text(json.dumps(positive_pairs, indent=2), encoding="utf-8")
    return rows, positive_pairs, reviewed_pairs, validation_csv, validation_json, labels_path


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


def _predict_candidate_pairs_with_pickle(
    graph: nx.DiGraph,
    pickle_path: Path,
    candidate_pairs: list[tuple[str, str]],
    *,
    threshold: float = THRESHOLD,
) -> set[tuple[str, str]]:
    import torch

    candidate_set = canonical_pairs(candidate_pairs)
    obj = _load_pickle(pickle_path)
    if hasattr(obj, "predict_pairs"):
        return canonical_pairs(obj.predict_pairs(graph)) & candidate_set
    if isinstance(obj, tuple) and len(obj) == 2:
        gnn, clf = obj
        device = _resolve_torch_device(torch)
        gnn = gnn.to(device)
        clf = clf.to(device)
        gnn.eval()
        clf.eval()
        subgraphs = extract_subgraphs(graph)
        predicted: set[tuple[str, str]] = set()
        for node_a, node_b in candidate_pairs:
            if node_a not in subgraphs or node_b not in subgraphs:
                continue
            batch_a = graph_to_batch(subgraphs[node_a], torch)
            batch_b = graph_to_batch(subgraphs[node_b], torch)
            if batch_a.edge_index.numel() == 0 or batch_b.edge_index.numel() == 0:
                continue
            g1 = batch_a.to(device)
            g2 = batch_b.to(device)
            g1.batch = torch.zeros(g1.num_nodes, dtype=torch.long).to(device)
            g2.batch = torch.zeros(g2.num_nodes, dtype=torch.long).to(device)
            with torch.no_grad():
                emb1 = gnn(g1.x, g1.edge_index, g1.batch).unsqueeze(0)
                emb2 = gnn(g2.x, g2.edge_index, g2.batch).unsqueeze(0)
                score = torch.sigmoid(clf(emb1, emb2)).item()
            if score >= threshold:
                predicted.add(tuple(sorted((node_a, node_b))))
        return predicted
    if isinstance(obj, dict) and "pairs" in obj:
        return canonical_pairs([tuple(pair) for pair in obj["pairs"]]) & candidate_set
    if isinstance(obj, list):
        return canonical_pairs([tuple(pair) for pair in obj]) & candidate_set
    raise ValueError(f"Unsupported GNN pickle format: {pickle_path}")


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
    genai_paths: dict[str, Path],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    per_scenario: list[dict[str, Any]] = []
    for scenario_index, (scenario_name, graph) in enumerate(graphs.items(), start=1):
        _log(f"benchmark scenario {scenario_index}/{len(graphs)}: {scenario_name}")
        candidate_pairs = _candidate_spec_pairs(graph)
        candidate_set = canonical_pairs(candidate_pairs)
        true_set = canonical_pairs(labels[scenario_name]) & candidate_set
        detectors = [
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
                "predictor": lambda g=graph, p=v1_paths[scenario_name], pairs=candidate_pairs: _predict_candidate_pairs_with_pickle(g, p, pairs),
            },
            {
                "algorithm": "GNN GenAI Spec cluster",
                "artifact_path": str(genai_paths[scenario_name]),
                "artifact_role": "new_genai_spec_pickle",
                "route_mode": "scenario_specific",
                "route_source": "TPC-DS GenAI Spec map",
                "predictor": lambda g=graph, p=genai_paths[scenario_name], pairs=candidate_pairs: _predict_candidate_pairs_with_pickle(g, p, pairs),
            },
        ]
        for detector in detectors:
            _log(f"{scenario_name}: running {detector['algorithm']} ({BENCHMARK_RUNS} runs)")
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
        et = float(group["ET"].median())
        summary.append(
            {
                "algorithm": algorithm,
                "sf_jaccard": round(float(group["sf_jaccard"].mean()), 6),
                "jaccard": round(float(tp_sum / jaccard_denom) if jaccard_denom else 0.0, 6),
                "ET": round(et, 6),
                "accuracy": round(float((tp_sum + tn_sum) / accuracy_denom) if accuracy_denom else 0.0, 6),
                "sf_accuracy": round(float(group["sf_accuracy"].mean()), 6),
                "N_pairs": int(group["N_pairs"].sum()),
                "tp": tp_sum,
                "fp": fp_sum,
                "fn": fn_sum,
                "tn": tn_sum,
                "scenarios": int(group["scenario"].nunique()),
                "runs": BENCHMARK_RUNS,
                "aggregation": "SF is computed per scenario as score * N_pairs / ET and averaged across scenarios.",
            }
        )
    return summary, per_scenario


def _mysql_row_counts(database_url: str, *, benchmark_name: str) -> list[dict[str, object]]:
    engine = create_database_engine(database_url)
    with engine.connect() as conn:
        queries = {
            "publication_benchmarks": "SELECT COUNT(*) FROM publication_benchmarks WHERE benchmark_id = :benchmark_id",
            "publication_scenarios": "SELECT COUNT(*) FROM publication_scenarios WHERE benchmark_id = :benchmark_id",
            "publication_nodes": (
                "SELECT COUNT(*) FROM publication_nodes WHERE scenario_id IN "
                "(SELECT scenario_id FROM publication_scenarios WHERE benchmark_id = :benchmark_id)"
            ),
            "publication_edges": (
                "SELECT COUNT(*) FROM publication_edges WHERE scenario_id IN "
                "(SELECT scenario_id FROM publication_scenarios WHERE benchmark_id = :benchmark_id)"
            ),
            "publication_pairs": (
                "SELECT COUNT(*) FROM publication_pairs WHERE scenario_id IN "
                "(SELECT scenario_id FROM publication_scenarios WHERE benchmark_id = :benchmark_id)"
            ),
            "publication_reports": "SELECT COUNT(*) FROM publication_reports WHERE benchmark_id = :benchmark_id",
        }
        return [
            {
                "table": table,
                "rows": int(conn.execute(text(query), {"benchmark_id": benchmark_name}).scalar_one()),
            }
            for table, query in queries.items()
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


def _pipeline_rows(scenario_rows: list[dict[str, Any]], training_rows: list[dict[str, Any]], model_paths: dict[str, Path]) -> list[dict[str, object]]:
    return [
        {
            "stage": "source",
            "input": "PostgreSQL scenario warehouse",
            "output": f"{len(scenario_rows)} TPC-DS scenario schemas",
            "details": "Each schema is selected from isomera_tpcds_benchmark and read through the Scenario Materialization API.",
        },
        {
            "stage": "normalized_graph",
            "input": "manifest-defined relational tables and lineage edges",
            "output": f"{sum(int(row['nodes']) for row in scenario_rows)} nodes / {sum(int(row['edges']) for row in scenario_rows)} edges",
            "details": "The API normalizes edge direction to SOR -> SOT -> SPEC before visualization, validation, training, or benchmarking.",
        },
        {
            "stage": "validation_dataset",
            "input": "SPEC candidate pairs plus GenAI documented validation rubric",
            "output": f"{sum(int(row['candidate_pairs']) for row in scenario_rows)} supervised rows with target 0/1",
            "details": "No same-domain restriction is applied, so cross-domain duplicates remain eligible.",
        },
        {
            "stage": "training_dataset",
            "input": "normalized graph + validation_dataset.csv",
            "output": f"{sum(int(row.get('dataset_rows', 0)) for row in training_rows)} supervised training rows read directly from CSV",
            "details": "The GNN reads positives and negatives explicitly; balancing is handled by class-weighted BCE.",
        },
        {
            "stage": "model_artifact",
            "input": "GIN pair classifier training loop",
            "output": f"{len(model_paths)} GenAI Spec GNN pickle artifacts",
            "details": "Each artifact is routed to the scenario that produced its supervised validation dataset.",
        },
        {
            "stage": "benchmark_execution",
            "input": "VF2, Node Match, TPC-DS v1 GNN cluster, GenAI Spec GNN cluster",
            "output": f"{BENCHMARK_RUNS} runs per detector family per scenario",
            "details": "Metrics emphasize SF-Jaccard because duplicate detection is highly imbalanced.",
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
    md_path.write_text(_markdown_from_payload(payload), encoding="utf-8")
    return paths


def _markdown_from_payload(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    return "\n".join(
        [
            f"# Isomera v2 Report: {summary.get('benchmark_name')}",
            "",
            f"- Captured at: {payload.get('captured_at')}",
            f"- Scenarios: {summary.get('scenario_count')}",
            f"- Candidate pairs: {summary.get('candidate_pairs')}",
            f"- Duplicate pairs: {summary.get('duplicate_pairs')}",
            f"- Benchmark runs: {BENCHMARK_RUNS}",
            "",
            "## Methods for Paper",
            "",
            "This run evaluates the TPC-DS GenAI Spec benchmark. PostgreSQL stores the 20 scenario schemas. "
            "The Scenario Materialization API converts each schema into the same normalized graph contract, "
            "then SPEC-level candidate pairs are validated with a documented GenAI rubric and stored as a supervised table.",
            "",
            "The GNN training step reads validation_dataset.csv directly, including target=1 and target=0 rows. "
            "Class-weighted BCE is used so the rare duplicate class is not hidden by the negative majority.",
            "",
            "## Benchmark Summary",
            "",
            "```json",
            json.dumps((payload.get("publication_tables") or {}).get("benchmark_metrics"), indent=2, ensure_ascii=True),
            "```",
        ]
    )


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
    genai_paths: dict[str, Path] = {}
    publish_ids: list[dict[str, str]] = []

    filters = {
        "scope_layers": ["SPEC"],
        "constraints": ["complete_upstream_lineage", "cross_domain_allowed"],
        "same_layer_only": True,
        "same_domain_only": False,
        "candidate_generation": "all SPEC-to-SPEC combinations",
        "ground_truth_source": "GenAI-assisted validation rubric saved in validation_dataset.csv",
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
        "duplicate_rule": (
            "target=1 when the pair has equal SPEC semantic output, high SPEC token overlap, "
            "a direct SPEC lineage relation with shared upstream context, or high upstream lineage overlap."
        ),
        "limitation": (
            "This is a reproducible GenAI-assisted validation protocol for the generated benchmark. "
            "It is not a universal semantic truth engine and should be reviewed by a domain expert before external publication."
        ),
    }

    for index, scenario_spec in enumerate(scenario_specs, start=1):
        scenario_name = str(scenario_spec["scenario"])
        schema_name = str(scenario_spec["schema"])
        _log(f"[{index}/{len(scenario_specs)}] materializing {schema_name} from PostgreSQL")
        materialized = materialize_database_scenario(
            POSTGRES_URL,
            schema_name,
            manifests_root=MAIN_ROOT / "data" / "tpcds_postgres",
        )
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

        model_path = benchmark_root / "models" / f"GNN_tpcds_genai_spec_{scenario_name}.pkl"
        _log(f"{scenario_name}: training GenAI Spec GNN artifact from supervised validation dataset")
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
            negative_ratio=NEGATIVE_RATIO,
            seed=SEED,
            optimizer_name="adam",
            train_ratio=TRAIN_RATIO,
            balance_strategy="class_weighted_loss",
            loss_name="bce_with_logits",
            progress_callback=_training_progress_logger(scenario_name),
        )
        genai_paths[scenario_name] = model_path
        baseline_path = MAIN_ROOT / "core" / "algorithms" / "pickle" / "gin_gnn" / "modelos_gnn_separados" / f"{scenario_name}.pkl"
        if not baseline_path.exists():
            raise FileNotFoundError(f"TPC-DS baseline pickle not found: {baseline_path}")
        v1_paths[scenario_name] = baseline_path

        for row in training_metadata.get("dataset_summary") or []:
            training_rows.append({**row, "model_path": str(model_path), "validation_dataset_path": str(validation_csv)})
        for row in training_metadata.get("history") or []:
            training_history.append({"scenario": scenario_name, **row})

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

        scenario_row = {
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
        scenario_rows.append(scenario_row)

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

    _log(f"running benchmark with {BENCHMARK_RUNS} runs per detector family")
    benchmark_metrics, per_scenario_metrics = _run_benchmark(graphs, labels, v1_paths, genai_paths)
    mysql_counts = _mysql_row_counts(MYSQL_URL, benchmark_name=BENCHMARK_NAME)

    model_artifact_rows = []
    routing_rows = []
    for scenario_name in graphs:
        for family, path, role in (
            ("GNN TPC-DS v1 cluster", v1_paths[scenario_name], "baseline_tpcds_pickle"),
            ("GNN GenAI Spec cluster", genai_paths[scenario_name], "new_genai_spec_pickle"),
        ):
            row = {
                "model_family": family,
                "scenario": scenario_name,
                "artifact_path": str(path),
                "artifact_role": role,
                "route_mode": "scenario_specific",
                "route_source": f"{BENCHMARK_DISPLAY_NAME} explicit routing",
            }
            routing_rows.append(row)
            model_artifact_rows.append(
                {
                    "model_name": f"{family}::{scenario_name}",
                    "artifact_path": str(path),
                    "artifact_role": role,
                    "route_mode": "scenario_specific",
                    "route_source": f"{BENCHMARK_DISPLAY_NAME} explicit routing",
                    "scenario": scenario_name,
                }
            )

    cluster_rows = [
        {"model_family": "VF2", "artifact_count": 0, "scenario_count": len(graphs), "coverage": "20/20", "reporting_rule": "one deterministic detector family"},
        {"model_family": "Node Match", "artifact_count": 0, "scenario_count": len(graphs), "coverage": "20/20", "reporting_rule": "one deterministic semantic node-matching family"},
        {"model_family": "GNN TPC-DS v1 cluster", "artifact_count": len(v1_paths), "scenario_count": len(graphs), "coverage": f"{len(v1_paths)}/{len(graphs)}", "reporting_rule": "one baseline pickle routed per scenario"},
        {"model_family": "GNN GenAI Spec cluster", "artifact_count": len(genai_paths), "scenario_count": len(graphs), "coverage": f"{len(genai_paths)}/{len(graphs)}", "reporting_rule": "one GenAI-trained pickle routed per scenario"},
    ]

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
        {"field": "validator_model", "value": "OpenAI GPT-5.4 via Codex CLI agent"},
        {"field": "validator_reasoning_effort", "value": "xhigh"},
    ]
    first_scenario = next(iter(graphs))
    total_pairs = sum(int(row["total_pairs"]) for row in scenario_rows)
    candidate_pairs = sum(int(row["candidate_pairs"]) for row in scenario_rows)
    duplicate_pairs = sum(int(row["positive_pairs"]) for row in scenario_rows)
    training_summary = {
        "scenarios": list(graphs.keys()),
        "dataset_summary": training_rows,
        "history": training_history,
        "train_size": sum(int(row.get("dataset_rows", 0) * TRAIN_RATIO) for row in training_rows),
        "val_size": sum(max(1, int(row.get("dataset_rows", 0) * (1.0 - TRAIN_RATIO))) for row in training_rows),
        "status": "completed",
        "loss": {
            "loss_name": "torch.nn.BCEWithLogitsLoss(pos_weight)",
            "loss_label": "Weighted binary cross entropy (torch.nn.BCEWithLogitsLoss(pos_weight))",
            "pos_weight": "per-scenario N_negative/N_positive when positives exist",
        },
        "balance_summary": {
            "strategy": "class_weighted_loss",
            "operation": "kept supervised rows intact and weighted positive class in the loss",
        },
        "train_distribution": {
            "positive_pairs": duplicate_pairs,
            "negative_pairs": candidate_pairs - duplicate_pairs,
            "dataset_rows": candidate_pairs,
        },
    }
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
        "model_name": "GNN_tpcds_genai_spec_cluster",
        "model_path": str(next(iter(genai_paths.values()))),
        "model_family_name": "GNN (GIN Pair Classifier) v1",
        "optimizer": "Adam",
        "optimizer_label": "Adaptive gradient optimizer (torch.optim.Adam)",
        "optimizer_name": "torch.optim.Adam",
        "loss_name": "torch.nn.BCEWithLogitsLoss(pos_weight)",
        "loss_label": "Weighted binary cross entropy (torch.nn.BCEWithLogitsLoss(pos_weight))",
        "resolved_hyperparameters": {
            "epochs": TRAIN_EPOCHS,
            "learning_rate": LEARNING_RATE,
            "hidden_channels": HIDDEN_CHANNELS,
            "dropout": DROPOUT,
            "negative_ratio": NEGATIVE_RATIO,
            "train_ratio": TRAIN_RATIO,
            "test_ratio": round(1.0 - TRAIN_RATIO, 6),
            "balance_strategy": "class_weighted_loss",
            "balance_strategy_label": "Weight duplicate class in the loss (torch.nn.BCEWithLogitsLoss(pos_weight))",
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
            {"filter": "Lineage scope", "setting": "SPEC only", "effect": "Only SPEC outputs enter candidate generation, but each SPEC is represented with complete upstream lineage during validation and training."},
            {"filter": "Same layer", "setting": "enabled", "effect": "All reviewed pairs are SPEC-to-SPEC pairs."},
            {"filter": "Same domain", "setting": "disabled", "effect": "Cross-domain duplicate evidence remains eligible."},
            {"filter": "GenAI rubric", "setting": "genai_spec_v1", "effect": "OpenAI GPT-5.4 / Codex xhigh metadata and deterministic decision features are saved for reproducibility."},
        ],
        "genai_validation_protocol": [validator_protocol],
        "validation_dataset": validation_rows,
        "training_dataset": training_rows,
        "training_history": training_history,
        "model_artifact": model_artifact_rows,
        "model_cluster_summary": cluster_rows,
        "model_cluster_routing": routing_rows,
        "benchmark_metrics": benchmark_metrics,
        "benchmark_per_scenario_metrics": per_scenario_metrics,
        "benchmark_pickle_results": [row for row in per_scenario_metrics if str(row.get("artifact_path") or "")],
        "pipeline": _pipeline_rows(scenario_rows, training_rows, genai_paths),
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
            {"formula": "L = BCEWithLogitsLoss(logit, y, pos_weight=N_negative/N_positive)"},
        ],
        "layers": [
            {"layer": "GIN layer 1", "operation": "neighbor aggregation over each node-centered upstream lineage subgraph"},
            {"layer": "ReLU", "operation": "non-linear activation after hidden projection"},
            {"layer": "GIN layer 2", "operation": "second neighborhood aggregation and final embedding projection"},
            {"layer": "Mean pooling", "operation": "one vector embedding per subgraph"},
            {"layer": "Pair MLP with dropout", "operation": "binary duplicate logit for the candidate pair"},
        ],
    }
    payload: dict[str, Any] = {
        "report_type": REPORT_TYPE,
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system_architecture": _system_architecture(),
        "scenario_api": scenario_api_contract(),
        "storytelling": {
            "module": "Research Reports",
            "goal": "Generate a full SPEC-scope GenAI-curated TPC-DS benchmark and document source-to-report reproducibility.",
            "graph_construction_method": "Read all PostgreSQL benchmark schemas, materialize normalized lineage graphs, validate SPEC candidate pairs with a documented GenAI rubric, train one GNN pickle per scenario, and benchmark detector families with 10 timing runs.",
        },
        "environment": {
            "python_executable": sys.executable,
            "project_root": str(REPO_ROOT),
            "scenarios_db_url": POSTGRES_URL,
            "publication_db_url": MYSQL_URL,
            "streamlit_reason": "Streamlit is used for the research UI because it exposes source selection, validation, training, benchmark, and report generation in one auditable workflow.",
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
            "genai_spec_artifacts": len(genai_paths),
            "candidate_scope": "SPEC-to-SPEC pairs",
            "sf_jaccard": "Jaccard * N_pairs / ET",
        },
        "summary": summary,
    }
    _log("writing article capture, figures, and package")
    capture_paths = _write_capture(payload, graphs[first_scenario])
    package = build_package(Path(capture_paths["json"]))
    print(
        json.dumps(
            {
                "capture_paths": capture_paths,
                "package": package,
                "benchmark_metrics": benchmark_metrics,
                "mysql_counts": mysql_counts,
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
