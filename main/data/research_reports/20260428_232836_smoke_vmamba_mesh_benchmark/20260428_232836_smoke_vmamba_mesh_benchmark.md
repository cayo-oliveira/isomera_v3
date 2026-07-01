# Smoke VMamba-Mesh Benchmark Report

This smoke report validates that the VMamba-Mesh adapter can be loaded by the existing benchmark pickle path and compared with VF2 and Node Match on the same scenario.

- Benchmark: `smoke_operational`
- Scenario: `graph_SOR2_D1_seed42`
- Pickle: `main/data/architectures/smoke_operational/models/vmamba_mesh/VMambaMesh_graph_SOR2_D1_seed42.pkl`
- Module: `core.algorithms.vmamba_mesh`
- Study package: `main/data/research_reports/20260428_232836_graph_SOR2_D1_seed42_vmamba_mesh_study`

| algorithm           |   tp |   fp |   fn |   tn |   precision |   recall |       f1 |   accuracy |          ET |   jaccard |   sf_jaccard |
|:--------------------|-----:|-----:|-----:|-----:|------------:|---------:|---------:|-----------:|------------:|----------:|-------------:|
| VF2                 |    1 |    2 |    0 |   12 |    0.333333 |        1 | 0.5      |   0.866667 | 0.000391625 |  0.333333 |      12767.3 |
| Node Match (Custom) |    1 |    1 |    0 |   13 |    0.5      |        1 | 0.666667 |   0.933333 | 0.00038275  |  0.5      |      19595   |
| GIN/GNN (Pickle)    |    1 |    0 |    0 |   14 |    1        |        1 | 1        |   1        | 0.000451708 |  1        |      33207.3 |