# 02 — Data Flow, State, and Persistence

> **Navigation:** [README](README.md) | [01 What Is Isomera](01_What_Is_Isomera.md) | [03 UI Tabs](03_UI_Tabs_Guide.md) | [04 Core Modules](04_Core_Modules.md) | [05 Algorithms](05_Algorithms_and_Models.md) | [06 Libraries](06_Libraries_and_Stack.md) | [07 Pseudocode](07_Pseudocode_Reference.md) | [08 Graph Maps](08_Graph_Maps.md)

---

## End-to-End Control Flow

The entire Isomera workflow follows five sequential steps. Every step depends on the one before it completing successfully.

```
START APPLICATION
  ├── initialize session logging (JSONL + terminal tee)
  ├── initialize all session_state defaults
  └── render step indicators + tab layout

STEP 1 ─── OBTAIN A GRAPH
  ├── Mode A: TPC-DS Benchmark → load .gml from data/architectures/
  ├── Mode B: Random → generate_random_lineage_graph() → save .gml snapshot
  ├── Mode C: Manual Builder → build nx.DiGraph from node/edge input tables
  ├── Mode D: Architecture Scenario → read_gml from saved scenario
  └── Mode E: Database Connector → create_sqlite_engine() → build_lineage_from_db()
  
  → stores: graph, initial_graph, graph_source, layout_seed
  → resets: metrics_df, isomorphic_pairs, labeled_pairs, model_ran

STEP 2 ─── DETECT PAIRS
  └── find_isomorphic_pairs(graph, algorithm_name)
        └── get_algorithm(algorithm_name).predict_pairs(graph)
  → stores: isomorphic_pairs, model_ran = True

STEP 3 ─── VALIDATE PAIRS (human-in-the-loop)
  ├── Mode UI: user decides keep/remove per pair
  │     └── apply_removals(graph, candidate_nodes, protect_prefixes, min_remaining)
  │           → returns (new_graph, removed, skipped, isolated_removed)
  │     → recomputes: isomorphic_pairs on updated graph
  └── Mode CSV: export all-pairs template → user labels → import
        → updates: labeled_pairs, ground_truth_complete

STEP 4 ─── EVALUATE METRICS
  ├── metrics_table(initial_graph, labeled_pairs, algorithms, all_pairs)
  ├── execution_times(initial_graph, algorithms, runs=25)
  └── derive SF per algorithm
  → stores: metrics_df, exec_times, exec_times_stats

STEP 5 ─── (optional) BENCHMARK MODE
  └── Loop over all .gml scenarios × all algorithms × 25 runs
  → stores: benchmark_results, benchmark_exec_stats

LOGGING (throughout all steps)
  └── _log_event() / _log_action() / _log_exception() → session_*.jsonl
```

---

## Key Design Decision: `initial_graph` is Immutable

The `initial_graph` is set once when a graph is first obtained and **never modified** afterwards, even when the user removes nodes through the validation tab.

All metric evaluations use `initial_graph`, not `graph`. This guarantees that:
- Results are comparable across algorithms (apples-to-apples).
- Interactive removals do not contaminate evaluation.
- A session can be replayed from `initial_graph` + the `removed_pairs_log`.

```python
# core/isomorphism.py
def find_isomorphic_pairs(graph, algorithm="VF2"):
    algo = get_algorithm(algorithm)
    return algo.predict_pairs(graph)

# In the metrics tab: always uses initial_graph
metrics_table(st.session_state["initial_graph"], labeled_pairs, algorithms)
```

---

## Session State Model

All application state lives in `st.session_state`. Streamlit re-runs the entire script on every user interaction; session state is the mechanism that persists data across reruns.

### A. Graph lifecycle

| Key | Type | Description |
|---|---|---|
| `graph` | `nx.DiGraph` | Current mutable working graph |
| `initial_graph` | `nx.DiGraph` | Immutable baseline; used for all metric evaluations |
| `graph_source` | `str` | Source type: `Random`, `Manual`, `Architecture scenario`, `TPC-DS Benchmark` |
| `layout_seed` | `int` | Seed for consistent visualization layout across reruns |

### B. Analysis lifecycle

| Key | Type | Description |
|---|---|---|
| `isomorphic_pairs` | `list[tuple[str,str]]` | Current prediction output from active algorithm |
| `model_ran` | `bool` | Whether detection has executed in this session |
| `removed_nodes` | `list[str]` | Nodes removed after validated decisions |
| `removed_pairs_log` | `dict` | Human action audit keyed by pair |

### C. Validation lifecycle

| Key | Type | Description |
|---|---|---|
| `label_mode` | `str` | `UI` or `CSV` |
| `labeled_pairs` | `set[tuple[str,str]]` | Canonical set of trusted positive pairs |
| `ground_truth_complete` | `bool` | Whether all pairs (not just positives) are labeled |
| `review_status` | `dict` | Per-pair decision metadata (kept / removed A / removed B) |

### D. Metrics and benchmark lifecycle

| Key | Type | Description |
|---|---|---|
| `metrics_df` | `pd.DataFrame` | TP, FP, FN, TN, ACC, F1, Precision, Recall per algorithm |
| `exec_times` | `dict[str, list[float]]` | Raw timing samples per algorithm |
| `exec_times_stats` | `pd.DataFrame` | Mean, median, std of execution times |
| `benchmark_results` | `pd.DataFrame` | Full benchmark matrix output |
| `benchmark_exec_stats` | `pd.DataFrame` | Timing stats for benchmark scenarios |

### E. Operational controls

| Key | Type | Description |
|---|---|---|
| `cancel_build` | `bool` | Interrupt flag for long-running graph generation |
| `cancel_exec` | `bool` | Interrupt flag for algorithm execution |
| `cancel_benchmark` | `bool` | Interrupt flag for benchmark loop |
| `build_timeout_secs` | `int` | Maximum seconds for random graph generation |
| `global_timeout_secs` | `int` | Maximum seconds for full benchmark execution |
| `last_error` | `str \| None` | User-visible error message from most recent exception |

---

## Artifact Persistence Model

Isomera persists all important artifacts to disk. This supports reproducibility and post-hoc audit.

### Directory structure

```
data/
├── architectures/
│   └── <arch_name>/
│       ├── gml/
│       │   └── <scenario>.gml           # scenario lineage graphs
│       ├── real_pairs/
│       │   └── <scenario>.json          # ground truth duplicate pairs
│       └── validations/
│           └── <scenario>/
│               └── *.png                # graph visualization snapshots
└── graphs/
    └── random_lineage_*.gml             # random generation snapshots

logs/
├── session_<timestamp>.jsonl            # structured session event log
└── terminal/
    └── terminal_<timestamp>.log         # stdout/stderr tee capture

core/algorithms/pickle/
└── <scenario>.pkl                       # trained GNN model per scenario
```

### Log format (JSONL)

Each line in a session log is a JSON object:

```json
{
  "timestamp": "2026-04-01T14:32:11",
  "context": "benchmark",
  "action": "run_algorithm",
  "payload": {"algorithm": "GIN/GNN (Pickle)", "scenario": "SOR16_D3_seed42"},
  "error": null
}
```

**Why JSONL and not a database?** JSONL is stream-safe (append-only, no locking), human-readable, and portable. A session log can be replayed or analyzed with standard Unix tools.

### GML format

```
graph [
  directed 1
  node [ id 0 label "SOR1_D1_T0" ]
  node [ id 1 label "SOT_D1_T1" ]
  edge [ source 0 target 1 ]
]
```

NetworkX reads and writes GML natively with `nx.read_gml()` and `nx.write_gml()`. The format preserves node attributes (layer type, domain ID) alongside topology.

---

## Data Flow Entities (Summary)

| Entity | Format | Direction | When created |
|---|---|---|---|
| Scenario graph | `.gml` | disk ↔ memory | On graph load / generation |
| Predicted pairs | `list[tuple]` in memory | algorithm → validation tab | After `find_isomorphic_pairs` |
| Validated pairs | `.json` | disk ↔ memory | After CSV import or UI validation |
| Metrics table | `pd.DataFrame` in memory | metrics → UI charts | After `metrics_table` call |
| Session log | `.jsonl` append | memory → disk | Throughout session (streaming) |
| GNN model | `.pkl` | disk → memory | On GNN pickle load |
