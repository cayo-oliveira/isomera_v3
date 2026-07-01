# TPC-DS Benchmark Setup

This benchmark expects multiple `.gml` graphs plus optional label files.

## Folder structure

Place the graphs in:

`data/architectures/tpc_ds/gml/`

Example:

```
benchmarks/tpcds/
  scenario_1.gml
  scenario_1_labels.csv
  scenario_2.gml
  scenario_2_labels.csv
```

## GML format

Each file should be a directed graph where nodes represent tables and edges represent lineage.
Keep node identifiers stable across scenarios if you want comparable results.

## Labels format

Label files are optional. When present, they must use:

```
node_a,node_b,is_isomorphic
```

Use `1` for true isomorphic pairs and `0` for non-isomorphic pairs.

If the label file includes **all possible pairs**, the UI will treat it as a complete
ground truth and compute TN/accuracy automatically.

## Notes

The UI runs all registered algorithms on every `.gml` file and shows one row per
scenario + algorithm in the benchmark results table.
