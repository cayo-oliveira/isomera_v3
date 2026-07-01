# VMamba Foundation

## 1. Definicoes

Mamba e uma familia de modelos de espaco de estados seletivos. A ideia central e manter uma memoria recorrente eficiente em sequencias longas, usando parametros dependentes da entrada.

VMamba leva essa ideia para visao computacional. Como uma imagem e bidimensional, o modulo SS2D converte mapas 2D em rotas 1D, aplica selective scan e depois reconstrói a representacao espacial.

## 2. Conceitos Principais

- `VSSM`: Visual State-Space Model, o backbone visual do VMamba.
- `VSS block`: bloco residual que envolve normalizacao, SS2D e MLP.
- `SS2D`: rota 2D para 1D, selective scan e merge.
- `cross_scan`: cria rotas por linhas e colunas, nos sentidos direto e reverso.
- `cross_merge`: recombina as rotas em uma representacao 2D.
- `forward_type`: variantes internas do VMamba, como `v04`, `v05`, `v051d` e `v052d`.

## 3. Evidencia Local

Os notebooks locais validaram que o codigo oficial pode ser estudado sem alterar o clone upstream:

- `research/vmamba/notebooks/vmamba_local_source_smoke.ipynb`
- `research/vmamba/notebooks/vmamba_official_source_walkthrough_isomera_case.ipynb`

Resultados registrados:

- `cross_scan` recebeu entrada `[1, 1, 4, 4]` e produziu `[1, 4, 1, 16]`.
- `cross_merge` produziu `[1, 1, 16]`.
- Os forward types `v04`, `v05`, `v051d` e `v052d` executaram em smoke test.
- O modelo reduzido usado no estudo tem `83,586` parametros.
- A saida de smoke e `[1, 2]`, interpretada no Isomera como dois logits: nao duplicado e duplicado.

## 4. Limites

Os resultados oficiais do VMamba em ImageNet, COCO e ADE20K nao foram reproduzidos localmente porque exigem datasets externos, Linux/CUDA, Triton/selective-scan kernels e checkpoints/configs oficiais completos.

## 5. Referencias

- Fonte oficial: `research/vmamba/source/VMamba`
- Patch local de estudo CPU: `research/vmamba/source/VMamba_isomera_cpu_patch/vmamba_cpu.py`
- VMamba paper: `https://arxiv.org/abs/2401.10166`
- Mamba paper: `https://arxiv.org/abs/2312.00752`
