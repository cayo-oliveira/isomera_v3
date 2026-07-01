# CPU vs MPS Trainable VMamba Comparison

- CPU report: `20260604_001425_29426_563067000_vmamba_trainable_ablation`
- MPS report: `20260604_105532_38014_502849000_vmamba_trainable_ablation`
- Benchmark: `tpc_ds_genai_spec_v2`, 20 article scenarios, SPEC layer.
- Configuration: `article_cpu`, resolution 16, epochs 10, batch 16, negative ratio 16, Weighted BCE, learning rates 0.001 and 0.0005.

## Result

| execution_device   | algorithm     |   jaccard |   sf_jaccard |       ET |   accuracy |   tp |   fp |   fn |   tn |
|:-------------------|:--------------|----------:|-------------:|---------:|-----------:|-----:|-----:|-----:|-----:|
| CPU                | VMamba-T      |  0.481481 |      200.577 | 0.158292 |   0.818789 |  403 |  298 |  136 | 1558 |
| CPU                | VMamba-Mesh-T |  0.488268 |      202.394 | 0.167882 |   0.808768 |  437 |  356 |  102 | 1500 |
| MPS                | VMamba-T      |  0.472222 |      150.851 | 0.208802 |   0.82547  |  374 |  253 |  165 | 1603 |
| MPS                | VMamba-Mesh-T |  0.416138 |      143.671 | 0.219413 |   0.731106 |  459 |  564 |   80 | 1292 |

## Deltas: MPS minus CPU

| algorithm     |   jaccard_delta_mps_minus_cpu |   sf_jaccard_delta_mps_minus_cpu |   ET_delta_mps_minus_cpu |   accuracy_delta_mps_minus_cpu |
|:--------------|------------------------------:|---------------------------------:|-------------------------:|-------------------------------:|
| VMamba-T      |                   -0.00925926 |                         -49.7265 |                 0.05051  |                     0.00668058 |
| VMamba-Mesh-T |                   -0.0721304  |                         -58.7225 |                 0.051531 |                    -0.0776618  |

## Interpretation

MPS was validated as an active PyTorch backend in the Mac execution environment (`resolved_device=mps`, `mps_available=true`). The SPEC v2 MPS rerun did not improve aggregate SF-Jaccard relative to the previous CPU campaign. This is acceptable evidence: device changes mainly affect execution time and may alter stochastic training numerics, but they do not change the Jaccard/SF-Jaccard definitions. For the article, the MPS run should be reported as a device validation and not as the best result unless a later hyperparameter campaign improves the metrics.

Deterministic baselines such as VF2, Node Match, Vanilla VMamba adapter and VMamba-Mesh adapter are device-independent in this implementation. They remain CPU/non-tensor baselines in the combined report. GNN rows are read from the existing exported benchmark evidence unless their own training pipeline is rerun separately with a torch device contract.
