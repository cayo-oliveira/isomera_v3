# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_full_lineage`
- Scenarios: `graph_SOR2_D1_seed42, graph_SOR2_D2_seed42, graph_SOR2_D3_seed42, graph_SOR2_D4_seed42, graph_SOR2_D5_seed42, graph_SOR4_D1_seed42, graph_SOR4_D2_seed42, graph_SOR4_D3_seed42, graph_SOR4_D4_seed42, graph_SOR4_D5_seed42, graph_SOR8_D1_seed42, graph_SOR8_D2_seed42, graph_SOR8_D3_seed42, graph_SOR8_D4_seed42, graph_SOR8_D5_seed42, graph_SOR16_D1_seed42, graph_SOR16_D2_seed42, graph_SOR16_D3_seed42, graph_SOR16_D4_seed42, graph_SOR16_D5_seed42`
- Variants: `vmamba_t, vmamba_mesh_t`
- Presets: `article_cpu`
- Experiment tag: `hardneg-mps-full`
- Hard-negative mining: `True` via `isomera_structural_hard_negative_miner`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_full_lineage", "scenario": "graph_SOR8_D5_seed42", "algorithm": "VMamba-Mesh-T (hardneg-mps-full)", "family": "VMamba-Mesh-T (hardneg-mps-full)", "family_base": "VMamba-Mesh-T", "variant": "vmamba_mesh_t", "experiment_tag": "hardneg-mps-full", "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}, {\"channel\": \"C2\", \"name\": \"Layer diagonal\", \"role\": \"SOR/SOT/SPEC layer identity on the diagonal\"}, {\"channel\": \"C3\", \"name\": \"Degree fingerprint\", \"role\": \"local structural degree signature on the diagonal\"}, {\"channel\": \"C4\", \"name\": \"Lineage route bias\", \"role\": \"route prior for SOR -> SOT -> SPEC traversal\"}, {\"channel\": \"C5\", \"name\": \"Sparse mask\", \"role\": \"occupied cells so sparse zeros are not treated as missing evidence\"}]", "preset": "article_cpu", "resolution": 16, "patch_size": 2, "depths": "2-2-8-2", "dims": "16-32-64-128", "hidden_dim": 128, "embedding_dim": 128, "epochs": 10, "batch_size": 16, "inference_batch_size": 4096, "encoder_batch_size": 64, "learning_rate": 0.001, "loss": "weighted_bce", "negative_ratio": 16, "hard_negative_mining": true, "hard_negative_agent": "isomera_structural_hard_negative_miner", "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.15, "weight_decay": 0.05, "requested_device": "mps", "resolved_device": "mps", "mps_available": true, "mps_fallback_reason": null, "threshold": 0.45, "candidate_pairs": 5460, "N_pairs": 5460, "elapsed_seconds": 0.7124190839999756, "ET": 0.7124190839999756, "sf_jaccard": 2903.4876331303767, "tp_per_second": 553.045263453405, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_full_lineage/models/vmamba_mesh_t/VMambaMeshT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_nr16_hardneg_hardneg_mps_full_lr0p001_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_full_lineage/models/vmamba_mesh_t/VMambaMeshT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_nr16_hardneg_hardneg_mps_full_lr0p001_seed42.json", "tp": 394, "fp": 645, "fn": 1, "tn": 4420, "jaccard": 0.37884615384615383, "accuracy": 0.8816849816849817, "precision": 0.37921077959576516, "recall": 0.9974683544303797, "f1": 0.5495118549511855}`

## Pipeline

The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding and VSS-style SS2D scan blocks. The pair head combines the learned embeddings with an auditable structural calibration vector, emits a sigmoid score, and applies the calibrated threshold to produce `predict_pairs(graph)`.

Hard-negative mining, when enabled, selects non-duplicate candidate pairs that are structurally similar under the Isomera feature contract. The current implementation is an auditable structural miner, not a hidden LLM call. Future LLM-assisted hard-negative curation can reuse the same provenance fields: agent, model, prompt, selected pairs and manifest.

## Article Outputs

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`
- paired_deltas_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/paired_deltas_with_trainable.csv`
- cpu_mps_comparison: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation/cpu_mps_comparison.csv`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.

## Aggregate Interpretation

| Model | Jaccard pooled | SF-Jaccard | ET | TP/FP/FN |
|---|---:|---:|---:|---:|
| VMamba-T (hardneg-mps-full) | 0.2906 | 868.30 | 0.3062 | 1548/3436/343 |
| VMamba-Mesh-T (hardneg-mps-full) | 0.2680 | 1375.31 | 0.1491 | 1556/3915/335 |

Paired scenario delta for `VMamba-Mesh-T - VMamba-T`: Jaccard `-0.0031`, 95% CI `[-0.0193, 0.0136]`; SF-Jaccard `+507.02`, 95% CI `[305.33, 715.73]`.

This run validates Full Lineage MPS execution with encoder/pair batching and structural hard-negative mining. It improves neural throughput substantially, especially for VMamba-Mesh-T, but it lowers pooled Jaccard relative to the best CPU trainable run. Use it as an efficiency/backend ablation and as evidence that Full Lineage still needs threshold calibration and better negative strategy.
