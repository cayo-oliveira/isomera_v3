# Batched Execution Probe

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenario: `graph_SOR2_D1_seed42`
- Rows: `18`
- CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_114233_39656_043483000_batched_execution_probe/batched_execution_probe.csv`

This probe compares pairwise versus chunked inference and batch-size effects for GNN/GIN, VMamba-T and VMamba-Mesh-T.

## Summary Rows

| Model | Phase | Device | Train batch | Infer batch | Encoder batch | Batched inference | ET (s) | Jaccard | SF-Jaccard | TP/FP/FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GNN/GIN | train | cpu | 4 |  |  |  | 1.153768 |  |  |  |
| GNN/GIN | inference | cpu | 4 | 1 | 1 | False | 0.004098 | 0.066667 | 244.04 | 1/14/0 |
| GNN/GIN | inference | cpu | 4 | 16 | 4 | True | 0.000634 | 0.066667 | 1577.19 | 1/14/0 |
| GNN/GIN | inference | cpu | 4 | 16 | 16 | True | 0.000524 | 0.066667 | 1908.55 | 1/14/0 |
| VMamba-T | train | cpu | 4 |  |  |  | 0.060566 |  |  |  |
| VMamba-T | inference | cpu | 4 | 1 | 1 | False | 0.008539 | 1.000000 | 1756.55 | 1/0/0 |
| VMamba-T | inference | cpu | 4 | 1 | 4 | True | 0.007613 | 1.000000 | 1970.43 | 1/0/0 |
| VMamba-T | inference | cpu | 4 | 1 | 16 | True | 0.007297 | 1.000000 | 2055.73 | 1/0/0 |
| VMamba-T | inference | cpu | 4 | 16 | 1 | True | 0.008176 | 1.000000 | 1834.66 | 1/0/0 |
| VMamba-T | inference | cpu | 4 | 16 | 4 | True | 0.007401 | 1.000000 | 2026.87 | 1/0/0 |
| VMamba-T | inference | cpu | 4 | 16 | 16 | True | 0.007564 | 1.000000 | 1983.09 | 1/0/0 |
| VMamba-Mesh-T | train | cpu | 4 |  |  |  | 0.037046 |  |  |  |
| VMamba-Mesh-T | inference | cpu | 4 | 1 | 1 | False | 0.008114 | 1.000000 | 1848.64 | 1/0/0 |
| VMamba-Mesh-T | inference | cpu | 4 | 1 | 4 | True | 0.007559 | 1.000000 | 1984.38 | 1/0/0 |
| VMamba-Mesh-T | inference | cpu | 4 | 1 | 16 | True | 0.007300 | 1.000000 | 2054.78 | 1/0/0 |
| VMamba-Mesh-T | inference | cpu | 4 | 16 | 1 | True | 0.007858 | 1.000000 | 1908.77 | 1/0/0 |
| VMamba-Mesh-T | inference | cpu | 4 | 16 | 4 | True | 0.007407 | 1.000000 | 2025.13 | 1/0/0 |
| VMamba-Mesh-T | inference | cpu | 4 | 16 | 16 | True | 0.007475 | 1.000000 | 2006.62 | 1/0/0 |
