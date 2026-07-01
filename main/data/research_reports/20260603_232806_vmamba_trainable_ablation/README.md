# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenarios: `graph_SOR16_D1_seed42`
- Variants: `vmamba_t, vmamba_mesh_t`
- Presets: `small`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232806_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_spec_v2", "scenario": "graph_SOR16_D1_seed42", "family": "VMamba-Mesh-T", "variant": "vmamba_mesh_t", "preset": "small", "resolution": 16, "patch_size": 2, "depths": "2-2-4-2", "dims": "64-128-256-512", "hidden_dim": 256, "embedding_dim": 256, "epochs": 1, "learning_rate": 0.001, "loss": "weighted_bce", "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.1, "weight_decay": 0.05, "threshold": 0.1, "candidate_pairs": 15, "elapsed_seconds": 0.15616308400000012, "sf_jaccard": 19.210686182401457, "tp_per_second": 19.210686182401457, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_small_r16_d2-2-4-2_w64-128-256-512_lossweighted_bce_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_small_r16_d2-2-4-2_w64-128-256-512_lossweighted_bce_seed42.json", "tp": 3, "fp": 12, "fn": 0, "jaccard": 0.2, "precision": 0.2, "recall": 1.0}`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.
