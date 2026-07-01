# Isomera v3

Isomera v3 is an executable research workbench for detecting duplicate or redundant tables in data architectures represented as lineage graphs. It was developed in the context of research at Centro de Informática da Universidade Federal de Pernambuco (CIn/UFPE).

The repository contains the application code, benchmark scenarios, trained model artifacts and reproducibility evidence needed to run the public Isomera demo locally. Research notebooks, TeXLab workspaces, manuscript drafts and exploratory study files are intentionally not included.

## What Is Included

```text
main/ui/app.py                         Streamlit application entry point
main/core/                             Core graph, benchmark, model and persistence logic
main/core/algorithms/                  VF2, Node Match, GNN, VMamba, VMamba-Mesh and trainable VMamba models
main/scripts/                          Local launcher and reproducibility helpers
main/data/architectures/               Benchmark graphs, labels and stored model artifacts
main/data/tpcds_postgres/              PostgreSQL scenario manifests and schema files
main/data/article_evidence/            Packaged Article IV evidence used by the app
main/data/research_reports/            Reproducibility reports and result packages used by the UI
main/docs/presentations/               Runtime presentation assets shown inside the app
.github/knowledge_bases/               Knowledge base files shown in the Study Lab help
```

## What Is Not Included

```text
research/
papercept_compiler/
Jupyter notebooks
LaTeX manuscript workspaces
local virtual environments
runtime logs and caches
```

## Requirements

Recommended environment:

- macOS or Linux
- Python 3.11+
- Git
- Internet access for first dependency installation

Optional but useful:

- PostgreSQL 16, for materialized TPC-DS scenario inspection
- MySQL, for publication/backend demonstrations
- Apple Silicon MPS or another PyTorch-supported device for neural experiments

The app can still open and inspect packaged benchmarks without manually creating the databases first. Database-backed flows require local database services.

## Quick Start

From the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r main/requirements.txt
.venv/bin/python -m streamlit run main/ui/app.py --server.port 8501 --server.address localhost
```

Then open:

```text
http://localhost:8501
```

On macOS, the launcher can also be used:

```bash
./launch_isomera.command
```

The launcher checks the local virtual environment, dependencies, Streamlit process state and local database services before opening the app.

## Main App Paths

Use these screens to inspect the public VMamba-Mesh workflow:

```text
Help -> VMamba-Mesh Presentation
Study Lab -> Deep Learning Workbench
Study Lab -> Model Reports
Study Lab -> Model Interpretability
Benchmark & Examples -> Article Reproducibility
Research Reports
```

## Reproducing The Demo Evidence

The packaged Article IV evidence is available under:

```text
main/data/article_evidence/vmamba_mesh_genai_benchmark/
```

The benchmark/model artifacts are available under:

```text
main/data/architectures/tpc_ds_genai_spec_v2/
main/data/architectures/tpc_ds_genai_full_lineage/
```

Inside the app, open:

```text
Benchmark & Examples -> Article Reproducibility
```

Select:

```text
Article IV - VMamba-Mesh operational study
```

Use quick mode for a single scenario or article evidence mode to compare stored metrics against the expected article values.

## Model Families

The public package includes the executable model families used by the app:

- VF2 deterministic graph isomorphism baseline
- Node Match deterministic baseline
- GNN/GIN pair classifier artifacts
- Vanilla VMamba lineage-tensor baseline
- VMamba-Mesh deterministic adapter
- VMamba-T trainable PyTorch model using channels C0/C1
- VMamba-Mesh-T trainable PyTorch model using channels C0-C5

The trainable path follows the app contract:

```text
graph pair -> CanonSort -> tensor channels -> patch embedding -> VSS/SS2D-style blocks -> pooling -> neural pair head -> logit -> sigmoid -> threshold -> duplicate / non-duplicate
```

## Repository Scope

This repository is intended as a clean executable release of Isomera. It is not the full private research workspace. Generated manuscripts, notebooks and TeXLab materials should remain outside this public repository unless explicitly prepared for publication.

## Citation

If you use this software in academic work, cite the Isomera project and the related CIn/UFPE research artifacts associated with data lineage, duplicate table detection and VMamba-Mesh reproducibility.

A formal citation file may be added after the final publication metadata is available.

## License

This repository is released under the MIT License. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
