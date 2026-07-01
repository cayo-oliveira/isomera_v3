*{Abstract}

This report documents an end-to-end Isomera v2 execution: relational scenario selection, lineage graph materialization, manual validation, supervised dataset creation, model training, and benchmark publication. It is generated as a reproducible package containing the article draft, source data, model artifacts, figures, and metadata.

## Introduction

Isomera v2 supports redundancy analysis in Data Mesh-like architectures by representing data products and transformations as directed lineage graphs. The system combines graph visualization, candidate-pair filtering, manual ground-truth creation, benchmark execution, and GNN-based model training.

The main reproducible path used by this report is database source selection, relational schema loading, lineage graph materialization, candidate-pair reduction, manual duplicate validation, supervised dataset publication, model training, benchmark execution, and article package export.

## Related Work Context

The report package is designed to support a later IEEE-style article. It connects graph-based lineage modeling, graph isomorphism, duplicate detection, and graph neural networks into one reproducible experimental workflow.

## System Architecture

Isomera v2 separates source scenario materialization, curation, model training, benchmark execution, and publication packaging.

[h]

**External Sources / Benchmark Warehouse**\\
PostgreSQL schemas, GML files, or future database connectors\\[0.5em]
$$\\[0.2em]
**Scenario Materialization API**\\
database inspection, manifest-to-table mapping, relational-to-graph transformation, SOR--SOT--SPEC normalization\\[0.5em]
$$\\[0.2em]
**Scenario Studio**\\
candidate filters, graph/table review, autosaved duplicate labels, benchmark publication\\[0.5em]
$$\\[0.2em]
**Training and Benchmark Execution**\\
standard graph input, supervised validation dataset, model artifact, benchmark metrics\\[0.5em]
$$\\[0.2em]
**Publication Backend and Research Package**\\
MySQL publication tables, model pickle, JSON/CSV evidence, LaTeX, PDF, ZIP
}

The architecture deliberately separates the source benchmark warehouse from the publication backend. PostgreSQL represents the external relational benchmark under analysis. MySQL stores curated publication evidence, reviewed pairs, report summaries, and model references. This split prevents benchmark source data from being mixed with experimental metadata and makes it easier to export a reproducible package.

### Component Responsibilities and Rationale

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**component** & **responsibility** & **rationale** \\ 
Streamlit UI & Provides the interactive workflow for loading scenarios, reviewing candidate pairs, training models, inspecting stores, and exporting research packages. & Streamlit keeps the research prototype fast to iterate while still exposing every intermediate artifact needed for paper writing. \\ 
Scenario Materialization API & Converts PostgreSQL schemas, GML files, or manual graphs into one normalized graph contract. & Centralizes the table-to-graph transformation so UI, training, benchmark, and reports consume the same graph, edge table, adjacency matrix, and metadata. \\ 
PostgreSQL Scenario Warehouse & Stores benchmark relational scenarios as database schemas. & Represents the external relational environment being analyzed; it is the source of scenario data, not the operational backend. \\ 
MySQL Publication Backend & Stores published benchmarks, scenarios, nodes, edges, reviewed pairs, and publication reports. & Separates article/research evidence from the benchmark warehouse and prepares the project for a durable backend store. \\ 
GML/JSON File Layer & Stores portable graphs, labels, manifests, article captures, and exported package metadata. & Provides reproducible files for DOI/data sharing and makes the benchmark portable outside the local database. \\ 
Training Pipeline & Transforms normalized graphs and curated duplicate labels into supervised datasets and pickle model artifacts. & Keeps model input standardized so future GNN/CNN/other detectors can share the same upstream materialization contract. \\ 
Research Report Builder & Generates LaTeX, PDF, ZIP, figures, CSVs, JSONs, and model references from Article Capture evidence. & Turns experimental actions into article-ready evidence without manually copying app state into the manuscript. \\ 

### Architectural Layers

{3pt}
{1.18}
{|>{}p{0.26}|>{}p{0.62}|}

**layer** & **responsibility** \\ 
Source Warehouse & PostgreSQL/GML scenarios used as reproducible lineage sources. \\ 
Scenario Materialization API & Normalizes each scenario into graph, edge table, matrix, and metadata. \\ 
Curation and Validation & Produces supervised duplicate-pair datasets with filters and target labels. \\ 
Training and Benchmark & Routes detector families and model clusters to each evaluated scenario. \\ 
Research Reports & Exports JSON, CSV, figures, LaTeX, PDF, ZIP, and model references. \\ 

### Data Stores

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**store** & **technology** & **purpose** \\ 
PostgreSQL Scenario Warehouse & PostgreSQL & Relational benchmark source schemas. \\ 
MySQL Publication Backend & MySQL & Publication/backend evidence, logs, reports, and curated scenario metadata. \\ 
GML/JSON & Files & Portable graphs, labels, manifests, and model routing. \\ 
Research Packages & LaTeX/PDF/ZIP & Article-ready reproducibility package. \\ 

## Database Architecture

The benchmark warehouse is stored in PostgreSQL. Each benchmark scenario is represented by one schema, such as scenario\_sor2\_d5\_seed42. In practical terms, SOR2 means that the scenario was generated with two source-of-record nodes per configured domain group, D5 means that five business domains are present, and seed42 identifies the reproducible random seed/contract variant. If two scenarios are selected, Isomera reads two schemas and produces two normalized graphs, two validation datasets, and then one benchmark-level model/metrics package that references both scenarios.

The MySQL backend is used as the publication/research backend for scenarios, nodes, edges, reviewed pairs, model artifacts, reports, and future operational logs. SQLite is retained only as a local fallback while the backend migration is completed.

### TPC-DS Domain Catalog

The current TPC-DS pilot uses five practical business domains. The D identifiers are not arbitrary visual labels: they identify the domain bucket used to generate SOR, SOT, and SPEC tables and to later filter candidate pairs. Future D6/D7 domains should be added through the same manifest-based contract.

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.23}|>{}p{0.24}|>{}p{0.28}|}

**domain** & **practical\_ & **examples** & **extension\_ \\ 
D1 & Customer, catalog, and warehouse-performance context. & customer, customer\_demographics, catalog\_performance, warehouse\_logistics. & Keep D1 when the business view is customer/catalog performance. \\ 
D2 & Store, geography, customer attributes, and order summary context. & nation, store, customer\_attr, customer\_orders, customer\_summary. & Use the same pattern for another geography/store/customer domain. \\ 
D3 & Item, promotion, catalog sales, and analytical reuse context. & item, promotion, catalog\_sales, time\_analysis. & Use for product/promotion/catalog-sales analytical scenarios. \\ 
D4 & Date, time, customer orders, and warehouse stock context. & date\_dim, time\_dim, customer\_orders, warehouse\_stock. & Use for temporal and inventory-history scenarios. \\ 
D5 & Income band, warehouse, store sales, and store-sales summary context. & income\_band, warehouse, store\_sales, store\_sales\_summary. & Use for income/warehouse/store-sales scenarios. \\ 
D6+ & Future user-defined domain. & Any new business domain introduced by the user. & Add a manifest/mapping contract defining domain name, SOR tables, SOT tables, SPEC outputs, and lineage edges. \\ 

### Source Details

{3pt}
{1.18}
{|>{}p{0.26}|>{}p{0.62}|}

**field** & **value** \\ 
benchmark & tpc\_ds\_genai\_sot\_spec \\ 
display\_name & TPC-DS GenAI SOT + SPEC \\ 
architecture\_root & /Users/cayofel/Documents/GitHub/isomera\_v2/main/data/architectures/tpc\_ds\_genai\_sot\_spec \\ 
candidate\_scope & sot\_spec \\ 
runs & 10 \\ 
best\_of\_all & True \\ 

### Selected Benchmark Scenarios

When more than one scenario is selected, each PostgreSQL schema is materialized independently and then grouped under the same benchmark-level execution. The full scenario table is exported as CSV inside the package.

{3pt}
{1.18}
{|>{}p{0.14}|>{}p{0.17}|>{}p{0.17}|>{}p{0.17}|>{}p{0.23}|}

**scenario** & **schema** & **nodes** & **edges** & **positive\_ \\ 
graph\_SOR2\_D1\_seed42 & scenario\_sor2\_d1\_seed42 & 6 & 6 & 2 \\ 
graph\_SOR2\_D2\_seed42 & scenario\_sor2\_d2\_seed42 & 12 & 13 & 4 \\ 
graph\_SOR2\_D3\_seed42 & scenario\_sor2\_d3\_seed42 & 18 & 19 & 9 \\ 
graph\_SOR2\_D4\_seed42 & scenario\_sor2\_d4\_seed42 & 24 & 24 & 13 \\ 
graph\_SOR2\_D5\_seed42 & scenario\_sor2\_d5\_seed42 & 30 & 32 & 25 \\ 
graph\_SOR4\_D1\_seed42 & scenario\_sor4\_d1\_seed42 & 12 & 14 & 9 \\ 
graph\_SOR4\_D2\_seed42 & scenario\_sor4\_d2\_seed42 & 24 & 32 & 27 \\ 
graph\_SOR4\_D3\_seed42 & scenario\_sor4\_d3\_seed42 & 36 & 42 & 48 \\ 
graph\_SOR4\_D4\_seed42 & scenario\_sor4\_d4\_seed42 & 48 & 63 & 82 \\ 
graph\_SOR4\_D5\_seed42 & scenario\_sor4\_d5\_seed42 & 60 & 70 & 121 \\ 
graph\_SOR8\_D1\_seed42 & scenario\_sor8\_d1\_seed42 & 21 & 30 & 23 \\ 
graph\_SOR8\_D2\_seed42 & scenario\_sor8\_d2\_seed42 & 42 & 61 & 64 \\ 
graph\_SOR8\_D3\_seed42 & scenario\_sor8\_d3\_seed42 & 63 & 92 & 149 \\ 
graph\_SOR8\_D4\_seed42 & scenario\_sor8\_d4\_seed42 & 84 & 122 & 247 \\ 
graph\_SOR8\_D5\_seed42 & scenario\_sor8\_d5\_seed42 & 105 & 153 & 395 \\ 
graph\_SOR16\_D1\_seed42 & scenario\_sor16\_d1\_seed42 & 29 & 30 & 17 \\ 
graph\_SOR16\_D2\_seed42 & scenario\_sor16\_d2\_seed42 & 58 & 61 & 46 \\ 
graph\_SOR16\_D3\_seed42 & scenario\_sor16\_d3\_seed42 & 87 & 92 & 109 \\ 
graph\_SOR16\_D4\_seed42 & scenario\_sor16\_d4\_seed42 & 116 & 122 & 192 \\ 
graph\_SOR16\_D5\_seed42 & scenario\_sor16\_d5\_seed42 & 145 & 153 & 309 \\ 

### MySQL Publication Backend Validation

No rows available.

## Scenario Materialization API

Expose a reproducible source-to-graph transformation contract used by the UI, training code, benchmark runner, and report builder.

Technically, the API is the reproducibility boundary of Isomera. Every supported source must be transformed into the same materialized contract before visualization, validation, training, benchmarking, or reporting. This avoids having one representation for the UI and another for the model.

### API Functions

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**function** & **input** & **output** \\ 
load\_source & benchmark architecture or database schema & scenario graph and labels \\ 
normalize\_lineage & SOR/SOT/SPEC node metadata and edges & directed graph normalized to SOR -> SOT -> SPEC when semantics are available \\ 
candidate\_scope & all, SPEC, or SOT+SPEC & evaluated candidate-pair universe \\ 
route\_models & scenario name and detector cluster & scenario-specific pickle path or post-hoc best-of selector \\ 

### API Input/Output Contract

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**artifact** & **description** & **consumer** \\ 
normalized\_graph & NetworkX directed graph with canonical edge direction when layer semantics are available. & Scenario Studio, graph visualization, candidate filtering, training. \\ 
lineage\_structure & Node table with domain, layer, node, source table, semantic name, in-degree, and out-degree. & Research Reports, Admin inspection, article tables. \\ 
edge\_table & Directed edge table with origin, destination, and edge type. & Report package, DOI export, future semantic edge extensions. \\ 
adjacency\_matrix & Binary adjacency matrix aligned to the normalized graph. & Graph diagnostics, report figures, future CNN/image-based detector experiments. \\ 
source\_metadata & Database URL, schema, build mode, manifest usage, manifest path, table count, and graph build steps. & Article Capture, package manifest, reproducibility section. \\ 

### Normalization Method

The current normalization is not a general semantic inference engine. It is a deterministic layer-aware graph-direction procedure. It works reliably when the source exposes SOR, SOT, and SPEC semantics through names, node attributes, or a manifest. For arbitrary databases, Isomera needs a mapping contract before it can claim semantic SOR--SOT--SPEC normalization.

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**step** & **technical\_ & **limitation** \\ 
Layer detection & Each node is assigned a rank by inspecting node names and metadata: SOR=0, SOT=1, SPEC=2, OTHER=3. & If a database uses arbitrary names such as customers, orders, mart\_sales without a manifest or mapping, the API cannot know which layer each table belongs to. \\ 
Direction scoring & For every edge, the API compares source\_rank and target\_rank. Edges with source\_rank < target\_rank count as downstream; source\_rank > target\_rank count as upstream. & The score only measures consistency with known layer ranks. It does not infer business semantics by itself. \\ 
Graph reversal & If upstream\_edges\_before is greater than downstream\_edges\_before, all edges are reversed. Otherwise the graph is copied as-is. & Mixed or ambiguous graphs can be partially incorrect if the source does not expose layer semantics or a reliable manifest. \\ 
Manifest mode & When a benchmark manifest is available, it provides node, table\_name, semantic\_name, type/layer, domain, and explicit lineage edges. & This is the preferred article-grade mode, but it requires preparing or importing a mapping contract. \\ 
Foreign-key-only mode & Without a manifest, the API can inspect tables and foreign keys to build a graph, then apply the same direction heuristic. & Foreign keys are physical constraints, not necessarily transformation lineage. This mode is exploratory unless validated by the user. \\ 

### API Limits

{3pt}
{1.18}
{|>{}p{0.88}|}

**limit** \\ 
Generic databases without a manifest or SOR/SOT/SPEC semantics cannot be normalized semantically; they require a mapping contract. \\ 
Best-of-all routing is a diagnostic selector and must be reported as post-hoc/oracle-style evidence unless the selection policy is fixed before execution. \\ 
Accuracy is retained but SF-Jaccard is the primary metric under pair-imbalance. \\ 

## Pipeline

The pipeline is source $$ normalized graph $$ validation dataset $$ training dataset $$ model artifact.

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.23}|>{}p{0.24}|>{}p{0.28}|}

**stage** & **input** & **output** & **details** \\ 
source & tpc\_ds\_genai\_sot\_spec & 20 GML scenarios & Combined SOT and SPEC benchmark that merges default SOT positives with GenAI SPEC positives. \\ 
normalized graph & GML + node layer metadata & NetworkX directed graph & Edges and nodes are evaluated under the selected candidate scope. \\ 
validation dataset & real\_pairs JSON & 1891 positives inside 11210 candidates & Pairs outside the selected candidate scope are excluded from metric denominators. \\ 
model routing & scenario name + cluster map & pickle path per scenario & Best-of-all is post-hoc diagnostic routing when enabled. \\ 
benchmark execution & detector families & 10 family rows & 10 runs per detector family per scenario. \\ 

## Lineage Graph and Matrix Views

The normalized graph contains 1020 nodes and 1231 directed edges. The direction is normalized to SOR $$ SOT $$ SPEC whenever the manifest or table names expose those layers.

## Candidate Filtering and Ground Truth

The final supervised table is produced by selecting candidate filters, reviewing each pair, and assigning a binary target. The target is 1 for duplicate and 0 for not duplicate. This table is the ground truth used by the training pipeline. A small subset can be used only to smoke-test the MySQL store, but article-grade datasets must come from complete ground-truth review or a documented benchmark label source such as TPC-DS real\_pairs.

{3pt}
{1.18}
{|>{}p{0.26}|>{}p{0.62}|}

**quantity** & **value** \\ 
total\_pairs & 11210 \\ 
candidate\_pairs & 11210 \\ 
reviewed\_pairs & 11210 \\ 
duplicate\_pairs & 1891 \\ 

### Filter Protocol

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**filter** & **setting** & **effect** \\ 
candidate\_scope & sot\_spec & Defines the candidate-pair universe used by metrics. \\ 

### Supervised Validation Dataset

No rows available.

## Training Configuration

The current model family is the Graph Isomorphism Network Pair Classifier. The article-grade path uses a supervised validation dataset with target=1 for duplicate pairs and target=0 for non-duplicate pairs. Legacy-compatible runs can still derive negatives through negative sampling, but the report always records the effective loss, optimizer, split, and balancing strategy used to train the pickle.

The model input is intentionally standardized: any future connector must first produce the same normalized graph, edge table, adjacency matrix, and supervised pair table. This is what allows a pickle trained from one curated benchmark to be evaluated consistently by Benchmark \& Examples.

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.23}|>{}p{0.24}|>{}p{0.28}|}

**scenario** & **positive\_ & **negative\_ & **dataset\_ \\ 
graph\_SOR2\_D1\_seed42 & 2 & 4 & 6 \\ 
graph\_SOR2\_D2\_seed42 & 4 & 24 & 28 \\ 
graph\_SOR2\_D3\_seed42 & 9 & 57 & 66 \\ 
graph\_SOR2\_D4\_seed42 & 13 & 107 & 120 \\ 
graph\_SOR2\_D5\_seed42 & 25 & 165 & 190 \\ 
graph\_SOR4\_D1\_seed42 & 9 & 19 & 28 \\ 
graph\_SOR4\_D2\_seed42 & 27 & 93 & 120 \\ 
graph\_SOR4\_D3\_seed42 & 48 & 228 & 276 \\ 
graph\_SOR4\_D4\_seed42 & 82 & 414 & 496 \\ 
graph\_SOR4\_D5\_seed42 & 121 & 659 & 780 \\ 

Only the first 10 rows are shown; the full table is exported as CSV.

### Available Training Options

The following options are exposed in Isomera. The friendly name is what the user sees in the application; the technical function is what the backend actually executes or records.

{3pt}
{1.18}
{|>{}p{0.14}|>{}p{0.17}|>{}p{0.17}|>{}p{0.17}|>{}p{0.23}|}

**group** & **friendly\_ & **technical\_ & **formula** & **use** \\ 
optimizer & Adaptive gradient optimizer (torch.optim.Adam) & torch.optim.Adam & m\_t = beta\_1 m\_\{t-1\} + (1 - beta\_1) g\_t; v\_t = beta\_2 v\_\{t-1\} + (1 - beta\_2) g\_t2 & Default optimizer for the GNN. It adapts the learning rate per parameter using first and second gradient moments. \\ 
optimizer & Adam with decoupled weight decay (torch.optim.AdamW) & torch.optim.AdamW & theta\_t = theta\_\{t-1\} - eta (AdamGradient + lambda theta\_\{t-1\}) & Adam variant with decoupled weight decay. Useful when later experiments add explicit regularization. \\ 
optimizer & Stochastic gradient descent (torch.optim.SGD) & torch.optim.SGD & theta\_t = theta\_\{t-1\} - eta * grad\_theta L & Simple gradient descent baseline. It is slower but useful as a methodological control. \\ 
loss & Binary cross entropy on logits (torch.nn.BCEWithLogitsLoss) & torch.nn.BCEWithLogitsLoss & L = -[y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))] & Default binary classification loss. It receives raw logits and applies the sigmoid internally in a numerically stable way. \\ 
loss & Weighted binary cross entropy (torch.nn.BCEWithLogitsLoss(pos\_weight)) & torch.nn.BCEWithLogitsLoss(pos\_weight) & L = -[pos\_weight * y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))] & Same BCE loss, but positive duplicate pairs receive a larger weight when the dataset has many more negatives. \\ 
loss & Focal loss for rare duplicates (custom sigmoid focal loss) & custom sigmoid focal loss & FL(p\_t) = -alpha * (1 - p\_t)gamma * log(p\_t) & Focuses training on hard examples by down-weighting easy negatives. Useful when almost every pair is non-duplicate. \\ 
balancing & Weight duplicate class in the loss (torch.nn.BCEWithLogitsLoss(pos\_weight)) & torch.nn.BCEWithLogitsLoss(pos\_weight=N\_negative/N\_positive) & pos\_weight = N\_negative / N\_positive & Recommended default for article-grade training. It keeps the supervised dataset intact and increases the penalty for missing rare duplicate pairs. \\ 
balancing & Sample negatives by ratio (negative\_sampling) & negative\_sampling with negative\_ratio & N\_negative\_sampled = N\_positive * negative\_ratio & Legacy-compatible path. Positives come from curated labels and negatives are sampled from non-labeled graph pairs. \\ 
balancing & Use real distribution without balancing (no sampler/no class weight) & no balancing & D\_train = D\_train\_original & Keeps the imbalanced distribution exactly as produced by the supervised table. Useful as a baseline, but can hide duplicate failures behind high accuracy. \\ 
balancing & Reduce non-duplicates in training (random undersampling) & random undersampling of target=0 & N\_negative\_kept <= N\_positive * negative\_ratio & Keeps all positives and randomly reduces negatives. Faster, but may discard useful negative diversity. \\ 
balancing & Repeat duplicate pairs in training (random oversampling) & random oversampling of target=1 & N\_positive\_repeated = N\_negative & Duplicates positive rows so the model sees rare duplicate evidence more often. Can overfit if positives are too few. \\ 
balancing & Balanced training batches (balanced batch sampler) & balanced positive/negative epoch sampler & batch = 50\% target=1 + 50\% target=0 & Approximates balanced batches by oversampling positives before each epoch. This stabilizes gradients in highly imbalanced training. \\ 
balancing & Prefer difficult non-duplicates (hard negative mining) & structural hard-negative sampler & score = |nodes\_a - nodes\_b| + |edges\_a - edges\_b| & Keeps negatives whose subgraphs have similar size/edge profiles to positives. These are harder examples than random non-duplicates. \\ 

### Strategy Theory

The imbalance strategies below are not cosmetic labels. They change either the loss function or the composition of the training examples. This distinction matters for the article because duplicate pairs are rare and high accuracy can be achieved without discovering duplicates.

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.23}|>{}p{0.24}|>{}p{0.28}|}

**strategy** & **technical\_ & **formula** & **interpretation** \\ 
Weighted BCE & torch.nn.BCEWithLogitsLoss(pos\_weight) & L = -[w\_p y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))] & Keeps all validated pairs and increases the cost of missing rare duplicate pairs. This is the preferred first strategy when positives are scarce. \\ 
Focal Loss & custom sigmoid focal loss & FL(p\_t) = -alpha(1-p\_t)gamma log(p\_t) & Down-weights easy examples and concentrates gradient on hard or misclassified pairs. It is useful when the model otherwise learns only the dominant negative class. \\ 
Hard Negative Mining & structural hard-negative sampler + BCEWithLogitsLoss & score = |nodes\_a-nodes\_b| + |edges\_a-edges\_b| & Keeps non-duplicate pairs that look structurally similar to positives. This tests whether the model can separate difficult near-matches instead of only easy negatives. \\ 

### Isomera Staged Hyperparameter Protocol

The recommended Isomera protocol is a staged search, not an exhaustive grid. Exhaustive search grows combinatorially and would spend most compute on configurations that are unlikely to survive model selection. The staged protocol first screens representative scenarios, selects the top configurations by SF-Jaccard, and only then runs the complete 20-scenario validation. Users can still bypass this protocol and train a manual configuration when they want a single controlled run.

For the proposed grid, one configuration means one combination of training strategy, learning rate, hidden-channel size, dropout, and inference threshold. The reduced grid has 108 configurations. Across three benchmark variants, screening on five representative scenarios requires 1620 trainings. Final validation of the top five configurations per benchmark over all 20 scenarios adds 300 trainings, for a total of 1920 trainings before the final detector-family benchmark.

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.23}|>{}p{0.24}|>{}p{0.28}|}

**parameter** & **values** & **count** & **reason** \\ 
training strategy & Weighted BCE; Focal Loss; Hard Negatives & 3 & Compares the main imbalance-handling families used by the GNN pipeline. \\ 
learning rate & 0.001; 0.005; 0.010 & 3 & Controls optimizer step size and training stability. \\ 
hidden channels & 16; 32 & 2 & Controls embedding capacity while keeping the search lightweight. \\ 
dropout & 0.0; 0.1 & 2 & Tests whether regularization improves generalization on scarce positives. \\ 
inference threshold & 0.4; 0.5; 0.6 & 3 & Moves the decision boundary between conservative and recall-oriented duplicate detection. \\ 

{3pt}
{1.18}
{|>{}p{0.14}|>{}p{0.17}|>{}p{0.17}|>{}p{0.17}|>{}p{0.23}|}

**stage** & **scope** & **trainings** & **selection\_ & **protocol\_ \\ 
screening\_5\_scenarios & 3 benchmarks x 5 representative scenarios x 108 configs & 1620 & Rank configurations by SF-Jaccard, then retain top 5 per benchmark. & Documents broad search behavior without paying the cost of a full exhaustive grid. \\ 
full\_validation\_20\_scenarios & 3 benchmarks x 20 scenarios x top 5 configs & 300 & Retrain and evaluate only the top configurations across the complete benchmark suite. & Produces final results with complete scenario coverage and controlled compute cost. \\ 
benchmark\_final & Best GNN configurations vs VF2, Node Match, GNN TPC-DS v1, GNN GenAI v1, and GNN GenAI v2 & 0 & Report detector-family metrics by scenario and aggregate family. & Separates model-selection evidence from final detector-family comparison. \\ 

### Options Used in This Run

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.23}|>{}p{0.24}|>{}p{0.28}|}

**setting** & **selected** & **technical** & **effect\_run} \\ 
optimizer &  &  & updates GIN and pair-classifier parameters \\ 
loss &  &  & pos\_weight=-, alpha=-, gamma=- \\ 
balancing &  &  &  \\ 
train\_distribution &  & target counts after balancing & validation/test distribution= \\ 

### Training Data Flow

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**step** & **operation** & **real\_ \\ 
1. Normalize graph input & Load the curated scenario graph and normalize direction to SOR -> SOT -> SPEC. & scenarios=[] \\ 
2. Build node-centered subgraphs & For each candidate node, extract a local subgraph. SPEC nodes use upstream lineage; SOR nodes use downstream lineage; SOT nodes use both directions. & subgraphs generated from normalized NetworkX graph \\ 
3. Encode graph tensors & Convert each subgraph into node feature matrix x and edge\_index. Current baseline uses one scalar node feature per node. & x = ones(num\_nodes, 1) \\ 
4. Sample supervised pairs & Use the supervised validation table when available. In legacy-compatible runs, curated duplicate pairs define positives and negatives are sampled from non-labeled graph pairs. & negative\_ratio=, generated\_rows= \\ 
5. Split train/test & Split the supervised dataset into train and validation/test partitions. & train\_ratio=, test\_ratio=, train\_size=, val\_size= \\ 
6. Balance training distribution & Apply the selected imbalance strategy only to the training partition. The validation/test partition keeps its observed label distribution. & strategy=, operation= \\ 
7. GIN embedding layers & Apply Graph Isomorphism Network aggregation to produce one embedding per subgraph. & hidden\_channels= \\ 
8. Pair classifier & Concatenate two subgraph embeddings and classify the pair with an MLP binary head. & output logit interpreted through sigmoid for duplicate probability \\ 
9. Optimization & Optimize the configured loss with the selected optimizer over the configured epochs. & loss=, epochs=, learning\_rate=, dropout= \\ 

### Model and Hyperparameters

{3pt}
{1.18}
{|>{}p{0.26}|>{}p{0.62}|}

**field** & **value** \\ 
model\_family & VF2\_NodeMatch\_GNN\_clusters \\ 
model\_name & all\_detector\_families \\ 
model\_path &  \\ 
optimizer &  \\ 
loss &  \\ 
effective\_loss\_function &  \\ 
activation & ReLU in GIN/MLP hidden layers; sigmoid/logit interpretation at binary output \\ 
train\_ratio &  \\ 
test\_ratio &  \\ 
balance\_strategy &  \\ 
balance\_operation &  \\ 
pos\_weight &  \\ 
epochs &  \\ 
hidden\_channels &  \\ 
negative\_ratio &  \\ 
train\_size &  \\ 
validation\_size &  \\ 

### Training Results

The following table records observed training and validation/test behavior per epoch. The current execution uses a short epoch budget to keep the end-to-end validation fast; article-grade runs can increase the epoch budget while reporting the same table.

No rows available.

### Formula to Parameter Mapping

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**formula** & **meaning** & **values\_run} \\ 
h\_v(k) = MLP(k)((1 + eps(k)) h\_v(k-1) + sum\_\{u in N(v)\} h\_u(k-1)) & GIN layer update. Neighbor messages are summed and transformed by an MLP. & hidden\_channels= \\ 
z\_G = mean\_pool(\{h\_v(K)\}) & Subgraph embedding. Node embeddings are pooled into one vector. & embedding dimension= \\ 
y\_hat = sigmoid(MLP([z\_G1 || z\_G2])) & Pair classifier. Two subgraph embeddings are concatenated and classified. & binary target: duplicate=1, not\_duplicate=0 \\ 
L = -[y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))] & Configured training loss: . & optimizer=, learning\_rate=, pos\_weight=- \\ 
N\_negative\_sampled = N\_positive * negative\_ratio & Selected imbalance strategy: . & operation= \\ 

## Model Artifact

The trained pickle is copied into the report package and also referenced back to its original training location. For article reporting, GNN artifacts are interpreted as a detector family/cluster with scenario-specific artifact routing, not as one benchmark row per pickle.

{3pt}
{1.18}
{|>{}p{0.26}|>{}p{0.62}|}

**field** & **value** \\ 
original\_model\_path &  \\ 
package\_model\_path & models/model.pkl \\ 
expected\_input & normalized graph plus supervised pair table generated by the Scenario Materialization API \\ 

### Model Family / Cluster Reporting

The benchmark compares detector families. VF2 and Node Match are deterministic families without pickle artifacts. GNN v1 and GNN v2 are reported as families with scenario-specific pickle routing. This keeps the paper readable: the number of benchmark rows is the number of detector families, while the number of pickle files is reported as artifact count. The routing table is mandatory evidence: a cluster can only be interpreted as complete when every evaluated scenario maps to an explicit pickle artifact.

{3pt}
{1.18}
{|>{}p{0.14}|>{}p{0.17}|>{}p{0.17}|>{}p{0.17}|>{}p{0.23}|}

**model\_ & **artifact\_ & **scenario\_ & **coverage** & **reporting\_ \\ 
GNN TPC-DS v1 cluster & 20 & 20 & 20/20 & detector family with scenario-specific pickle routing \\ 
GNN GenAI SPEC v1 cluster & 20 & 20 & 20/20 & detector family with scenario-specific pickle routing \\ 
GNN GenAI SPEC Protocol rank 1 & 20 & 20 & 20/20 & detector family with scenario-specific pickle routing \\ 
GNN GenAI SPEC Protocol rank 2 & 20 & 20 & 20/20 & detector family with scenario-specific pickle routing \\ 
GNN GenAI SPEC Protocol rank 3 & 20 & 20 & 20/20 & detector family with scenario-specific pickle routing \\ 
GNN GenAI SPEC Protocol rank 4 & 20 & 20 & 20/20 & detector family with scenario-specific pickle routing \\ 
GNN GenAI SPEC Protocol rank 5 & 20 & 20 & 20/20 & detector family with scenario-specific pickle routing \\ 
GNN Best-of-all cluster selector & 20 & 20 & 20/20 & post-hoc diagnostic selector; cite separately from fixed detector families \\ 

### Scenario-Specific Artifact Routing

The PDF view uses artifact file names to keep the table readable. The exported CSV keeps the full absolute artifact paths for reproducibility.

{3pt}
{1.18}
{|>{}p{0.11}|>{}p{0.14}|>{}p{0.15}|>{}p{0.14}|>{}p{0.15}|>{}p{0.18}|}

**model\_ & **scenario** & **artifact\_ & **artifact\_ & **route\_ & **route\_ \\ 
GNN TPC-DS v1 cluster & graph\_SOR2\_D1\_seed42 & graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC v1 cluster & graph\_SOR2\_D1\_seed42 & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 1 & graph\_SOR2\_D1\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 2 & graph\_SOR2\_D1\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 3 & graph\_SOR2\_D1\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 4 & graph\_SOR2\_D1\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 5 & graph\_SOR2\_D1\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN TPC-DS v1 cluster & graph\_SOR2\_D2\_seed42 & graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC v1 cluster & graph\_SOR2\_D2\_seed42 & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 1 & graph\_SOR2\_D2\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 2 & graph\_SOR2\_D2\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 3 & graph\_SOR2\_D2\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 4 & graph\_SOR2\_D2\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 5 & graph\_SOR2\_D2\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN TPC-DS v1 cluster & graph\_SOR2\_D3\_seed42 & graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC v1 cluster & graph\_SOR2\_D3\_seed42 & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 1 & graph\_SOR2\_D3\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 2 & graph\_SOR2\_D3\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 3 & graph\_SOR2\_D3\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 4 & graph\_SOR2\_D3\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 5 & graph\_SOR2\_D3\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN TPC-DS v1 cluster & graph\_SOR2\_D4\_seed42 & graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC v1 cluster & graph\_SOR2\_D4\_seed42 & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 1 & graph\_SOR2\_D4\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 2 & graph\_SOR2\_D4\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 3 & graph\_SOR2\_D4\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 4 & graph\_SOR2\_D4\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC Protocol rank 5 & graph\_SOR2\_D4\_seed42 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN TPC-DS v1 cluster & graph\_SOR2\_D5\_seed42 & graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 
GNN GenAI SPEC v1 cluster & graph\_SOR2\_D5\_seed42 & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & explicit scenario pickle map \\ 

Only the first 30 rows are shown; the full table is exported as CSV.

## Benchmark Metrics and Future Runs

Benchmark metrics are different from training metrics. Training metrics describe how the GNN behaved during supervised fitting. Benchmark metrics compare complete detector outputs against the selected ground truth and also measure runtime. Repetition medians are used because local execution time and stochastic training can vary between runs.

In Isomera v2, ET is the median detector runtime for the evaluated scenario. SF metrics are not copies of Accuracy or Jaccard: they divide the score by ET and scale by the number of evaluated candidate pairs, preserving the original Isomera interpretation of successful pair decisions per second. Detector-family summaries report scenario-level SF values aggregated across the selected benchmark scenarios.

Accuracy is retained as a diagnostic metric, but it is not the primary comparison metric for imbalanced duplicate detection. When most candidate pairs are negative, a detector can obtain high accuracy by correctly rejecting negatives while still failing to find duplicate pairs. For this reason, the report emphasizes SF-Jaccard: it uses Jaccard to focus on duplicate-pair overlap and then normalizes that overlap by execution time and evaluated pair volume.

### Benchmark Metric Formulas

{3pt}
{1.18}
{|>{}p{0.18}|>{}p{0.34}|>{}p{0.38}|}

**metric** & **formula** & **interpretation** \\ 
Accuracy & (TP + TN) / (TP + TN + FP + FN) & Fraction of duplicate and non-duplicate pair decisions classified correctly. \\ 
Jaccard & TP / (TP + FP + FN) & Overlap between predicted duplicate pairs and validated duplicate pairs. \\ 
ET & median(t\_i), i = 1..runs & Median wall-clock execution time for the detector on the scenario. \\ 
SF\_accuracy & Accuracy * N\_pairs / ET & Throughput-like rate of correct pair decisions per second. \\ 
SF\_jaccard & Jaccard * N\_pairs / ET & Jaccard-adjusted rate of successful duplicate-pair overlap per second. \\ 

### Primary View: SF-Jaccard

The primary table places SF-Jaccard first and keeps Accuracy visible as a secondary diagnostic column. A high Accuracy with Jaccard equal to zero indicates that the detector is mostly benefiting from true negatives rather than detecting validated duplicate pairs.

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|}

**algorithm** & **sf\_ & **jaccard** & **ET** & **accuracy** & **sf\_ & **N\_ \\ 
VF2 & 1850.45879 & 0.181761 & 0.052217 & 0.539786 & 4049.005801 & 11210 \\ 
Node Match & 2266.205983 & 0.246113 & 0.047843 & 0.697235 & 5020.264616 & 11210 \\ 
GNN TPC-DS v1 cluster & 522.792636 & 0.05267 & 0.046408 & 0.765745 & 6382.437823 & 11210 \\ 
GNN GenAI SPEC v1 cluster & 1742.922276 & 0.154016 & 0.036544 & 0.555575 & 5365.599705 & 11210 \\ 
GNN GenAI SPEC Protocol rank 1 & 1270.839347 & 0.139641 & 0.030916 & 0.645495 & 6300.228454 & 11210 \\ 
GNN GenAI SPEC Protocol rank 2 & 1666.846405 & 0.154487 & 0.038983 & 0.574755 & 5234.792101 & 11210 \\ 
GNN GenAI SPEC Protocol rank 3 & 1573.568559 & 0.154016 & 0.04032 & 0.555575 & 5009.7137 & 11210 \\ 
GNN GenAI SPEC Protocol rank 4 & 1633.102725 & 0.155544 & 0.04407 & 0.573327 & 4973.86914 & 11210 \\ 
GNN GenAI SPEC Protocol rank 5 & 1613.584026 & 0.144503 & 0.042912 & 0.708475 & 5864.265695 & 11210 \\ 
GNN Best-of-all cluster selector & 1996.529659 & 0.159468 & 0.034468 & 0.588582 & 6101.974407 & 11210 \\ 

### Theory, Result, and Interpretation

This table connects the theoretical expectation of the detector family with the observed benchmark result. It is the paragraph-level bridge that should be used when writing the article discussion section.

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.23}|>{}p{0.24}|>{}p{0.28}|}

**algorithm** & **observed\_ & **interpretation** & **article\_ \\ 
VF2 & SF-Jaccard=1850.46; Jaccard=0.181761; Accuracy=0.539786; ET=0.052217 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
Node Match & SF-Jaccard=2266.21; Jaccard=0.246113; Accuracy=0.697235; ET=0.047843 & Best primary metric in this run; use as the current article candidate configuration. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN TPC-DS v1 cluster & SF-Jaccard=522.793; Jaccard=0.05267; Accuracy=0.765745; ET=0.046408 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN GenAI SPEC v1 cluster & SF-Jaccard=1742.92; Jaccard=0.154016; Accuracy=0.555575; ET=0.036544 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN GenAI SPEC Protocol rank 1 & SF-Jaccard=1270.84; Jaccard=0.139641; Accuracy=0.645495; ET=0.030916 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN GenAI SPEC Protocol rank 2 & SF-Jaccard=1666.85; Jaccard=0.154487; Accuracy=0.574755; ET=0.038983 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN GenAI SPEC Protocol rank 3 & SF-Jaccard=1573.57; Jaccard=0.154016; Accuracy=0.555575; ET=0.04032 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN GenAI SPEC Protocol rank 4 & SF-Jaccard=1633.1; Jaccard=0.155544; Accuracy=0.573327; ET=0.04407 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN GenAI SPEC Protocol rank 5 & SF-Jaccard=1613.58; Jaccard=0.144503; Accuracy=0.708475; ET=0.042912 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 
GNN Best-of-all cluster selector & SF-Jaccard=1996.53; Jaccard=0.159468; Accuracy=0.588582; ET=0.034468 & Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET. & SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table. \\ 

### Full Benchmark Summary by Detector Family

{3pt}
{1.18}
{|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|>{}p{0.13}|}

**algorithm** & **accuracy** & **jaccard** & **sf\_ & **sf\_ & **ET** & **N\_ \\ 
VF2 & 0.539786 & 0.181761 & 1850.45879 & 4049.005801 & 0.052217 & 11210 \\ 
Node Match & 0.697235 & 0.246113 & 2266.205983 & 5020.264616 & 0.047843 & 11210 \\ 
GNN TPC-DS v1 cluster & 0.765745 & 0.05267 & 522.792636 & 6382.437823 & 0.046408 & 11210 \\ 
GNN GenAI SPEC v1 cluster & 0.555575 & 0.154016 & 1742.922276 & 5365.599705 & 0.036544 & 11210 \\ 
GNN GenAI SPEC Protocol rank 1 & 0.645495 & 0.139641 & 1270.839347 & 6300.228454 & 0.030916 & 11210 \\ 
GNN GenAI SPEC Protocol rank 2 & 0.574755 & 0.154487 & 1666.846405 & 5234.792101 & 0.038983 & 11210 \\ 
GNN GenAI SPEC Protocol rank 3 & 0.555575 & 0.154016 & 1573.568559 & 5009.7137 & 0.04032 & 11210 \\ 
GNN GenAI SPEC Protocol rank 4 & 0.573327 & 0.155544 & 1633.102725 & 4973.86914 & 0.04407 & 11210 \\ 
GNN GenAI SPEC Protocol rank 5 & 0.708475 & 0.144503 & 1613.584026 & 5864.265695 & 0.042912 & 11210 \\ 
GNN Best-of-all cluster selector & 0.588582 & 0.159468 & 1996.529659 & 6101.974407 & 0.034468 & 11210 \\ 

### Benchmark Results by Scenario

{3pt}
{1.18}
{|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|}

**scenario** & **algorithm** & **accuracy** & **jaccard** & **sf\_ & **sf\_ & **ET** & **N\_ & **runs** \\ 
graph\_SOR2\_D1\_seed42 & VF2 & 1.0 & 1.0 & 9214.813767 & 9214.813767 & 0.000651 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & Node Match & 0.833333 & 0.5 & 6848.658582 & 11414.43097 & 0.000438 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & GNN TPC-DS v1 cluster & 0.5 & 0.25 & 1638.710215 & 3277.42043 & 0.000915 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC v1 cluster & 0.5 & 0.25 & 1683.187192 & 3366.374383 & 0.000891 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 1 & 0.833333 & 0.5 & 3174.324432 & 5290.54072 & 0.000945 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 2 & 0.5 & 0.25 & 1082.527959 & 2165.055918 & 0.001386 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 3 & 0.5 & 0.25 & 1460.950253 & 2921.900506 & 0.001027 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 4 & 0.5 & 0.25 & 1654.753333 & 3309.506666 & 0.000906 & 6 & 10 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 5 & 0.833333 & 0.5 & 3403.772672 & 5672.954454 & 0.000881 & 6 & 10 \\ 
graph\_SOR2\_D2\_seed42 & VF2 & 0.607143 & 0.214286 & 2494.888594 & 7068.851018 & 0.002405 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & Node Match & 0.75 & 0.3 & 3865.067719 & 9662.669298 & 0.002173 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & GNN TPC-DS v1 cluster & 0.857143 & 0.0 & 0.0 & 13715.594589 & 0.00175 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC v1 cluster & 0.785714 & 0.25 & 4076.334617 & 12811.337369 & 0.001717 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 1 & 0.857143 & 0.0 & 0.0 & 15112.355952 & 0.001588 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 2 & 0.785714 & 0.25 & 3772.483635 & 11856.377137 & 0.001856 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 3 & 0.785714 & 0.25 & 4622.24236 & 14527.047417 & 0.001514 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 4 & 0.785714 & 0.25 & 4564.288086 & 14344.905414 & 0.001534 & 28 & 10 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 5 & 0.785714 & 0.25 & 4552.7227 & 14308.557056 & 0.001538 & 28 & 10 \\ 
graph\_SOR2\_D3\_seed42 & VF2 & 0.69697 & 0.259259 & 3963.638611 & 10655.496007 & 0.004317 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & Node Match & 0.69697 & 0.259259 & 3741.172923 & 10057.438896 & 0.004574 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & GNN TPC-DS v1 cluster & 0.863636 & 0.0 & 0.0 & 12246.102789 & 0.004655 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC v1 cluster & 0.636364 & 0.111111 & 1642.365448 & 9406.274839 & 0.004465 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 1 & 0.636364 & 0.111111 & 1541.560781 & 8828.939016 & 0.004757 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 2 & 0.636364 & 0.111111 & 1074.62538 & 6154.67263 & 0.006824 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 3 & 0.636364 & 0.111111 & 987.296967 & 5654.518991 & 0.007428 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 4 & 0.636364 & 0.111111 & 979.666316 & 5610.816172 & 0.007486 & 66 & 10 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 5 & 0.636364 & 0.111111 & 1038.308312 & 5946.674881 & 0.007063 & 66 & 10 \\ 
graph\_SOR2\_D4\_seed42 & VF2 & 0.641667 & 0.232143 & 2155.73284 & 5958.666671 & 0.012922 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & Node Match & 0.641667 & 0.232143 & 2422.180378 & 6695.154993 & 0.011501 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & GNN TPC-DS v1 cluster & 0.891667 & 0.0 & 0.0 & 8512.048552 & 0.01257 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC v1 cluster & 0.725 & 0.108108 & 1122.925643 & 7530.620094 & 0.011553 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 1 & 0.891667 & 0.0 & 0.0 & 9933.966943 & 0.010771 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 2 & 0.725 & 0.108108 & 1077.651726 & 7227.001886 & 0.012038 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 3 & 0.725 & 0.108108 & 963.601943 & 6462.155532 & 0.013463 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 4 & 0.725 & 0.108108 & 798.048275 & 5351.911241 & 0.016256 & 120 & 10 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 5 & 0.891667 & 0.0 & 0.0 & 4700.65793 & 0.022763 & 120 & 10 \\ 
graph\_SOR2\_D5\_seed42 & VF2 & 0.621053 & 0.2 & 960.070236 & 2981.270733 & 0.03958 & 190 & 10 \\ 
graph\_SOR2\_D5\_seed42 & Node Match & 0.673684 & 0.225 & 1363.822144 & 4083.490865 & 0.031346 & 190 & 10 \\ 
graph\_SOR2\_D5\_seed42 & GNN TPC-DS v1 cluster & 0.868421 & 0.0 & 0.0 & 7583.069087 & 0.021759 & 190 & 10 \\ 
graph\_SOR2\_D5\_seed42 & GNN GenAI SPEC v1 cluster & 0.631579 & 0.066667 & 473.326725 & 4484.147924 & 0.026761 & 190 & 10 \\ 

Only the first 40 rows are shown; the full table is exported as CSV.

### Per-Pickle Benchmark Results

This table links each GNN result to the exact pickle artifact used for that scenario. It is the table to cite when discussing model clusters, because each row is a concrete scenario--pickle--metric execution.

The PDF view uses artifact file names; the full absolute artifact paths are preserved in benchmark\_pickle\_results.csv.

{3pt}
{1.18}
{|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|>{}p{0.10}|}

**scenario** & **algorithm** & **artifact\_ & **artifact\_ & **route\_ & **sf\_ & **jaccard** & **ET** & **N\_ \\ 
graph\_SOR2\_D1\_seed42 & GNN TPC-DS v1 cluster & graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1638.710215 & 0.25 & 0.000915 & 6 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC v1 cluster & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1683.187192 & 0.25 & 0.000891 & 6 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 1 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 3174.324432 & 0.5 & 0.000945 & 6 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 2 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1082.527959 & 0.25 & 0.001386 & 6 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 3 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1460.950253 & 0.25 & 0.001027 & 6 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 4 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1654.753333 & 0.25 & 0.000906 & 6 \\ 
graph\_SOR2\_D1\_seed42 & GNN GenAI SPEC Protocol rank 5 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 3403.772672 & 0.5 & 0.000881 & 6 \\ 
graph\_SOR2\_D2\_seed42 & GNN TPC-DS v1 cluster & graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.00175 & 28 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC v1 cluster & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 4076.334617 & 0.25 & 0.001717 & 28 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 1 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.001588 & 28 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 2 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 3772.483635 & 0.25 & 0.001856 & 28 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 3 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 4622.24236 & 0.25 & 0.001514 & 28 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 4 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 4564.288086 & 0.25 & 0.001534 & 28 \\ 
graph\_SOR2\_D2\_seed42 & GNN GenAI SPEC Protocol rank 5 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D2\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 4552.7227 & 0.25 & 0.001538 & 28 \\ 
graph\_SOR2\_D3\_seed42 & GNN TPC-DS v1 cluster & graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.004655 & 66 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC v1 cluster & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1642.365448 & 0.111111 & 0.004465 & 66 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 1 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1541.560781 & 0.111111 & 0.004757 & 66 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 2 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1074.62538 & 0.111111 & 0.006824 & 66 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 3 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 987.296967 & 0.111111 & 0.007428 & 66 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 4 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 979.666316 & 0.111111 & 0.007486 & 66 \\ 
graph\_SOR2\_D3\_seed42 & GNN GenAI SPEC Protocol rank 5 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D3\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1038.308312 & 0.111111 & 0.007063 & 66 \\ 
graph\_SOR2\_D4\_seed42 & GNN TPC-DS v1 cluster & graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.01257 & 120 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC v1 cluster & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1122.925643 & 0.108108 & 0.011553 & 120 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 1 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.010771 & 120 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 2 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 1077.651726 & 0.108108 & 0.012038 & 120 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 3 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 963.601943 & 0.108108 & 0.013463 & 120 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 4 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 798.048275 & 0.108108 & 0.016256 & 120 \\ 
graph\_SOR2\_D4\_seed42 & GNN GenAI SPEC Protocol rank 5 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D4\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.022763 & 120 \\ 
graph\_SOR2\_D5\_seed42 & GNN TPC-DS v1 cluster & graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.021759 & 190 \\ 
graph\_SOR2\_D5\_seed42 & GNN GenAI SPEC v1 cluster & GNN\_tpcds\_genai\_spec\_graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 473.326725 & 0.066667 & 0.026761 & 190 \\ 
graph\_SOR2\_D5\_seed42 & GNN GenAI SPEC Protocol rank 1 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 312.452112 & 0.036364 & 0.022112 & 190 \\ 
graph\_SOR2\_D5\_seed42 & GNN GenAI SPEC Protocol rank 2 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 619.467574 & 0.066667 & 0.020448 & 190 \\ 
graph\_SOR2\_D5\_seed42 & GNN GenAI SPEC Protocol rank 3 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 638.976954 & 0.066667 & 0.019823 & 190 \\ 
graph\_SOR2\_D5\_seed42 & GNN GenAI SPEC Protocol rank 4 & GNN\_tpcds\_genai\_spec\_protocol\_rank4\_graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 656.002312 & 0.066667 & 0.019309 & 190 \\ 
graph\_SOR2\_D5\_seed42 & GNN GenAI SPEC Protocol rank 5 & GNN\_tpcds\_genai\_spec\_protocol\_rank5\_graph\_SOR2\_D5\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 0.0 & 0.0 & 0.0195 & 190 \\ 
graph\_SOR4\_D1\_seed42 & GNN TPC-DS v1 cluster & graph\_SOR4\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 7367.452055 & 0.666667 & 0.002534 & 28 \\ 
graph\_SOR4\_D1\_seed42 & GNN GenAI SPEC v1 cluster & GNN\_tpcds\_genai\_spec\_graph\_SOR4\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 7788.594195 & 0.666667 & 0.002397 & 28 \\ 
graph\_SOR4\_D1\_seed42 & GNN GenAI SPEC Protocol rank 1 & GNN\_tpcds\_genai\_spec\_protocol\_rank1\_graph\_SOR4\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 7154.836041 & 0.666667 & 0.002609 & 28 \\ 
graph\_SOR4\_D1\_seed42 & GNN GenAI SPEC Protocol rank 2 & GNN\_tpcds\_genai\_spec\_protocol\_rank2\_graph\_SOR4\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 7222.836637 & 0.666667 & 0.002584 & 28 \\ 
graph\_SOR4\_D1\_seed42 & GNN GenAI SPEC Protocol rank 3 & GNN\_tpcds\_genai\_spec\_protocol\_rank3\_graph\_SOR4\_D1\_seed42.pkl & scenario\_specific\_pickle & scenario\_specific & 5585.268834 & 0.666667 & 0.003342 & 28 \\ 

Only the first 40 rows are shown; the full table is exported as CSV.

### Benchmark Figures

[h]

[h]

[h]

[h]

[h]

[h]

## Reproducibility Package

The accompanying zip package contains the LaTeX source, compiled PDF when available, source JSON, lineage and adjacency figures, source GML, labels, manifest, exported tables, model pickle, model metadata, and benchmark references.
