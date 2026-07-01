# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenarios: `graph_SOR2_D1_seed42`
- Variants: `vmamba_t, vmamba_mesh_t`
- Presets: `tiny`
- Experiment tag: `hardneg-smoke`
- Hard-negative mining: `True` via `isomera_structural_hard_negative_miner`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120916_40334_742954000_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_spec_v2", "scenario": "graph_SOR2_D1_seed42", "algorithm": "VMamba-T (hardneg-smoke)", "family": "VMamba-T (hardneg-smoke)", "family_base": "VMamba-T", "variant": "vmamba_t", "experiment_tag": "hardneg-smoke", "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}]", "preset": "tiny", "resolution": 16, "patch_size": 2, "depths": "1-1-2-1", "dims": "32-64-128-256", "hidden_dim": 128, "embedding_dim": 128, "epochs": 1, "batch_size": 4, "inference_batch_size": 64, "encoder_batch_size": 16, "learning_rate": 0.001, "loss": "weighted_bce", "negative_ratio": 4, "hard_negative_mining": true, "hard_negative_agent": "isomera_structural_hard_negative_miner", "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.05, "weight_decay": 0.05, "requested_device": "cpu", "resolved_device": "cpu", "mps_available": false, "mps_fallback_reason": null, "threshold": 0.1, "candidate_pairs": 1, "N_pairs": 1, "elapsed_seconds": 0.007627583000000104, "ET": 0.007627583000000104, "sf_jaccard": 131.1031292612596, "tp_per_second": 131.1031292612596, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_t/VMambaT_graph_SOR2_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr4_hardneg_hardneg_smoke_lr0p001_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_t/VMambaT_graph_SOR2_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr4_hardneg_hardneg_smoke_lr0p001_seed42.json", "tp": 1, "fp": 0, "fn": 0, "tn": 0, "jaccard": 1.0, "accuracy": 1.0, "precision": 1.0, "recall": 1.0, "f1": 1.0}`

## Pipeline

The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding and VSS-style SS2D scan blocks. The pair head combines the learned embeddings with an auditable structural calibration vector, emits a sigmoid score, and applies the calibrated threshold to produce `predict_pairs(graph)`.

Hard-negative mining, when enabled, selects non-duplicate candidate pairs that are structurally similar under the Isomera feature contract. The current implementation is an auditable structural miner, not a hidden LLM call. Future LLM-assisted hard-negative curation can reuse the same provenance fields: agent, model, prompt, selected pairs and manifest.

## Article Outputs

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120916_40334_742954000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120916_40334_742954000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120916_40334_742954000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120916_40334_742954000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120916_40334_742954000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_120916_40334_742954000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.
