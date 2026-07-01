# 04 — Core Modules and Functions

> **Navigation:** [README](README.md) | [01 What Is Isomera](01_What_Is_Isomera.md) | [02 Data Flow](02_Data_Flow_and_State.md) | [03 UI Tabs](03_UI_Tabs_Guide.md) | [05 Algorithms](05_Algorithms_and_Models.md) | [06 Libraries](06_Libraries_and_Stack.md) | [07 Pseudocode](07_Pseudocode_Reference.md) | [08 Graph Maps](08_Graph_Maps.md)

---

## Module Map

```
core/
├── lineage.py        — graph construction and I/O
├── isomorphism.py    — detection API and node removal
├── metrics.py        — ACC, ET, SF computation
├── database.py       — SQLite → lineage graph adapter
└── algorithms/
    ├── __init__.py   — registers all algorithms
    ├── base.py       — IsomorphismAlgorithm Protocol
    ├── registry.py   — name → instance map
    ├── vf2.py        — VF2 implementation
    ├── node_match.py — Node Match implementation
    ├── gnn_pickle.py — GNN adapter (loads .pkl, runs inference)
    └── gnn_model.py  — GINLayer, SubgraphGNN, PairClassifier
```

---

## `core/lineage.py` — Graph Construction

### Role
Builds and serializes lineage graphs from multiple sources. The "graph factory" of the system.

### Functions

#### `generate_lineage_graph(num_domains, min_columns, max_columns) → nx.DiGraph`

Generates a deterministic lineage graph with exactly one SOR, SOT, and SPEC per domain. Used for simple structured scenarios.

Structure per domain `d`:
```
Domain_d → Domain_d-SOR
Domain_d → Domain_d-SOT → Domain_d-SOR (feeds into SOT)
Domain_d → Domain_d-SPEC → Domain_d-SOT (feeds into SPEC)
```

#### `generate_random_lineage_graph(num_domains, num_sors, min_tables, max_tables, seed) → nx.DiGraph`

Generates a stochastic lineage graph with a randomized SOR/SOT/SPEC topology. This is the function used for benchmark scenario generation.

- `num_sors`: how many SOR nodes per domain (controls density; corresponds to the `SOR=2/4/8/16` parameter in the paper).
- `min_tables`, `max_tables`: range for the number of SOT nodes sampled.
- `seed`: makes generation reproducible.

Node naming convention:
- SOR: `SOR{sor}_D{domain}_T0`
- SOT: `SOT_D{domain}_T{n}`
- SPEC: `SPEC_{domain}_T{n}`

Connectivity rules:
- Each SOT is connected to 1–3 random SOR nodes.
- Each SPEC is connected to 1–3 random SOT nodes.
- Domain membership is encoded in the node label.

#### `plot_lineage_graph(graph, seed) → plt.Figure`

Renders the graph as a directed matplotlib figure. Uses a spring layout with deterministic seed. Called by the UI for visualization in the data model and validation tabs.

#### `save_graph_gml(graph, path)`

Writes the graph to a GML file using `nx.write_gml`. The path structure follows the artifact layout (`data/architectures/<arch>/gml/`).

#### `adjacency_matrix_dataframe(graph) → pd.DataFrame`

Returns the adjacency matrix as a labeled DataFrame (rows and columns are node labels). Used in the UI for table-form inspection.

#### `edge_dataframe(graph) → pd.DataFrame`

Returns all edges as a two-column DataFrame `(source, target)`. Used for CSV export and manual inspection.

---

## `core/isomorphism.py` — Detection API

### Role
Algorithm-agnostic service layer. The bridge between the UI (which knows about user actions) and the algorithm layer (which knows about graph structures). Also handles safe node removal.

### Why this layer exists
The UI should never call `VF2Algorithm.predict_pairs()` directly. By going through `find_isomorphic_pairs()`, the UI is decoupled from any specific algorithm implementation. Swapping algorithms requires no UI change.

### Functions

#### `find_isomorphic_pairs(graph, algorithm="VF2") → list[tuple[str, str]]`

```python
def find_isomorphic_pairs(graph: nx.DiGraph, algorithm: str = "VF2"):
    algo = get_algorithm(algorithm)      # registry lookup by name
    return algo.predict_pairs(graph)     # uniform interface
```

The central dispatch function. Every detection call in the system, from the algorithm tab to the metrics evaluation loop, goes through this function.

#### `predict_isomorphic_nodes(graph, algorithm="VF2") → set[str]`

Convenience wrapper that flattens the pairs list into the set of all nodes that appear in at least one predicted pair. Used when the UI needs to highlight nodes rather than pairs.

#### `apply_removals(graph, nodes_to_remove, protect_prefixes=None, min_remaining_by_prefix=None)`

```python
def apply_removals(graph, nodes_to_remove,
                   protect_prefixes=None,
                   min_remaining_by_prefix=None):
    # Returns: (new_graph, removed, skipped, isolated_removed)
```

Applies validated removal decisions with safety guards. The function:
1. Checks each node against `protect_prefixes` (e.g., `["SOR"]`) — skips if protected.
2. Checks `min_remaining_by_prefix` — skips if removing would violate the minimum count.
3. Removes the node from a copy of the graph.
4. After all explicit removals, scans for isolated nodes (no in- or out-edges) and removes them too.
5. Returns 4 values: the new graph, list of removed nodes, list of skipped nodes, list of auto-removed isolated nodes.

**Why the copy?** `graph.copy()` ensures the original is not mutated. The caller decides whether to replace `st.session_state["graph"]` with the new graph. `initial_graph` is never passed to this function.

---

## `core/metrics.py` — Metrics and Timing

### Role
All evaluation logic for comparing algorithms. Computes confusion matrix metrics, execution time distributions, and the SF throughput measure.

### Key design choices

**Canonical pairs:** All pair comparisons go through `canonical_pairs()`, which sorts each tuple so `(A, B)` and `(B, A)` are treated identically. Without this, evaluation results would depend on the arbitrary order algorithms return pairs.

**TN validity:** True negatives are only computable when the complete pair universe is labeled. The code explicitly sets `tn = None` when `all_pairs` is not provided. This prevents reporting invalid accuracy numbers.

### Functions

#### `_canonical_pair(node_a, node_b) → tuple[str, str]`
```python
def _canonical_pair(a, b): return tuple(sorted((a, b)))
```
Internal helper. Normalizes a single pair.

#### `canonical_pairs(pairs) → set[tuple[str, str]]`
```python
def canonical_pairs(pairs): return {_canonical_pair(a, b) for a, b in pairs}
```
Returns a canonical set. Used everywhere pairs are compared.

#### `confusion_metrics_pairs(true_pairs, predicted_pairs, all_pairs=None) → dict`

```python
true_set = canonical_pairs(true_pairs)
pred_set = canonical_pairs(predicted_pairs)

tp = len(true_set & pred_set)
fp = len(pred_set - true_set)
fn = len(true_set - pred_set)
tn = len(all_set - (true_set | pred_set))  # only if all_pairs provided
```

Returns: `{tp, fp, fn, tn, precision, recall, f1, accuracy}`.

`accuracy` is `None` if `tn` is None (incomplete labeling).

#### `metrics_table(graph, true_pairs, algorithms, all_pairs=None) → pd.DataFrame`

Runs the full metrics pipeline for a list of algorithms on a given graph. Calls `find_isomorphic_pairs` for each algorithm and `confusion_metrics_pairs` for each result. Returns a DataFrame with one row per algorithm.

This is the function called in both the interactive metrics tab and the benchmark loop.

#### `execution_times(graph, algorithms, runs=25) → dict[str, list[float]]`

```python
for algo in algorithms:
    for _ in range(runs):
        start = perf_counter()
        find_isomorphic_pairs(graph, algo)
        times[algo].append(perf_counter() - start)
```

Returns raw timing samples per algorithm. The benchmark computes mean, median, and std from these samples.

**Why 25 runs?** Balances statistical stability with wall-clock cost. The first run may include Python caching effects; averaging over 25 gives a stable estimate.

#### `error_rate(metrics) → float`
```python
total = tp + fp + fn  # (or + tn if available)
return (fp + fn) / total
```
Computes error rate from a confusion metrics dict.

---

## `core/database.py` — Database Connector

### Role
Converts a relational database schema into a lineage graph by treating foreign keys as lineage edges.

### Semantics
If table `B` has a foreign key referencing table `A`, then `A → B` in the lineage graph — table A is a source for table B.

### Functions

#### `create_sqlite_engine(db_path) → Engine`
```python
from sqlalchemy import create_engine
return create_engine(f"sqlite:///{db_path}")
```
Creates a SQLAlchemy engine for the specified SQLite file path.

#### `build_lineage_from_db(engine) → nx.DiGraph`
```python
inspector = inspect(engine)
for table in inspector.get_table_names():
    graph.add_node(table)   # each table becomes a node
for fk in inspector.get_foreign_keys(table):
    referred = fk["referred_table"]
    graph.add_edge(referred, table)  # FK implies lineage dependency
```

This enables Isomera to extract a lineage graph from any SQLite database without manual schema specification. The current implementation targets SQLite via `information_schema`; the Artigo III roadmap extends this to real database systems (PostgreSQL, Snowflake, BigQuery) via SQLAlchemy connectors.

---

## `core/algorithms/registry.py` — Algorithm Registry

### Role
Decouples UI and metrics code from concrete algorithm implementations via a name-to-instance map.

### Why it matters
Without a registry, every place that runs algorithms would need an `if/elif/else` chain. Adding a new algorithm would require modifying multiple files. The registry reduces this to one `register_algorithm()` call.

### Functions

```python
_registry: dict[str, IsomorphismAlgorithm] = {}

def register_algorithm(name: str, algo: IsomorphismAlgorithm) -> None:
    _registry[name] = algo

def get_algorithm(name: str) -> IsomorphismAlgorithm:
    if name not in _registry:
        raise KeyError(f"Unknown: '{name}'. Available: {list(_registry)}")
    return _registry[name]

def list_algorithms() -> list[str]:
    return list(_registry.keys())
```

### Registration (in `core/algorithms/__init__.py`)
```python
register_algorithm("VF2", VF2Algorithm())
register_algorithm("Node Match (Custom)", NodeMatchAlgorithm())
register_algorithm("GIN/GNN (Pickle)", GNNPickleAlgorithm())
```

This happens at import time, so the registry is populated as soon as `core.algorithms` is imported by the app.

### Failure mode
An unknown algorithm name raises `KeyError` with the list of available names. This provides a clear error message instead of a silent wrong result.

---

## `core/algorithms/base.py` — Interface Contract

```python
from typing import Protocol
import networkx as nx

class IsomorphismAlgorithm(Protocol):
    name: str
    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]: ...
```

All algorithms satisfy this Protocol. The contract is: given a directed graph, return a list of node pairs predicted to be redundant (isomorphic at the subgraph level). This is the only API the rest of the system sees.

---

## Full Function Index

### `core/lineage.py`
| Function | Signature | Purpose |
|---|---|---|
| `generate_lineage_graph` | `(num_domains, min_columns, max_columns) → DiGraph` | Structured graph per domain |
| `generate_random_lineage_graph` | `(num_domains, num_sors, min_tables, max_tables, seed) → DiGraph` | Random benchmark graph |
| `plot_lineage_graph` | `(graph, seed) → Figure` | Matplotlib visualization |
| `save_graph_gml` | `(graph, path)` | Persist graph to GML |
| `adjacency_matrix_dataframe` | `(graph) → DataFrame` | Adjacency matrix as table |
| `edge_dataframe` | `(graph) → DataFrame` | Edge list as table |

### `core/isomorphism.py`
| Function | Signature | Purpose |
|---|---|---|
| `find_isomorphic_pairs` | `(graph, algorithm) → list[tuple]` | Central dispatch for detection |
| `predict_isomorphic_nodes` | `(graph, algorithm) → set[str]` | Nodes in any predicted pair |
| `apply_removals` | `(graph, nodes, protect_prefixes, min_remaining) → tuple` | Safe node removal |

### `core/metrics.py`
| Function | Signature | Purpose |
|---|---|---|
| `canonical_pairs` | `(pairs) → set[tuple]` | Normalize pair ordering |
| `confusion_metrics_pairs` | `(true, pred, all) → dict` | TP/FP/FN/TN/ACC/F1 |
| `metrics_table` | `(graph, true, algos, all) → DataFrame` | Multi-algorithm comparison |
| `execution_times` | `(graph, algos, runs) → dict` | Per-algorithm timing samples |
| `error_rate` | `(metrics) → float` | (FP+FN)/total |

### `core/database.py`
| Function | Signature | Purpose |
|---|---|---|
| `create_sqlite_engine` | `(db_path) → Engine` | SQLAlchemy engine from path |
| `build_lineage_from_db` | `(engine) → DiGraph` | FK metadata → lineage graph |

### `core/algorithms/registry.py`
| Function | Signature | Purpose |
|---|---|---|
| `register_algorithm` | `(name, algo)` | Register implementation |
| `get_algorithm` | `(name) → IsomorphismAlgorithm` | Lookup by name |
| `list_algorithms` | `() → list[str]` | All registered names |

### `core/algorithms/vf2.py`
| Function/Class | Signature | Purpose |
|---|---|---|
| `_subgraphs_by_successors` | `(graph) → list[(anchor, subgraph)]` | Build local subgraphs |
| `VF2Algorithm.predict_pairs` | `(graph) → list[tuple]` | VF2 isomorphism detection |

### `core/algorithms/node_match.py`
| Function/Class | Signature | Purpose |
|---|---|---|
| `_subgraphs_by_successors` | `(graph) → list[(anchor, subgraph)]` | Build local subgraphs |
| `NodeMatchAlgorithm.predict_pairs` | `(graph) → list[tuple]` | Node-attribute isomorphism |

### `core/algorithms/gnn_pickle.py`
| Function/Class | Signature | Purpose |
|---|---|---|
| `set_gnn_pickle_path` | `(path)` | Configure active `.pkl` path |
| `set_gnn_pickle_module` | `(module)` | Configure class resolution module |
| `validate_gnn_pickle` | `(path) → str \| None` | Check loadability, return error or None |
| `GNNPickleAlgorithm.predict_pairs` | `(graph) → list[tuple]` | Model-based inference via pickle |
