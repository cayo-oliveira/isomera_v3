# 11 — Study Lab: VMamba and VMamba-Mesh

Study Lab is the learning and prototyping workspace for model internals. It is intentionally separate from `Scenario Studio`, `Model Lab`, and `Benchmark & Examples`.

## Purpose

Study Lab answers four questions:

- What does VMamba do at a code-architecture level?
- How does SS2D turn a 2D image into scan routes and context?
- Why is a plain VMamba backbone not enough for Data Mesh lineage graphs?
- Where exactly will Isomera change VMamba to create VMamba-Mesh?
- How can a VMamba-Mesh candidate be trained on Isomera scenarios and exported as a benchmarkable `.pkl`?

## Current Scope

Study Lab now has two levels:

1. **Official VMamba runtime study**: optional clone/update of the public VMamba repository for reading and source-level experiments.
2. **Isomera VMamba-Mesh adapter**: a deterministic benchmarkable `.pkl` that follows the same Isomera model contract as the existing GNN pickles.

The adapter is not yet the final neural VMamba-Mesh backbone. It is the first safe bridge between the VMamba-Mesh design and the existing benchmark engine.

The current module provides:

- VMamba concept cards with pseudocode for patch embedding, VSS blocks, SS2D cross scan, and selective scan.
- A synthetic SOR/SOT/SPEC lineage graph similar to Isomera benchmark scenarios.
- A lineage image heatmap generated from the graph.
- A SS2D-style context heatmap showing how memory propagates across scan routes.
- Interactive controls for scan route, memory decay, input gain, CanonSort, DiagFP, and SparseGate.
- A VMamba-Mesh change inspector explaining what changes, where it changes, why it changes, and how to test it.
- An optional official VMamba runtime installer/checker.
- A VMamba-Mesh adapter trainer that reads a benchmark GML and its validated positive pairs.
- Automatic `.pkl` and metadata export.
- Registration in `Benchmark & Examples` for comparison with VF2, Node Match and GNN clusters.
- A Study Report package with Markdown, TEX, JSON manifest, ZIP and optional PDF.

## Why the Runtime Is Optional

The public VMamba implementation relies on the vision backbone, PyTorch tensors, configuration files, and optimized selective-scan kernels. Loading this stack inside the Streamlit UI before the model is integrated would make Isomera harder to open and debug.

Therefore the UI separates installation from benchmarking:

- `Official Runtime`: clone/update VMamba when the user wants to inspect or run the original code.
- `Train Adapter`: train the Isomera-compatible VMamba-Mesh adapter without modifying the official VMamba repository.

This prevents the app from becoming unusable if a CUDA/selective-scan dependency is missing.

## Executable Concept Simulation

The simulation keeps the concepts needed for learning:

```text
lineage graph
  -> canonical node order
  -> adjacency-like image
  -> cross scan routes
  -> selective memory update
  -> context intensity map
```

This lets the user change a parameter and immediately see how the representation changes.

## VMamba-Mesh Adapter Contract

The first operational model is saved as a pickle object with this public contract:

```python
model.predict_pairs(graph: networkx.DiGraph) -> list[tuple[str, str]]
```

The benchmark engine loads it through:

```text
pickle_module = core.algorithms.vmamba_mesh
algorithm = GIN/GNN (Pickle)
```

This means it can be compared with:

- VF2.
- Node Match.
- GNN TPC-DS v1 cluster.
- GNN GenAI clusters.
- Future VMamba-Mesh neural checkpoints.

The current adapter uses canonical lineage features inspired by the planned VMamba-Mesh input contract:

| Feature family | What it captures |
|---|---|
| CanonSort | Stable SOR/SOT/SPEC node ordering |
| DiagFP | Schema/table identity on the matrix diagonal |
| HierInit | Similarity between upstream and downstream context signatures |
| SparseGate | Similarity of sparse edge density |
| Layer/domain signatures | Whether two anchors live in comparable semantic regions |

The trainer calibrates a decision threshold over the validated duplicate-pair table and sampled negatives. It writes the selected threshold and calibration metrics to metadata.

## Training Flow

```text
benchmark GML + validated pairs
  -> VMambaMeshConfig
  -> lineage feature extraction
  -> threshold calibration
  -> VMambaMeshPickle
  -> metadata JSON
  -> benchmark manifest registration
  -> Study Report package
```

The `.pkl` is saved under:

```text
main/data/architectures/<benchmark>/models/vmamba_mesh/
```

The metadata JSON contains:

- `model_family_name = VMamba-Mesh Isomera adapter`
- `pickle_module = core.algorithms.vmamba_mesh`
- source benchmark and scenario
- graph path and label path
- hyperparameters
- positive/negative pair counts
- selected threshold
- calibration Jaccard, accuracy, precision and recall

## Benchmark Comparison

After training, open `Benchmark & Examples`, choose the same benchmark, and include `VMamba-Mesh Isomera adapter` in the model selection. The routing table must show the VMamba-Mesh `.pkl` and its module:

```text
core.algorithms.vmamba_mesh
```

If the module is missing, the benchmark would try to load the object as a GNN tuple. Version `2.4.0` fixes that by carrying `pickle_module` through model routing and best-of-candidate selection.

## VMamba Concepts Shown

### Patch Embedding

Original role:

```python
x = patch_embed(image)
```

VMamba-Mesh change:

```python
x = patch_embed(lineage_tensor)
```

The input is no longer a natural image. It is a structured tensor derived from a lineage pair.

### VSS Block

Original role:

```python
residual = x
x = norm(x)
x = ss2d(x)
x = residual + drop_path(x)
x = x + mlp(norm2(x))
```

VMamba-Mesh keeps this structure. The main intervention happens inside the input contract and SS2D.

### SS2D

Original role:

```python
routes = cross_scan(x)
routes = selective_scan(routes)
x = cross_merge(routes)
```

VMamba-Mesh changes the scan behavior:

- `HierInit`: downstream layer states are initialized from upstream layer states.
- `SparseGate`: empty lineage cells decay faster than active lineage cells.

## VMamba-Mesh Changes

| Change | Where | Why |
|---|---|---|
| CanonSort | Before patch embedding | Stabilizes node order so equivalent subgraphs produce comparable images |
| Block SOR/SOT/SPEC encoding | Graph-to-image encoder | Makes lineage layers visible to the visual model |
| Adaptive resolution | Graph-to-image encoder | Avoids truncating larger SOR16 neighborhoods |
| DiagFP | Matrix diagonal | Adds schema/table identity where adjacency is normally unused |
| HierInit | SS2D state initialization | Propagates memory according to SOR -> SOT -> SPEC causality |
| SparseGate | Selective scan step gate | Reduces memory propagation through mostly-empty sparse cells |

## Implementation Roadmap

The real implementation should be added in stages:

1. `canon_sort.py`: deterministic lineage ordering.
2. `mesh_image_encoder.py`: pair tensor with graph A, graph B, difference, layer masks, and diagonal fingerprint.
3. `schema_fingerprint.py`: stable schema/table fingerprint.
4. `vmamba_mesh_ss2d.py`: HierInit and SparseGate.
5. `train_vmamba_mesh.py`: train MLP/CNN/VMamba/VMamba-Mesh on the same split.
6. `benchmark_vmamba_mesh.py`: export Jaccard, SF-Jaccard, ET, precision, recall, F1, and ablation tables.

## Evidence Status

The current measured evidence comes from local notebooks:

| Model | Jaccard | Accuracy | Recall | Precision | False positives |
|---|---:|---:|---:|---:|---:|
| MLP | 0.1373 | 0.9845 | 0.4667 | 0.1628 | 72 |
| CNN | 0.2812 | 0.9959 | 0.3000 | 0.8182 | 2 |

These are not VMamba-Mesh results. They show that visual encodings are useful and motivate the next implementation.

## Article Rule

Until the full neural VMamba-Mesh implementation and ablation are executed, write:

```text
VMamba-Mesh adapter results provide the first benchmark-compatible operational evidence.
CNN/MLP notebook evidence motivates the visual lineage representation.
```

Do not write:

```text
The final neural VMamba-Mesh improves Jaccard.
```

That stronger claim requires measured full-backbone experiments with ablations over CanonSort, DiagFP, HierInit and SparseGate.
