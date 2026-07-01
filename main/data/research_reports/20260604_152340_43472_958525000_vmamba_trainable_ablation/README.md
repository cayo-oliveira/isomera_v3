# VMamba Trainable Ablation

- Benchmark: `tpc_ds_genai_spec_v2`
- Scenarios: `graph_SOR2_D1_seed42, graph_SOR2_D2_seed42, graph_SOR2_D3_seed42, graph_SOR2_D4_seed42, graph_SOR2_D5_seed42, graph_SOR4_D1_seed42, graph_SOR4_D2_seed42, graph_SOR4_D3_seed42, graph_SOR4_D4_seed42, graph_SOR4_D5_seed42, graph_SOR8_D1_seed42, graph_SOR8_D2_seed42, graph_SOR8_D3_seed42, graph_SOR8_D4_seed42, graph_SOR8_D5_seed42, graph_SOR16_D1_seed42, graph_SOR16_D2_seed42, graph_SOR16_D3_seed42, graph_SOR16_D4_seed42, graph_SOR16_D5_seed42`
- Variants: `vmamba_t, vmamba_mesh_t`
- Presets: `article_cpu`
- Experiment tag: `v3-fpreplay-mps-spec`
- Hard-negative mining: `True` via `codex_gpt5_llm_hard_negative_reviewer`
- Hard-negative strategy: `structural_plus_llm_manifest`
- Hard-negative manifest: `research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json`
- False-positive replay rounds: `1`
- False-positive replay top-k: `auto`
- False-positive replay weight: `3`
- Threshold policy: `precision_guard`
- Threshold precision floor: `0.5`
- Metrics CSV: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/metrics.csv`
- Best by SF-Jaccard: `{"benchmark": "tpc_ds_genai_spec_v2", "scenario": "graph_SOR8_D5_seed42", "algorithm": "VMamba-Mesh-T (v3-fpreplay-mps-spec)", "family": "VMamba-Mesh-T (v3-fpreplay-mps-spec)", "family_base": "VMamba-Mesh-T", "variant": "vmamba_mesh_t", "experiment_tag": "v3-fpreplay-mps-spec", "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}, {\"channel\": \"C2\", \"name\": \"Layer diagonal\", \"role\": \"SOR/SOT/SPEC layer identity on the diagonal\"}, {\"channel\": \"C3\", \"name\": \"Degree fingerprint\", \"role\": \"local structural degree signature on the diagonal\"}, {\"channel\": \"C4\", \"name\": \"Lineage route bias\", \"role\": \"route prior for SOR -> SOT -> SPEC traversal\"}, {\"channel\": \"C5\", \"name\": \"Sparse mask\", \"role\": \"occupied cells so sparse zeros are not treated as missing evidence\"}]", "preset": "article_cpu", "resolution": 16, "patch_size": 2, "depths": "2-2-8-2", "dims": "16-32-64-128", "hidden_dim": 128, "embedding_dim": 128, "epochs": 10, "batch_size": 16, "inference_batch_size": 4096, "encoder_batch_size": 64, "learning_rate": 0.001, "loss": "weighted_bce", "negative_ratio": 16, "hard_negative_mining": true, "hard_negative_strategy": "structural_plus_llm_manifest", "hard_negative_agent": "codex_gpt5_llm_hard_negative_reviewer", "hard_negative_manifest_path": "research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json", "hard_negative_manifest_id": "llm_hard_negatives_article_iv_20260604", "false_positive_replay_rounds": 1, "false_positive_replay_top_k": 0, "false_positive_replay_weight": 3, "false_positive_replay_epochs": 2, "threshold_policy": "precision_guard", "threshold_precision_floor": 0.5, "optimizer": "adamw", "dropout": 0.1, "drop_path_rate": 0.15, "weight_decay": 0.05, "requested_device": "mps", "resolved_device": "mps", "mps_available": true, "mps_fallback_reason": null, "threshold": 0.45, "candidate_pairs": 435, "N_pairs": 435, "elapsed_seconds": 0.19921891699999605, "ET": 0.19921891699999605, "sf_jaccard": 1622.0490604457184, "tp_per_second": 391.52908355586305, "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_nr16_hardneg_v3_fpreplay_mps_spec_lr0p001_seed42.pkl", "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_nr16_hardneg_v3_fpreplay_mps_spec_lr0p001_seed42.json", "tp": 78, "fp": 12, "fn": 15, "tn": 330, "jaccard": 0.7428571428571429, "accuracy": 0.9379310344827586, "precision": 0.8666666666666667, "recall": 0.8387096774193549, "f1": 0.8524590163934426}`

## Pipeline

The neural input is built before the model: CanonSort orders the graph context, then tensorization creates C0-C1 for VMamba-T or C0-C5 for VMamba-Mesh-T. The tensor then enters patch embedding and VSS-style SS2D scan blocks. The pair head combines the learned embeddings with an auditable structural calibration vector, emits a sigmoid score, and applies the calibrated threshold to produce `predict_pairs(graph)`.

Hard-negative mining, when enabled, selects difficult non-duplicate candidate pairs. The structural miner ranks pairs by Isomera features; the LLM-manifest strategy prioritizes an auditable Codex/GPT-5 JSON list and then falls back to the structural miner.

False-positive replay, when enabled, scores the selected negative rows after the initial training pass, reinforces the highest-scoring false-positive-like negatives, and continues training. Precision-aware thresholding can then select the best Jaccard threshold under a minimum precision floor.

## Article Outputs

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`
- paired_deltas_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation/paired_deltas_with_trainable.csv`

The generated `.pkl` files expose `predict_pairs(graph)` and can be routed by Benchmark & Examples.
