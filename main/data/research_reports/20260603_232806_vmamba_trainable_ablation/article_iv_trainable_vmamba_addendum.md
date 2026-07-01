# Article IV Trainable VMamba Addendum

## Scope

This report documents trainable VMamba-T and VMamba-Mesh-T runs. These rows are separate from the deterministic adapter evidence.

## Best Configuration

{
  "benchmark": "tpc_ds_genai_spec_v2",
  "scenario": "graph_SOR16_D1_seed42",
  "family": "VMamba-Mesh-T",
  "variant": "vmamba_mesh_t",
  "preset": "small",
  "resolution": 16,
  "patch_size": 2,
  "depths": "2-2-4-2",
  "dims": "64-128-256-512",
  "hidden_dim": 256,
  "embedding_dim": 256,
  "epochs": 1,
  "learning_rate": 0.001,
  "loss": "weighted_bce",
  "optimizer": "adamw",
  "dropout": 0.1,
  "drop_path_rate": 0.1,
  "weight_decay": 0.05,
  "threshold": 0.1,
  "candidate_pairs": 15,
  "elapsed_seconds": 0.15616308400000012,
  "sf_jaccard": 19.210686182401457,
  "tp_per_second": 19.210686182401457,
  "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_small_r16_d2-2-4-2_w64-128-256-512_lossweighted_bce_seed42.pkl",
  "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR16_D1_seed42_small_r16_d2-2-4-2_w64-128-256-512_lossweighted_bce_seed42.json",
  "tp": 3,
  "fp": 12,
  "fn": 0,
  "jaccard": 0.2,
  "precision": 0.2,
  "recall": 1.0
}

## Figures

- sf_jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232806_vmamba_trainable_ablation/figures/vmamba_t_ablation_sf_jaccard.png`
- jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232806_vmamba_trainable_ablation/figures/vmamba_t_ablation_jaccard.png`
- elapsed_seconds: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232806_vmamba_trainable_ablation/figures/vmamba_t_ablation_elapsed_time.png`
- top_configs: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232806_vmamba_trainable_ablation/figures/vmamba_t_ablation_top_configs.png`

## Suggested Article Wording

VMamba-T and VMamba-Mesh-T instantiate the trainable neural version of the VMamba family inside Isomera. VMamba-T uses the structural tensor channels only, while VMamba-Mesh-T uses the full six-channel lineage tensor contract. Both expose `predict_pairs(graph)` for fair comparison against VF2, Node Match, GNN clusters, Vanilla VMamba adapter and VMamba-Mesh adapter.
