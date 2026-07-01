# VMamba-T / VMamba-Mesh-T Video Runbook

## Core Contract

The trainable neural model starts after the VMamba-Mesh tensor input is built:

```text
graph -> CanonSort -> C0-C5 tensor -> patch embedding -> VSS/SS2D -> pair head -> logit -> sigmoid -> threshold -> predict_pairs(graph)
```

This means the six channels, DiagFP, lineage route bias and sparse mask are input features for the trainable model. They are not replaced by the neural network.

## What Was Actually Tested

The validated trainable reports are:

- SPEC v2: `main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation`
- Full Lineage: `main/data/research_reports/20260604_024038_31797_424575000_vmamba_trainable_ablation`
- SPEC v2 MPS hard-negative ablation: `main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation`
- Full Lineage MPS hard-negative ablation: `main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation`
- SPEC v2 MPS LLM-manifest hard-negative ablation: `main/data/research_reports/20260604_134510_42331_744213000_vmamba_trainable_ablation`
- SPEC v2 MPS V3 false-positive replay ablation: `main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation`
- Codex/GPT-5 hard-negative manifest: `research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json`

The SPEC v2 run used all 20 article scenarios, VMamba-T and VMamba-Mesh-T, `article_cpu`, resolution 16, 10 epochs, batch size 16, Weighted BCE, negative ratio 16, and learning rates 0.001 and 0.0005.

The Full Lineage run used all 20 article scenarios across SOR/SOT/SPEC scope, VMamba-T and VMamba-Mesh-T, `article_cpu`, resolution 16, 10 epochs, batch size 16, Weighted BCE, negative ratio 16, and learning rates 0.001 and 0.0005. The aggregate `N_pairs=39695` is the validation guard that confirms this is the complete Full Lineage scope, not a SPEC-only slice.

## What Is Not Fully Tested Yet

The current evidence does not yet prove that every hyperparameter was varied independently in a full factorial campaign. The implemented controls include model variant, preset, depths, dims, resolution, epochs, batch size, learning rate, loss, negative ratio, dropout, drop path and weight decay, but the full factorial GPU campaign remains pending.

The local machine is a MacBook Air M4 with 16 GB RAM and Apple M4 GPU. PyTorch 2.8.0 can allocate tensors on `mps:0` outside the Codex sandbox; inside the sandbox, MPS can appear unavailable because the Metal device is not exposed to the process. The Isomera app now records `requested_device`, `resolved_device`, `mps_available` and fallback reason in the training manifest.

## Main Results

| Benchmark | Model | Jaccard | SF-Jaccard | ET | TP/FP/FN |
|---|---:|---:|---:|---:|---:|
| SPEC v2 | VMamba-T | 0.4815 | 200.58 | 0.1583 | 403/298/136 |
| SPEC v2 | VMamba-Mesh-T | 0.4883 | 202.39 | 0.1679 | 437/356/102 |
| Full Lineage | VMamba-T | 0.3326 | 590.34 | 0.4959 | 1759/3397/132 |
| Full Lineage | VMamba-Mesh-T | 0.3333 | 622.42 | 0.5271 | 1769/3416/122 |

## SPEC v2 MPS Hard-Negative Ablation

This run used all 20 SPEC v2 scenarios, `requested_device=mps`, `resolved_device=mps`, `article_cpu`, resolution 16, 10 epochs, train batch 16, inference batch 4096, encoder batch 64, Weighted BCE, negative ratio 16 and structural hard-negative mining.

| Model | Jaccard | SF-Jaccard | ET | TP/FP/FN |
|---|---:|---:|---:|---:|
| VMamba-T (hardneg-mps-spec) | 0.4361 | 319.46 | 0.1430 | 403/385/136 |
| VMamba-Mesh-T (hardneg-mps-spec) | 0.4447 | 434.69 | 0.0891 | 454/482/85 |

Paired scenario deltas:

| Comparison | Delta Jaccard | 95% CI | Delta SF-Jaccard | 95% CI |
|---|---:|---:|---:|---:|
| VMamba-Mesh-T - VMamba-T | +0.0494 | [0.0079, 0.0986] | +115.23 | [26.67, 217.73] |

Interpretation: hard-negative mining plus MPS batching strengthens the paired VMamba-Mesh-T advantage over VMamba-T in SPEC v2, but it does not beat the best CPU pooled Jaccard run. Present it as an ablation/backend result unless a later calibrated campaign improves pooled quality.

## SPEC v2 MPS LLM-Manifest Hard-Negative Ablation

This run used Codex/GPT-5 as the LLM-assisted hard-negative reviewer. The output is not a hidden runtime call: it is the auditable JSON manifest `research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json`, with 898 non-duplicate candidate pairs and explicit reasons. The criteria are same SOR/SOT/SPEC layer, same domain suffix, similar naming tokens, similar local degree/context size and high VMamba-Mesh structural feature score.

At training time, `structural_plus_llm_manifest` loads the manifest, prioritizes those selected pairs, records `hard_negative_agent`, `hard_negative_manifest_path` and `hard_negative_manifest_id`, then falls back to the structural miner until `negative_ratio` is satisfied. In Isomera, enable `Hard-negative mining`, keep `Hard-negative source = Structural + LLM manifest`, and edit the manifest path if the user wants to test a different reviewed list.

| Model | Jaccard | SF-Jaccard | ET | TP/FP/FN |
|---|---:|---:|---:|---:|
| VMamba-T (llmhardneg-mps-spec) | 0.4405 | 306.93 | 0.1504 | 389/344/150 |
| VMamba-Mesh-T (llmhardneg-mps-spec) | 0.4432 | 407.24 | 0.0894 | 410/386/129 |

Paired scenario deltas:

| Comparison | Delta Jaccard | 95% CI | Delta SF-Jaccard | 95% CI |
|---|---:|---:|---:|---:|
| VMamba-Mesh-T - VMamba-T | +0.0567 | [0.0064, 0.1138] | +100.32 | [38.72, 171.67] |

Interpretation: the LLM-reviewed list keeps the Mesh-T advantage stable under difficult negatives. Compared with the structural hard-negative run, it is more useful as a provenance and methodology improvement than as a new best pooled-quality row.

## Full Lineage MPS Hard-Negative Ablation

This run used all 20 Full Lineage scenarios, `requested_device=mps`, `resolved_device=mps`, `article_cpu`, resolution 16, 10 epochs, train batch 16, inference batch 4096, encoder batch 64, Weighted BCE, negative ratio 16 and structural hard-negative mining. It validates the complete SOR/SOT/SPEC universe with `N_pairs=39695`.

| Model | Jaccard | SF-Jaccard | ET | TP/FP/FN |
|---|---:|---:|---:|---:|
| VMamba-T (hardneg-mps-full) | 0.2906 | 868.30 | 0.3062 | 1548/3436/343 |
| VMamba-Mesh-T (hardneg-mps-full) | 0.2680 | 1375.31 | 0.1491 | 1556/3915/335 |

Paired scenario deltas:

| Comparison | Delta Jaccard | 95% CI | Delta SF-Jaccard | 95% CI |
|---|---:|---:|---:|---:|
| VMamba-Mesh-T - VMamba-T | -0.0031 | [-0.0193, 0.0136] | +507.02 | [305.33, 715.73] |

Interpretation: Full Lineage hard-negative MPS is an efficiency win and a quality warning. The Mesh tensor makes the trainable inference much faster under MPS batching, but the broad candidate universe still creates too many false positives. The next step is calibration/split strategy, not claiming that hard negatives solved Full Lineage.

## SPEC v2 MPS V3 False-Positive Replay Ablation

This is the newest SPEC v2 calibration attempt. It uses:

- `requested_device=mps`, `resolved_device=mps`;
- `structural_plus_llm_manifest`;
- manifest `research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json`;
- `false_positive_replay_rounds=1`;
- `false_positive_replay_weight=3`;
- `false_positive_replay_epochs=2`;
- `threshold_policy=precision_guard`;
- `threshold_precision_floor=0.50`.

| Model | Jaccard | SF-Jaccard | ET | Precision | Recall | TP/FP/FN |
|---|---:|---:|---:|---:|---:|---:|
| VMamba-T (v3-fpreplay-mps-spec) | 0.3926 | 345.75 | 0.0968 | 0.4775 | 0.6883 | 371/406/168 |
| VMamba-Mesh-T (v3-fpreplay-mps-spec) | 0.4757 | 419.32 | 0.0871 | 0.6049 | 0.6902 | 372/243/167 |

Paired delta Mesh-T minus VMamba-T: Jaccard `+0.0662` with 95% CI `[-0.0151, 0.1551]`; SF-Jaccard `+73.57` with 95% CI `[-14.15, 180.53]`.

Interpretation: V3 is the best calibrated MPS row and shows that false-positive replay works in the intended direction. Compared with the LLM-manifest MPS row, Mesh-T false positives drop from `386` to `243` and pooled Jaccard rises from `0.4432` to `0.4757`. It still does not beat the best CPU pooled-quality row (`0.4883`), so it should be reported as a calibration improvement, not the final best model.

## Final Article IV Recommendation

Use the following split in the article, Help tab and video:

| Role | Version | Evidence |
|---|---|---|
| Best pooled SPEC v2 quality | V2 `VMamba-Mesh-T CPU` | Jaccard `0.4883` |
| Best SPEC v2 operational efficiency | V1 `VMamba-Mesh Isomera adapter` | SF-Jaccard `5464.74`; Vanilla VMamba adapter is `5076.80` |
| Best calibrated MPS row | V3 `VMamba-Mesh-T MPS` | Jaccard `0.4757`, precision `0.6049`, false positives `243` |
| Best Full Lineage neural quality | V2 `VMamba-Mesh-T CPU` | Jaccard `0.3333`, SF-Jaccard `622.42` |

Do not say that Vanilla VMamba beat VMamba-Mesh on SPEC SF-Jaccard. It did not. The correct statement is that the deterministic adapter family is much faster than the trainable neural family, and within the deterministic adapter family VMamba-Mesh is stronger than Vanilla VMamba on both Jaccard and SF-Jaccard in SPEC v2.

The Article IV PDF now includes two separate SPEC v2 comparison figures:

- `vmamba_family_spec_v2_jaccard_comparison.png`
- `vmamba_family_spec_v2_sf_jaccard_comparison.png`

Article V candidate: a hybrid VMamba-Mesh + GNN two-stage detector, where a fast high-recall VMamba-Mesh/GNN gate filters candidates and VMamba-Mesh-T reranks only plausible pairs.

Final SPEC v2 table for presentation:

| Model | Jaccard | ET | SF-Jaccard | Accuracy | Precision | Recall |
|---|---:|---:|---:|---:|---:|---:|
| V1 VMamba adapter | 0.2555 | 0.0060 | 5076.80 | 0.5378 | 0.2861 | 0.7050 |
| V1 VMamba-Mesh adapter | 0.2748 | **0.0060** | **5464.74** | 0.5879 | 0.3127 | 0.6939 |
| V2 VMamba-T CPU | 0.4815 | 0.1583 | 200.58 | 0.8188 | 0.5749 | 0.7477 |
| V2 VMamba-Mesh-T CPU | **0.4883** | 0.1679 | 202.39 | 0.8088 | 0.5511 | **0.8108** |
| V3 VMamba-T MPS | 0.3926 | 0.0968 | 345.75 | 0.7603 | 0.4775 | 0.6883 |
| V3 VMamba-Mesh-T MPS | 0.4757 | 0.0871 | 419.32 | **0.8288** | 0.6049 | 0.6902 |

Use this sentence in Help/video: `V2 Mesh-T is the quality winner, V1 Mesh adapter is the efficiency winner, and V3 Mesh-T is the best calibrated MPS ablation.`

## Metrics

Jaccard:

```text
J = TP / (TP + FP + FN)
```

SF-Jaccard:

```text
SFJ = J * N_pairs / ET
```

The confidence intervals are scenario-bootstrap intervals. If a paired delta interval crosses zero, it means the superiority claim is not stable across scenarios.

Final paired trainable deltas:

| Comparison | Benchmark | Delta Jaccard | 95% CI | Delta SF-Jaccard | 95% CI |
|---|---|---:|---:|---:|---:|
| VMamba-Mesh-T - VMamba-T | SPEC v2 | +0.0243 | [-0.0387, 0.0898] | +1.82 | [-22.52, 30.47] |
| VMamba-Mesh-T - VMamba-T | Full Lineage | +0.0164 | [-0.0006, 0.0382] | +32.08 | [9.88, 54.87] |

## Honest Optimization Summary

The trainable campaign now has a clear negative-result story:

| Attempt | Scope | Main result | Interpretation |
|---|---|---|---|
| CPU trainable baseline | SPEC v2 | Mesh-T Jaccard `0.4883` | Best pooled-quality SPEC row. |
| CPU trainable baseline | Full Lineage | Mesh-T Jaccard `0.3333`, SF `622.42` | Best pooled-quality Full trainable row; Jaccard CI nearly clears zero but still touches it. |
| MPS validation | SPEC v2 | Mesh-T Jaccard `0.4161`, SF `143.67` | Backend validation, not best result. |
| MPS structural hard negatives | SPEC v2 | Mesh-T Jaccard `0.4447`, paired CI `[0.0079, 0.0986]` | Mesh-T advantage stabilizes, pooled Jaccard below CPU. |
| MPS Codex/GPT-5 manifest hard negatives | SPEC v2 | Mesh-T Jaccard `0.4432`, paired CI `[0.0064, 0.1138]` | LLM manifest improves provenance and keeps paired advantage positive. |
| MPS structural hard negatives | Full Lineage | Mesh-T Jaccard `0.2680`, SF `1375.31` | Efficiency improves strongly; precision/Jaccard not solved. |

Use this exact interpretation: MPS + batching + hard negatives improved neural efficiency, mainly in Full Lineage, but did not solve precision. The best pooled-quality result remains the CPU campaign without hard-negative mining. The MPS rows are ablation/backend evidence.

Best next tests for improving Jaccard and confidence intervals:

- False-positive replay hard negatives: mine the model's own high-confidence false positives and retrain against them.
- Scope-aware thresholds: global threshold for article comparability, plus SOR/SOT/SPEC or domain-family calibrated thresholds as an ablation.
- Two-stage gate plus reranker: fast VMamba-Mesh/GNN high-recall filter, then VMamba-Mesh-T only on plausible pairs.
- False-positive-sensitive loss: asymmetric focal, Tversky or soft-Jaccard surrogate.
- Full Lineage Codex/GPT-5 manifest: extend the reviewed hard-negative JSON to SOR/SOT/SPEC and tag each pair by reason category.
- Stratified reporting: Tier-1/Tier-2, layer scope and domain-family bootstrap. This explains variance; it does not hide it.

## Isomera Reproduction Path

1. Open `Help -> Tech Docs` and read `VMamba Mesh V2 T Video Runbook`.
2. Open `Study Lab -> Knowledge Base` and read this KB.
3. Open `Study Lab -> Deep Learning Workbench`.
4. Select `tpc_ds_genai_spec_v2` and `graph_SOR16_D1_seed42`.
5. Compare Vanilla VMamba and VMamba-Mesh adapter.
6. Open `Study Lab -> Train Model Adapter`.
7. Select `VMamba-T` or `VMamba-Mesh-T`.
8. Use the trainable hyperparameter controls.
9. Open `Study Lab -> Model Reports`.
10. Run a quick ablation or open the existing SPEC/Full trainable reports.
11. Open `Study Lab -> Model Interpretability`.
12. Use `tpc_ds_genai_spec_v2 / graph_SOR16_D1_seed42` and the pair `SPEC_customer_summary_D1` vs `SPEC_store_sales_summary_D1`.
13. Run interpretability with a `VMamba-Mesh-T` pickle. Expected reference package: score about `0.2232`, threshold `0.2000`, decision `duplicate`.
14. Open `Benchmark & Examples -> Article Reproducibility`.
15. Run the Article IV reproduction and compare expected values.

## Batched CPU/MPS Reproduction Path

Use this when recording the performance part of the video.

1. Open `Study Lab -> Train Model Adapter`.
2. For GNN/GIN, show `Device`, `Batch size`, `Batched inference`, `Inference batch`, and `Encoder batch`.
3. Explain:
   - `Batch size` is the number of supervised pairs used per optimizer step.
   - `Inference batch` is the number of candidate pairs scored together by the pair head.
   - `Encoder batch` is the number of subgraphs/tensors encoded together before pair scoring.
4. For VMamba-T/VMamba-Mesh-T, show `Device`, `Inference batch`, and `Encoder batch`.
5. Open `Study Lab -> Model Reports` and show the probe:
   `main/data/research_reports/20260604_120053_39950_604003000_batched_execution_probe`.
6. State clearly: batching does not change TP/FP/FN for the same trained model and threshold. It changes execution policy.

Runtime contract:

```text
graph -> node contexts -> CxRxR tensors
encoder batch -> h_u embeddings
pair batch -> logit z(u,v)
sigmoid(z) -> duplicate score
threshold -> predict_pairs(graph)
```

Pipeline figure used by the PDF/article:

`main/docs/presentations/vmamba_mesh_assets/vmamba_t_duplicate_decision_pipeline.png`

Latest runtime probe on `graph_SOR16_D1_seed42`:

| Model | Device | Pairwise ET | Batched ET | Note |
|---|---:|---:|---:|---|
| GNN/GIN | CPU | 0.0327 | 0.0014 | Best runtime in this small probe. |
| GNN/GIN | MPS | 0.7405 | 0.0196 | Large improvement, but still CPU-favored here. |
| VMamba-T | MPS | 0.0688 | 0.0387 | Encoder batch improves Metal dispatch. |
| VMamba-Mesh-T | MPS | 0.0654 | 0.0404 | Encoder batch 64 was the best tested MPS setting. |

This answers the MPS question: yes, larger encoder batching helps. It does not fully beat CPU on this small SPEC scenario because graph tensorization remains Python/CPU-side and the tensors are small. Larger scenarios, larger presets, more epochs, or fully vectorized tensorization are the next places where MPS may become more competitive.

## Next Campaign

Before claiming a full factorial neural result:

- enable and record MPS/GPU or explicitly declare CPU-only;
- extend Full Lineage with epochs 20 and 30;
- test negative ratio 4, 8 and 16;
- test learning rates 0.001, 0.0005 and 0.0001;
- test Weighted BCE and Focal Loss;
- extend the LLM-assisted hard-negative comparison to Full Lineage using the same manifest contract, with agent/model/prompt/selected-pair provenance archived;
- add neural saliency by channel after the trained head;
- archive every report with manifest, CSV, figures and PDF notes.
