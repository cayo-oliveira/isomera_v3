# Relatório — Treinamento e artefatos em `modelos_gnn_separados/`

Data: 20/01/2026

Este documento descreve **o modelo**, **a lógica/pipeline** e **o código** que gerou os arquivos `.pkl` na pasta `isomera/notebooks/modelos_gnn_separados/`.

## 1) Onde o treinamento acontece

- Notebook de origem: `isomera/notebooks/exploracao_isomera.ipynb`
- O treinamento é disparado dentro da função `run_isomorphism_on_benchmarks(...)` quando `"GNN"` está presente na lista `algorithms`.
- Os modelos são treinados **por cenário** (um modelo por grafo `.gml`) e salvos com o nome do cenário.

## 2) O que são os arquivos em `modelos_gnn_separados/`

- Cada arquivo `graph_SOR{X}_D{Y}_seed42.pkl` corresponde a um `scenario_id` extraído do nome do `.gml` em `benchmark_graphs/`:
  - `scenario_id = gml_file.replace(".gml", "")`
  - `model_path = os.path.join("modelos_gnn_separados", f"{scenario_id}.pkl")`

### Conteúdo serializado (formato do `.pkl`)

Os arquivos são gerados via `pickle.dump((gnn.cpu(), clf.cpu()), f)`, ou seja:

- Um **tuple** `(gnn, clf)`
  - `gnn`: instância de `SubgraphGNN` (GIN + pooling)
  - `clf`: instância de `PairClassifier` (MLP binário)

Observação importante: como o pickle guarda referências ao caminho/classe Python, **para carregar esses `.pkl` fora do notebook** você precisa ter as mesmas classes (`GINLayer`, `SubgraphGNN`, `PairClassifier`) definidas no ambiente no momento do `pickle.load`.

## 3) Qual foi o modelo

### 3.1 Encoder de subgrafo: `SubgraphGNN` (GIN simplificado)

- 2 camadas do tipo GIN (`GINLayer` custom), com `eps` treinável.
- Ativação `ReLU` entre as camadas.
- Pooling por grafo: `global_mean_pool(x, batch)`.
- Entrada (`in_channels`) é **1 feature constante por nó**.

### 3.2 Classificador de par: `PairClassifier`

- Concatena embeddings dos dois subgrafos (`[emb1, emb2]`).
- MLP: `Linear(2*emb_size -> 128) + ReLU + Linear(128 -> 1)`.
- Treino com `nn.BCEWithLogitsLoss()` (saída em logits).

## 4) Lógica do treinamento (pipeline)

### 4.1 Extração de subgrafos

- Para cada nó do grafo, extrai um subgrafo local com o nó + sucessores imediatos:
  - `subgraph([node] + list(G.successors(node)))`

### 4.2 Conversão para PyTorch Geometric (`Data`)

- Converte o `networkx` subgrafo para `torch_geometric.data.Data`.
- `x`: vetor de 1s (todos os nós têm a mesma feature): `torch.ones((num_nodes, 1))`.
- `edge_index`: arestas do subgrafo mapeadas para índices contíguos.

### 4.3 Construção do dataset supervisionado por cenário

Para cada cenário (`scenario_id`):

- **Positivos**: pares reais vindos de `validations/real_pairs_{scenario_id}.json`, rotulados como `1.0`.
- **Negativos**: amostrados aleatoriamente entre nós, garantindo que não estão no conjunto positivo;
  - quantidade: `num_negatives = num_positives * 3`
  - filtra casos sem arestas (`edge_index.numel() > 0`).

### 4.4 Loop de treino

- Otimizador: Adam com `lr=0.01`.
- Épocas:
  - função base `train_and_save_gnn_model(..., epochs=3)`
  - mas o treinamento por cenário usa `train_and_save_models_by_scenario(..., epochs=10)` por padrão.
- Treina **par a par** (sem batching/mini-batch), setando `batch = zeros(...)` para tratar cada `Data` como “um único grafo”.
- Acurácia impressa no treino usa threshold **0.6** em `sigmoid(logit)`.

### 4.5 Inferência

- Carrega `(gnn, clf)` do `.pkl`.
- Gera scores para **todos os pares** de subgrafos no cenário (combinações de 2 nós).
- Threshold padrão na inferência: **0.3**.

## 5) Código exato que gerou o treinamento

Abaixo está o trecho (do notebook `exploracao_isomera.ipynb`) que define o modelo, prepara datasets por cenário, treina e salva em `modelos_gnn_separados/`, e também executa o benchmark:

```python
import os
import json
import time
import pickle
import random
import networkx as nx
import pandas as pd
from itertools import combinations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import global_mean_pool

# ===============================
# MODELOS GNN
# ===============================

class GINLayer(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(GINLayer, self).__init__()
        self.eps = nn.Parameter(torch.zeros(1))
        self.mlp = nn.Sequential(
            nn.Linear(in_channels, out_channels),
            nn.ReLU(),
            nn.Linear(out_channels, out_channels)
        )

    def forward(self, x, edge_index):
        row, col = edge_index
        agg = torch.zeros_like(x)
        agg.index_add_(0, row, x[col])
        out = self.mlp((1 + self.eps) * x + agg)
        return out

class SubgraphGNN(nn.Module):
    def __init__(self, in_channels=1, hidden_channels=64, out_channels=64):
        super(SubgraphGNN, self).__init__()
        self.gin1 = GINLayer(in_channels, hidden_channels)
        self.gin2 = GINLayer(hidden_channels, out_channels)

    def forward(self, x, edge_index, batch):
        x = self.gin1(x, edge_index)
        x = F.relu(x)
        x = self.gin2(x, edge_index)
        return global_mean_pool(x, batch)

class PairClassifier(nn.Module):
    def __init__(self, emb_size=64):
        super(PairClassifier, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(emb_size * 2, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        )

    def forward(self, emb1, emb2):
        emb1 = emb1.view(1, -1)
        emb2 = emb2.view(1, -1)
        x = torch.cat([emb1, emb2], dim=1)
        return self.fc(x).squeeze(1)

# ===============================
# FUNÇÕES AUXILIARES
# ===============================

def extract_subgraphs(G):
    subgraphs = {}
    for node in G.nodes:
        neighbors = list(G.successors(node))
        subgraphs[node] = G.subgraph([node] + neighbors).copy()
    return subgraphs

def graph_to_pyg_data(G_nx):
    mapping = {n: i for i, n in enumerate(G_nx.nodes)}
    edge_index = torch.tensor(
        [[mapping[u], mapping[v]] for u, v in G_nx.edges],
        dtype=torch.long
    ).t().contiguous()
    x = torch.ones((len(G_nx.nodes), 1))
    return Data(x=x, edge_index=edge_index)

# ===============================
# DATASET POR CENÁRIO
# ===============================

def create_datasets_by_scenario(graph_dir="benchmark_graphs", validation_dir="validations"):
    scenario_datasets = {}
    for filename in os.listdir(validation_dir):
        if filename.endswith(".json") and filename.startswith("real_pairs_"):
            scenario_id = filename.replace("real_pairs_", "").replace(".json", "")
            gml_path = os.path.join(graph_dir, f"{scenario_id}.gml")

            with open(os.path.join(validation_dir, filename)) as f:
                real_pairs = json.load(f)

            G = nx.read_gml(gml_path)
            subgraphs = extract_subgraphs(G)
            nodes = list(subgraphs.keys())
            real_set = set(tuple(sorted(p)) for p in real_pairs)

            dataset = []

            # ✅ Positivos (pares reais)
            for u, v in real_set:
                g1 = graph_to_pyg_data(subgraphs[u])
                g2 = graph_to_pyg_data(subgraphs[v])
                dataset.append((g1, g2, 1.0))

            num_positives = len(real_set)
            num_negatives = num_positives * 3

            # ⚠️ Negativos (pares aleatórios não-isomorfos)
            negative_set = set()
            attempts = 0
            max_attempts = 5000
            while len(negative_set) < num_negatives and attempts < max_attempts:
                u, v = random.sample(nodes, 2)
                pair = tuple(sorted((u, v)))
                if pair not in real_set and pair not in negative_set:
                    g1 = graph_to_pyg_data(subgraphs[u])
                    g2 = graph_to_pyg_data(subgraphs[v])
                    if g1.edge_index.numel() > 0 and g2.edge_index.numel() > 0:
                        dataset.append((g1, g2, 0.0))
                        negative_set.add(pair)
                attempts += 1

            print(f"📦 Dataset para {scenario_id}: {len(real_set)} positivos, {len(negative_set)} negativos")
            scenario_datasets[scenario_id] = dataset

    return scenario_datasets

# ===============================
# TREINO + SAVE
# ===============================

def train_and_save_gnn_model(dataset, model_path="modelos_gnn/gnn_model.pkl", epochs=3, lr=0.01):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    gnn = SubgraphGNN().to(device)
    clf = PairClassifier().to(device)
    optimizer = torch.optim.Adam(list(gnn.parameters()) + list(clf.parameters()), lr=lr)
    criterion = nn.BCEWithLogitsLoss()

    print(f"🧠 Treinando modelo: {model_path} com {len(dataset)} pares...")
    for epoch in range(epochs):
        random.shuffle(dataset)
        total_loss = 0
        correct = 0
        total = 0
        for g1, g2, label in dataset:
            g1, g2 = g1.to(device), g2.to(device)
            g1.batch = torch.zeros(g1.num_nodes, dtype=torch.long).to(device)
            g2.batch = torch.zeros(g2.num_nodes, dtype=torch.long).to(device)
            emb1 = gnn(g1.x, g1.edge_index, g1.batch).unsqueeze(0)
            emb2 = gnn(g2.x, g2.edge_index, g2.batch).unsqueeze(0)
            pred = clf(emb1, emb2)
            loss = criterion(pred, torch.tensor([label], dtype=torch.float, device=device))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()

            # Acurácia simples
            predicted_label = (torch.sigmoid(pred).item() >= 0.6)
            if predicted_label == bool(label):
                correct += 1
            total += 1

        acc = 100 * correct / total if total > 0 else 0.0
        print(f"📚 Época {epoch+1}/{epochs} — Loss: {total_loss:.4f} — 🎯 Acurácia: {acc:.2f}%")

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    with open(model_path, "wb") as f:
        pickle.dump((gnn.cpu(), clf.cpu()), f)
    print(f"✅ Modelo salvo: {model_path}")


def train_and_save_models_by_scenario(datasets_dict, output_base_dir="modelos_gnn_separados", epochs=10, lr=0.01):
    os.makedirs(output_base_dir, exist_ok=True)
    for scenario_id, dataset in datasets_dict.items():
        model_path = os.path.join(output_base_dir, f"{scenario_id}.pkl")
        train_and_save_gnn_model(dataset, model_path=model_path, epochs=epochs, lr=lr)

# ===============================
# LOAD + PREDIÇÃO
# ===============================

def predict_isomorphism_with_saved_gnn(G, model_path="modelos_gnn/gnn_model.pkl", threshold=0.3):
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Modelo GNN ausente em: {model_path}")
    with open(model_path, "rb") as f:
        gnn, clf = pickle.load(f)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    gnn, clf = gnn.to(device), clf.to(device)

    subgraphs = extract_subgraphs(G)
    nodes = list(subgraphs.keys())
    isomorphic_pairs = []

    for u, v in combinations(nodes, 2):
        g1_data = graph_to_pyg_data(subgraphs[u])
        g2_data = graph_to_pyg_data(subgraphs[v])

        if g1_data.edge_index.dim() < 2 or g1_data.edge_index.shape[1] == 0:
            continue
        if g2_data.edge_index.dim() < 2 or g2_data.edge_index.shape[1] == 0:
            continue

        g1 = g1_data.to(device)
        g2 = g2_data.to(device)
        g1.batch = torch.zeros(g1.num_nodes, dtype=torch.long).to(device)
        g2.batch = torch.zeros(g2.num_nodes, dtype=torch.long).to(device)

        with torch.no_grad():
            emb1 = gnn(g1.x, g1.edge_index, g1.batch).unsqueeze(0)
            emb2 = gnn(g2.x, g2.edge_index, g2.batch).unsqueeze(0)
            score = torch.sigmoid(clf(emb1, emb2))
            print(f"[DEBUG] {u} ↔ {v} → score: {score.item():.4f}")
            if score.item() >= threshold:
                isomorphic_pairs.append((u, v))

    return isomorphic_pairs


def predict_isomorphism_by_scenario(G, scenario_id, model_dir="modelos_gnn_separados", threshold=0.3):
    model_path = os.path.join(model_dir, f"{scenario_id}.pkl")
    return predict_isomorphism_with_saved_gnn(G, model_path=model_path, threshold=threshold)

# ===============================
# ORQUESTRAÇÃO (TREINA + BENCHMARK)
# ===============================

def run_isomorphism_on_benchmarks(
    input_dir="benchmark_graphs",
    output_dir="predicted_pairs",
    algorithms=["VF2", "NodeMatch", "GNN"],
    runs=2,
    time_log="execution_times.csv"
):
    os.makedirs(output_dir, exist_ok=True)

    for f in os.listdir(output_dir):
        os.remove(os.path.join(output_dir, f))

    if "GNN" in algorithms:
        datasets_by_scenario = create_datasets_by_scenario()
        train_and_save_models_by_scenario(datasets_by_scenario)

    execution_data = []
    gml_files = [f for f in os.listdir(input_dir) if f.endswith(".gml")]

    total_steps = len(gml_files) * len(algorithms)
    current_step = 0

    for gml_file in gml_files:
        gml_path = os.path.join(input_dir, gml_file)
        scenario_id = gml_file.replace(".gml", "")
        G = nx.read_gml(gml_path)

        for algo in algorithms:
            current_step += 1
            progress = (current_step / total_steps) * 100
            print(f"\n📈 Progresso: {progress:.2f}% ({current_step}/{total_steps})")
            print(f"🚀 Executando {algo} em {scenario_id}...")

            total_time = 0
            all_pairs = set()

            for _ in range(runs if algo != "GNN" else 1):
                start = time.time()
                if algo == "GNN":
                    pairs = predict_isomorphism_by_scenario(G, scenario_id)
                else:
                    pairs = run_isomorphism(G, algorithm=algo)
                end = time.time()
                total_time += (end - start)
                all_pairs.update(tuple(sorted(p)) for p in pairs)

            avg_time = total_time / (1 if algo == "GNN" else runs)
            filename = f"{output_dir}/pairs_{scenario_id}_{algo}.json"
            with open(filename, "w") as f:
                json.dump(sorted(list(all_pairs)), f, indent=4)

            execution_data.append({
                "scenario": scenario_id,
                "algorithm": algo,
                "runs": 1 if algo == "GNN" else runs,
                "avg_time_seconds": round(avg_time, 6),
            })

            print(f"✅ Resultado salvo: {filename} | Tempo médio: {avg_time:.6f} s")

    df = pd.DataFrame(execution_data)
    df.to_csv(time_log, index=False)
    print(f"\n📊 Tabela de tempos salva em: {time_log}")


def run_isomorphism(G, algorithm="VF2"):
    subgraphs = [(node, G.subgraph([node] + list(G.successors(node)))) for node in G.nodes]
    isomorphic_pairs = []
    for i in range(len(subgraphs)):
        for j in range(i + 1, len(subgraphs)):
            if algorithm == "VF2":
                if nx.is_isomorphic(subgraphs[i][1], subgraphs[j][1]):
                    isomorphic_pairs.append((subgraphs[i][0], subgraphs[j][0]))
            elif algorithm == "NodeMatch":
                if nx.is_isomorphic(subgraphs[i][1], subgraphs[j][1], node_match=lambda x, y: x == y):
                    isomorphic_pairs.append((subgraphs[i][0], subgraphs[j][0]))
    return isomorphic_pairs

# ✅ Rodar
run_isomorphism_on_benchmarks()
```

## 6) Observações que afetam resultados

- O texto explicativo do notebook menciona `GCNConv`, mas o código efetivamente usado define um **GIN custom** (`GINLayer`).
- `x` é constante (todos 1s). Então, a distinção vem essencialmente da estrutura do subgrafo (arestas) e da agregação.
- O threshold muda entre:
  - treino (acurácia impressa): `0.6`
  - inferência/predição: `threshold=0.3` (default)

## 7) Como reproduzir (rápido)

- Abra `isomera/notebooks/exploracao_isomera.ipynb`.
- Garanta que as pastas `benchmark_graphs/` e `validations/` existam no diretório de trabalho do notebook.
- Execute a célula que chama `run_isomorphism_on_benchmarks()`.
- Os modelos serão gerados em `modelos_gnn_separados/` (relativo ao diretório de execução do notebook).
