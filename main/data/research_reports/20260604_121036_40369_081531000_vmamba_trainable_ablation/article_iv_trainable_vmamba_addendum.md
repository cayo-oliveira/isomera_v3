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
  "scenario": "graph_SOR8_D5_seed42",
  "algorithm": "VMamba-Mesh-T (hardneg-mps-spec)",
  "family": "VMamba-Mesh-T (hardneg-mps-spec)",
  "family_base": "VMamba-Mesh-T",
  "variant": "vmamba_mesh_t",
  "experiment_tag": "hardneg-mps-spec",
  "channel_contract": "[{\"channel\": \"C0\", \"name\": \"Forward adjacency\", \"role\": \"edges in canonical lineage direction\"}, {\"channel\": \"C1\", \"name\": \"Reverse adjacency\", \"role\": \"reverse edges for bidirectional scan context\"}, {\"channel\": \"C2\", \"name\": \"Layer diagonal\", \"role\": \"SOR/SOT/SPEC layer identity on the diagonal\"}, {\"channel\": \"C3\", \"name\": \"Degree fingerprint\", \"role\": \"local structural degree signature on the diagonal\"}, {\"channel\": \"C4\", \"name\": \"Lineage route bias\", \"role\": \"route prior for SOR -> SOT -> SPEC traversal\"}, {\"channel\": \"C5\", \"name\": \"Sparse mask\", \"role\": \"occupied cells so sparse zeros are not treated as missing evidence\"}]",
  "preset": "article_cpu",
  "resolution": 16,
  "patch_size": 2,
  "depths": "2-2-8-2",
  "dims": "16-32-64-128",
  "hidden_dim": 128,
  "embedding_dim": 128,
  "epochs": 10,
  "batch_size": 16,
  "inference_batch_size": 4096,
  "encoder_batch_size": 64,
  "learning_rate": 0.001,
  "loss": "weighted_bce",
  "negative_ratio": 16,
  "hard_negative_mining": true,
  "hard_negative_agent": "isomera_structural_hard_negative_miner",
  "optimizer": "adamw",
  "dropout": 0.1,
  "drop_path_rate": 0.15,
  "weight_decay": 0.05,
  "requested_device": "mps",
  "resolved_device": "mps",
  "mps_available": true,
  "mps_fallback_reason": null,
  "threshold": 0.6,
  "candidate_pairs": 435,
  "N_pairs": 435,
  "elapsed_seconds": 0.1790141670000196,
  "ET": 0.1790141670000196,
  "sf_jaccard": 1654.0167850221458,
  "tp_per_second": 452.47815498306977,
  "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_nr16_hardneg_hardneg_mps_spec_lr0p001_seed42.pkl",
  "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR8_D5_seed42_article_cpu_r16_d2-2-8-2_w16-32-64-128_lossweighted_bce_nr16_hardneg_hardneg_mps_spec_lr0p001_seed42.json",
  "tp": 81,
  "fp": 26,
  "fn": 12,
  "tn": 316,
  "jaccard": 0.680672268907563,
  "accuracy": 0.9126436781609195,
  "precision": 0.7570093457943925,
  "recall": 0.8709677419354839,
  "f1": 0.81
}

## Figures

- sf_jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/figures/vmamba_t_ablation_sf_jaccard.png`
- jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/figures/vmamba_t_ablation_jaccard.png`
- elapsed_seconds: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/figures/vmamba_t_ablation_elapsed_time.png`
- top_configs: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/figures/vmamba_t_ablation_top_configs.png`
- combined_sf_jaccard_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/figures/combined_sf_jaccard_with_trainable.png`
- combined_quality_runtime_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/figures/combined_quality_runtime_with_trainable.png`
- combined_sf_jaccard_line_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/figures/combined_sf_jaccard_line_with_trainable.png`

## Article Artifacts

- ablation_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/ablation_summary_metrics.csv`
- best_trainable_summary_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/best_trainable_summary_metrics.csv`
- best_trainable_per_scenario_metrics: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/best_trainable_per_scenario_metrics.csv`
- combined_summary_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/combined_summary_with_trainable.csv`
- combined_per_scenario_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/combined_per_scenario_with_trainable.csv`
- confidence_intervals_with_trainable: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation/confidence_intervals_with_trainable.csv`

## Suggested Article Wording

VMamba-T and VMamba-Mesh-T instantiate the trainable neural version of the VMamba family inside Isomera. VMamba-T is the neural baseline over the two adjacency channels. VMamba-Mesh-T keeps the same neural backbone but changes the input contract to the full six-channel lineage tensor, allowing DiagFP, lineage route bias and SparseGate information to be learned by the VSS/SS2D blocks. Both expose `predict_pairs(graph)` for fair comparison against VF2, Node Match, GNN clusters, Vanilla VMamba adapter and VMamba-Mesh adapter.
