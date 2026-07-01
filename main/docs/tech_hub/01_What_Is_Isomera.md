# 01 — What Is Isomera

> **Navigation:** [README](README.md) | [02 Data Flow](02_Data_Flow_and_State.md) | [03 UI Tabs](03_UI_Tabs_Guide.md) | [04 Core Modules](04_Core_Modules.md) | [05 Algorithms](05_Algorithms_and_Models.md) | [06 Libraries](06_Libraries_and_Stack.md) | [07 Pseudocode](07_Pseudocode_Reference.md) | [08 Graph Maps](08_Graph_Maps.md)

---

## What Isomera Is

**Isomera** is a Python-based software tool and reproducible benchmarking framework for **redundancy detection in Data Mesh lineage graphs**. It evaluates structural matching and learning-based detectors, and reports **SF-Jaccard** as the primary Success Frequency metric: a throughput-aware score that combines Jaccard quality with median execution time. Accuracy is still reported as a diagnostic because negative pairs dominate the benchmark.

The name combines *isomorphism* (structural equivalence of graphs) with *era* (the era of federated data architectures).

### One-sentence pitch

> "Isomera models each table as a node and each lineage dependency as an edge, then applies graph isomorphism algorithms and a GIN-based learned detector to identify structurally redundant table pipelines across Data Mesh domains."

---

## Why Isomera Exists: The Data Mesh Problem

### Data Mesh in 60 seconds

Data Mesh is a data architecture paradigm that **decentralizes data ownership** to business domains. Each domain owns and publishes its own **data products** with well-defined quality contracts. Four principles (Dehghani, 2020):

1. **Domain ownership** — product teams own their data pipelines end-to-end.
2. **Data as a product** — same engineering standards as software products: contracts, SLAs, versioning.
3. **Self-serve infrastructure** — platform team provides tooling; domain teams do not need data engineering expertise.
4. **Federated governance** — global policies enforced locally per domain.

### Why redundancy is a real problem in Data Mesh

When dozens of independent domains build autonomously, they frequently create equivalent pipelines without knowing it:

- **Domain A** builds a `sales_summary` SOT table from its SOR extracts.
- **Domain B** independently builds an identical pipeline, calling it `revenue_aggregate`.
- Both are structurally identical in the lineage graph. Neither team knows.

The result: duplicated storage, compute, and maintenance cost with zero additional value. In a centralized data lake this is visible. In a Data Mesh it is invisible until explicitly detected.

**Why names alone are not enough:** Tables across domains have different names by design. The redundancy lives in the **structure of the lineage pipeline**, not in the label of the table. That is why Isomera uses graph isomorphism detection.

---

## The Three Processing Layers: SOR / SOT / SPEC

The Isomera benchmark models three layers that mirror real Data Mesh deployments:

| Layer | Full name | Role |
|---|---|---|
| **SOR** | System of Record | Raw operational extracts. Ingestion layer, no transformations. Never removed. |
| **SOT** | System of Truth | Business rules, quality transformations. Middle tier. |
| **SPEC** | Specialized view | Denormalized views for downstream consumption (reports, ML, APIs). |

The data flow direction is always: `SOR → SOT → SPEC`. Edges in the lineage graph point from source to derived table.

**Why this layering matters for detection:** SOR tables are structural anchors. SOT and SPEC tables are where redundancy happens (two domains apply the same transformation to the same raw data). Detecting that two SOT subgraphs are isomorphic is a strong signal of pipeline duplication.

---

## Formal Graph Model

Let $G = (V, E)$ be a **directed lineage graph** where:

- $V$ = set of nodes (tables)
- $E \subseteq V \times V$ = set of directed edges (lineage dependencies)
- $(u, v) \in E$ means table $u$ feeds table $v$
- Each node carries attributes: `layer ∈ {SOR, SOT, SPEC}`, `domain_id`

### Local subgraph (the detection unit)

Isomera does **not** compare entire graphs. It extracts a **local neighborhood subgraph** for each node:

$$S_v = G\bigl[\{v\} \cup \operatorname{successors}(v)\bigr]$$

The anchor node plus all its direct successors. This subgraph captures the immediate transformation pattern of the table.

**Why local, not global?**
- Global graph edit distance (GED) is NP-hard.
- Redundancy patterns repeat at the local pipeline level.
- Subgraphs are small: efficient to compare and embed.

### Scenario families

Scenarios are parameterized by:

| Parameter | Values |
|---|---|
| SOR count (density) | 2, 4, 8, 16 |
| Domain count | 1, 2, 3, 4, 5 |

This gives 20 structural families. Graphs are stored as **GML** (Graph Modeling Language) files — plain-text, human-readable, natively supported by NetworkX. GML ensures reproducibility: anyone can re-run a benchmark from the `.gml` files.

---

## System Architecture

Isomera has a clean four-layer architecture:

```
┌───────────────────────────────────────────┐
│  Presentation & Orchestration Layer        │
│  ui/app.py — Streamlit tabs, state, logs  │
└────────────────────┬──────────────────────┘
                     │ calls
┌────────────────────▼──────────────────────┐
│  Core Domain Layer                         │
│  core/lineage.py   — graph construction   │
│  core/isomorphism.py — detection API      │
│  core/metrics.py   — ACC, ET, SF-Jaccard  │
│  core/database.py  — DB → graph adapter   │
└────────────────────┬──────────────────────┘
                     │ dispatches via registry
┌────────────────────▼──────────────────────┐
│  Algorithm Plug-in Layer                   │
│  core/algorithms/  — VF2, Node Match, GNN  │
│  (Protocol interface + registry pattern)   │
└────────────────────┬──────────────────────┘
                     │ persists
┌────────────────────▼──────────────────────┐
│  Artifact & Persistence Layer              │
│  data/architectures/  — .gml + .json      │
│  logs/                — .jsonl + .log     │
│  core/algorithms/pickle/ — .pkl models    │
└───────────────────────────────────────────┘
```

### Why this architecture is strong for research

- **Reproducibility**: every scenario graph, every label, every session is persisted.
- **Extensibility**: adding a new algorithm means implementing `predict_pairs(graph)` and calling `register_algorithm()`. Nothing else changes.
- **Comparability**: metrics always run against `initial_graph` — the immutable baseline. User removals never contaminate evaluation.
- **Explainability**: human validation is an explicit, auditable stage between prediction and action.

### Why Streamlit

Streamlit converts Python functions into interactive web apps with no HTML/JavaScript.

- **Primary reason**: the human-in-the-loop validation step requires interactive pair-by-pair decision making. Streamlit makes this trivial.
- **State**: `st.session_state` persists workflow state across reactive reruns without a backend.
- **Future roadmap**: the UI will be extended with generative AI (RAG + LLM) to explain in natural language why two subgraphs are redundant. Streamlit already has native chat components for this.
- **Rejected alternative**: Flask/FastAPI would require a separate frontend, increasing complexity with no research benefit.

### Why Python

- **Graph ecosystem**: NetworkX is the reference library for directed graphs in Python.
- **GNN ecosystem**: PyTorch + PyTorch Geometric are the dominant frameworks for graph neural networks in research.
- **Academic reproducibility**: Python scripts are the standard for benchmark pipelines in IEEE papers.
- **Prototyping speed**: fast iteration on algorithm design is essential in a PhD research workflow.

---

## Glossary

| Term | Plain English |
|---|---|
| **Lineage graph** | Directed graph where nodes are tables and edges mean "table A feeds table B". |
| **SOR** | System of Record — raw source table. |
| **SOT** | System of Truth — transformed/curated table. |
| **SPEC** | Specialized view — consumption-ready table. |
| **Isomorphic pair** | Two local subgraphs with the same structure (same shape and node mapping). |
| **Pair validation** | Human decision confirming or rejecting an algorithm's candidate pair. |
| **Ground truth** | Trusted label set used as the evaluation target (comes from TPC-DS mapping). |
| **TP / FP / FN / TN** | True positive / false positive / false negative / true negative (confusion matrix). |
| **ACC** | Accuracy: `(TP+TN) / (TP+TN+FP+FN)`. Only valid when all pairs are labeled. |
| **ET** | Execution time — average wall-clock time per algorithm run. |
| **SF** | Success Frequency: `(ACC × N_pairs) / ET` — throughput-like measure. |
| **Registry pattern** | A central map from algorithm name to implementation instance for decoupled dispatch. |
| **Pickle model path** | Loading a serialized `(SubgraphGNN, PairClassifier)` tuple from disk for GIN inference. |
| **GML** | Graph Modeling Language — plain-text format for storing graphs with attributes. |
| **WL test** | Weisfeiler-Lehman graph isomorphism test — iterative node label refinement algorithm. |
| **GIN** | Graph Isomorphism Network — GNN architecture with 1-WL expressive power. |
| **Subgraph embedding** | A fixed-size vector $\mathbf{h}_G \in \mathbb{R}^{64}$ representing a subgraph's structure. |

---

## Reading Order

### Short route (15–20 min, interview prep)

1. This file (01) — what and why
2. [02 Data Flow](02_Data_Flow_and_State.md) — end-to-end execution
3. [05 Algorithms](05_Algorithms_and_Models.md) — VF2, Node Match, GIN deep dive
4. [07 Pseudocode](07_Pseudocode_Reference.md) — exact algorithm flows

### Full route (complete technical depth)

1. **01** (this file) — context, architecture, glossary
2. **02** — execution flow, state model, artifact persistence
3. **03** — every UI tab: what it does, what it calls, what it stores
4. **04** — every module and function: what the code actually does
5. **05** — algorithms and models: VF2, Node Match, GIN/GNN in full detail
6. **06** — libraries and why each was chosen
7. **07** — pseudocode for every major process
8. **08** — relationship graphs showing call dependencies

### How to answer hard questions

- "Where is X computed?" → jump to **04** (modules) or **07** (pseudocode).
- "Is this algorithmic or model-based?" → jump to **05** (algorithms overview).
- "How does tab Y call core logic?" → jump to **03** (tabs) + **08** (graph maps).
- "What is the exact sequence?" → jump to **07** (pseudocode).
