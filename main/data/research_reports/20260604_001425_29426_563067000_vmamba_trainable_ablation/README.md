# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenarios: `graph_SOR2_D1_seed42, graph_SOR2_D2_seed42, graph_SOR2_D3_seed42, graph_SOR2_D4_seed42, graph_SOR2_D5_seed42, graph_SOR4_D1_seed42, graph_SOR4_D2_seed42, graph_SOR4_D3_seed42, graph_SOR4_D4_seed42, graph_SOR4_D5_seed42, graph_SOR8_D1_seed42, graph_SOR8_D2_seed42, graph_SOR8_D3_seed42, graph_SOR8_D4_seed42, graph_SOR8_D5_seed42, graph_SOR16_D1_seed42, graph_SOR16_D2_seed42, graph_SOR16_D3_seed42, graph_SOR16_D4_seed42, graph_SOR16_D5_seed42`
- Variants: `vmamba_t, vmamba_mesh_t`
- Presets: `article_cpu`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_spec_v2", "scenario": "graph_SOR8_D5_seed42", "algorithm": "VMamba-T", "family": "VMamba-T", "variant": "vmamba_t", "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}]", "preset": "article_cpu", "resolution": 16, "patch_size": 2, "depths": "2-2-8-2", "dims": "16-32-64-128", "hidden_dim": 128, "embedding_dim": 128, "epochs": 10, "batch_size": 16, "learning_rate": 0.001, "loss": "weighted_bce", "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.15, "weight_decay": 0.05, "threshold": 0.575, "candidate_pairs": 435, "N_pairs": 435, "elapsed_seconds": 0.5335377910000716, "ET": 0.5335377910000716, "sf_jaccard": 522.0860382857303, "tp_per_second": 136.82254796453623, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_t/VMambaT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_lr0p001_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_t/VMambaT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_lr0p001_seed42.json", "tp": 73, "fp": 21, "fn": 20, "tn": 321, "jaccard": 0.6403508771929824, "accuracy": 0.9057471264367816, "precision": 0.776595744680851, "recall": 0.7849462365591398, "f1": 0.7807486631016043}`

## Pipeline

The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding and VSS-style SS2D scan blocks. The pair head combines the learned embeddings with an auditable structural calibration vector, emits a sigmoid score, and applies the calibrated threshold to produce `predict_pairs(graph)`.

## Article Outputs

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`
- paired_deltas_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation/paired_deltas_with_trainable.csv`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.
