# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenarios: `graph_SOR16_D1_seed42`
- Variants: `vmamba_t, vmamba_mesh_t`
- Presets: `tiny`
- Experiment tag: `v3-smoke`
- Hard-negative mining: `True` via `isomera_structural_hard_negative_miner`
- Hard-negative strategy: `structural_similarity`
- Hard-negative manifest: `none`
- False-positive replay rounds: `1`
- False-positive replay top-k: `auto`
- False-positive replay weight: `2`
- Threshold policy: `precision_guard`
- Threshold precision floor: `0.55`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_spec_v2", "scenario": "graph_SOR16_D1_seed42", "algorithm": "VMamba-Mesh-T (v3-smoke)", "family": "VMamba-Mesh-T (v3-smoke)", "family_base": "VMamba-Mesh-T", "variant": "vmamba_mesh_t", "experiment_tag": "v3-smoke", "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}, {\"channel\": \"C2\", \"name\": \"Layer diagonal\", \"role\": \"SOR/SOT/SPEC layer identity on the diagonal\"}, {\"channel\": \"C3\", \"name\": \"Degree fingerprint\", \"role\": \"local structural degree signature on the diagonal\"}, {\"channel\": \"C4\", \"name\": \"Lineage route bias\", \"role\": \"route prior for SOR -> SOT -> SPEC traversal\"}, {\"channel\": \"C5\", \"name\": \"Sparse mask\", \"role\": \"occupied cells so sparse zeros are not treated as missing evidence\"}]", "preset": "tiny", "resolution": 16, "patch_size": 2, "depths": "1-1-2-1", "dims": "32-64-128-256", "hidden_dim": 128, "embedding_dim": 128, "epochs": 2, "batch_size": 8, "inference_batch_size": 1024, "encoder_batch_size": 32, "learning_rate": 0.001, "loss": "weighted_bce", "negative_ratio": 8, "hard_negative_mining": true, "hard_negative_strategy": "structural_similarity", "hard_negative_agent": "isomera_structural_hard_negative_miner", "hard_negative_manifest_path": "", "hard_negative_manifest_id": "", "false_positive_replay_rounds": 1, "false_positive_replay_top_k": 0, "false_positive_replay_weight": 2, "false_positive_replay_epochs": 1, "threshold_policy": "precision_guard", "threshold_precision_floor": 0.55, "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.05, "weight_decay": 0.05, "requested_device": "cpu", "resolved_device": "cpu", "mps_available": false, "mps_fallback_reason": null, "threshold": 0.125, "candidate_pairs": 15, "N_pairs": 15, "elapsed_seconds": 0.011692707999999996, "ET": 0.011692707999999996, "sf_jaccard": 274.8966034459866, "tp_per_second": 256.5701632162542, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr8_hardneg_v3_smoke_lr0p001_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr8_hardneg_v3_smoke_lr0p001_seed42.json", "tp": 3, "fp": 11, "fn": 0, "tn": 1, "jaccard": 0.21428571428571427, "accuracy": 0.26666666666666666, "precision": 0.21428571428571427, "recall": 1.0, "f1": 0.35294117647058826}`

## Pipeline

The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding and VSS-style SS2D scan blocks. The pair head combines the learned embeddings with an auditable structural calibration vector, emits a sigmoid score, and applies the calibrated threshold to produce `predict_pairs(graph)`.

Hard-negative mining, when enabled, selects difficult non-duplicate candidate pairs. The structural miner ranks pairs by Isomera features; the LLM-manifest strategy prioritizes an auditable Codex/GPT-5 JSON list and then falls back to the structural miner.

False-positive replay, when enabled, scores the selected negative rows after the initial training pass, reinforces the highest-scoring false-positive-like negatives, and continues training. Precision-aware thresholding can then select the best Jaccard threshold under a minimum precision floor.

## Article Outputs

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`
- paired_deltas_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/paired_deltas_with_trainable.csv`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.
