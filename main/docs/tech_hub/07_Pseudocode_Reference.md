# 07 — Pseudocode Reference

> **Navigation:** [README](README.md) | [01 What Is Isomera](01_What_Is_Isomera.md) | [02 Data Flow](02_Data_Flow_and_State.md) | [03 UI Tabs](03_UI_Tabs_Guide.md) | [04 Core Modules](04_Core_Modules.md) | [05 Algorithms](05_Algorithms_and_Models.md) | [06 Libraries](06_Libraries_and_Stack.md) | [08 Graph Maps](08_Graph_Maps.md)

---

This file contains formal pseudocode for every major procedure in Isomera. These pseudocode descriptions are algorithm-level — they describe *what* happens without language-specific syntax. For the actual Python code, see [04 Core Modules](04_Core_Modules.md) and [05 Algorithms](05_Algorithms_and_Models.md).

---

## Procedure 1: Build Graph (4 Modes)

### Mode A: Manual construction (Tab 2)

```
procedure BUILD_GRAPH_MANUAL(user_inputs):
    G ← new DiGraph
    for each edge (src, tgt) in user_inputs.edges:
        G.add_node(src)
        G.add_node(tgt)
        G.add_edge(src, tgt)
    session_state["initial_graph"] ← G.copy()    // immutable reference
    session_state["graph"] ← G.copy()             // mutable working copy
    session_state["pairs"] ← []
    session_state["removed_pairs"] ← []
    return G
```

### Mode B: Upload GML (Tab 1)

```
procedure BUILD_GRAPH_UPLOAD(file_bytes):
    G ← nx.read_gml(file_bytes)
    if G is not DiGraph: G ← G.to_directed()
    session_state["initial_graph"] ← G.copy()
    session_state["graph"] ← G.copy()
    return G
```

### Mode C: Random generation (Tab 3)

```
procedure BUILD_GRAPH_RANDOM(sor, n_domains, seed):
    G ← generate_random_lineage_graph(sor, n_domains, seed)
    // see Procedure 2 for internals
    session_state["initial_graph"] ← G.copy()
    session_state["graph"] ← G.copy()
    return G
```

### Mode D: Benchmark (Tab 4)

```
procedure BUILD_GRAPH_BENCHMARK(sor, domain_id, seed):
    G ← generate_random_lineage_graph(sor, domain_id, seed)
    // graph is ephemeral; NOT stored in session_state
    // benchmark uses its own loop context
    return G
```

---

## Procedure 2: Random Lineage Graph Generation

```
procedure GENERATE_RANDOM_LINEAGE_GRAPH(sor, n_domains, seed):
    rng ← Random(seed)
    G ← new DiGraph

    for d = 1 to n_domains:
        // Create SOR layer nodes
        sor_nodes ← []
        for i = 1 to sor:
            name ← "D{d}_SOR{i}"
            G.add_node(name, layer="SOR", domain=d)
            sor_nodes.append(name)

        // Create SOT layer (4 nodes per domain)
        sot_nodes ← []
        for i = 1 to 4:
            name ← "D{d}_SOT{i}"
            G.add_node(name, layer="SOT", domain=d)
            sot_nodes.append(name)
            // Connect multiple SOR nodes to each SOT node
            fanin ← rng.choice(1..min(3, sor))
            parents ← rng.sample(sor_nodes, fanin)
            for p in parents: G.add_edge(p, name)

        // Create SPEC layer (2 nodes per domain)
        spec_nodes ← []
        for i = 1 to 2:
            name ← "D{d}_SPEC{i}"
            G.add_node(name, layer="SPEC", domain=d)
            spec_nodes.append(name)
            // Connect 1–2 SOT nodes to each SPEC node
            fanin ← rng.choice(1..2)
            parents ← rng.sample(sot_nodes, fanin)
            for p in parents: G.add_edge(p, name)

    // Timestamp-based GML save
    ts ← datetime.now().strftime("%Y%m%d_%H%M%S")
    nx.write_gml(G, f"gml_package/random_lineage_{ts}.gml")

    return G
```

**Key invariants:**
- SOR nodes: `sor × n_domains` total.
- SOT nodes: `4 × n_domains` total.
- SPEC nodes: `2 × n_domains` total.
- Edges flow strictly: SOR → SOT → SPEC. No cross-layer backward edges.
- GML saved immediately; the in-memory graph is the same object, not re-read.

---

## Procedure 3: Pair Detection (VF2 / Node Match)

```
procedure DETECT_PAIRS_MATCHING(G, algorithm):
    subgraphs ← []
    for each node v in G:
        S_v ← G.subgraph({v} ∪ successors(v)).copy()
        subgraphs.append((v, S_v))

    pairs ← []
    for each (i, j) with i < j:
        (a, S_a) ← subgraphs[i]
        (b, S_b) ← subgraphs[j]

        if algorithm == VF2:
            match ← is_isomorphic(S_a, S_b)
        else:  // Node Match
            match ← is_isomorphic(S_a, S_b, node_match := λ x,y → x==y)

        if match: pairs.append((a, b))

    return pairs
```

**Complexity:** $O(n^2)$ calls to `is_isomorphic`, each $O(k!)$ worst case where $k$ = subgraph size. In practice much faster due to early termination and degree-based pruning inside VF2.

---

## Procedure 4: Pair Detection (GIN)

```
procedure DETECT_PAIRS_GIN(G, pkl_path, threshold=0.3):
    // Load model
    (gnn, clf) ← load_pickle(pkl_path)
    gnn.eval(); clf.eval()

    // Build subgraph embeddings
    embeddings ← {}
    for each node v in G:
        S_v ← G.subgraph({v} ∪ successors(v)).copy()
        if |E(S_v)| == 0: continue   // skip degenerate subgraphs
        data ← to_pyg_data(S_v)      // x = ones, edge_index = edges
        data.batch ← zeros(|V(S_v)|)
        embeddings[v] ← gnn(data.x, data.edge_index, data.batch)  // h_G ∈ R^64

    // Score all pairs
    pairs ← []
    for each (u, v) in Combinations(embeddings.keys(), 2):
        score ← sigmoid(clf(embeddings[u], embeddings[v]))
        if score ≥ threshold:
            pairs.append((u, v))

    return pairs
```

**Note:** Embeddings are computed once per node, not per pair. This is the amortization advantage over matching (which solves a new isomorphism problem per pair).

---

## Procedure 5: Validation and Removal

```
procedure APPLY_REMOVALS(G, pairs_to_remove):
    G_new ← G.copy()               // never mutate initial_graph
    removed ← []
    for each pair (u, v) in pairs_to_remove:
        if v in G_new.nodes:
            G_new.remove_node(v)   // remove second node of pair
            removed.append((u, v))
    session_state["graph"] ← G_new
    session_state["removed_pairs"] ← removed
    return G_new
```

**Protection:** Isomera checks `session_state["protection_active"]` before calling this procedure. If True, the call is blocked and a warning is shown in the UI.

**Decision — remove v (not u):** The first node in the pair is the "survivor." Conceptually, `u` is the original table and `v` is the redundancy. In practice, the user can reorder the pair before confirming removal.

---

## Procedure 6: Metrics — Single Run

```
procedure COMPUTE_METRICS(predicted_pairs, ground_truth_pairs, all_possible_pairs):
    TP ← |predicted ∩ ground_truth|
    FP ← |predicted \ ground_truth|
    FN ← |ground_truth \ predicted|
    TN ← |all_possible \ (predicted ∪ ground_truth)|

    Acc ← (TP + TN) / |all_possible_pairs|   // only valid when GT complete
    Prec ← TP / (TP + FP)                    // 0 if TP+FP=0
    Recall ← TP / (TP + FN)                  // 0 if TP+FN=0
    F1 ← 2 * Prec * Recall / (Prec + Recall) // 0 if denominator=0

    return {TP, FP, FN, TN, Acc, Prec, Recall, F1}
```

**Key constraint:** `Acc` requires `ground_truth_complete=True`. When only known pairs are provided (partial validation), TN is meaningless and Acc is invalid.

---

## Procedure 7: Benchmark Pipeline

```
procedure BENCHMARK(algorithms, scenario_families, runs_per_algo=25):
    results ← []

    for each family F in scenario_families:
        G ← load_or_generate_graph(F.sor, F.domain, F.seed)
        GT ← load_ground_truth(F)                   // known redundant pairs
        all_pairs ← all_possible_pairs(G)

        for each algorithm A in algorithms:
            // Measure execution time over 'runs' runs
            times ← []
            for r = 1 to runs:
                t_start ← perf_counter()
                predicted ← A.predict_pairs(G)
                t_end ← perf_counter()
                times.append(t_end - t_start)

            ET ← mean(times)                        // execution time
            metrics ← COMPUTE_METRICS(predicted, GT, all_pairs)
            SF ← (metrics.Acc × |all_pairs|) / ET   // scoring function

            results.append({
                "algorithm": A.name,
                "family": F,
                "ET": ET,
                "ACC": metrics.Acc,
                "SF": SF,
                **metrics
            })

    return results
```

**Note:** `predicted` is computed once, then timed over `runs` loops. This is important: the prediction result is obtained from the first call; timing loops repeat the computation to get a stable ET estimate.

---

## Procedure 8: GIN Training

```
procedure TRAIN_GIN(scenario_graph G, positive_pairs, epochs=10, lr=0.01, neg_ratio=3):
    // Build training dataset
    dataset ← []
    for (u, v) in positive_pairs:
        dataset.append((u, v, label=1))
    negatives ← 0
    attempts ← 0
    while negatives < |positive_pairs| * neg_ratio and attempts < 5000:
        u, v ← random_pair(G.nodes)
        if (u, v) not in positive_pairs and (v, u) not in positive_pairs:
            dataset.append((u, v, label=0))
            negatives ← negatives + 1
        attempts ← attempts + 1

    shuffle(dataset)

    // Build subgraph embeddings
    subgraphs ← {v: to_pyg_data(G.subgraph({v} ∪ successors(v))) for v in G.nodes}

    // Initialize models
    gnn ← SubgraphGNN(in=1, hidden=64, out=64)
    clf ← PairClassifier(emb_size=64)
    optimizer ← Adam(gnn.parameters() + clf.parameters(), lr=lr)
    criterion ← BCEWithLogitsLoss()

    // Training loop
    for epoch = 1 to epochs:
        epoch_loss ← 0
        correct ← 0
        for (u, v, label) in dataset:
            if subgraphs[u].edge_index empty or subgraphs[v].edge_index empty:
                continue
            optimizer.zero_grad()
            emb_u ← gnn(subgraphs[u])
            emb_v ← gnn(subgraphs[v])
            logit ← clf(emb_u, emb_v)
            loss ← criterion(logit, tensor([label], float))
            loss.backward()
            optimizer.step()
            epoch_loss ← epoch_loss + loss.item()
            pred ← (sigmoid(logit) ≥ 0.6)           // training monitor threshold
            correct ← correct + (pred == label ? 1 : 0)
        print(epoch, epoch_loss / |dataset|, correct / |dataset|)

    // Save model
    save_pickle((gnn, clf), output_path)
    return gnn, clf
```

**Note on training threshold vs inference threshold:** During training the threshold 0.6 is used only for logging/monitoring accuracy prints. The actual training signal is the BCE loss (continuous, not thresholded). During inference, threshold is 0.3 to favor recall.

---

## Procedure 9: Scoring Function (SF) Calculation

```
procedure COMPUTE_SF(acc, n_pairs, et):
    if et == 0: return None          // avoid division by zero (should not happen)
    return (acc * n_pairs) / et
```

**Interpretation:** SF measures how many "correct pair decisions" the algorithm makes per second. An algorithm with higher SF than another dominates on the throughput-accuracy trade-off.

**Use case:** Used in the paper to compare GIN vs Node Match at SOR=16 D=4:
- GIN: SF = 19.0 (ACC × pairs / ET)
- Node Match: SF = 21.1

Despite GIN having higher ACC at SOR=16 overall, the ET overhead brings its SF below Node Match at D=4 specifically.

---

## Procedure 10: End-to-End Interactive Session

This procedure describes the full sequence of a typical user session in the Isomera UI:

```
procedure INTERACTIVE_SESSION():
    // Phase 1: Graph ingestion
    G ← BUILD_GRAPH(mode=user_choice)   // upload, random, or manual
    display(G)

    // Phase 2: Algorithm selection and detection
    algorithm ← user_select(["VF2", "Node Match (Custom)", "GIN/GNN Pickle"])
    if algorithm == GIN: pkl_path ← user_upload(".pkl file")
    pairs ← algorithm.predict_pairs(G)
    session_state["pairs"] ← pairs
    display_pairs(pairs)

    // Phase 3a: Manual validation (UI)
    if user_chooses_manual_validation:
        validated_df ← st.data_editor(pairs_as_df)
        session_state["validated_pairs"] ← extract_confirmed(validated_df)

    // Phase 3b: CSV validation (upload ground truth)
    if user_chooses_csv_validation:
        df_csv ← read_csv(uploaded_file)
        metrics ← COMPUTE_METRICS(pairs, df_csv.pairs, all_possible_pairs(G))
        display_metrics(metrics)

    // Phase 4: Removal (with protection check)
    if user_confirms and not session_state["protection_active"]:
        G_reduced ← APPLY_REMOVALS(G, session_state["validated_pairs"])
        session_state["graph"] ← G_reduced
        display(G_reduced)

    // Phase 5: Export
    if user_requests_export:
        export(session_state["pairs"], format=user_choice) // JSON / JSONL / GML
```
