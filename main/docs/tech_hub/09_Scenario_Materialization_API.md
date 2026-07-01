# Scenario Materialization API

## Purpose

The `Scenario Materialization API` is the reusable layer that transforms a source scenario into the canonical Isomera representation used everywhere else in the product:

1. normalized directed lineage graph
2. structured lineage table
3. adjacency matrix
4. edge table
5. reproducibility metadata and graph build steps

Module:

```python
main/core/scenario_api.py
```

## Why It Exists

This API isolates one important deliverable from the UI:

- connect to a relational scenario database
- reconstruct lineage from relational contracts or GML
- normalize direction to `SOR -> SOT -> SPEC`
- emit one standard structure for curation, reporting, and model training

That makes the scenario creation workflow portable. The same code path can be reused in:

- Isomera UI
- scripts
- notebooks
- benchmarks
- external tooling

## Public Functions

### `materialize_database_scenario(database_url, schema_name, manifests_root=...)`

Use this when the scenario comes from a relational warehouse schema.

Input:

- `database_url`
- `schema_name`
- `manifests_root`

Output:

- `ScenarioMaterialization`

### `materialize_gml_scenario(gml_path, source_mode, source_metadata=None)`

Use this when the scenario comes from a portable GML asset.

### `materialize_graph(graph, source_mode, source_metadata=None)`

Use this when the scenario is already available in memory, for example from the manual builder.

### `scenario_api_contract()`

Returns the API contract metadata used by `Research Reports` and article captures.

## Standard Output

Each `ScenarioMaterialization` object returns:

- `graph`
- `source_metadata`
- `structure_rows`
- `edge_rows`
- `adjacency_rows`

This is the canonical structure reused by:

- `Scenario Studio`
- `Research Reports`
- publication store
- training pipeline

## Example

```python
from core.scenario_api import materialize_database_scenario

bundle = materialize_database_scenario(
    "postgresql+psycopg://localhost:5432/isomera_tpcds_benchmark",
    "scenario_sor2_d5_seed42",
    manifests_root="main/data/tpcds_postgres",
)

graph = bundle.graph
source_metadata = bundle.source_metadata
structure_rows = bundle.structure_rows
edge_rows = bundle.edge_rows
adjacency_rows = bundle.adjacency_rows
```

## Guarantees

- edge direction is normalized to `SOR -> SOT -> SPEC`
- the same scenario representation is reused across UI, reports, and training
- graph build steps are persisted for reproducibility

## Limits

The API does not magically understand every database schema.

Automatic normalization to `SOR -> SOT -> SPEC` works when at least one of these is true:

- nodes or table names expose layer tokens such as `SOR`, `SOT`, and `SPEC`
- the scenario has a manifest contract with layer metadata
- the caller provides semantic metadata before materialization

If a future user connects a database with arbitrary names such as `tbl001`, `orders_tmp`, or `final_view`, the API can still inspect tables and foreign keys, but it cannot reliably infer:

- whether a table is SOR, SOT, or SPEC
- which domain a table belongs to
- whether an edge means lineage, lookup, enrichment, or operational dependency
- which subgraph should be compared for duplicate detection

For those cases, Isomera needs a mapping contract.

Minimum generic mapping:

```json
{
  "tables": [
    {
      "table_name": "orders_raw",
      "node": "SOR_orders_D1",
      "layer": "SOR",
      "domain": "sales",
      "semantic_name": "orders"
    }
  ],
  "edges": [
    {
      "from": "SOR_orders_D1",
      "to": "SOT_orders_enriched_D1",
      "edge_type": "lineage"
    }
  ]
}
```

Foreign-key-only mode is useful for exploration, but manifest mode is preferred for article-grade reproducibility.

## Materialization Sanity Check

For database-backed scenarios, Isomera also records a simple validation requested during review:

```text
database_table_count = count(tables in information_schema.tables for selected schema)
graph_node_count = count(vertices in the full lineage graph)
table_to_graph_validation = pass if both counts match
```

For the TPC-DS manifest-backed benchmark, the expected condition is:

```text
database_table_count == graph_node_count
```

This check does not prove that every edge is semantically correct, but it proves that materialization did not silently drop or duplicate tables. Edge correctness is handled by the manifest contract and by the edge table exported in Research Reports.

## How It Connects to Training

The training pipeline consumes the standardized graph emitted by this API.

Pipeline:

1. `source`
2. `normalized_graph`
3. `validation_dataset`
4. `training_dataset`
5. `model_artifact`

That is why this API is not only a UI helper. It is the canonical preprocessing layer of Isomera.
