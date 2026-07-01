# 05 — Algorithms and Models

> **Navigation:** [README](README.md) | [01 What Is Isomera](01_What_Is_Isomera.md) | [02 Data Flow](02_Data_Flow_and_State.md) | [03 UI Tabs](03_UI_Tabs_Guide.md) | [04 Core Modules](04_Core_Modules.md) | [06 Libraries](06_Libraries_and_Stack.md) | [07 Pseudocode](07_Pseudocode_Reference.md) | [08 Graph Maps](08_Graph_Maps.md)

---

## Algorithms, One Interface

All algorithms implement the same contract:

```python
class IsomorphismAlgorithm(Protocol):
    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]: ...
```

Given a lineage graph, return a list of node pairs predicted to be structurally redundant. The registry dispatches by name. The UI and metrics pipeline never import algorithm classes directly.

| Algorithm | Type | Training | Deterministic | Key file |
|---|---|---|---|---|
| **VF2** | Exact matching | None | Yes | `core/algorithms/vf2.py` |
| **Node Match (Custom)** | Matching + attribute filter | None | Yes | `core/algorithms/node_match.py` |
| **GIN/GNN (Pickle)** | Learned inference | Scenario-specific | No (probabilistic) | `core/algorithms/gnn_pickle.py` + `gnn_model.py` |
| **VMamba-Mesh Isomera adapter** | Lineage-aware pickle adapter | Scenario-specific threshold calibration | Yes for fixed config | `core/algorithms/vmamba_mesh.py` routed through `gnn_pickle.py` |

---

## Key Distinction: Algorithm vs Model vs Function

When asked "what did you implement?", separate these three levels:

1. **Functions** — code units that perform a step (e.g., `_subgraphs_by_successors`, `graph_to_pyg_data`).
2. **Algorithms** — decision logic implementations for pair detection (VF2, Node Match, GIN).
3. **Model** — a trained parameterized PyTorch object used by the GIN inference path (`SubgraphGNN`, `PairClassifier`).

VMamba-Mesh currently enters Isomera as a model object with `predict_pairs(graph)`. It is routed through the same pickle adapter as GNN models, but its metadata must declare:

```json
{
  "pickle_module": "core.algorithms.vmamba_mesh",
  "model_family_name": "VMamba-Mesh Isomera adapter"
}
```

This avoids incorrectly loading it as a `(SubgraphGNN, PairClassifier)` tuple.

---

## Algorithm 1: VF2 — Exact Structural Isomorphism

### What VF2 does

VF2 (Vento-Foggia, 2nd version) searches for a node-to-node bijection $f: V(G_1) \to V(G_2)$ such that:
$$(u, v) \in E(G_1) \iff (f(u), f(v)) \in E(G_2)$$

If such a mapping exists, the graphs are isomorphic. In Isomera, VF2 is applied locally: it tests whether two **local subgraphs** (anchor + successors) are isomorphic.

NetworkX provides `nx.is_isomorphic()` which implements VF2 under the hood.

### Exact implementation

```python
# core/algorithms/vf2.py

def _subgraphs_by_successors(graph: nx.DiGraph) -> list[tuple[str, nx.DiGraph]]:
    subgraphs = []
    for node in graph.nodes:
        neighbors = list(graph.successors(node))
        subgraph = graph.subgraph([node] + neighbors)  # induced subgraph
        subgraphs.append((node, subgraph))
    return subgraphs

class VF2Algorithm(IsomorphismAlgorithm):
    name = "VF2"

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        pairs = []
        subgraphs = _subgraphs_by_successors(graph)
        for i in range(len(subgraphs)):
            for j in range(i + 1, len(subgraphs)):
                node_a, sub_a = subgraphs[i]
                node_b, sub_b = subgraphs[j]
                if nx.is_isomorphic(sub_a, sub_b):  # no node attribute check
                    pairs.append((node_a, node_b))
        return pairs
```

### Complexity

$O(n^2)$ calls to `is_isomorphic`, where $n$ is the number of nodes. Each call has a cost that depends on subgraph size. As SOR count increases, subgraphs grow and the combinatorial cost compounds.

### Strengths and limitations

**Strengths:** Deterministic. No hyperparameters. Fully explainable. Zero training cost.

**Limitations:**
- Does not use node attributes: only topology matters.
- Quadratic number of comparisons.
- Structural equivalence does not imply semantic equivalence (can produce FP from template reuse).

---

## Algorithm 2: Node Match (Custom) — Attribute-Aware Isomorphism

### What it adds over VF2

Node Match uses the same local subgraph strategy as VF2, but passes a `node_match` callback to `nx.is_isomorphic`:

```python
# core/algorithms/node_match.py

class NodeMatchAlgorithm(IsomorphismAlgorithm):
    name = "Node Match (Custom)"

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        pairs = []
        subgraphs = _subgraphs_by_successors(graph)
        for i in range(len(subgraphs)):
            for j in range(i + 1, len(subgraphs)):
                node_a, sub_a = subgraphs[i]
                node_b, sub_b = subgraphs[j]
                if nx.is_isomorphic(sub_a, sub_b,
                                    node_match=lambda x, y: x == y):
                    pairs.append((node_a, node_b))
        return pairs
```

The `node_match=lambda x, y: x == y` callback requires that **node attribute dictionaries be equal** in addition to topological equivalence.

### Critical caveat

In the benchmark graphs generated by `generate_random_lineage_graph()`, node attributes are minimal (node labels are strings; attribute dicts may be sparse). When node attributes are empty or default, `lambda x, y: x == y` evaluates to `{} == {}` which is always True — making Node Match behave identically to VF2.

This is why VF2 and Node Match produce similar results in many experiments. The value of Node Match becomes apparent when node attributes are explicitly populated (e.g., with layer type as a feature).

### Strengths and limitations

**Strengths:** More precise when attributes exist. Same simplicity as VF2.

**Limitations:** Same quadratic cost as VF2. Result depends on attribute richness.

---

## Algorithm 3: GIN/GNN (Pickle) — Learned Inference

### Motivation: from matching to amortized learning

Matching algorithms are **combinatorial**: for each candidate pair, they search for a valid node mapping. As SOR count increases and domains grow, the number of pairs increases combinatorially and near-duplicate structures become hard to separate.

The GIN detector uses **amortization**: compute an embedding $\mathbf{h}_G \in \mathbb{R}^{64}$ once per subgraph, then classify all pairs using a single forward pass through a small MLP. This makes the approach scale better to large scenario families.

### Isomera Staged Hyperparameter Protocol

The recommended Isomera protocol is not an exhaustive grid over every possible hyperparameter. A full grid quickly becomes computationally wasteful because the benchmark contains multiple scenarios, each scenario has its own supervised validation dataset, and each GNN cluster may contain scenario-specific pickle artifacts.

The preferred protocol is staged and can be used for articles, internal benchmarks, or any reproducible model-selection experiment. Users can still bypass it and train a single manual configuration when they need full manual control.

| Stage | Scope | Trainings | Decision |
|---|---:|---:|---|
| `screening_5_scenarios` | 3 benchmarks x 5 representative scenarios x 108 configs | 1620 | Select top 5 configs per benchmark using SF-Jaccard. |
| `full_validation_20_scenarios` | 3 benchmarks x 20 scenarios x top 5 configs | 300 | Validate selected configs on complete scenario coverage. |
| `benchmark_final` | Best configs vs VF2, Node Match, GNN TPC-DS v1, GNN GenAI v1, GNN GenAI v2 | 0 additional trainings | Report detector-family, per-scenario, and pickle-routing metrics. |

The reduced grid has 108 configurations:

| Parameter | Values | Count |
|---|---|---:|
| Training strategy | Weighted BCE; Focal Loss; Hard Negatives | 3 |
| Learning rate | 0.001; 0.005; 0.010 | 3 |
| Hidden channels | 16; 32 | 2 |
| Dropout | 0.0; 0.1 | 2 |
| Inference threshold | 0.4; 0.5; 0.6 | 3 |

Total planned trainings before the final benchmark:

```text
screening = 3 * 5 * 108 = 1620
full_validation = 3 * 20 * 5 = 300
total = 1920 trainings
```

This is methodologically stronger than running a small arbitrary comparison and computationally more realistic than attempting hundreds of thousands of trainings. The report must state that this is a staged model-selection protocol, not an exhaustive search.

### Imbalance strategies used in article experiments

Duplicate pairs are rare. Accuracy can therefore look high even when the detector fails to find duplicates. The article should use SF-Jaccard as the primary metric and keep accuracy as a diagnostic metric.

| Strategy | Technical function | Formula | Interpretation |
|---|---|---|---|
| Weighted BCE | `torch.nn.BCEWithLogitsLoss(pos_weight)` | $L = -[w_p y \log(\sigma(z)) + (1-y)\log(1-\sigma(z))]$ | Keeps all validated pairs and increases the cost of missing rare duplicate pairs. |
| Focal Loss | custom sigmoid focal loss | $FL(p_t) = -\alpha(1-p_t)^\gamma \log(p_t)$ | Reduces easy-example influence and focuses gradient on hard or misclassified pairs. |
| Hard Negative Mining | structural hard-negative sampler + BCE | $score = |nodes_a-nodes_b| + |edges_a-edges_b|$ | Keeps non-duplicate pairs that look structurally similar to positives. |

### Theoretical foundation: Weisfeiler-Lehman test and GIN

The **Weisfeiler-Lehman (WL) 1-dim test** is a classical algorithm for graph isomorphism:
1. Assign equal initial labels to all nodes.
2. At each iteration, each node gets a new label encoding its current label and the **multiset** of neighbor labels.
3. Declare graphs non-isomorphic when their multiset histograms diverge.

**Why standard GNNs fall short:** GNNs using mean or max aggregation cannot distinguish cases that WL distinguishes. Example: a node with 2 identical neighbors and a node with 4 identical neighbors produce the same result under mean pooling (both average to the neighbor value) — but they are structurally different.

**GIN's insight:** Use **sum** aggregation (not mean/max) and an **injective MLP** as the update function. Sum preserves the full neighbor multiset. This makes GIN as expressive as 1-WL.

The GIN update equation:
$$\mathbf{h}_v^{(k)} = \mathrm{MLP}^{(k)}\!\left((1+\epsilon^{(k)})\,\mathbf{h}_v^{(k-1)} + \sum_{u\in\mathcal{N}(v)} \mathbf{h}_u^{(k-1)}\right)$$

- $\epsilon^{(k)}$: learnable scalar that weights the self-loop contribution.
- Sum: preserves neighbor multiset cardinality.
- MLP: injective function (theoretically can distinguish all distinct inputs).

Graph-level readout using mean pooling over final node embeddings:
$$\mathbf{h}_G = \frac{1}{|V(G)|}\sum_{v \in V(G)} \mathbf{h}_v^{(K)}$$

**Note on readout:** GIN's original paper uses sum readout for maximum expressivity. Isomera uses mean pooling because subgraphs have varying numbers of nodes — sum readout would make the pooled vector scale with graph size, making embeddings incomparable across subgraphs of different sizes.

---

## GNN Model Classes (gnn_model.py)

### Visual mapping used in the paper

The current public figure below summarizes the packaged trainable decision path used by the app and by the final report. It should be treated as the technical contract for the GNN explanation in Help and in the IEEE SMC paper.

![VMamba-Mesh trainable decision pipeline](../presentations/vmamba_mesh_assets/final_paper_figures/trainable_decision_pipeline.png)

The important bridge is:

| Isomera object | GNN object | Meaning |
|---|---|---|
| PostgreSQL table or GML node | graph node `v` | one table/data product in SOR, SOT, or SPEC |
| lineage dependency | directed edge `(u, v)` | table `v` depends on upstream table `u` |
| candidate duplicate pair | pair `(G_a, G_b)` | two local upstream lineage subgraphs compared by the model |
| node feature matrix `x` | `ones(|V|, 1)` today | structural-only input; no semantic text features yet |
| edge table / adjacency matrix | `edge_index` | directed graph connectivity consumed by GIN |
| duplicate validation table | target `y ∈ {0,1}` | supervised ground truth from human/GenAI validation |
| model artifact | `.pkl` route | trained `(SubgraphGNN, PairClassifier)` for a scenario/family |

Current configurable options exposed in Isomera:

| UI option | Internal implementation | What it changes |
|---|---|---|
| Activation | `ReLU` in hidden layers | Non-linear transformation after GIN/MLP layers |
| Loss: Standard BCE | `BCEWithLogitsLoss` | Binary logit classification without explicit class weighting |
| Loss: Weighted BCE | `BCEWithLogitsLoss(pos_weight=...)` | Penalizes missed rare duplicate pairs more strongly |
| Loss: Focal Loss | focal loss over sigmoid probability | Focuses learning on hard or misclassified examples |
| Optimizer | `Adam` | Adaptive gradient update for GIN and pair-classifier parameters |
| Output threshold | `sigmoid(logit) >= τ` | Converts probability into duplicate/non-duplicate decision |
| Balancing | negative sampling / hard negatives | Controls how many non-duplicate examples are shown during training |

These parameters are not cosmetic. They control how the validated lineage pairs become a trained detector family. For example, Weighted BCE is useful because most candidate pairs are non-duplicates; without balancing, a model can look accurate by predicting zero for nearly everything.

### `GINLayer` — single GIN layer

```python
class GINLayer(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.eps = nn.Parameter(torch.zeros(1))  # trainable epsilon
        self.mlp = nn.Sequential(
            nn.Linear(in_channels, out_channels),
            nn.ReLU(),
            nn.Linear(out_channels, out_channels),
        )

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        row, col = edge_index          # edge: row → col
        agg = torch.zeros_like(x)
        agg.index_add_(0, row, x[col]) # sum neighbor messages
        out = self.mlp((1 + self.eps) * x + agg)
        return out
```

**Line-by-line explanation:**
- `row, col = edge_index`: for each edge, `row` is the receiver and `col` is the sender.
- `agg.index_add_(0, row, x[col])`: for each edge `col→row`, adds embedding of `col` to `row`'s accumulator. This is the sum aggregation.
- `(1 + self.eps) * x + agg`: combines self-loop (weighted by $1+\epsilon$) with aggregated neighbor sum.
- `self.mlp(...)`: two-layer MLP with ReLU produces the new embedding.

### `SubgraphGNN` — 2-layer GIN encoder

```python
class SubgraphGNN(nn.Module):
    def __init__(self, in_channels=1, hidden_channels=64, out_channels=64):
        super().__init__()
        self.gin1 = GINLayer(in_channels, hidden_channels)   # 1 → 64
        self.gin2 = GINLayer(hidden_channels, out_channels)  # 64 → 64

    def forward(self, x, edge_index, batch):
        x = self.gin1(x, edge_index)
        x = F.relu(x)
        x = self.gin2(x, edge_index)
        return global_mean_pool(x, batch)  # h_G ∈ R^64
```

**Architecture:** input dim 1 → GIN(64) → ReLU → GIN(64) → mean pool → output $\mathbf{h}_G \in \mathbb{R}^{64}$.

**Why 2 layers?** 2-hop neighborhood coverage is sufficient for local subgraphs (anchor + direct successors). More layers would capture beyond the subgraph boundary and risk over-smoothing.

**Why input dim 1?** Structural-only configuration: every node gets a constant scalar feature `x = 1`. The model learns solely from connectivity patterns. This is a deliberate lower bound — adding semantic features (layer type, column names) is a planned improvement.

### `PairClassifier` — pair scoring head

```python
class PairClassifier(nn.Module):
    def __init__(self, emb_size=64):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(emb_size * 2, 128),  # [h_Su || h_Sv] ∈ R^128
            nn.ReLU(),
            nn.Linear(128, 1),              # logit z_uv
        )

    def forward(self, emb1, emb2):
        emb1 = emb1.view(1, -1)
        emb2 = emb2.view(1, -1)
        x = torch.cat([emb1, emb2], dim=1)  # concatenate embeddings
        return self.fc(x).squeeze(1)         # scalar logit
```

The prediction: $p_{uv} = \sigma(z_{uv})$ where $z_{uv} = \mathrm{MLP}([\mathbf{h}_{S_u} \| \mathbf{h}_{S_v}])$.

**Why concatenation?** Concatenation is the simplest operation that gives the classifier access to both embeddings and their joint signal. Alternatives (difference, product, cosine similarity) are possible but concatenation + MLP is the most expressive.

---

## Hyperparameters — Complete Reference Table

| Hyperparameter | Value | Where defined | Rationale |
|---|---|---|---|
| `in_channels` | 1 | `SubgraphGNN.__init__` | Structural-only: constant scalar per node |
| `hidden_channels` | 64 | `SubgraphGNN.__init__` | Compact capacity; low runtime |
| `out_channels` | 64 | `SubgraphGNN.__init__` | Embedding dimension |
| GIN layers K | 2 | `SubgraphGNN.__init__` | 2-hop coverage; avoids over-smoothing |
| `emb_size` | 64 | `PairClassifier.__init__` | Matches out_channels |
| Pair MLP hidden | 128 | `PairClassifier.fc` | 2× input dim (128); standard practice |
| Epochs E | 10 | Training script | Fast; adequate for scenario-specific fitting |
| Learning rate η | 0.01 | Adam | Stable default, no tuning needed |
| Negative ratio r | 3 | Dataset construction | 3:1 neg:pos; controls class imbalance |
| Max sampling attempts | 5000 | Dataset construction | Prevents infinite loop in sparse scenarios |
| Training threshold | 0.6 | Monitoring only | Used to report training accuracy; not in the loss |
| **Inference threshold τ** | **0.3** | `gnn_pickle.py` | **Favors recall; governance workflows can filter** |
| Loss function | BCE | `BCEWithLogitsLoss` | Standard binary classification |
| Optimizer | Adam | Training script | Adaptive, robust to variable batch sizes |
| Edge filter | `numel() > 0` | Dataset + inference | Remove degenerate subgraphs with no edges |

### The dual threshold explained (important for presentation)

The training threshold (0.6) and inference threshold (0.3) differ intentionally:
- **0.6 during training:** monitors convergence on a stricter criterion. The model is trained with BCE loss directly — this threshold is only for logging accuracy.
- **0.3 during inference:** permissive to favor recall. In a governance workflow, it is better to produce a larger candidate set for human review (some FP acceptable) than to miss redundant tables (FN means the problem persists undetected).

The inference threshold is a configurable operating point: organizations with high review capacity can lower it (more candidates, higher recall); with low capacity, raise it (fewer candidates, higher precision).

### Why scenario-specific training (not a global model)

Preliminary experiments showed that a single global model trained on all scenarios had very low accuracy. The reason: **distribution shift** between scenario families. A graph with SOR=2 has small, sparse local subgraphs. A graph with SOR=16 has large, dense ones. The GIN embedding space learned for one regime does not transfer cleanly to the other.

Scenario-specific training is more stable within each regime. The trade-off is storage and compute: one `.pkl` file per scenario. This is acceptable for a research benchmark.

---

## GNN Inference Pipeline (gnn_pickle.py)

The `GNNPickleAlgorithm.predict_pairs` method loads the pickle and runs inference. The full tuple-based path:

```python
# Step 1: load model
with path.open("rb") as handle:
    gnn, clf = _FallbackUnpickler(handle).load()

gnn.eval(); clf.eval()

# Step 2: extract local subgraphs
def extract_subgraphs(G):
    return {node: G.subgraph([node] + list(G.successors(node))).copy()
            for node in G.nodes}

# Step 3: convert to PyG Data
def graph_to_pyg_data(G_nx):
    mapping = {n: i for i, n in enumerate(G_nx.nodes)}
    edge_index = torch.tensor(
        [[mapping[u], mapping[v]] for u, v in G_nx.edges]
    ).t().contiguous()
    x = torch.ones((len(G_nx.nodes), 1))          # constant feature
    return Data(x=x, edge_index=edge_index)

# Step 4: score all pairs
subgraphs = extract_subgraphs(graph)
for u, v in combinations(subgraphs.keys(), 2):
    g1 = graph_to_pyg_data(subgraphs[u])
    g2 = graph_to_pyg_data(subgraphs[v])
    if g1.edge_index.numel() == 0 or g2.edge_index.numel() == 0:
        continue                                   # skip degenerate subgraphs
    # batch tensor: all nodes belong to the same graph
    g1.batch = torch.zeros(g1.num_nodes, dtype=torch.long)
    g2.batch = torch.zeros(g2.num_nodes, dtype=torch.long)
    with torch.no_grad():
        emb1 = gnn(g1.x, g1.edge_index, g1.batch)
        emb2 = gnn(g2.x, g2.edge_index, g2.batch)
        score = torch.sigmoid(clf(emb1, emb2))
    if score.item() >= 0.3:
        pairs.append((u, v))
```

### Supported pickle payload formats

The adapter handles four payload types, from most to least common:

| Format | Detection | Behavior |
|---|---|---|
| `tuple (gnn, clf)` | `isinstance(obj, tuple)` | Full neural inference (described above) |
| Object with `predict_pairs` | `hasattr(obj, "predict_pairs")` | Delegates directly |
| `dict` with `"pairs"` key | `isinstance(obj, dict)` | Returns stored pairs |
| `list` | `isinstance(obj, list)` | Returns list directly |

The fallback unpickler (`_FallbackUnpickler`) handles the common case where the pickle was saved with classes defined in `__main__` (e.g., from a notebook) and needs to be loaded in a module context.

## VMamba-Mesh Adapter Pipeline

The first VMamba-Mesh implementation is intentionally benchmark-compatible before it is a full neural VMamba backbone. It converts the VMamba-Mesh design into a deterministic adapter that can be evaluated against the same ground truth as VF2, Node Match and GNN clusters.

```text
validated scenario graph
  -> CanonSort node order
  -> local context signatures
  -> DiagFP/schema-token similarity
  -> HierInit upstream/downstream signature similarity
  -> SparseGate edge-density similarity
  -> calibrated duplicate threshold
  -> predict_pairs(graph)
```

The adapter is useful for two reasons:

- It lets the benchmark and report pipeline test VMamba-Mesh routing immediately.
- It defines the input/output contract that the future neural VMamba-Mesh checkpoint must preserve.

It should not be described as the final VMamba selective-scan model. The article wording should distinguish:

- **VMamba-Mesh adapter**: current reproducible `.pkl` exported by Study Lab.
- **Full neural VMamba-Mesh**: future implementation using VMamba/SS2D internals and ablation over CanonSort, DiagFP, HierInit and SparseGate.

---

## Comparison Summary: When to Use Which Algorithm

| Scenario | Best algorithm | Reason |
|---|---|---|
| SOR=2 or SOR=4, any domain count | Node Match or VF2 | Sparse structure; GIN lacks sufficient signal |
| SOR=8, SOR=16 | GIN (if .pkl available) | Rich structure; learned embeddings capture repeated patterns better |
| Runtime is critical | VF2 or Node Match | GIN is ~7.5× slower at SOR=16 |
| No training data available | VF2 or Node Match | GIN requires labeled pairs for training |
| Large-scale production | GIN (with optimizations) | Amortized embedding beats combinatorial search at scale |
| Strict determinism required | VF2 | Fully deterministic; no stochastic elements |
