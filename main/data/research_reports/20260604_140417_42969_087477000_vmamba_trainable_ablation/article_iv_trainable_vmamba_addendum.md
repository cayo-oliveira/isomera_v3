# Article IV Trainable VMamba Addendum

## Scope

This report documents trainable VMamba-T and VMamba-Mesh-T runs. The deterministic adapters remain as baselines; the `-T` rows are neural models trained from Isomera tensors.

## Processing Contract

1. Read the lineage graph and the labeled duplicate pairs.
2. CanonSort defines a stable node order for each context subgraph.
3. Tensorization creates the model input before the neural network.
4. VMamba-T uses C0 forward adjacency and C1 reverse adjacency.
5. VMamba-Mesh-T uses C0 forward adjacency, C1 reverse adjacency, C2 layer diagonal, C3 degree fingerprint, C4 lineage route bias, and C5 sparse mask.
6. The tensor enters a VMamba-style neural backbone: patch embedding, staged VSS-style blocks, bidirectional row/column SS2D-style scans, stochastic depth/dropout, and a pair head.
7. The pair head also receives an auditable structural feature vector for calibration; the final logit is still learned by the neural head.
8. Sigmoid converts the logit to a continuous duplicate score; the calibrated threshold converts the score into `predict_pairs(graph)`.

## Best Configuration

{
  "benchmark": "tpc_ds_genai_spec_v2",
  "scenario": "graph_SOR16_D1_seed42",
  "algorithm": "VMamba-Mesh-T (v3-smoke)",
  "family": "VMamba-Mesh-T (v3-smoke)",
  "family_base": "VMamba-Mesh-T",
  "variant": "vmamba_mesh_t",
  "experiment_tag": "v3-smoke",
  "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}, {\"channel\": \"C2\", \"name\": \"Layer diagonal\", \"role\": \"SOR/SOT/SPEC layer identity on the diagonal\"}, {\"channel\": \"C3\", \"name\": \"Degree fingerprint\", \"role\": \"local structural degree signature on the diagonal\"}, {\"channel\": \"C4\", \"name\": \"Lineage route bias\", \"role\": \"route prior for SOR -> SOT -> SPEC traversal\"}, {\"channel\": \"C5\", \"name\": \"Sparse mask\", \"role\": \"occupied cells so sparse zeros are not treated as missing evidence\"}]",
  "preset": "tiny",
  "resolution": 16,
  "patch_size": 2,
  "depths": "1-1-2-1",
  "dims": "32-64-128-256",
  "hidden_dim": 128,
  "embedding_dim": 128,
  "epochs": 2,
  "batch_size": 8,
  "inference_batch_size": 1024,
  "encoder_batch_size": 32,
  "learning_rate": 0.001,
  "loss": "weighted_bce",
  "negative_ratio": 8,
  "hard_negative_mining": true,
  "hard_negative_strategy": "structural_similarity",
  "hard_negative_agent": "isomera_structural_hard_negative_miner",
  "hard_negative_manifest_path": "",
  "hard_negative_manifest_id": "",
  "false_positive_replay_rounds": 1,
  "false_positive_replay_top_k": 0,
  "false_positive_replay_weight": 2,
  "false_positive_replay_epochs": 1,
  "threshold_policy": "precision_guard",
  "threshold_precision_floor": 0.55,
  "optimizer": "adamw",
  "dropout": 0.1,
  "drop_path_rate": 0.05,
  "weight_decay": 0.05,
  "requested_device": "cpu",
  "resolved_device": "cpu",
  "mps_available": false,
  "mps_fallback_reason": null,
  "threshold": 0.125,
  "candidate_pairs": 15,
  "N_pairs": 15,
  "elapsed_seconds": 0.011692707999999996,
  "ET": 0.011692707999999996,
  "sf_jaccard": 274.8966034459866,
  "tp_per_second": 256.5701632162542,
  "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr8_hardneg_v3_smoke_lr0p001_seed42.pkl",
  "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_nr8_hardneg_v3_smoke_lr0p001_seed42.json",
  "tp": 3,
  "fp": 11,
  "fn": 0,
  "tn": 1,
  "jaccard": 0.21428571428571427,
  "accuracy": 0.26666666666666666,
  "precision": 0.21428571428571427,
  "recall": 1.0,
  "f1": 0.35294117647058826
}

## Figures

- sf_jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/figures/vmamba_t_ablation_sf_jaccard.png`
- jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/figures/vmamba_t_ablation_jaccard.png`
- elapsed_seconds: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/figures/vmamba_t_ablation_elapsed_time.png`
- top_configs: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/figures/vmamba_t_ablation_top_configs.png`
- combined_sf_jaccard_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/figures/combined_sf_jaccard_with_trainable.png`
- combined_quality_runtime_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/figures/combined_quality_runtime_with_trainable.png`
- combined_sf_jaccard_line_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/figures/combined_sf_jaccard_line_with_trainable.png`

## Article Artifacts

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`
- paired_deltas_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_140417_42969_087477000_vmamba_trainable_ablation/paired_deltas_with_trainable.csv`

## Suggested Article Wording

VMamba-T and VMamba-Mesh-T instantiate the trainable neural version of the VMamba family inside Isomera. VMamba-T is the neural baseline over the two adjacency channels. VMamba-Mesh-T keeps the same neural backbone but changes the input contract to the full six-channel lineage tensor, allowing DiagFP, lineage route bias and SparseGate information to be learned by the VSS/SS2D blocks. Both expose `predict_pairs(graph)` for fair comparison against VF2, Node Match, GNN clusters, Vanilla VMamba adapter and VMamba-Mesh adapter.
