# VMamba-Mesh Reproducibility

## 1. Objetivo

Reproduzir dentro do Isomera os numeros, imagens e artefatos usados no artigo VMamba-Mesh, com uma trilha auditavel de execucao.

## 2. Fontes

- Notebooks locais: `research/vmamba/notebooks/`
- Scripts: `research/vmamba/scripts/run_vmamba_mesh_genai_benchmark.py`
- Analise de revisao: `research/vmamba/scripts/run_vmamba_mesh_review_analysis.py`
- Outputs: `research/vmamba/outputs/`
- Pacote TeXLab: `papercept_compiler/workspace/creation/final/20260429_182244_vmamba_mesh_operational_journal_draft`

## 3. Benchmarks Principais

- `tpc_ds_genai_spec_v2`
- `tpc_ds_genai_full_lineage`
- `tpc_ds`

Os cenarios seguem o padrao `graph_SOR<k>_D<d>_seed42`.

## 4. Metricas

- `Jaccard = TP / (TP + FP + FN)`
- `Accuracy = (TP + TN) / (TP + TN + FP + FN)`
- `ET`: tempo de execucao.
- `SF-Jaccard = Jaccard * N_pairs / ET`
- `SF-Accuracy = Accuracy * N_pairs / ET`

Accuracy deve ser tratada como diagnostica porque ha forte desbalanceamento de pares negativos.

## 5. Numeros Esperados Do Artigo IV

Em `tpc_ds_genai_spec_v2`:

- Vanilla VMamba baseline: Jaccard aproximado `0.255548`.
- VMamba-Mesh Isomera adapter: Jaccard aproximado `0.274798`.

Em `tpc_ds_genai_full_lineage`:

- Vanilla VMamba baseline: Jaccard aproximado `0.111757`.
- VMamba-Mesh Isomera adapter: Jaccard aproximado `0.090915`.

Tempos dependem do hardware e devem ser comparados com tolerancia.

## 6. Trilha Auditavel

A reproducao deve registrar:

- artigo;
- benchmark;
- modelos;
- cenario/par;
- parametros;
- seed;
- arquivos lidos;
- arquivos gerados;
- metrica calculada;
- valor esperado;
- tolerancia;
- status: `match`, `within_tolerance`, `mismatch`, `not_available`.
