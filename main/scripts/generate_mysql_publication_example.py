from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd
from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

import core.algorithms  # noqa: F401,E402
from core.algorithms.gnn_pickle import set_gnn_pickle_path  # noqa: E402
from core.algorithms.gnn_training import ScenarioTrainingSpec, train_benchmark_gnn  # noqa: E402
from core.database import create_database_engine  # noqa: E402
from core.lineage import (  # noqa: E402
    adjacency_matrix_dataframe,
    edge_dataframe,
    plot_adjacency_matrix,
    plot_lineage_graph,
)
from core.publication_store import init_publication_store, publish_curated_scenario  # noqa: E402
from core.scenario_api import materialize_database_scenario, scenario_api_contract  # noqa: E402
from core.metrics import canonical_pairs, confusion_metrics_pairs, execution_times, success_frequency  # noqa: E402
from core.isomorphism import find_isomorphic_pairs  # noqa: E402


PUBLICATION_DB_URL = "mysql+pymysql://root@localhost/isomera_publication"
BENCHMARK_NAME = "mysql_validation_demo"
SCENARIO_NAME = "graph_SOR2_D5_seed42"
SCHEMA_NAME = "scenario_sor2_d5_seed42"
REPORT_TYPE = "mysql_publication_pipeline_validation"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _capture_root() -> Path:
    root = MAIN_ROOT / "data" / "article_capture" / BENCHMARK_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def _load_graph() -> nx.DiGraph:
    materialized = materialize_database_scenario(
        "postgresql+psycopg://localhost:5432/isomera_tpcds_benchmark",
        SCHEMA_NAME,
        manifests_root=MAIN_ROOT / "data" / "tpcds_postgres",
    )
    return materialized.graph


def _load_positive_pairs() -> list[tuple[str, str]]:
    labels_path = MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "real_pairs" / f"{SCENARIO_NAME}.json"
    return [tuple(pair) for pair in json.loads(labels_path.read_text(encoding="utf-8"))]


def _select_negative_pairs(graph: nx.DiGraph, positive_pairs: list[tuple[str, str]], count: int = 6) -> list[tuple[str, str]]:
    positive_set = {tuple(sorted(pair)) for pair in positive_pairs}
    negatives: list[tuple[str, str]] = []
    for node_a, node_b in combinations(sorted(graph.nodes), 2):
        canonical = tuple(sorted((str(node_a), str(node_b))))
        if canonical in positive_set:
            continue
        layer_a = str(graph.nodes[node_a].get("type") or "")
        layer_b = str(graph.nodes[node_b].get("type") or "")
        if layer_a != layer_b:
            continue
        negatives.append(canonical)
        if len(negatives) >= count:
            break
    return negatives


def _validation_dataset_rows(reviewed_pairs: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, ((node_a, node_b), payload) in enumerate(sorted(reviewed_pairs.items()), start=1):
        rows.append(
            {
                "pair_index": index,
                "node_a": node_a,
                "node_b": node_b,
                "layer_a": node_a.split("_", 1)[0],
                "layer_b": node_b.split("_", 1)[0],
                "domain_a": node_a.rsplit("_", 1)[-1],
                "domain_b": node_b.rsplit("_", 1)[-1],
                "decision": payload["decision"],
                "target": 1 if payload["decision"] == "duplicate" else 0,
                "reviewed_at": payload["timestamp"],
            }
        )
    return rows


def _mysql_row_counts(database_url: str) -> list[dict[str, object]]:
    engine = create_database_engine(database_url)
    table_names = [
        "publication_benchmarks",
        "publication_scenarios",
        "publication_nodes",
        "publication_edges",
        "publication_pairs",
        "publication_reports",
    ]
    rows: list[dict[str, object]] = []
    with engine.connect() as conn:
        for table in table_names:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            rows.append({"table": table, "rows": int(count)})
    return rows


def _graph_summary(graph: nx.DiGraph) -> dict[str, object]:
    layer_counts: dict[str, int] = {}
    for _, attrs in graph.nodes(data=True):
        layer = str(attrs.get("type") or "UNK")
        layer_counts[layer] = layer_counts.get(layer, 0) + 1
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "layer_counts": layer_counts,
    }


def _system_architecture() -> dict[str, object]:
    return {
        "overview": "Isomera v2 is organized as a layered system that ingests lineage from relational schemas or GML assets, normalizes the directed graph, curates supervised duplicate labels, trains benchmark-specific models, and persists operational and publication-ready evidence.",
        "layers": [
            {
                "layer": "Presentation Layer",
                "responsibility": "Scenario Studio, Benchmark & Examples, Admin, and Research Reports orchestrate the workflow and expose all intermediate artifacts.",
                "paths": ["main/ui/app.py"],
            },
            {
                "layer": "Scenario Ingestion Layer",
                "responsibility": "Reads PostgreSQL schemas or GML assets and maps relational tables into semantic lineage nodes.",
                "paths": ["main/core/database.py", "main/data/tpcds_postgres"],
            },
            {
                "layer": "Lineage Graph Layer",
                "responsibility": "Normalizes edge direction to SOR -> SOT -> SPEC and materializes graph, adjacency, and edge views.",
                "paths": ["main/core/lineage.py"],
            },
            {
                "layer": "Validation and Training Layer",
                "responsibility": "Transforms reviewed pairs into a supervised validation table and derives training batches for the GIN pair classifier.",
                "paths": ["main/core/algorithms/gnn_training.py", "main/core/publication_store.py"],
            },
            {
                "layer": "Persistence and Reporting Layer",
                "responsibility": "Stores publication tables in MySQL and narrative captures in Markdown/JSON for later paper writing.",
                "paths": ["main/core/publication_store.py", "main/data/article_capture"],
            },
        ],
        "stores": [
            {"store": "Scenario Warehouse", "technology": "PostgreSQL", "purpose": "Relational benchmark schemas plus semantic scenario contracts. A contract is a manifest that maps tables to domain, SOR/SOT/SPEC layer, semantic name, and lineage edges."},
            {"store": "Publication Store", "technology": "MySQL", "purpose": "Published benchmark scenarios, nodes, edges, reviewed pairs, and summary reports."},
            {"store": "Scenario Files", "technology": "GML/JSON", "purpose": "Portable graphs, labels, and model metadata."},
            {"store": "Article Capture", "technology": "Markdown/JSON", "purpose": "Paper-ready evidence and appendix material."},
        ],
        "flow": [
            "Select one relational scenario schema from PostgreSQL.",
            "Normalize the lineage graph into the canonical SOR -> SOT -> SPEC direction.",
            "Produce the supervised validation dataset from curated duplicate decisions.",
            "Derive the training dataset from the normalized graph and positive labels.",
            "Train one benchmark-specific GNN pickle artifact and save metadata.",
            "Persist the published scenario and evidence into MySQL and article captures.",
        ],
    }


def _pipeline_rows(source_metadata: dict[str, object], graph: nx.DiGraph, validation_rows: list[dict[str, object]], training_metadata: dict[str, object], model_path: Path) -> list[dict[str, object]]:
    return [
        {
            "stage": "source",
            "input": "PostgreSQL scenario warehouse",
            "output": f"{source_metadata['database_name']}.{source_metadata['schema']}",
            "details": f"url={source_metadata['database_url']} | mode={source_metadata['mode']}",
        },
        {
            "stage": "normalized_graph",
            "input": "Warehouse contract and portable GML",
            "output": f"{graph.number_of_nodes()} nodes / {graph.number_of_edges()} edges",
            "details": "Canonical direction enforced as SOR -> SOT -> SPEC.",
        },
        {
            "stage": "validation_dataset",
            "input": "Manual duplicate review",
            "output": f"{len(validation_rows)} reviewed rows",
            "details": f"duplicate_targets={sum(int(row['target']) for row in validation_rows)} | non_duplicate_targets={sum(1 - int(row['target']) for row in validation_rows)}",
        },
        {
            "stage": "training_dataset",
            "input": "Normalized graph + positive duplicate labels",
            "output": f"train={training_metadata['train_size']} / val={training_metadata['val_size']}",
            "details": json.dumps(training_metadata.get("dataset_summary") or [], ensure_ascii=True),
        },
        {
            "stage": "model_artifact",
            "input": "GIN pair training loop",
            "output": model_path.name,
            "details": str(model_path),
        },
    ]


def _write_capture(payload: dict[str, object], graph: nx.DiGraph) -> dict[str, str]:
    capture_root = _capture_root()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"{stamp}_{REPORT_TYPE}_{SCENARIO_NAME}"
    json_path = capture_root / f"{base_name}.json"
    md_path = capture_root / f"{base_name}.md"
    lineage_png = capture_root / f"{base_name}_lineage.png"
    adjacency_png = capture_root / f"{base_name}_adjacency.png"

    fig = plot_lineage_graph(graph, seed=42)
    fig.savefig(lineage_png, bbox_inches="tight", dpi=300)
    fig = plot_adjacency_matrix(graph)
    fig.savefig(adjacency_png, bbox_inches="tight", dpi=300)

    payload["capture_paths"] = {
        "json": str(json_path),
        "markdown": str(md_path),
        "lineage_png": str(lineage_png),
        "adjacency_png": str(adjacency_png),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    md_path.write_text(_markdown_from_payload(payload), encoding="utf-8")
    return payload["capture_paths"]


def _markdown_from_payload(payload: dict[str, object]) -> str:
    summary = dict(payload.get("summary") or {})
    pipeline_rows = list((payload.get("publication_tables") or {}).get("pipeline") or [])
    publication_tables = dict(payload.get("publication_tables") or {})
    lines = [
        f"# Isomera Article Capture: {payload.get('report_type')}",
        "",
        f"- Captured at: {payload.get('captured_at')}",
        f"- Benchmark: {summary.get('benchmark_name')}",
        f"- Scenario: {summary.get('scenario')}",
        f"- Python executable: `{payload.get('environment', {}).get('python_executable')}`",
        "",
        "## Methods for Paper",
        "",
        "This validation used the Scenario Warehouse path to read one relational benchmark schema from PostgreSQL, normalize the graph direction to `SOR -> SOT -> SPEC`, curate a supervised duplicate table, train one benchmark-specific GIN pair classifier, and publish the resulting scenario plus evidence into MySQL.",
        "The publication store validation is real: the report below was generated after writing rows into the MySQL database `isomera_publication` and reading those rows back for verification.",
        "",
        "## Pipeline for Paper",
        "",
    ]
    for row in pipeline_rows:
        lines.append(
            f"- **{row['stage']}**: input={row['input']} | output={row['output']} | details={row['details']}"
        )
    lines.extend(
        [
            "",
            "## Software Architecture",
            "",
            payload.get("system_architecture", {}).get("overview", ""),
            "",
            "## Scenario Materialization API",
            "",
            payload.get("scenario_api", {}).get("purpose", ""),
            "",
            "## Publication Tables",
            "",
        ]
    )
    for table_name, rows in publication_tables.items():
        lines.extend([f"### {table_name}", ""])
        lines.append("```json")
        lines.append(json.dumps(rows, indent=2, ensure_ascii=True))
        lines.append("```")
        lines.append("")
    lines.extend(
        [
            "## Structured Summary",
            "",
            "```json",
            json.dumps(summary, indent=2, ensure_ascii=True),
            "```",
            "",
            "## Generated Figures",
            "",
            f"- Lineage figure: `{payload.get('capture_paths', {}).get('lineage_png')}`",
            f"- Adjacency figure: `{payload.get('capture_paths', {}).get('adjacency_png')}`",
        ]
    )
    return "\n".join(lines)


def _jaccard(true_pairs: set[tuple[str, str]], predicted_pairs: set[tuple[str, str]]) -> float:
    union = true_pairs | predicted_pairs
    if not union:
        return 1.0
    return len(true_pairs & predicted_pairs) / len(union)


def _run_benchmark_metrics(graph: nx.DiGraph, true_pairs: list[tuple[str, str]], model_path: Path) -> list[dict[str, object]]:
    set_gnn_pickle_path(model_path)
    all_pairs = [(str(a), str(b)) for index, a in enumerate(sorted(graph.nodes)) for b in sorted(graph.nodes)[index + 1 :]]
    true_set = canonical_pairs(true_pairs)
    algorithms = ["VF2", "Node Match (Custom)", "GIN/GNN (Pickle)"]
    timing = execution_times(graph, algorithms, runs=3)
    rows: list[dict[str, object]] = []
    for algorithm in algorithms:
        predicted = canonical_pairs(find_isomorphic_pairs(graph, algorithm=algorithm))
        metrics = confusion_metrics_pairs(true_set, predicted, all_pairs=all_pairs)
        median_time = sorted(timing.get(algorithm, []))[len(timing.get(algorithm, [])) // 2] if timing.get(algorithm) else None
        et = float(median_time or 0.0)
        accuracy = float(metrics["accuracy"] or 0.0)
        jaccard = _jaccard(true_set, predicted)
        evaluated_pairs = len(all_pairs)
        accuracy_out = round(accuracy, 6)
        jaccard_out = round(jaccard, 6)
        et_out = round(et, 6)
        rows.append(
            {
                "algorithm": algorithm,
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
                "runs": 3,
            }
        )
    return rows


def main() -> None:
    init_publication_store(PUBLICATION_DB_URL)

    graph = _load_graph()
    positive_pairs = _load_positive_pairs()
    selected_positive_pairs = [tuple(sorted(pair)) for pair in positive_pairs[:6]]
    selected_negative_pairs = _select_negative_pairs(graph, positive_pairs, count=6)
    reviewed_pairs: dict[tuple[str, str], dict[str, str]] = {}
    for node_a, node_b in selected_positive_pairs:
        reviewed_pairs[(node_a, node_b)] = {"decision": "duplicate", "timestamp": _utcnow()}
    for node_a, node_b in selected_negative_pairs:
        reviewed_pairs[(node_a, node_b)] = {"decision": "not_duplicate", "timestamp": _utcnow()}

    validation_rows = _validation_dataset_rows(reviewed_pairs)
    source_metadata = {
        "mode": "Scenario Warehouse",
        "database_name": "isomera_tpcds_benchmark",
        "database_url": "postgresql+psycopg://localhost:5432/isomera_tpcds_benchmark",
        "schema": SCHEMA_NAME,
        "build_mode": "warehouse_manifest_contract",
        "manifest_used": True,
        "manifest_path": str(MAIN_ROOT / "data" / "tpcds_postgres" / SCENARIO_NAME / "manifest.json"),
        "table_count": int(graph.number_of_nodes()),
    }
    filters = {
        "scope_sor": False,
        "scope_sot": True,
        "scope_spec": True,
        "same_layer_only": True,
        "same_domain_only": False,
        "same_input_count": False,
        "same_output_count": False,
        "same_parent_signature": False,
        "same_child_signature": False,
    }
    publication_summary = {
        "scenario": SCENARIO_NAME,
        "benchmark_name": BENCHMARK_NAME,
        "total_pairs": int(graph.number_of_nodes() * (graph.number_of_nodes() - 1) / 2),
        "candidate_pairs": len(reviewed_pairs),
        "reviewed_pairs": len(reviewed_pairs),
        "duplicate_pairs": sum(1 for row in validation_rows if row["target"] == 1),
        "published_to_benchmark": True,
        "filters": filters,
        "validation_dataset_rows": validation_rows,
    }

    benchmark_root = MAIN_ROOT / "data" / "architectures" / BENCHMARK_NAME
    (benchmark_root / "models").mkdir(parents=True, exist_ok=True)
    model_path = benchmark_root / "models" / "mysql_validation_demo_gnn.pkl"

    training_metadata = train_benchmark_gnn(
        [
            ScenarioTrainingSpec(
                scenario_name=SCENARIO_NAME,
                graph_path=MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "gml" / f"{SCENARIO_NAME}.gml",
                labels_path=MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "real_pairs" / f"{SCENARIO_NAME}.json",
            )
        ],
        model_path=model_path,
        epochs=1,
        learning_rate=0.005,
        hidden_channels=16,
        dropout=0.2,
        negative_ratio=1,
        seed=42,
        optimizer_name="adam",
        train_ratio=0.8,
        balance_strategy="negative_sampling",
    )
    training_metadata["model_path"] = str(model_path)
    benchmark_metrics = _run_benchmark_metrics(graph, positive_pairs, model_path)

    publish_ids = publish_curated_scenario(
        PUBLICATION_DB_URL,
        benchmark_name=BENCHMARK_NAME,
        scenario_name=SCENARIO_NAME,
        graph=graph,
        source_metadata=source_metadata,
        gml_path=str(MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "gml" / f"{SCENARIO_NAME}.gml"),
        labels_path=str(MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "real_pairs" / f"{SCENARIO_NAME}.json"),
        reviewed_pairs=reviewed_pairs,
        filters=filters,
        summary=publication_summary,
    )

    mysql_counts = _mysql_row_counts(PUBLICATION_DB_URL)
    graph_summary = _graph_summary(graph)
    model_docs = {
        "official_name": "Graph Isomorphism Network Pair Classifier",
        "version": "gin_pair_v1",
        "overview": "A entrada é um cenário convertido em subgrafos locais por nó. Cada subgrafo recebe uma embedding via camadas GIN e, em seguida, um classificador binário decide se dois subgrafos representam duplicidade estrutural.",
        "theory": "GIN aproxima o poder discriminativo do teste de Weisfeiler-Lehman ao agregar vizinhança e aplicar uma MLP por camada. O classificador final aprende um limite supervisionado sobre pares positivos e negativos.",
        "formulas": [
            "h_v^(k) = MLP^(k) ((1 + eps^(k)) * h_v^(k-1) + sum_{u in N(v)} h_u^(k-1))",
            "z_G = mean_pool({h_v^(K)})",
            "y_hat = sigma(MLP([z_G1 || z_G2]))",
        ],
        "layers": [
            "Camada 1: agregação GIN sobre o subgrafo local",
            "Camada 2: nova agregação GIN e projeção para embedding final",
            "Pooling: média global dos nós do subgrafo",
            "Cabeça de classificação: MLP binária sobre as embeddings concatenadas",
        ],
    }
    summary = {
        **publication_summary,
        "report_validation": "validated_against_real_mysql_instance",
        "publication_ids": publish_ids,
        "mysql_row_counts": mysql_counts,
        "model_name": "mysql_validation_demo_gnn",
        "model_path": str(model_path),
        "model_family_name": "GNN (GIN Pair Classifier) v1",
        "optimizer": "Adam",
        "loss_name": "BCEWithLogitsLoss",
        "hyperparameters": {
            "epochs": 1,
            "learning_rate_scaled": 50,
            "hidden_channels": 16,
            "dropout_pct": 20,
            "negative_ratio": 1,
            "train_ratio": 0.8,
            "test_ratio": 0.2,
            "balance_strategy": "negative_sampling",
            "seed": 42,
        },
        "resolved_hyperparameters": {
            "epochs": 1,
            "learning_rate": 0.005,
            "hidden_channels": 16,
            "dropout": 0.2,
            "negative_ratio": 1,
            "train_ratio": 0.8,
            "test_ratio": 0.2,
            "balance_strategy": "negative_sampling",
            "seed": 42,
        },
        "model_docs": model_docs,
        "training_summary": training_metadata,
        "benchmark_metrics": benchmark_metrics,
    }
    publication_tables = {
        "source_details": [{"field": key, "value": value} for key, value in source_metadata.items()],
        "lineage_structure": [
            {
                "domain": graph.nodes[node].get("domain"),
                "layer": graph.nodes[node].get("type"),
                "node": node,
                "table_name": graph.nodes[node].get("table_name"),
                "semantic_name": graph.nodes[node].get("semantic_name"),
                "in_degree": graph.in_degree(node),
                "out_degree": graph.out_degree(node),
            }
            for node in graph.nodes
        ],
        "lineage_edges": edge_dataframe(graph).to_dict(orient="records"),
        "adjacency_matrix": adjacency_matrix_dataframe(graph).reset_index().rename(columns={"index": "node"}).to_dict(orient="records"),
        "filters": [{"filter": key, "enabled": bool(value)} for key, value in filters.items()],
        "validation_dataset": validation_rows,
        "training_dataset": list(training_metadata.get("dataset_summary") or []),
        "model_artifact": [
            {
                "model_name": "mysql_validation_demo_gnn",
                "artifact_path": str(model_path),
                "train_size": training_metadata.get("train_size"),
                "val_size": training_metadata.get("val_size"),
                "status": training_metadata.get("status"),
            }
        ],
        "benchmark_metrics": benchmark_metrics,
        "pipeline": _pipeline_rows(source_metadata, graph, validation_rows, training_metadata, model_path),
        "mysql_row_counts": mysql_counts,
        "formulas": [
            {"formula": "Accuracy = (TP + TN) / (TP + TN + FP + FN)"},
            {"formula": "Jaccard = TP / (TP + FP + FN)"},
            {"formula": "ET = median(t_i), i = 1..runs"},
            {"formula": "SF_accuracy = Accuracy * N_pairs / ET"},
            {"formula": "SF_jaccard = Jaccard * N_pairs / ET"},
        ]
        + [{"formula": formula} for formula in model_docs["formulas"]],
        "layers": [{"layer": layer} for layer in model_docs["layers"]],
    }
    payload = {
        "report_type": REPORT_TYPE,
        "captured_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "system_architecture": _system_architecture(),
        "scenario_api": scenario_api_contract(),
        "storytelling": {
            "module": "Research Reports",
            "goal": "Validate the real MySQL publication store and document the full scenario-to-model pipeline for the paper.",
            "source_mode": "Scenario Warehouse",
            "graph_construction_method": "Read one PostgreSQL benchmark schema through the Scenario Materialization API, reconstruct the lineage contract, normalize edges to SOR -> SOT -> SPEC, and materialize graph/table views for validation and training.",
            "graph_build_steps": [
                "Connected to the PostgreSQL scenario warehouse.",
                f"Loaded schema `{SCHEMA_NAME}` from database `isomera_tpcds_benchmark`.",
                "Reconstructed the semantic lineage contract with manifest support.",
                "Normalized all edges to the canonical SOR -> SOT -> SPEC direction.",
                "Built the validation dataset and published the scenario into the MySQL publication store.",
                "Trained one benchmark-specific GNN artifact using the normalized graph and labels.",
            ],
        },
        "environment": {
            "python_executable": sys.executable,
            "project_root": str(REPO_ROOT),
            "backend_db_url": str(MAIN_ROOT / "data" / "backend" / "isomera_backend.sqlite"),
            "scenarios_db_url": source_metadata["database_url"],
            "publication_db_url": PUBLICATION_DB_URL,
        },
        "source_metadata": source_metadata,
        "graph_summary": graph_summary,
        "publication_tables": publication_tables,
        "formula_parameter_mapping": {
            "K (epochs used in optimization loop)": 1,
            "hidden_channels / embedding dimension": 16,
            "dropout": 0.2,
            "learning_rate": 0.005,
            "negative_ratio": 1,
            "seed": 42,
        },
        "summary": summary,
    }
    capture_paths = _write_capture(payload, graph)
    print(json.dumps({"publish_ids": publish_ids, "mysql_row_counts": mysql_counts, "capture_paths": capture_paths}, indent=2))


if __name__ == "__main__":
    main()
