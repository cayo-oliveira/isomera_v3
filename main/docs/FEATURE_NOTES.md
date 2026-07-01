# Isomera Feature Notes

## Versioning

Isomera follows semantic versioning:

- `MAJOR`: architectural generation or incompatible workflow change.
- `MINOR`: new product capabilities that keep the current workflow compatible.
- `PATCH`: fixes, UI refinements, reports, and operational hardening.

Current release: `2.4.0`.

## 2.4.0 - VMamba-Mesh Study Runtime and Benchmarkable Adapter

Release date: 2026-04-29

This minor release turns Study Lab from an educational-only workspace into an operational model-study workflow.

Main changes:

- Added an optional official VMamba runtime panel that checks whether the public VMamba repository is present and can clone/update it for source-level study.
- Added a side-by-side VMamba -> VMamba-Mesh flow showing where CanonSort, pair tensors, DiagFP, HierInit and SparseGate change the original vision pipeline.
- Added `core.algorithms.vmamba_mesh`, a deterministic Isomera-compatible VMamba-Mesh adapter that exports a `.pkl` with `predict_pairs(graph)`.
- Added Study Lab training controls for benchmark source, scenario, scope layers, negative ratio, seed, tensor resolution, CanonSort, DiagFP, HierInit and SparseGate.
- Added automatic model metadata with `pickle_module=core.algorithms.vmamba_mesh`, source scenario, graph path, label path, selected threshold, calibration Jaccard, precision and recall.
- Added benchmark registration for VMamba-Mesh models so they can be compared against VF2, Node Match and GNN pickle clusters.
- Updated benchmark routing so each `.pkl` can declare its own inference module instead of assuming every pickle uses `core.algorithms.gnn_model`.
- Added VMamba-Mesh study report packages under Research Reports with Markdown, TEX, manifest, ZIP and optional Tectonic PDF compilation.

Important limitation:

- The current `.pkl` is the VMamba-Mesh Isomera adapter, not the final neural VMamba-Mesh backbone. It is benchmarkable and reproducible now, but the article should describe it as the first operational adapter until the full VMamba selective-scan implementation and ablation study are completed.

## 2.3.0 - Study Lab and VMamba-Mesh Learning Path

Release date: 2026-04-29

This minor release adds a separate Study Lab module for learning model internals before implementation.

Main changes:

- Added `Study Lab` as a core module in the sidebar and Home page.
- Added a VMamba/SS2D study view with educational pseudocode mapped to VMamba concepts.
- Added an executable SS2D-style lineage simulation using synthetic SOR/SOT/SPEC graphs.
- Added controls for CanonSort, DiagFP, scan route, memory decay, input gain, and SparseGate strength.
- Added VMamba-Mesh change cards showing where the original VMamba pipeline changes, why the change exists, and how to test it.
- Added an implementation roadmap for CanonSort, mesh image encoding, schema fingerprints, MeshSS2D, training, and benchmark export.
- Clarified that measured notebook evidence currently covers MLP/CNN only; VMamba-Mesh results must be produced after implementation and ablation.

## 2.2.6 - Inline Review and GenAI Batch Budgeting

Release date: 2026-04-19

This patch release turns the final article review into inline manuscript comments and hardens the GenAI validation workflow.

Main changes:

- Added Jamilson and Paulo comments directly inside `research/artigo_iii.tex`, with blue/yellow and purple/orange review boxes.
- Added draw.io guidance inline in the manuscript for architecture, API, GNN, protocol and result figures.
- Replaced Streamlit popovers with a controlled SVG information control to avoid unreadable dark `(i)` panels.
- Improved dropdown menu readability with wider, non-truncated option rendering.
- Added GenAI token and cost estimates for the current pair and full review queue.
- Added GenAI batch validation with a confirmation step before applying labels to the supervised validation dataset.
- Added OpenAI response usage capture so actual tokens and estimated cost appear after each validation.
- Added reviewed-source metadata to curated validation rows so reports can show whether labels came from manual review or GenAI.

## 2.2.5 - Final Review and GenAI Validation UX

Release date: 2026-04-19

This patch release adds the final IEEE SMC review artifacts and closes critical UX gaps before returning focus to the application.

Main changes:

- Added reusable Jamilson and Paulo reviewer-agent prompts at the repository root.
- Added a separate color-coded article review PDF/TEX with structural and theoretical comments.
- Added an optional GenAI validation terminal in Scenario Studio for validating the current pair with the OpenAI Models and Responses APIs.
- Added saveable GenAI validation-agent presets under `main/data/genai_agents`.
- Added database-to-graph materialization sanity checks comparing PostgreSQL table count to full lineage graph vertex count.
- Added DDL/DML inspection inside pair review table views when the scenario was loaded from a manifest-backed PostgreSQL schema.
- Reworked Help navigation into a clickable section list and moved References/PDFs above the section list.
- Strengthened dropdown and popover styling to avoid unreadable truncated options and dark popover backgrounds.

## 2.2.4 - Article Visuals and GNN Explanation

Release date: 2026-04-19

This patch release adds article-grade explanatory figures and documentation for the IEEE SMC manuscript.

Main changes:

- Added reproducible high-resolution figures for Isomera software architecture, Scenario Materialization API flow, user/service sequence, GIN pair-classifier pipeline, and staged protocol architecture pattern.
- Updated the IEEE SMC draft to connect relational tables, lineage graphs, tensor encoding, GIN layers, loss functions, routing, and report generation in one coherent visual narrative.
- Added draw.io guidance directly in the article draft for the final vector redraws.
- Updated Help documentation with the GNN visual mapping from PostgreSQL/GML lineage to `x`, `edge_index`, graph embeddings, logits, sigmoid threshold, and pickle routing.
- Added a reusable figure-generation script so the article visuals can be regenerated from the repository instead of maintained as external screenshots.

## 2.2.3 - Benchmark Routing UX and Fast Reports

Release date: 2026-04-19

This patch release focuses on the final paper workflow and removes confusing UI behavior before IEEE SMC submission.

Main changes:

- Restricted the benchmark catalog to the default benchmark, the operational smoke example, and the Article III workloads.
- Added explicit per-run model selection in Benchmark & Examples with information popovers for VF2, Node Match, and GNN clusters.
- Moved best-of routing decisions into Benchmark & Examples because they change execution semantics.
- Converted Model Lab routing into a read-only inventory view for model/pickle inspection.
- Reworked Research Reports into a fast Markdown-first reader with Open PDF and download buttons for TEX, PDF, Markdown, manifest, and ZIP.
- Added Markdown previews to research report packages and ZIP regeneration from the selected report folder.
- Replaced the fragile Home image with a native workflow card so the page no longer depends on Streamlit media cache URLs.
- Improved dropdown, popover, table, and Plotly legend contrast.
- Added launcher log files to the Logs page alongside app-level terminal logs.

## 2.2.2 - UI Readability and Local Artifact Cleanup

Release date: 2026-04-18

This patch release cleans local generated files and improves the benchmark/report UI.

Main changes:

- Removed thousands of regenerable validation images from local `main/data/architectures/**/validations`.
- Removed old intermediate research reports, keeping only the five Article III packages.
- Removed the legacy `research/deep_learning_classes` folder locally and kept it ignored.
- Re-enabled versioning for the five Article III report folders and lightweight scenario contracts used by the paper.
- Replaced text-only help popovers with Streamlit material info icons.
- Fixed dataframe/dropdown styling that could render empty gray boxes or unreadable select menus.
- Changed benchmark screen labels and charts so `SF` represents `SF-Jaccard`, not `SF-Accuracy`.
- Improved Plotly legend contrast for benchmark charts.

## 2.2.1 - Git and Reproducibility Hardening

Release date: 2026-04-18

This patch release focuses on repository health and paper reproducibility.

Main changes:

- Removed generated validation images, validation datasets, and pickle binaries from Git tracking without deleting local files.
- Strengthened `.gitignore` for generated validation artefacts under `main/data/architectures`.
- Added `main/docs/git_reproducibility.md` with Git hygiene, Source Control troubleshooting, benchmark routing policies, and reproducibility rules.
- Added a high-resolution protocol/routing flow figure for the Article III draft.
- Refined the article discussion around explicit scenario-to-pickle routing, transfer routing, and best-of diagnostic routing.
- Clarified that best-of-all is a routing experiment unless the policy is declared before benchmark execution.

## 2.2.0 - Benchmark Report Refinement

Release date: 2026-04-18

This release hardens the paper-oriented benchmark workflow and cleans the training/reporting experience.

Main changes:

- Added final article benchmark workloads for GenAI SOR+SOT and GenAI Full Lineage.
- Updated the IEEE SMC article draft with five benchmark views: Default, SPEC, SOT+SPEC, SOR+SOT, and Full Lineage.
- Recompiled final benchmark report packages and ZIP bundles after PDF generation.
- Refined Research Reports into a fast package-first view with selected PDF preview and optional capture scanning.
- Reduced the `(i)` help icon to a compact blue accessibility marker with white text.
- Reordered Scenario Studio model training so loss, balancing, and hyperparameters are visible before the benchmark save destination.
- Increased dropdown readability and stabilized select/popover font sizing.
- Added generated artifact exclusions to `.gitignore` to protect repository health.

## 2.1.0 - Lineage Workbench

Release date: 2026-04-17

This release consolidates the second-generation Isomera workflow as a local research workbench.

Main changes:

- Added macOS launcher with visible bootstrap progress and real-time Streamlit logs.
- Added safe shutdown through `Stop Isomera` in the sidebar, coordinated by a launcher signal file.
- Added lifecycle management for local PostgreSQL/MySQL sessions started by the launcher.
- Recreated the project `.venv` around Python 3.11 and documented the stable startup path.
- Stabilized Scenario Studio around a database-first journey:
  source database -> scenario schema -> normalized lineage graph -> pair validation -> curated benchmark -> model training.
- Added Scenario Warehouse flow for PostgreSQL TPC-DS benchmark schemas.
- Added database-to-graph API documentation and explicit limitations for SOR/SOT/SPEC normalization.
- Added benchmark publication and model-routing concepts for benchmark-specific `.pkl` clusters.
- Added GNN training configuration with named optimizer, loss, balancing strategy, train split, and protocol metadata.
- Added Isomera Staged Protocol for screening, selected full validation, and final benchmark comparison.
- Added Research Reports with package export, `.tex`, PDF generation path, figures, CSV/JSON artifacts, and DOI-ready folder structure.
- Added report sections for software architecture, database architecture, API contract, validation dataset, training dataset, model artifact, benchmark metrics, and limitations.
- Added metric corrections and documentation for `ET`, `SF-Jaccard`, and `SF-Accuracy`.
- Added Admin/Scenario Manager concepts for relational inspection and future backend governance.
- Improved UI palette consistency and simplified the module navigation.

## 2.0.0 - Isomera v2 Foundation

This version marks the transition from the original Isomera prototype to the v2 architecture.

Main changes:

- Reorganized repository into `main/` and `research/`.
- Established the v2 module structure:
  Home, Benchmark & Examples, Scenario Studio, Model Lab, Production Run, Admin, Logs, Help, and About.
- Preserved Streamlit as the v2 application shell.
- Defined PostgreSQL as the relational benchmark warehouse.
- Defined MySQL as the future publication/research backend.
- Preserved GML as the portable graph contract.
- Defined Neo4j as backlog for later visualization/exploration support.
- Established phased implementation with validation after each phase.

## 1.x - Original Isomera Prototype

The original Isomera focused on graph-based redundancy detection and benchmark experimentation.

Main capabilities:

- Load lineage graphs.
- Run VF2 and node-matching baselines.
- Compare detected pairs against known duplicate pairs.
- Calculate accuracy, Jaccard, runtime, and related metrics.
- Support early GNN/pickle experiments derived from the dissertation and article prototypes.

Limitations that motivated v2:

- Limited scenario lifecycle.
- Limited relational warehouse integration.
- Limited ground-truth traceability.
- Limited benchmark publication workflow.
- Limited model-to-scenario routing.
- Limited article/report evidence capture.
