# 03 — UI Tabs Guide

> **Navigation:** [README](README.md) | [01 What Is Isomera](01_What_Is_Isomera.md) | [02 Data Flow](02_Data_Flow_and_State.md) | [04 Core Modules](04_Core_Modules.md) | [05 Algorithms](05_Algorithms_and_Models.md) | [06 Libraries](06_Libraries_and_Stack.md) | [07 Pseudocode](07_Pseudocode_Reference.md) | [08 Graph Maps](08_Graph_Maps.md)

---

## Tab Overview

Isomera v2 is organized as a module-based Streamlit workspace. The current navigation is:

```
Home                  <- conceptual onboarding
Benchmark & Examples  <- official benchmark runs and model routing
Scenario Studio       <- database/GML scenario creation, pair validation, training
Study Lab             <- model internals, VMamba/SS2D learning, official runtime checks, VMamba-Mesh adapter training
Model Lab             <- read-only model and pickle inventory
Research Reports      <- article-ready packages
Admin                 <- databases, backend store, SQL workspace
Logs                  <- terminal and session traceability
Help                  <- technical documentation
About                 <- provenance, version notes, references
```

The older tabs documented below map to the v1/v2 foundations. For current workflows, use `10_Isomera_Protocol_and_Article_Workflow.md` and `11_Study_Lab_VMamba_Mesh.md`.

---

## Tab 1: Overview

### Purpose
Conceptual landing page. Establishes the mental model before the user interacts with graphs and algorithms.

### What it shows
- Tool purpose and motivation (Data Mesh, redundancy problem).
- Data layer semantics: SOR / SOT / SPEC with a diagram.
- Formal graph model: $G = (V, E)$ where nodes are tables, edges are dependencies.
- Isomorphism concept: "structurally equivalent subgraph" and why it signals redundancy.
- Metrics summary: what ACC, ET, and SF measure.
- Optional methodology flow image from `core/img`.

### Technical role
This tab does no computation. It reduces misuse by clarifying upfront that **structural similarity is not the same as business duplication** — human validation is always required.

---

## Tab 2: Data Model Selection

### Purpose
Entry point for graph creation or loading. All downstream tabs depend on a graph being available in `st.session_state["graph"]`.

### Five input modes

| Mode | Description | Key function |
|---|---|---|
| **TPC-DS Benchmark** | Load `.gml` scenario files; supports full benchmark loop | `metrics_table`, `execution_times` |
| **Random** | Generate a randomized SOR/SOT/SPEC graph with seed | `generate_random_lineage_graph` |
| **Manual Builder** | Build graph from editable node/edge tables | custom build from DataFrames |
| **Architecture Scenario** | Load a saved named-architecture scenario from storage | `nx.read_gml` |
| **Database Connector** | Extract lineage from SQLite FK metadata | `create_sqlite_engine`, `build_lineage_from_db` |

### State effects
On graph creation/load:
- Sets `graph` and `initial_graph` (both to the loaded graph)
- Sets `graph_source`, `layout_seed`
- Resets `metrics_df`, `isomorphic_pairs`, `labeled_pairs`, `model_ran` to defaults

**Why reset downstream state?** When a new graph is loaded, previous pairs and metrics belong to a different graph. Keeping them would produce incorrect comparisons.

### Benchmark mode (TPC-DS)
The benchmark loop runs automatically over all scenario files, all enabled algorithms, and a configurable number of timing runs. It:
1. Reads each `.gml` from `data/architectures/<arch>/gml/`.
2. Loads ground-truth pairs from `data/architectures/<arch>/real_pairs/`.
3. Calls `metrics_table` and `execution_times` for each algorithm.
4. Skips GNN if the pickle file for the scenario does not exist or torch is unavailable.
5. Stores results in `benchmark_results` and `benchmark_exec_stats`.

A cancellation flag (`cancel_benchmark`) is checked in the loop to keep the UI responsive.

### Risks and controls
- Long-running generation/benchmark is bounded by `build_timeout_secs` and `global_timeout_secs`.
- Random generation with invalid parameters (e.g., `min_tables > max_tables`) raises `ValueError` caught by the UI.
- Missing real-pair files produce a warning but do not stop the benchmark.

---

## Tab 3: Algorithm Selection

### Purpose
Execute structural similarity detection and produce candidate node pairs.

### User flow
1. User selects algorithm from dropdown (`VF2`, `Node Match (Custom)`).
2. User clicks "Find isomorphic pairs".
3. App calls `find_isomorphic_pairs(graph, algorithm)` → dispatches via registry.
4. Predicted pairs are stored in `isomorphic_pairs` and displayed in a table.

### Algorithm availability
- `VF2` and `Node Match (Custom)` are always available.
- `GIN/GNN (Pickle)` is present in the registry but is excluded from the standard interactive dropdown. It is used in the benchmark path (Tab 2) when a `.pkl` file is configured.

### Output contract
- `list[tuple[str, str]]` — each tuple is a predicted isomorphic node pair.
- Canonical normalization: `(A, B)` and `(B, A)` are treated as the same pair everywhere.

### State effects
- Updates `isomorphic_pairs`
- Sets `model_ran = True`

---

## Tab 4: Manual User Validation

### Purpose
Human-in-the-loop quality gate. Converts structural predictions into trusted labels and optional graph edits.

### Why this stage is academically important
Pure structural isomorphism can produce false positives relative to business semantics. Two pipelines can be structurally identical but serve different purposes (e.g., different domains processing different customer segments). This stage explicitly introduces **domain judgment** before any optimization decisions.

### Two validation methods

**Method A: UI validation**
1. User selects one predicted pair `(A, B)`.
2. The pair's subgraphs are visualized side by side.
3. User decision:
   - *Not isomorphic*: reject the pair, keep both nodes.
   - *Remove node A*: call `apply_removals([A])`.
   - *Remove node B*: call `apply_removals([B])`.
4. After removal: `find_isomorphic_pairs` is re-run on the updated `graph`.
5. Decision is recorded in `removed_pairs_log` and `review_status`.

**Method B: CSV validation**
1. App generates a full pair template: every unordered node pair from `initial_graph`, with `is_isomorphic=0` default.
2. User downloads, labels externally (any spreadsheet or script), re-uploads.
3. App parses: rows with `is_isomorphic=1` become `labeled_pairs`.
4. If uploaded row count equals total pair count, `ground_truth_complete = True`.

### Protection controls (`apply_removals`)

```python
def apply_removals(graph, nodes_to_remove,
                   protect_prefixes=None,       # e.g., ["SOR"] — never remove
                   min_remaining_by_prefix=None): # e.g., {"SOT": 1, "SPEC": 1}
```

If enabled:
- `SOR` nodes are never removed (protect_prefixes).
- At least 1 SOT and 1 SPEC must remain (min_remaining_by_prefix).
- After removals, isolated nodes (no edges) are also cleaned up automatically.

**Why SOR is protected:** SOR nodes are structural anchors representing raw data sources. Removing them would break the lineage DAG semantics entirely.

---

## Tab 5: Metrics Evaluation

### Purpose
Quantify algorithm quality and cost after validation labels exist.

### Prerequisite
`labeled_pairs` must be non-empty. If `ground_truth_complete = False` (only positive pairs labeled), TN and full accuracy are undefined by design.

### Metrics pipeline

1. For each algorithm in `[VF2, Node Match (Custom), GIN/GNN (Pickle)]`:
   - Predict: `find_isomorphic_pairs(initial_graph, algo)`.
   - Evaluate: `confusion_metrics_pairs(labeled_pairs, pred_pairs, all_pairs)`.
2. Measure execution times: `execution_times(initial_graph, algorithms, runs=25)`.
3. Derive SF: `(ACC / ET) × node_count`.

### Metric semantics and gotchas

| Metric | Formula | Valid when |
|---|---|---|
| TP, FP, FN | Set intersection/difference of canonical pairs | Always |
| TN | `all_pairs - (true_pairs ∪ pred_pairs)` | Only when `ground_truth_complete=True` |
| ACC | `(TP+TN)/(TP+TN+FP+FN)` | Only when `ground_truth_complete=True` |
| Benchmark ACC | `TP/(TP+FP+FN)` | Always (no TN needed) |
| ET | Mean of 25 `perf_counter` measurements | Always |
| SF | `(ACC/ET) × node_count` | When ACC is valid |

### Charts rendered
- Boxplots of ET distribution per algorithm.
- Boxplots of ACC distribution per algorithm.
- SF line chart by domain count and SOR regime.

### Why `initial_graph` is used (not `graph`)
After Tab 4 removals, `graph` has fewer nodes. Evaluating algorithms on the modified graph would give artificially better results (fewer nodes = fewer candidates to evaluate). `initial_graph` guarantees a fair, reproducible baseline.

---

## Tab 6: Session Logs

### Purpose
Provide full traceability and auditability for app behavior.

### Two log channels

**Channel 1: Session logs (`.jsonl`)**
- Structured, timestamped events.
- Each line: `{"timestamp": ..., "context": ..., "action": ..., "payload": ..., "error": ...}`.
- Useful for: step-by-step replay, debugging, understanding what happened in a run.

**Channel 2: Terminal logs (`.log`)**
- Raw stdout/stderr captured via a tee wrapper initialized at startup.
- Useful for: low-level exception tracebacks, import errors, framework warnings.

### Key logging functions
- `_init_session_log()` — creates the JSONL file for the session
- `_log_event(context, payload)` — records a generic event
- `_log_action(context, action, payload)` — records a user action
- `_log_exception(context, exc)` — records an exception with traceback
- `_init_terminal_logging()` / `_finalize_terminal_log()` — start/stop file tee

### Retention
A rolling cleanup keeps only the N most recent log files to prevent unbounded disk growth.

### Why this matters for defense and governance
Logs provide empirical evidence of:
- Which algorithms were run and in what order.
- What decisions the user made in the validation step.
- Timing and timeout events that affected benchmark results.
- Exception traces that explain unexpected behavior.

---

## Tab 7: About

### Purpose
Project context, academic references, and downloadable artifacts.

### What it provides
- Links to the Isomera paper (Artigo I) and dissertation.
- BibTeX entries for citing the tool.
- Download buttons for source PDFs used as methodological foundation.
- Authors and institutional affiliations.

### Technical role
No algorithmic computation. This tab is a documentation and provenance channel — it anchors the implementation to its research context.

---

## Tab 8: Validation Admin

### Purpose
Administrative interface for managing benchmark datasets and scenario-level assets. Primarily used by the researcher (not end users).

### Capabilities
- Select architecture and scenario.
- View scenario graph as visualization.
- Review, edit, and persist pair labels (`real_pairs/*.json`).
- Export/import CSV templates for bulk labeling.
- Delete scenario or entire architecture (with confirmation dialog).
- Clone scenario to a new architecture for experiments.
- Save updated graph snapshots for visual audit.

### Why this matters for research
This tab formalizes **dataset governance** for the benchmark. It allows ground truth to evolve (new pairs discovered, mislabeled pairs corrected) without modifying algorithm code. The dataset and the algorithm evaluation pipeline are explicitly decoupled.

### Key behaviors
- Label normalization: pairs imported via CSV are canonicalized with `canonical_pairs()` before saving.
- Deletion is irreversible (no undo) and requires explicit confirmation in the UI.
- Visual snapshots are saved as PNG alongside the GML so reviewers can audit the graph structure.
