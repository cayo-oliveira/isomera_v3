# 06 — Libraries and Technology Stack

> **Navigation:** [README](README.md) | [01 What Is Isomera](01_What_Is_Isomera.md) | [02 Data Flow](02_Data_Flow_and_State.md) | [03 UI Tabs](03_UI_Tabs_Guide.md) | [04 Core Modules](04_Core_Modules.md) | [05 Algorithms](05_Algorithms_and_Models.md) | [07 Pseudocode](07_Pseudocode_Reference.md) | [08 Graph Maps](08_Graph_Maps.md)

---

## Stack Summary

| Layer | Library | Version constraint | Purpose |
|---|---|---|---|
| UI | **Streamlit** | ≥1.30 | Reactive UI, session state, file I/O |
| Graphs | **NetworkX** | ≥3.0 | Graph construction, VF2, GML I/O |
| Neural (core) | **PyTorch** | optional (≥2.0) | GIN model weights, training |
| Neural (graph) | **PyTorch Geometric** | optional (≥2.0) | Data object, global_mean_pool |
| Data | **Pandas** | ≥2.0 | DataFrames for validation, metrics tables |
| Visualization | **Plotly** | ≥5.0 | Interactive bar/scatter charts in UI |
| Visualization | **Matplotlib** | ≥3.0 | Static graph drawings |
| Storage | **SQLAlchemy** | ≥2.0 | Session log persistence (SQLite backend) |
| Serialization | **pickle** (stdlib) | — | GNN model persistence |

PyTorch and PyTorch Geometric are **optional imports**. Isomera degrades gracefully: if they are not installed, the GIN algorithm is unavailable but VF2 and Node Match still work.

---

## Streamlit

**Why Streamlit?** Zero-boilerplate Python → UI mapping. The target users are researchers and data engineers, not front-end developers. Streamlit lets you write Python-first code where UI elements are function calls. No HTML, no JS, no REST API.

**Key features used:**

| Feature | Usage in Isomera |
|---|---|
| `st.session_state` | Centralized mutable state (graph, pairs, metrics, validation) |
| `st.tabs()` | 8-tab layout separating graph, analysis, benchmark, validation |
| `st.file_uploader()` | GML/CSV upload in tabs 1, 5, 8 |
| `st.download_button()` | Export pairs (JSON), logs (JSONL), scenarios (GML) |
| `st.data_editor()` | Editable validation table (Tab 6) |
| `st.plotly_chart()` | Benchmark visualization |
| `st.rerun()` | Trigger rerender after state changes |
| `st.expander()` | Collapsible sections (log viewer, details) |

**Reactivity model:** Streamlit re-runs the entire script on every user interaction. All state must live in `st.session_state` to survive re-renders. Ephemeral local variables are recomputed each run — this is a deliberate design choice, not a bug.

**Limitation:** Streamlit has a single-threaded execution model. Benchmark runs execute synchronously. For long benchmarks, the UI is blocked. This is acceptable for research; a production version would use async workers.

---

## NetworkX

**Why NetworkX?** Rich directed graph API, built-in VF2 implementation via `nx.is_isomorphic`, and native GML read/write. The `DiGraph` type supports attributes on both nodes and edges.

**Key usage:**

```python
import networkx as nx

# Graph construction
G = nx.DiGraph()
G.add_node("table_A", layer="SOR")
G.add_edge("table_A", "table_B")

# Local subgraph extraction (induced)
subgraph = G.subgraph(["table_A"] + list(G.successors("table_A")))

# VF2 isomorphism check
nx.is_isomorphic(subgraph_a, subgraph_b)

# Attribute-aware isomorphism
nx.is_isomorphic(subgraph_a, subgraph_b, node_match=lambda x, y: x == y)

# GML persistence
nx.write_gml(G, "scenario.gml")
G_loaded = nx.read_gml("scenario.gml")

# Copy a specific subgraph to a new graph object
subgraph_copy = G.subgraph(nodes).copy()

# Successors and predecessors
list(G.successors("node"))
list(G.predecessors("node"))
```

**GML format:** NetworkX serializes all node and edge attributes. Node `id` and `label` are automatically added. Edge `source` and `target` are automatically serialized. Round-trips (write → read) are lossless for standard types (str, int, float, bool).

---

## PyTorch

**Why PyTorch?** De facto standard for deep learning research. Dynamic computation graph (eager mode) allows inspection at any step. Strong community support. The `nn.Module` API provides clean model definition + parameter management.

**Key usage in Isomera:**

```python
import torch
import torch.nn as nn
import torch.nn.functional as F

# Parameter (learnable epsilon in GINLayer)
self.eps = nn.Parameter(torch.zeros(1))

# Linear layer
self.linear = nn.Linear(in_features, out_features)

# Loss
criterion = nn.BCEWithLogitsLoss()
loss = criterion(logits, labels.float())

# Optimizer
optimizer = torch.optim.Adam(model.parameters(), lr=0.01)

# No-grad inference
with torch.no_grad():
    output = model(x)

# Tensor operations
x = torch.ones((n_nodes, 1))           # feature matrix
edge_index = torch.tensor([[u, v]], dtype=torch.long).t().contiguous()
batch = torch.zeros(n_nodes, dtype=torch.long)
```

**Optional import pattern:**

```python
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
```

The GNN algorithm raises a clear error if torch is missing rather than crashing silently.

---

## PyTorch Geometric (PyG)

**Why PyG?** Provides the `Data` object (PyG's graph container) and graph-level pooling functions. The `Data` class bundles `x`, `edge_index`, and `batch` tensors in a standard format. `global_mean_pool` reduces per-node embeddings to a per-graph embedding efficiently.

**Key usage:**

```python
from torch_geometric.data import Data
from torch_geometric.nn import global_mean_pool

# Construct a graph data object
data = Data(
    x=torch.ones((n_nodes, 1)),          # node feature matrix
    edge_index=edge_index,                # shape [2, n_edges]
)
data.batch = torch.zeros(n_nodes, dtype=torch.long)  # batch assignment

# Global mean pool
h_G = global_mean_pool(node_embeddings, batch)  # shape [1, emb_size]
```

**Batching note:** PyG's `batch` tensor assigns each node to a graph index. When processing a single graph, all values are 0. When batching multiple graphs for training efficiency, PyG assigns sequential indices. Isomera trains in a mini-batch fashion during training but processes one graph at a time during inference.

---

## Pandas

**Why Pandas?** Standard tabular data tool for Python. Used for validation tables (ground truth comparison), metrics tables (per-algorithm rows), and CSV import/export.

**Key usage:**

```python
import pandas as pd

# Metrics table construction (from core/metrics.py)
df = pd.DataFrame(
    records,
    columns=["Algorithm", "TP", "FP", "FN", "TN", "Accuracy", ...]
)

# Validation CSV import (Tab 8)
df_validation = pd.read_csv(uploaded_file)

# DataFrames displayed with st.dataframe(df) or st.data_editor(df)
```

**DataFrame ↔ `st.data_editor`:** The validation workflow uses `st.data_editor` which returns a modified DataFrame with user edits applied. This edited DF is stored in `session_state["validated_df"]` for downstream use.

---

## Plotly

**Why Plotly?** Interactive charts (hover, zoom, pan) in Streamlit. `plotly.express` provides a terse API for common chart types.

**Key charts used:**

| Chart | Location | Data |
|---|---|---|
| Bar chart — Per-algorithm accuracy | Tab 4 (Benchmark) | Metric rows from benchmark loop |
| Bar chart — Execution time | Tab 4 | ET from each run |
| Scatter — SF vs SOR | Tab 4 | SF metric across scenario families |
| Grouped bars — Algorithm comparison | Tab 4 | Multi-metric per-algorithm comparison |

**Rendering:**

```python
import plotly.express as px

fig = px.bar(df, x="Algorithm", y="Accuracy", color="Algorithm",
             title="Accuracy by Algorithm", barmode="group")
st.plotly_chart(fig, use_container_width=True)
```

---

## Matplotlib

**Why Matplotlib?** NetworkX's native drawing engine. Used for static graph visualizations (Tab 1 and Tab 2).

**Key usage:**

```python
import matplotlib
matplotlib.use("Agg")              # non-interactive backend for Streamlit
import matplotlib.pyplot as plt

pos = nx.spring_layout(G)
nx.draw_networkx(G, pos, ...)
buf = io.BytesIO()
plt.savefig(buf, format="png")
st.image(buf.getvalue())
plt.close()
```

**Important:** `matplotlib.use("Agg")` must be called before importing `pyplot` to avoid display errors in headless environments (Streamlit server, Docker, CI).

---

## SQLAlchemy

**Why SQLAlchemy?** Wraps SQLite for session log storage. Enables SQL queries against log history without raw file parsing. SQLAlchemy 2.0's new-style API is used.

**Storage path:** `logs/` directory, SQLite file named after session timestamp.

**Key usage:**

```python
from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///logs/session.db")
with engine.connect() as conn:
    conn.execute(text("INSERT INTO logs VALUES (:ts, :event, :data)"),
                 {"ts": ..., "event": ..., "data": ...})
    conn.commit()
```

The JSONL log files in `logs/` are an alternative flat-file persistence path. Both persist the same event schema.

---

## Pickle (stdlib)

**Why pickle?** Standard Python serialization for PyTorch models. A `(SubgraphGNN, PairClassifier)` tuple is saved as a `.pkl` file, recoverable with `pickle.load`.

**Fallback unpickler:**

```python
class _FallbackUnpickler(pickle.Unpickler):
    """Remaps class paths that were saved with __main__ as the module."""
    def find_class(self, module, name):
        if module == "__main__" and name in ("SubgraphGNN", "PairClassifier", "GINLayer"):
            from core.algorithms.gnn_model import SubgraphGNN, PairClassifier, GINLayer
            return {"SubgraphGNN": SubgraphGNN, "PairClassifier": PairClassifier,
                    "GINLayer": GINLayer}[name]
        return super().find_class(module, name)
```

This is a critical piece: when a notebook trains and saves the model as `__main__.SubgraphGNN`, and the production server loads it as `core.algorithms.gnn_model.SubgraphGNN`, pickle's standard unpickler would fail with an `AttributeError`. The fallback unpickler intercepts the class lookup and returns the correct class.

**Security note:** Pickle is unsafe against untrusted sources (arbitrary code execution). In Isomera, `.pkl` files are only loaded from trusted local paths uploaded by authenticated users. Do not expose pickle loading to unauthenticated endpoints.

---

## Dependency Graph (Load Order)

```
streamlit
└── app/main.py (entry point)
    ├── core/lineage.py
    │   └── networkx
    ├── core/isomorphism.py
    │   ├── networkx
    │   └── core/algorithms/ (registry + all algorithms)
    │       ├── vf2.py (networkx)
    │       ├── node_match.py (networkx)
    │       └── gnn_pickle.py
    │           ├── torch (optional)
    │           ├── torch_geometric (optional)
    │           └── gnn_model.py (torch)
    ├── core/metrics.py
    │   └── pandas
    └── core/database.py
        └── sqlalchemy
```

Optional: `plotly`, `matplotlib` (visualization modules loaded on demand in UI).
