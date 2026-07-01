# VMamba-Mesh V2-T Video Runbook

This note is the in-app companion for the printable PDF:

`papercept_compiler/workspace/creation/final/20260429_182244_vmamba_mesh_operational_journal_draft/v2_t/vmamba_mesh_v2_t_video_runbook.pdf`

## One-Sentence Explanation

The neural VMamba-T family starts after graph-to-tensor encoding: graph context is ordered with CanonSort, converted into C0-C5 channels, read by a VMamba-style VSS/SS2D backbone, converted into a pair score by a neural head, and thresholded into duplicate/non-duplicate decisions.

## Demo Sequence

1. Open `Help -> VMamba-Mesh Presentation`.
2. Show the problem: duplicate tables in Data Mesh lineage.
3. Open `Study Lab -> Deep Learning Workbench`.
4. Select `tpc_ds_genai_spec_v2`.
5. Select `graph_SOR16_D1_seed42`.
6. Show the graph, matrix, channels and ERF.
7. Compare Vanilla VMamba adapter and VMamba-Mesh adapter.
8. Open `Study Lab -> Train Model Adapter`.
9. Select `VMamba-T` or `VMamba-Mesh-T`.
10. Show the trainable hyperparameters.
11. Open `Study Lab -> Model Reports`.
12. Open the trainable report and show combined metrics, confidence intervals and figures.
13. Open `Study Lab -> Model Interpretability`.
14. Select `tpc_ds_genai_spec_v2 / graph_SOR16_D1_seed42`, pair `SPEC_customer_summary_D1` vs `SPEC_store_sales_summary_D1`, and a `VMamba-Mesh-T` pickle.
15. Run interpretability and show score about `0.2232`, threshold `0.2000`, decision `duplicate`, and saliency by channel.
16. Open `Benchmark & Examples -> Article Reproducibility`.
17. Run Article IV reproduction.

## Batched CPU/MPS Demo Sequence

Use this segment when recording the video to explain why MPS was slower before and what changed.

1. Open `Study Lab -> Train Model Adapter`.
2. For GNN/GIN training, set:
   - `Device`: `cpu` or `mps`;
   - `Batch size`: number of supervised pairs per optimizer step;
   - `Batched inference`: enabled;
   - `Inference batch`: number of candidate pairs scored together;
   - `Encoder batch`: number of subgraph embeddings computed together.
3. For VMamba-T or VMamba-Mesh-T, set:
   - `Device`: `auto`, `mps` or `cpu`;
   - `Inference batch`: number of candidate pairs evaluated by the pair head;
   - `Encoder batch`: number of graph-context tensors sent together through the VSS/SS2D backbone.
4. Open `Study Lab -> Model Reports`.
5. Run or show the batched execution probe report.
6. Explain that batching does not change the mathematical decision: it changes how many examples PyTorch/MPS processes per dispatch.

The exact runtime contract is:

```text
graph -> context subgraphs -> tensor/cache per node
encoder batch -> embeddings h_u
pair inference batch -> logits z(u,v)
sigmoid(z) -> score
score >= threshold -> duplicate pair in predict_pairs(graph)
```

For GNN/GIN, the encoder batch is a batch of variable-size subgraphs collated into one tensor plus a `batch` vector. For VMamba-T/Mesh-T, the encoder batch is a stack of `C x R x R` lineage tensors. The tensorization itself is still graph-aware Python code because each node has its own context; the expensive neural encoder and pair head are batched.

Pipeline figure for the video:

![VMamba-T duplicate decision pipeline](../presentations/vmamba_mesh_assets/vmamba_t_duplicate_decision_pipeline.png)

## Validated Reports

- SPEC v2 trainable campaign: `main/data/research_reports/20260604_001425_29426_563067000_vmamba_trainable_ablation`
- Full Lineage trainable campaign: `main/data/research_reports/20260604_024038_31797_424575000_vmamba_trainable_ablation`
- Batched CPU/MPS execution probe: `main/data/research_reports/20260604_120053_39950_604003000_batched_execution_probe`
- SPEC v2 MPS hard-negative campaign: `main/data/research_reports/20260604_121036_40369_081531000_vmamba_trainable_ablation`
- Full Lineage MPS hard-negative campaign: `main/data/research_reports/20260604_122205_40674_719225000_vmamba_trainable_ablation`
- SPEC v2 MPS LLM hard-negative campaign: `main/data/research_reports/20260604_134510_42331_744213000_vmamba_trainable_ablation`
- SPEC v2 MPS V3 false-positive calibration campaign: `main/data/research_reports/20260604_152340_43472_958525000_vmamba_trainable_ablation`
- LLM hard-negative manifest: `research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json`

## Current Results

| Benchmark | Model | Jaccard | SF-Jaccard | ET |
|---|---:|---:|---:|---:|
| SPEC v2 | VMamba-T | 0.4815 | 200.58 | 0.1583 |
| SPEC v2 | VMamba-Mesh-T | 0.4883 | 202.39 | 0.1679 |
| Full Lineage | VMamba-T | 0.3326 | 590.34 | 0.4959 |
| Full Lineage | VMamba-Mesh-T | 0.3333 | 622.42 | 0.5271 |

## SPEC v2 MPS Hard-Negative Campaign

This campaign was run on all 20 SPEC v2 article scenarios with `requested_device=mps`, `resolved_device=mps`, `article_cpu`, resolution 16, 10 epochs, batch size 16, inference batch 4096, encoder batch 64, negative ratio 16, Weighted BCE and structural hard-negative mining.

| Model | Jaccard pooled | SF-Jaccard | ET | Accuracy | TP/FP/FN |
|---|---:|---:|---:|---:|---:|
| VMamba-T (hardneg-mps-spec) | 0.4361 | 319.46 | 0.1430 | 0.7825 | 403/385/136 |
| VMamba-Mesh-T (hardneg-mps-spec) | 0.4447 | 434.69 | 0.0891 | 0.7633 | 454/482/85 |

Paired scenario delta for `VMamba-Mesh-T - VMamba-T` in this campaign: Jaccard `+0.0494` with 95% CI `[0.0079, 0.0986]`; SF-Jaccard `+115.23` with 95% CI `[26.67, 217.73]`. This supports the channel contribution under the MPS hard-negative protocol.

Important limitation: compared with the best CPU trainable SPEC run, hard-negative mining improved MPS throughput and recall, but not pooled Jaccard. It should be presented as an ablation and backend validation, not as the primary best-quality result.

## SPEC v2 MPS LLM-Assisted Hard-Negative Campaign

This campaign answers the explicit hard-negative question: Codex/GPT-5 was used as the LLM-assisted reviewer to define and materialize an auditable hard-negative manifest. The manifest contains 898 candidate pairs selected from real Article IV scenarios. The selection criteria are same SOR/SOT/SPEC layer, same domain suffix, similar naming tokens, similar local degree/context size and high VMamba-Mesh structural feature score. Training does not call an LLM at runtime: it loads the JSON manifest, prioritizes those pairs, records the agent/model/manifest id, and falls back to the structural miner until `negative_ratio=16` is satisfied.

Isomera exposes this under `Study Lab -> Train Model Adapter` and `Study Lab -> Model Reports`: enable `Hard-negative mining`, keep `Hard-negative source = Structural + LLM manifest`, and edit `LLM hard-negative manifest` if a different reviewed JSON should be used.

| Model | Jaccard pooled | SF-Jaccard | ET | Accuracy | Precision | Recall | TP/FP/FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| VMamba-T (llmhardneg-mps-spec) | 0.4405 | 306.93 | 0.1504 | 0.7937 | 0.5307 | 0.7217 | 389/344/150 |
| VMamba-Mesh-T (llmhardneg-mps-spec) | 0.4432 | 407.24 | 0.0894 | 0.7850 | 0.5151 | 0.7607 | 410/386/129 |

Paired scenario delta for `VMamba-Mesh-T - VMamba-T` in the LLM-manifest campaign: Jaccard `+0.0567` with 95% CI `[0.0064, 0.1138]`; SF-Jaccard `+100.32` with 95% CI `[38.72, 171.67]`.

Interpretation: compared with structural hard negatives, the LLM manifest slightly improved VMamba-T precision and reduced false positives, but the Mesh-T pooled Jaccard stayed close to the structural run. The strongest claim is paired and methodological: under a Codex/GPT-5 reviewed hard-negative list, the C0-C5 Mesh-T input still wins over C0-C1 VMamba-T with positive 95% CIs for both Jaccard and SF-Jaccard.

## SPEC v2 MPS V3: False-Positive Calibration + Precision Guard

This is the newest calibration attempt. It keeps the Codex/GPT-5 hard-negative manifest, then runs one error-focused calibration round: the model scores training negatives, collects the highest-confidence false positives, gives those cases extra training weight, and continues training for two calibration epochs. Threshold selection uses `precision_guard` with `threshold_precision_floor=0.50`.

In Isomera this is reproducible in `Study Lab -> Model Reports -> Run trainable VMamba ablation campaign`:

1. Select benchmark `tpc_ds_genai_spec_v2`.
2. Enable article scenarios and SPEC scope.
3. Select `VMamba-T` and `VMamba-Mesh-T`.
4. Set preset `article_cpu`, resolution `16`, epochs `10`, batch size `16`, inference batch `4096`, encoder batch `64`.
5. Set learning rates `0.001` and `0.0005`, loss `weighted_bce`, negative ratio `16`, device `mps`.
6. Enable hard-negative mining and select `Structural + LLM manifest`.
7. Use manifest `research/vmamba/manifests/llm_hard_negatives_article_iv_20260604.json`.
8. Set false-positive calibration rounds `1`, calibration epochs `2`, calibration weight `3`.
9. Set threshold policy `precision_guard` and precision floor `0.50`.

| Model | Jaccard | SF-Jaccard | ET | Accuracy | Precision | Recall | TP/FP/FN |
|---|---:|---:|---:|---:|---:|---:|---:|
| VMamba-T (v3-calibration-mps-spec) | 0.3926 | 345.75 | 0.0968 | 0.7603 | 0.4775 | 0.6883 | 371/406/168 |
| VMamba-Mesh-T (v3-calibration-mps-spec) | 0.4757 | 419.32 | 0.0871 | 0.8288 | 0.6049 | 0.6902 | 372/243/167 |

Paired scenario delta for `VMamba-Mesh-T - VMamba-T`: Jaccard `+0.0662` with 95% CI `[-0.0151, 0.1551]`; SF-Jaccard `+73.57` with 95% CI `[-14.15, 180.53]`.

Interpretation: V3 directly attacks false positives. Compared with the LLM-manifest MPS row, Mesh-T reduces false positives from `386` to `243` and raises Jaccard from `0.4432` to `0.4757`. It is the best calibrated MPS row so far, but it is still below the CPU trainable pooled-quality row (`0.4883`) and its paired confidence intervals still cross zero.

## Full Lineage MPS Hard-Negative Campaign

This campaign repeated the MPS hard-negative protocol on the complete Full Lineage candidate universe (`N_pairs=39695`).

| Model | Jaccard pooled | SF-Jaccard | ET | Accuracy | TP/FP/FN |
|---|---:|---:|---:|---:|---:|
| VMamba-T (hardneg-mps-full) | 0.2906 | 868.30 | 0.3062 | 0.9048 | 1548/3436/343 |
| VMamba-Mesh-T (hardneg-mps-full) | 0.2680 | 1375.31 | 0.1491 | 0.8929 | 1556/3915/335 |

Paired scenario delta for `VMamba-Mesh-T - VMamba-T`: Jaccard `-0.0031` with 95% CI `[-0.0193, 0.0136]`; SF-Jaccard `+507.02` with 95% CI `[305.33, 715.73]`.

Interpretation: MPS batching plus Mesh channels strongly improves trainable throughput on Full Lineage, but hard-negative mining did not solve precision. The best quality row remains the CPU VMamba-Mesh-T campaign; the MPS hard-negative Full Lineage row is an efficiency ablation and a guide for the next calibration work.

## Batched Runtime Results

Probe: `tpc_ds_genai_spec_v2 / graph_SOR16_D1_seed42`, 1 epoch, train batch 16, inference batch 4096, encoder batch 64.

| Model | Device | Pairwise ET | Batched ET | Main observation |
|---|---:|---:|---:|---|
| GNN/GIN | CPU | 0.0327 | 0.0014 | Batching removes repeated per-pair embedding work. |
| GNN/GIN | MPS | 0.7405 | 0.0196 | MPS remains slower than CPU here, but batching removes most dispatch overhead. |
| VMamba-T | CPU | 0.0153 | 0.0108 | Encoder batching helps more than pair-head batching alone. |
| VMamba-T | MPS | 0.0688 | 0.0387 | MPS improves when both encoder and pair head are batched. |
| VMamba-Mesh-T | CPU | 0.0162 | 0.0119 | Same decisions, lower ET. |
| VMamba-Mesh-T | MPS | 0.0654 | 0.0404 | Encoder batch 64 is the best tested MPS setting in this probe. |

Important interpretation: this is a runtime probe, not a new accuracy campaign. It uses tiny 1-epoch models to isolate execution overhead. The validated article-quality numbers remain the SPEC v2 and Full Lineage trainable campaigns listed above.

## Important Caveat

The current evidence includes complete SPEC v2 and complete Full Lineage runs over 20 scenarios, MPS structural hard-negative campaigns, and a SPEC v2 Codex/GPT-5 LLM-manifest hard-negative campaign. It is still not a full factorial hyperparameter campaign: the next campaign should add more epochs, negative ratios, learning rates, losses, threshold calibration strategies and device logging before making a stronger Full Lineage claim about confidence intervals not crossing zero.

The final Full Lineage trainable paired delta is `VMamba-Mesh-T - VMamba-T = +0.0164` Jaccard with 95% CI `[-0.0006, 0.0382]`, and `+32.08` SF-Jaccard with 95% CI `[9.88, 54.87]`.

## What We Tried To Improve The Trainable Rows

## Final Article IV Recommendation

Use three separate claims:

| Role | Recommended version | Evidence | Article wording |
|---|---|---|---|
| Best pooled SPEC v2 quality | V2 `VMamba-Mesh-T CPU` | Jaccard `0.4883` | Best local neural quality row. |
| Best SPEC v2 operational efficiency | V1 `VMamba-Mesh Isomera adapter` | SF-Jaccard `5464.74`; Vanilla VMamba adapter is `5076.80` | Production-speed candidate when runtime dominates. |
| Best calibrated MPS row | V3 `VMamba-Mesh-T MPS` | Jaccard `0.4757`, precision `0.6049`, FP `243` | Calibration ablation that reduces false positives but does not beat V2 CPU. |
| Best Full Lineage neural quality | V2 `VMamba-Mesh-T CPU` | Jaccard `0.3333`, SF-Jaccard `622.42` | Cautious Full Lineage result; Jaccard CI still touches zero. |

Important distinction: Vanilla VMamba does **not** beat VMamba-Mesh on SPEC v2 SF-Jaccard when both are deterministic adapters. VMamba-Mesh adapter is higher (`5464.74` vs `5076.80`). What beats the trainable neural rows on SF-Jaccard is the deterministic adapter family, because it is much faster.

Final figures added to Article IV and the presentation assets:

- `main/docs/presentations/vmamba_mesh_assets/vmamba_family_spec_v2_jaccard_comparison.png`
- `main/docs/presentations/vmamba_mesh_assets/vmamba_family_spec_v2_sf_jaccard_comparison.png`

Unified SPEC v2 comparison used in the article, professor presentation and video:

| Model | Protocol | Jaccard | ET | SF-Jaccard | Accuracy | Precision | Recall | TP/FP/FN |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| VF2 | deterministic graph matcher | 0.1842 | 0.0218 | 546.68 | 0.4618 | 0.2185 | 0.5399 | 291/1041/248 |
| Node Match | node-label matcher | 0.0000 | 0.0151 | 0.00 | 0.7749 | 0.0000 | 0.0000 | 0/0/539 |
| GNN TPC-DS v1 | historical GNN | 0.1128 | 0.0118 | 333.64 | 0.6685 | 0.2210 | 0.1874 | 101/356/438 |
| GNN GenAI v2 WBCE | GNN loss reweighting | 0.2184 | 0.0111 | 1348.31 | 0.3754 | 0.2331 | 0.7755 | 418/1375/121 |
| GNN GenAI v2 hardneg | GNN hard negatives | 0.0092 | 0.0109 | 271.84 | 0.7758 | **0.6250** | 0.0093 | 5/3/534 |
| V1 VMamba | C0-C1 adapter | 0.2555 | 0.0060 | 5076.80 | 0.5378 | 0.2861 | 0.7050 | 380/948/159 |
| V1 VMamba-Mesh | C0-C5 adapter | 0.2748 | **0.0060** | **5464.74** | 0.5879 | 0.3127 | 0.6939 | 374/822/165 |
| V2 VMamba-T CPU | trainable C0-C1 | 0.4815 | 0.1583 | 200.58 | 0.8188 | 0.5749 | 0.7477 | 403/298/136 |
| V2 VMamba-Mesh-T CPU | trainable C0-C5 | **0.4883** | 0.1679 | 202.39 | 0.8088 | 0.5511 | **0.8108** | 437/356/102 |
| V3 VMamba-T MPS | LLM manifest + calibration | 0.3926 | 0.0968 | 345.75 | 0.7603 | 0.4775 | 0.6883 | 371/406/168 |
| V3 VMamba-Mesh-T MPS | LLM manifest + calibration | 0.4757 | 0.0871 | 419.32 | **0.8288** | 0.6049 | 0.6902 | 372/243/167 |

Reading: V2 Mesh-T CPU is the best quality row, V1 Mesh adapter is the best efficiency row, and V3 Mesh-T MPS is the best calibrated MPS row. Precision is diagnostic: the GNN hard-negative row has the highest precision only because it predicts almost no positives, so it is not the best practical detector.

| Attempt | Scope | Result | Honest interpretation |
|---|---|---|---|
| CPU trainable baseline | SPEC v2 | Mesh-T Jaccard `0.4883`, paired delta CI `[-0.0387, 0.0898]` | Best pooled quality; paired CI still crosses zero. |
| CPU trainable baseline | Full Lineage | Mesh-T Jaccard `0.3333`, paired delta CI `[-0.0006, 0.0382]`; SF CI `[9.88, 54.87]` | Best Full Lineage pooled quality; Jaccard almost stable, SF stable. |
| MPS validation | SPEC v2 | Mesh-T Jaccard `0.4161`, SF `143.67` | MPS works, but small unbatched operations hurt. |
| MPS + batching + structural hard negatives | SPEC v2 | Mesh-T Jaccard `0.4447`, paired Jaccard CI `[0.0079, 0.0986]`, SF CI `[26.67, 217.73]` | Efficiency and paired Mesh-T advantage improved; pooled quality stayed below CPU. |
| MPS + Codex/GPT-5 hard-negative manifest | SPEC v2 | Mesh-T Jaccard `0.4432`, paired Jaccard CI `[0.0064, 0.1138]`, SF CI `[38.72, 171.67]` | Good provenance and stable paired advantage; not a new best-quality row. |
| MPS + Codex/GPT-5 manifest + false-positive calibration + precision guard | SPEC v2 | Mesh-T Jaccard `0.4757`, precision `0.6049`, FP reduced to `243`, paired Jaccard CI `[-0.0151, 0.1551]` | Best calibrated MPS row; improves false positives and quality versus MPS hard-negative rows, but still below CPU pooled Jaccard. |
| MPS + batching + structural hard negatives | Full Lineage | Mesh-T Jaccard `0.2680`, SF `1375.31`, Jaccard CI `[-0.0193, 0.0136]`, SF CI `[305.33, 715.73]` | Big efficiency gain, but precision/Jaccard got worse. |

Use this phrasing in the article/video: V1 gives the fastest deterministic adapter, V2 gives the best pooled-quality trainable row, and V3 is the best calibrated MPS row because it reduces false positives with error-focused calibration and precision-aware thresholding. V3 is important progress, but it is not yet the final best row because the CPU trainable campaign still has the highest pooled SPEC v2 Jaccard.

## Best Next Tests To Improve Jaccard And CI

1. Extend false-positive calibration to Full Lineage and test calibration rounds `1-3`, calibration weight `2-5`, and precision floors `0.50-0.70`.
2. Scope-aware calibration: keep a global threshold for comparability, but also test thresholds by layer scope or domain family. This targets Full Lineage variance directly.
3. Article V hybrid: use fast VMamba-Mesh/GNN as a high-recall candidate gate and run VMamba-Mesh-T only as a reranker on plausible pairs. This should improve precision and SF together.
4. Loss functions aimed at false positives: test asymmetric focal loss, Tversky loss or a soft-Jaccard surrogate, not only Weighted BCE.
5. Full Lineage LLM manifest: extend the Codex/GPT-5 hard-negative manifest beyond SPEC and tag each pair by reason category, so we know whether failures come from same-domain, same-layer or dense-structure ambiguity.
6. Stratified reporting: report Tier-1 vs Tier-2, SOR/SOT/SPEC and domain-family slices. This does not “fix” the IC, but it shows which slice causes the variance and prevents overclaiming.

## Mathematical Summary

Adapter score:

```text
s(u,v) = sum_i w_i f_i(u,v) / sum_i |w_i|
duplicate if s(u,v) >= threshold
```

Neural score:

```text
X_u, X_v = graph_context_tensor(graph, u/v)
h_u, h_v = VMambaStyleEncoder(X_u/X_v)
z = PairHead([h_u, h_v, |h_u-h_v|, h_u*h_v, auxiliary_features])
p_dup = sigmoid(z)
duplicate if p_dup >= threshold
```

SF-Jaccard:

```text
SFJ = Jaccard * N_pairs / ET
```
