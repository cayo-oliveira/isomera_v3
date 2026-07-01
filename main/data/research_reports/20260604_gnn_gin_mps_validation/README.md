# GIN/GNN CPU vs MPS Smoke Validation

This validates whether the native PyTorch GIN/GNN path can train and infer on Apple MPS. It is not an article-grade benchmark.

| requested | resolved | train_seconds | inference_seconds | jaccard | accuracy | predicted_pairs |
|---|---:|---:|---:|---:|---:|---:|
| cpu | cpu | 0.396448 | 0.010341 | 0.000000 | 0.969697 | 0 |
| mps | mps | 0.468614 | 0.243708 | 0.000000 | 0.969697 | 0 |

Notes:
- The implementation is native PyTorch GIN, not torch-geometric.
- MPS is enabled through `ISOMERA_ENABLE_ACCELERATOR=1` and `ISOMERA_GNN_DEVICE=mps`.
- Pickles are saved back on CPU for portable loading; inference moves them to the requested runtime device.
