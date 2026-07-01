# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenarios: `graph_SOR16_D5_seed42`
- Variants: `vmamba_t, vmamba_mesh_t`
- Presets: `article_cpu`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_spec_v2", "scenario": "graph_SOR16_D5_seed42", "algorithm": "VMamba-Mesh-T", "family": "VMamba-Mesh-T", "variant": "vmamba_mesh_t", "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}, {\"channel\": \"C2\", \"name\": \"Layer diagonal\", \"role\": \"SOR/SOT/SPEC layer identity on the diagonal\"}, {\"channel\": \"C3\", \"name\": \"Degree fingerprint\", \"role\": \"local structural degree signature on the diagonal\"}, {\"channel\": \"C4\", \"name\": \"Lineage route bias\", \"role\": \"route prior for SOR -> SOT -> SPEC traversal\"}, {\"channel\": \"C5\", \"name\": \"Sparse mask\", \"role\": \"occupied cells so sparse zeros are not treated as missing evidence\"}]", "preset": "article_cpu", "resolution": 16, "patch_size": 2, "depths": "2-2-8-2", "dims": "16-32-64-128", "hidden_dim": 128, "embedding_dim": 128, "epochs": 10, "batch_size": 16, "learning_rate": 0.001, "loss": "weighted_bce", "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.15, "weight_decay": 0.05, "threshold": 0.525, "candidate_pairs": 435, "N_pairs": 435, "elapsed_seconds": 0.5318855419999977, "ET": 0.5318855419999977, "sf_jaccard": 568.9357422920422, "tp_per_second": 150.40829968640196, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_seed42.json", "tp": 80, "fp": 22, "fn": 13, "tn": 320, "jaccard": 0.6956521739130435, "accuracy": 0.9195402298850575, "precision": 0.7843137254901961, "recall": 0.8602150537634409, "f1": 0.8205128205128205}`

## Pipeline

The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding, VSS-style SS2D scan blocks, a pair head, sigmoid scoring, and thresholded `predict_pairs(graph)` output.

## Article Outputs

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`
- paired_deltas_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_000844_29318_906374000_vmamba_trainable_ablation/paired_deltas_with_trainable.csv`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.
