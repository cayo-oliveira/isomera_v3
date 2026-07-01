"""Publication store helpers for benchmark scenarios."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import networkx as nx
from sqlalchemy import text

from core.database import create_database_engine


def _utcnow_text() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_publication_store(database_url: str) -> None:
    engine = create_database_engine(database_url)
    statements = [
        """
        CREATE TABLE IF NOT EXISTS publication_benchmarks (
            benchmark_id VARCHAR(255) PRIMARY KEY,
            benchmark_name VARCHAR(255) NOT NULL UNIQUE,
            metadata_json LONGTEXT,
            created_at VARCHAR(64) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS publication_scenarios (
            scenario_id VARCHAR(255) PRIMARY KEY,
            benchmark_id VARCHAR(255) NOT NULL,
            scenario_name VARCHAR(255) NOT NULL,
            source_mode VARCHAR(255),
            source_database VARCHAR(255),
            source_schema VARCHAR(255),
            gml_path TEXT,
            labels_path TEXT,
            node_count INTEGER NOT NULL,
            edge_count INTEGER NOT NULL,
            metadata_json LONGTEXT,
            created_at VARCHAR(64) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS publication_nodes (
            scenario_id VARCHAR(255) NOT NULL,
            node_name VARCHAR(255) NOT NULL,
            layer VARCHAR(64),
            domain VARCHAR(64),
            table_name TEXT,
            semantic_name TEXT,
            in_degree INTEGER,
            out_degree INTEGER,
            PRIMARY KEY (scenario_id, node_name)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS publication_edges (
            scenario_id VARCHAR(255) NOT NULL,
            source_node VARCHAR(255) NOT NULL,
            target_node VARCHAR(255) NOT NULL,
            edge_type VARCHAR(128) NOT NULL,
            PRIMARY KEY (scenario_id, source_node, target_node)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS publication_pairs (
            scenario_id VARCHAR(255) NOT NULL,
            node_a VARCHAR(255) NOT NULL,
            node_b VARCHAR(255) NOT NULL,
            decision VARCHAR(64) NOT NULL,
            target INTEGER NOT NULL,
            reviewed_at VARCHAR(64),
            features_json LONGTEXT,
            PRIMARY KEY (scenario_id, node_a, node_b)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS publication_reports (
            report_id VARCHAR(255) PRIMARY KEY,
            benchmark_id VARCHAR(255) NOT NULL,
            scenario_id VARCHAR(255) NOT NULL,
            report_type VARCHAR(128) NOT NULL,
            summary_json LONGTEXT,
            created_at VARCHAR(64) NOT NULL
        )
        """,
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def publish_curated_scenario(
    database_url: str,
    *,
    benchmark_name: str,
    scenario_name: str,
    graph: nx.DiGraph,
    source_metadata: dict[str, Any],
    gml_path: str | None,
    labels_path: str | None,
    reviewed_pairs: dict[tuple[str, str], dict[str, Any]],
    filters: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, str]:
    init_publication_store(database_url)
    engine = create_database_engine(database_url)
    benchmark_id = benchmark_name
    scenario_id = f"{benchmark_name}:{scenario_name}"
    created_at = _utcnow_text()
    report_id = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                DELETE FROM publication_reports WHERE scenario_id = :scenario_id
                """
            ),
            {"scenario_id": scenario_id},
        )
        conn.execute(
            text(
                """
                DELETE FROM publication_pairs WHERE scenario_id = :scenario_id
                """
            ),
            {"scenario_id": scenario_id},
        )
        conn.execute(
            text(
                """
                DELETE FROM publication_edges WHERE scenario_id = :scenario_id
                """
            ),
            {"scenario_id": scenario_id},
        )
        conn.execute(
            text(
                """
                DELETE FROM publication_nodes WHERE scenario_id = :scenario_id
                """
            ),
            {"scenario_id": scenario_id},
        )
        conn.execute(
            text(
                """
                DELETE FROM publication_scenarios WHERE scenario_id = :scenario_id
                """
            ),
            {"scenario_id": scenario_id},
        )
        benchmark_metadata = json.dumps({"source_mode": source_metadata.get("mode")})
        existing_benchmark = conn.execute(
            text("SELECT benchmark_id FROM publication_benchmarks WHERE benchmark_id = :benchmark_id"),
            {"benchmark_id": benchmark_id},
        ).first()
        if existing_benchmark:
            conn.execute(
                text(
                    """
                    UPDATE publication_benchmarks
                    SET benchmark_name = :benchmark_name, metadata_json = :metadata_json
                    WHERE benchmark_id = :benchmark_id
                    """
                ),
                {
                    "benchmark_id": benchmark_id,
                    "benchmark_name": benchmark_name,
                    "metadata_json": benchmark_metadata,
                },
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO publication_benchmarks (benchmark_id, benchmark_name, metadata_json, created_at)
                    VALUES (:benchmark_id, :benchmark_name, :metadata_json, :created_at)
                    """
                ),
                {
                    "benchmark_id": benchmark_id,
                    "benchmark_name": benchmark_name,
                    "metadata_json": benchmark_metadata,
                    "created_at": created_at,
                },
            )
        conn.execute(
            text(
                """
                INSERT INTO publication_scenarios (
                    scenario_id, benchmark_id, scenario_name, source_mode, source_database, source_schema,
                    gml_path, labels_path, node_count, edge_count, metadata_json, created_at
                ) VALUES (
                    :scenario_id, :benchmark_id, :scenario_name, :source_mode, :source_database, :source_schema,
                    :gml_path, :labels_path, :node_count, :edge_count, :metadata_json, :created_at
                )
                """
            ),
            {
                "scenario_id": scenario_id,
                "benchmark_id": benchmark_id,
                "scenario_name": scenario_name,
                "source_mode": source_metadata.get("mode"),
                "source_database": source_metadata.get("database_name"),
                "source_schema": source_metadata.get("schema"),
                "gml_path": gml_path,
                "labels_path": labels_path,
                "node_count": int(graph.number_of_nodes()),
                "edge_count": int(graph.number_of_edges()),
                "metadata_json": json.dumps(source_metadata),
                "created_at": created_at,
            },
        )
        for node, attrs in graph.nodes(data=True):
            conn.execute(
                text(
                    """
                    INSERT INTO publication_nodes (
                        scenario_id, node_name, layer, domain, table_name, semantic_name, in_degree, out_degree
                    ) VALUES (
                        :scenario_id, :node_name, :layer, :domain, :table_name, :semantic_name, :in_degree, :out_degree
                    )
                    """
                ),
                {
                    "scenario_id": scenario_id,
                    "node_name": str(node),
                    "layer": str(attrs.get("type") or ""),
                    "domain": str(attrs.get("domain") or ""),
                    "table_name": str(attrs.get("table_name") or ""),
                    "semantic_name": str(attrs.get("semantic_name") or ""),
                    "in_degree": int(graph.in_degree(node)),
                    "out_degree": int(graph.out_degree(node)),
                },
            )
        for source, target in graph.edges:
            conn.execute(
                text(
                    """
                    INSERT INTO publication_edges (scenario_id, source_node, target_node, edge_type)
                    VALUES (:scenario_id, :source_node, :target_node, :edge_type)
                    """
                ),
                {
                    "scenario_id": scenario_id,
                    "source_node": str(source),
                    "target_node": str(target),
                    "edge_type": "lineage",
                },
            )
        for (node_a, node_b), payload in reviewed_pairs.items():
            decision = str(payload.get("decision", ""))
            conn.execute(
                text(
                    """
                    INSERT INTO publication_pairs (
                        scenario_id, node_a, node_b, decision, target, reviewed_at, features_json
                    ) VALUES (
                        :scenario_id, :node_a, :node_b, :decision, :target, :reviewed_at, :features_json
                    )
                    """
                ),
                {
                    "scenario_id": scenario_id,
                    "node_a": str(node_a),
                    "node_b": str(node_b),
                    "decision": decision,
                    "target": 1 if decision == "duplicate" else 0,
                    "reviewed_at": payload.get("timestamp"),
                    "features_json": json.dumps(filters),
                },
            )
        conn.execute(
            text(
                """
                INSERT INTO publication_reports (
                    report_id, benchmark_id, scenario_id, report_type, summary_json, created_at
                ) VALUES (
                    :report_id, :benchmark_id, :scenario_id, :report_type, :summary_json, :created_at
                )
                """
            ),
            {
                "report_id": report_id,
                "benchmark_id": benchmark_id,
                "scenario_id": scenario_id,
                "report_type": "scenario_publication_summary",
                "summary_json": json.dumps(summary),
                "created_at": created_at,
            },
        )
    return {"benchmark_id": benchmark_id, "scenario_id": scenario_id, "report_id": report_id}
