# VMamba-Mesh Encoding

## 1. Definicoes

VMamba-Mesh adapta VMamba para grafos de linhagem Data Mesh. O modelo nao deve ver uma imagem natural; ele deve ver um tensor canonico que representa SOR, SOT, SPEC, estrutura, identidade semantica e sparsidade.

## 2. Componentes

- `CanonSort`: ordena nos por camada, dominio, grau e nome para estabilizar a matriz.
- `Block SOR-SOT-SPEC`: organiza regioes do tensor por camada de linhagem.
- `DiagFP`: usa a diagonal para fingerprint de tabela/schema quando a diagonal nao carrega arestas de linhagem.
- `MeshSS2D`: especializa a rota SS2D para fluxo SOR -> SOT -> SPEC.
- `HierInit`: inicializa memoria downstream com contexto upstream.
- `SparseGate`: reduz propagacao de memoria em regioes vazias de matrizes esparsas.
- `C5 Sparse Mask`: mascara binaria das coordenadas ativas, incluindo diagonal e evidencia nos canais C0/C1. C5 nao rotaciona a matriz nem preenche regioes vazias; as rotas pertencem ao MeshSS2D.

## 3. Contrato De Tensor

O estudo local usa tensores pequenos e reproduziveis, normalmente `[1, 3, 32, 32]`, com canais para estrutura, camada/dominio e identidade. O notebook de prototipo tambem descreve o contrato futuro para tensores de pares.

Fonte principal:

- `research/vmamba/notebooks/vmamba_mesh_prototype_isomera_case.ipynb`

## 4. Contrato De Modelo No Isomera

O artefato benchmarkavel atual preserva a interface:

```python
predict_pairs(graph: networkx.DiGraph) -> list[tuple[str, str]]
```

Esse contrato permite comparar VMamba, VMamba-Mesh, GNN, VF2 e Node Match no mesmo pipeline de metricas.

## 5. Implementacao Atual

Implementacao existente:

- `main/core/algorithms/vmamba_mesh.py`

O adaptador atual e deterministico. Ele calibra threshold com pares positivos e negativos amostrados, salva pickle e metadata, e pode ser roteado pelo benchmark.

## 6. Checklist

- Garantir ordem canonica antes de gerar matriz.
- Registrar seed, resolution, negative_ratio e threshold.
- Separar evidencias do adaptador atual de claims sobre o futuro modelo neural CUDA.
- Preservar `predict_pairs(graph)` para compatibilidade.
