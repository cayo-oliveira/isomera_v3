# Batched Execution Probe

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenario: `graph_SOR16_D1_seed42`
- Rows: `36`
- CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120053_39950_604003000_batched_execution_probe/batched_execution_probe.csv`

This probe compares pairwise versus chunked inference and batch-size effects for GNN/GIN, VMamba-T and VMamba-Mesh-T.

## Summary Rows

| Model | Phase | Device | Train batch | Infer batch | Encoder batch | Batched inference | ET (s) | Jaccard | SF-Jaccard | TP/FP/FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GNN/GIN | train | cpu | 16 |  |  |  | 0.366408 |  |  |  |
| GNN/GIN | inference | cpu | 16 | 1 | 1 | False | 0.032680 | 0.012987 | 161.35 | 3/228/0 |
| GNN/GIN | inference | cpu | 16 | 4096 | 16 | True | 0.001548 | 0.012987 | 3407.16 | 3/228/0 |
| GNN/GIN | inference | cpu | 16 | 4096 | 64 | True | 0.001426 | 0.012987 | 3697.35 | 3/228/0 |
| GNN/GIN | train | mps | 16 |  |  |  | 0.206044 |  |  |  |
| GNN/GIN | inference | mps | 16 | 1 | 1 | False | 0.740520 | 0.012987 | 7.12 | 3/228/0 |
| GNN/GIN | inference | mps | 16 | 4096 | 16 | True | 0.043251 | 0.012987 | 121.91 | 3/228/0 |
| GNN/GIN | inference | mps | 16 | 4096 | 64 | True | 0.019623 | 0.012987 | 268.70 | 3/228/0 |
| VMamba-T | train | cpu | 16 |  |  |  | 0.099362 |  |  |  |
| VMamba-T | inference | cpu | 16 | 1 | 1 | False | 0.015277 | 0.200000 | 5315.14 | 3/12/0 |
| VMamba-T | inference | cpu | 16 | 1 | 16 | True | 0.011321 | 0.200000 | 7172.62 | 3/12/0 |
| VMamba-T | inference | cpu | 16 | 1 | 64 | True | 0.011149 | 0.200000 | 7283.00 | 3/12/0 |
| VMamba-T | inference | cpu | 16 | 4096 | 1 | True | 0.014602 | 0.200000 | 5560.90 | 3/12/0 |
| VMamba-T | inference | cpu | 16 | 4096 | 16 | True | 0.010651 | 0.200000 | 7623.76 | 3/12/0 |
| VMamba-T | inference | cpu | 16 | 4096 | 64 | True | 0.010784 | 0.200000 | 7529.99 | 3/12/0 |
| VMamba-T | train | mps | 16 |  |  |  | 0.635457 |  |  |  |
| VMamba-T | inference | mps | 16 | 1 | 1 | False | 0.189289 | 0.200000 | 428.97 | 3/12/0 |
| VMamba-T | inference | mps | 16 | 1 | 16 | True | 0.264027 | 0.200000 | 307.54 | 3/12/0 |
| VMamba-T | inference | mps | 16 | 1 | 64 | True | 0.057679 | 0.200000 | 1407.79 | 3/12/0 |
| VMamba-T | inference | mps | 16 | 4096 | 1 | True | 0.068799 | 0.200000 | 1180.26 | 3/12/0 |
| VMamba-T | inference | mps | 16 | 4096 | 16 | True | 0.039880 | 0.200000 | 2036.12 | 3/12/0 |
| VMamba-T | inference | mps | 16 | 4096 | 64 | True | 0.038670 | 0.200000 | 2099.83 | 3/12/0 |
| VMamba-Mesh-T | train | cpu | 16 |  |  |  | 0.107890 |  |  |  |
| VMamba-Mesh-T | inference | cpu | 16 | 1 | 1 | False | 0.017170 | 0.200000 | 4729.10 | 3/12/0 |
| VMamba-Mesh-T | inference | cpu | 16 | 1 | 16 | True | 0.012479 | 0.200000 | 6506.89 | 3/12/0 |
| VMamba-Mesh-T | inference | cpu | 16 | 1 | 64 | True | 0.012275 | 0.200000 | 6614.91 | 3/12/0 |
| VMamba-Mesh-T | inference | cpu | 16 | 4096 | 1 | True | 0.016161 | 0.200000 | 5024.47 | 3/12/0 |
| VMamba-Mesh-T | inference | cpu | 16 | 4096 | 16 | True | 0.011782 | 0.200000 | 6891.89 | 3/12/0 |
| VMamba-Mesh-T | inference | cpu | 16 | 4096 | 64 | True | 0.011858 | 0.200000 | 6847.75 | 3/12/0 |
| VMamba-Mesh-T | train | mps | 16 |  |  |  | 0.147542 |  |  |  |
| VMamba-Mesh-T | inference | mps | 16 | 1 | 1 | False | 0.073833 | 0.333333 | 1832.98 | 3/6/0 |
| VMamba-Mesh-T | inference | mps | 16 | 1 | 16 | True | 0.054770 | 0.333333 | 2470.92 | 3/6/0 |
| VMamba-Mesh-T | inference | mps | 16 | 1 | 64 | True | 0.049782 | 0.333333 | 2718.51 | 3/6/0 |
| VMamba-Mesh-T | inference | mps | 16 | 4096 | 1 | True | 0.065391 | 0.333333 | 2069.60 | 3/6/0 |
| VMamba-Mesh-T | inference | mps | 16 | 4096 | 16 | True | 0.042795 | 0.333333 | 3162.38 | 3/6/0 |
| VMamba-Mesh-T | inference | mps | 16 | 4096 | 64 | True | 0.040370 | 0.333333 | 3352.34 | 3/6/0 |
