# VMamba-Mesh Interpretability

## 1. Objetivo

Mostrar por que um par foi classificado como duplicado ou nao duplicado, conectando grafo, tensor, rotas SS2D, canais e metricas.

## 2. Artefatos Interpretaveis

- Rotas `cross_scan` 4x4.
- Mapa dos canais do tensor de linhagem.
- Heatmaps de contexto SS2D.
- Comparacao de grafo simples e complexo.
- Ablation ladder: Vanilla VMamba, +CanonSort, +DiagFP, +MeshSS2D, +HierInit, +SparseGate.
- ERF estrutural para SOR16 e rotas SS2D.
- Saliency neural pos-treino quando houver pickle VMamba-T ou VMamba-Mesh-T carregavel.
- Pacote auditavel em `main/data/research_reports/*_vmamba_interpretability_*`.

Referencia final usada no Article IV, livro e video: benchmark `tpc_ds_genai_spec_v2`, cenario `graph_SOR16_D1_seed42`, par `SPEC_customer_summary_D1` vs `SPEC_store_sales_summary_D1`. O pacote smoke esperado registra score aproximado `0.2232`, threshold `0.2000` e decisao `duplicate`. O grafo, a matriz e os canais descrevem o contexto do SOR16-D1; a saliency neural e local ao par e ao checkpoint carregado.

## 3. Figuras Existentes

Fontes locais:

- `research/vmamba/outputs/local_source_smoke/vmamba_cross_scan_routes.png`
- `research/vmamba/outputs/official_source_walkthrough/official_cross_scan_4x4_routes.png`
- `research/vmamba/outputs/official_source_walkthrough/isomera_real_graph_tensor_channels.png`
- `research/vmamba/outputs/vmamba_mesh_didactic/`
- `papercept_compiler/workspace/creation/final/20260429_182244_vmamba_mesh_operational_journal_draft/figures/`

## 4. ERF

O VMamba oficial inclui analises em:

- `research/vmamba/source/VMamba/analyze/erf.py`

No Isomera, ERF estrutural e rotas SS2D sao usados como explicacao operacional do tensor de linhagem. A reproducao fiel do ERF oficial do VMamba upstream ainda exige ambiente CUDA/datasets/checkpoints, mas o app agora tambem calcula saliency neural local para os modelos treinaveis do Isomera.

## 5. Model Interpretability No App

Fluxo implementado:

1. `Study Lab -> Model Interpretability`.
2. Selecionar um relatorio ou manifest ja gerado.
3. Selecionar benchmark, cenario e par.
4. Selecionar `Structural C0-C5 explanation` ou um pickle `VMamba-T`/`VMamba-Mesh-T`.
5. Clicar `Run Interpretability`.

Para reproduzir as figuras finais, usar `tpc_ds_genai_spec_v2`, `graph_SOR16_D1_seed42`, `SPEC_customer_summary_D1` contra `SPEC_store_sales_summary_D1`, e um pickle `VMamba-Mesh-T` salvo pela campanha SPEC v2.

Saidas:

- `left_channels.png`: tensor do primeiro subgrafo.
- `right_channels.png`: tensor do segundo subgrafo.
- `pair_difference.png`: diferenca absoluta entre os tensores.
- `structural_influence.png`: mapa estrutural quando nao ha pickle neural.
- `neural_saliency.png`: saliency por canal para modelos treinaveis.
- `saliency_aggregate.png`: mapa agregado de sensibilidade.
- `manifest.json`: benchmark, cenario, par, modelo, score, threshold e decisao.
- `interpretability_trace.csv`: trilha auditavel de arquivos, parametros e etapas.

Formula usada na saliency neural:

`S = |d p_duplicate / d X_u| * |X_u| + |d p_duplicate / d X_v| * |X_v|`

Depois o Isomera agrega `S` por canal para mostrar a contribuicao relativa de C0-C5.

## 6. Diretriz De UI

O app deve mostrar trilha operacional, nao raciocinio interno. A explicacao aceitavel inclui:

- quais parametros foram escolhidos;
- qual arquivo foi usado;
- qual modelo e checkpoint/pickle foi executado;
- quais features/canais tiveram maior peso ou contraste;
- quais metricas foram geradas;
- se o resultado bateu com a evidencia esperada.
