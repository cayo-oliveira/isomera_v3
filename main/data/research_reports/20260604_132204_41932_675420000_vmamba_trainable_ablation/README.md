# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenarios: `graph_SOR2_D2_seed42`
- Variants: `vmamba_mesh_t`
- Presets: `tiny`
- Experiment tag: `llmhardneg-smoke`
- Hard-negative mining: `True` via `codex_gpt5_llm_hard_negative_reviewer`
- Hard-negative strategy: `structural_plus_llm_manifest`
- Hard-negative manifest: `research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_spec_v2", "scenario": "graph_SOR2_D2_seed42", "algorithm": "VMamba-Mesh-T (llmhardneg-smoke)", "family": "VMamba-Mesh-T (llmhardneg-smoke)", "family_base": "VMamba-Mesh-T", "variant": "vmamba_mesh_t", "experiment_tag": "llmhardneg-smoke", "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}, {\"channel\": \"C2\", \"name\": \"Layer diagonal\", \"role\": \"SOR/SOT/SPEC layer identity on the diagonal\"}, {\"channel\": \"C3\", \"name\": \"Degree fingerprint\", \"role\": \"local structural degree signature on the diagonal\"}, {\"channel\": \"C4\", \"name\": \"Lineage route bias\", \"role\": \"route prior for SOR -> SOT -> SPEC traversal\"}, {\"channel\": \"C5\", \"name\": \"Sparse mask\", \"role\": \"occupied cells so sparse zeros are not treated as missing evidence\"}]", "preset": "tiny", "resolution": 16, "patch_size": 2, "depths": "1-1-2-1", "dims": "32-64-128-256", "hidden_dim": 128, "embedding_dim": 128, "epochs": 1, "batch_size": 4, "inference_batch_size": 64, "encoder_batch_size": 16, "learning_rate": 0.001, "loss": "weighted_bce", "negative_ratio": 4, "hard_negative_mining": true, "hard_negative_strategy": "structural_plus_llm_manifest", "hard_negative_agent": "codex_gpt5_llm_hard_negative_reviewer", "hard_negative_manifest_path": "research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json", "hard_negative_manifest_id": "llm_hard_negatives_article_iv_20260604", "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.05, "weight_decay": 0.05, "requested_device": "cpu", "resolved_device": "cpu", "mps_available": false, "mps_fallback_reason": null, "threshold": 0.1, "candidate_pairs": 6, "N_pairs": 6, "elapsed_seconds": 0.009655583999999884, "ET": 0.009655583999999884, "sf_jaccard": 207.13402731518093, "tp_per_second": 207.13402731518093, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR2_D2_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr4_hardneg_llmhardneg_smoke_lr0p001_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR2_D2_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr4_hardneg_llmhardneg_smoke_lr0p001_seed42.json", "tp": 2, "fp": 4, "fn": 0, "tn": 0, "jaccard": 0.3333333333333333, "accuracy": 0.3333333333333333, "precision": 0.3333333333333333, "recall": 1.0, "f1": 0.5}`

## Pipeline

The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding and VSS-style SS2D scan blocks. The pair head combines the learned embeddings with an auditable structural calibration vector, emits a sigmoid score, and applies the calibrated threshold to produce `predict_pairs(graph)`.

Hard-negative mining, when enabled, selects non-duplicate candidate pairs that are structurally similar under the Isomera feature contract. The current implementation is an auditable structural miner, not a hidden LLM call. Future LLM-assisted hard-negative curation can reuse the same provenance fields: agent, model, prompt, selected pairs and manifest.

## Article Outputs

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`
- paired_deltas_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_132204_41932_675420000_vmamba_trainable_ablation/paired_deltas_with_trainable.csv`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.
