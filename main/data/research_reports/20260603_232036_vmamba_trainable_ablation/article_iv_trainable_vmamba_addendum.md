# Article IV Trainable VMamba Addendum

## Scope

This report documents trainable VMamba-T and VMamba-Mesh-T runs. These rows are separate from the deterministic adapter evidence.

## Best Configuration

{
  "benchmark": "tpc_ds_genai_spec_v2",
  "scenario": "graph_SOR2_D1_seed42",
  "family": "VMamba-Mesh-T",
  "variant": "vmamba_mesh_t",
  "preset": "tiny",
  "resolution": 16,
  "patch_size": 2,
  "depths": "1-1-2-1",
  "dims": "32-64-128-256",
  "hidden_dim": 128,
  "embedding_dim": 128,
  "epochs": 1,
  "learning_rate": 0.001,
  "loss": "weighted_bce",
  "optimizer": "adamw",
  "dropout": 0.1,
  "drop_path_rate": 0.05,
  "weight_decay": 0.05,
  "threshold": 0.1,
  "candidate_pairs": 1,
  "elapsed_seconds": 0.019933125000000107,
  "sf_jaccard": 50.16774840874146,
  "tp_per_second": 50.16774840874146,
  "pickle_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR2_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_seed42.pkl",
  "metadata_path": "/Users/cayofel/Documents/GitHub/isomera_v2/main/data/architectures/tpc_ds_genai_spec_v2/models/vmamba_mesh_t/VMambaMeshT_graph_SOR2_D1_seed42_tiny_r16_d1-1-2-1_w32-64-128-256_lossweighted_bce_seed42.json",
  "tp": 1,
  "fp": 0,
  "fn": 0,
  "jaccard": 1.0,
  "precision": 1.0,
  "recall": 1.0
}

## Figures

- sf_jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232036_vmamba_trainable_ablation/figures/vmamba_t_ablation_sf_jaccard.png`
- jaccard: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232036_vmamba_trainable_ablation/figures/vmamba_t_ablation_jaccard.png`
- elapsed_seconds: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232036_vmamba_trainable_ablation/figures/vmamba_t_ablation_elapsed_time.png`
- top_configs: `/Users/cayofel/Documents/GitHub/isomera_v2/main/data/research_reports/20260603_232036_vmamba_trainable_ablation/figures/vmamba_t_ablation_top_configs.png`

## Suggested Article Wording

VMamba-T and VMamba-Mesh-T instantiate the trainable neural version of the VMamba family inside Isomera. VMamba-T uses the structural tensor channels only, while VMamba-Mesh-T uses the full six-channel lineage tensor contract. Both expose `predict_pairs(graph)` for fair comparison against VF2, Node Match, GNN clusters, Vanilla VMamba adapter and VMamba-Mesh adapter.
