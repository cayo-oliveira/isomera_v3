"""Reusable API for turning scenario sources into normalized lineage artifacts."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

from core.database import build_lineage_from_database_url
from core.lineage import adjacency_matrix_dataframe, edge_dataframe, normalize_lineage_direction


@dataclass(frozen=True)
class ScenarioMaterialization:
    source_mode: str
    graph: nx.DiGraph
    source_metadata: dict[str, Any]
    structure_rows: list[dict[str, Any]]
    edge_rows: list[dict[str, Any]]
    adjacency_rows: list[dict[str, Any]]


def graph_structure_rows(graph: nx.DiGraph | None) -> list[dict[str, Any]]:
    if graph is None:
        return []
    rows: list[dict[str, Any]] = []
    for node, attrs in sorted(graph.nodes(data=True), key=lambda item: str(item[0])):
        node_name = str(node)
        upper = node_name.upper()
        if "SOR" in upper:
            layer = "SOR"
        elif "SOT" in upper:
            layer = "SOT"
        elif "SPEC" in upper:
            layer = "SPEC"
        else:
            layer = "OTHER"
        domain = "-"
        if "_D" in node_name.upper():
            domain = f"D{node_name.upper().rsplit('_D', 1)[-1]}"
        elif node_name.lower().startswith("d") and "_" in node_name:
            domain = f"D{node_name.split('_', 1)[0][1:]}"
        rows.append(
            {
                "domain": domain,
                "layer": layer,
                "node": node_name,
                "table_name": attrs.get("table_name") or attrs.get("raw_name") or "-",
                "semantic_name": attrs.get("semantic_name") or "-",
                "in_degree": int(graph.in_degree(node)),
                "out_degree": int(graph.out_degree(node)),
            }
        )
    return rows


def scenario_api_contract() -> dict[str, object]:
    return {
        "name": "Scenario Materialization API",
        "module": "main/core/scenario_api.py",
        "purpose": (
            "Provide one reproducible API to ingest relational schemas, GML assets, or manual graphs, "
            "normalize lineage direction, and materialize the standard graph outputs used by Scenario Studio, "
            "Research Reports, and model training."
        ),
        "canonical_pipeline": [
            "source",
            "normalized_graph",
            "lineage_structure",
            "adjacency_matrix",
            "edge_table",
        ],
        "functions": [
            {
                "function": "materialize_database_scenario",
                "input": "database_url, schema_name, manifests_root",
                "output": "ScenarioMaterialization",
            },
            {
                "function": "materialize_gml_scenario",
                "input": "gml_path, source_mode, source_metadata",
                "output": "ScenarioMaterialization",
            },
            {
                "function": "materialize_graph",
                "input": "graph, source_mode, source_metadata",
                "output": "ScenarioMaterialization",
            },
        ],
        "guarantees": [
            "Canonical edge direction is normalized to SOR -> SOT -> SPEC.",
            "The same structure, edge table, and adjacency matrix are reused across UI, reporting, and training.",
            "The API emits metadata and graph build steps for article-grade reproducibility.",
        ],
        "limits": [
            "Automatic SOR/SOT/SPEC normalization depends on layer semantics in node or manifest metadata.",
            "Generic databases with arbitrary table names need an explicit mapping contract before semantic normalization is reliable.",
            "If no manifest is provided, table names such as customers, orders, products, or marts are treated as OTHER unless the connector can map them to SOR, SOT, or SPEC.",
            "The current normalization reverses graph direction using a majority edge-direction score; it does not discover business transformations from column names alone.",
            "Foreign-key-only mode can construct a graph, but it cannot infer business lineage that is not encoded as constraints.",
            "Manifest mode is preferred for reproducible benchmark scenarios because it records table layer, domain, semantic name, and lineage edges.",
        ],
    }


def _warehouse_manifest_for_schema(schema_name: str, manifests_root: Path) -> dict[str, object] | None:
    for manifest_path in manifests_root.glob("**/manifest.json"):
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("schema") == schema_name:
            payload["_manifest_path"] = str(manifest_path)
            return payload
    return None


def materialize_graph(
    graph: nx.DiGraph,
    *,
    source_mode: str,
    source_metadata: dict[str, Any] | None = None,
) -> ScenarioMaterialization:
    normalized_graph, direction_meta = normalize_lineage_direction(graph)
    metadata = dict(source_metadata or {})
    metadata.setdefault("mode", source_mode)
    metadata.update(direction_meta)
    return ScenarioMaterialization(
        source_mode=source_mode,
        graph=normalized_graph,
        source_metadata=metadata,
        structure_rows=graph_structure_rows(normalized_graph),
        edge_rows=edge_dataframe(normalized_graph).to_dict(orient="records"),
        adjacency_rows=adjacency_matrix_dataframe(normalized_graph)
        .reset_index()
        .rename(columns={"index": "node"})
        .to_dict(orient="records"),
    )


def materialize_gml_scenario(
    gml_path: str | Path,
    *,
    source_mode: str,
    source_metadata: dict[str, Any] | None = None,
) -> ScenarioMaterialization:
    gml_path = Path(gml_path)
    raw_graph = nx.read_gml(gml_path)
    metadata = dict(source_metadata or {})
    metadata.setdefault("path", str(gml_path))
    return materialize_graph(raw_graph, source_mode=source_mode, source_metadata=metadata)


def materialize_database_scenario(
    database_url: str,
    schema_name: str,
    *,
    manifests_root: str | Path,
) -> ScenarioMaterialization:
    manifests_root = Path(manifests_root)
    manifest = _warehouse_manifest_for_schema(schema_name, manifests_root)
    if not manifest:
        raw_graph = build_lineage_from_database_url(database_url, schema=schema_name)
        return materialize_graph(
            raw_graph,
            source_mode="Scenario Warehouse",
            source_metadata={
                "database_url": database_url,
                "schema": schema_name,
                "build_mode": "foreign_keys_only",
                "manifest_used": False,
                "graph_build_steps": [
                    "Connected to the scenario warehouse database.",
                    f"Loaded schema `{schema_name}`.",
                    "Inspected tables and foreign keys in that schema.",
                    "Built a directed lineage graph from FK relationships only.",
                    "Normalized edge direction to SOR -> SOT -> SPEC.",
                ],
            },
        )

    graph = nx.DiGraph()
    table_names: list[str] = []
    for domain_payload in dict(manifest.get("domains") or {}).values():
        for table in list(domain_payload.get("tables") or []):
            node_name = str(table.get("node"))
            if not node_name:
                continue
            graph.add_node(
                node_name,
                table_name=table.get("table_name"),
                type=table.get("type"),
                semantic_name=table.get("semantic_name"),
                raw_name=table.get("raw_name"),
                domain=domain_payload.get("name"),
            )
            if table.get("table_name"):
                table_names.append(str(table.get("table_name")))
    for edge in list(manifest.get("edges") or []):
        source = str(edge.get("from"))
        target = str(edge.get("to"))
        if source and target:
            graph.add_edge(source, target)
    return materialize_graph(
        graph,
        source_mode="Scenario Warehouse",
        source_metadata={
            "database_url": database_url,
            "schema": schema_name,
            "table_names": sorted(set(table_names)),
            "table_count": len(set(table_names)),
            "build_mode": "warehouse_manifest_contract",
            "manifest_used": True,
            "manifest_path": manifest.get("_manifest_path"),
            "graph_build_steps": [
                "Connected to the scenario warehouse database.",
                f"Loaded schema `{schema_name}`.",
                "Loaded the relational contract manifest linked to that schema.",
                "Mapped relational tables to lineage nodes using the benchmark manifest.",
                "Normalized all edges to the canonical SOR -> SOT -> SPEC direction.",
            ],
        },
    )
