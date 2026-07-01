from __future__ import annotations

import csv
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

from core.algorithms.gnn_training import (  # noqa: E402
    TRAINING_BALANCE_OPTIONS,
    TRAINING_LOSS_OPTIONS,
    TRAINING_OPTIMIZER_OPTIONS,
)


def _slug(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_\\-]+", "_", value.strip())
    return re.sub(r"_+", "_", value).strip("_").lower() or "report"


def _compact_slug(value: str, max_len: int = 36) -> str:
    slug = _slug(value)
    slug = re.sub(r"^graph_", "", slug)
    slug = re.sub(r"_+", "_", slug).strip("_")
    if len(slug) <= max_len:
        return slug
    parts = slug.split("_")
    compact = []
    for part in parts:
        candidate = "_".join([*compact, part])
        if len(candidate) > max_len:
            break
        compact.append(part)
    return "_".join(compact) or slug[:max_len].rstrip("_")


def _tex_escape(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_\allowbreak{}",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "/": r"/\allowbreak{}",
        "-": r"-\allowbreak{}",
        ".": r".\allowbreak{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _latest_capture() -> Path:
    captures = sorted(
        (MAIN_ROOT / "data" / "article_capture").glob("*/*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not captures:
        raise FileNotFoundError("No article captures found.")
    return captures[0]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for field in row.keys():
            if field not in fieldnames:
                fieldnames.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _copy_if_exists(source: str | Path | None, target: Path) -> str | None:
    if not source:
        return None
    source_path = Path(str(source))
    if not source_path.exists():
        return None
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    return str(target)


def _table_rows(rows: list[dict[str, Any]], columns: list[str], limit: int = 12) -> str:
    if not rows:
        return "No rows available."
    width_map = {
        1: ["0.88\\linewidth"],
        2: ["0.26\\linewidth", "0.62\\linewidth"],
        3: ["0.18\\linewidth", "0.34\\linewidth", "0.38\\linewidth"],
        4: ["0.13\\linewidth", "0.23\\linewidth", "0.24\\linewidth", "0.28\\linewidth"],
        5: ["0.14\\linewidth", "0.17\\linewidth", "0.17\\linewidth", "0.17\\linewidth", "0.23\\linewidth"],
        6: ["0.11\\linewidth", "0.14\\linewidth", "0.15\\linewidth", "0.14\\linewidth", "0.15\\linewidth", "0.18\\linewidth"],
    }
    widths = width_map.get(len(columns), [f"{0.88 / max(len(columns), 1):.2f}\\linewidth"] * len(columns))
    col_spec = "|".join([f">{{\\RaggedRight\\arraybackslash}}p{{{width}}}" for width in widths])
    lines = [
        "\\begingroup",
        "\\scriptsize",
        "\\setlength{\\tabcolsep}{3pt}",
        "\\renewcommand{\\arraystretch}{1.18}",
        "\\begin{longtable}{|" + col_spec + "|}",
        "\\hline",
    ]
    lines.append(" & ".join(f"\\textbf{{{_tex_escape(col)}}}" for col in columns) + r" \\ \hline")
    for row in rows[:limit]:
        lines.append(" & ".join(_tex_escape(row.get(col, "")) for col in columns) + r" \\ \hline")
    lines.extend(["\\end{longtable}", "\\endgroup"])
    if len(rows) > limit:
        lines.append(f"Only the first {limit} rows are shown; the full table is exported as CSV.")
    return "\n".join(lines)


def _artifact_display_rows(rows: list[dict[str, Any]], path_field: str = "artifact_path") -> list[dict[str, Any]]:
    display_rows: list[dict[str, Any]] = []
    for row in rows:
        display = dict(row)
        artifact_path = str(display.get(path_field, "") or "")
        if artifact_path:
            display["artifact_file"] = Path(artifact_path).name
        else:
            display["artifact_file"] = ""
        display_rows.append(display)
    return display_rows


def _architecture_diagram_tex() -> str:
    return "\n".join(
        [
            r"\begin{figure}[h]",
            r"\centering",
            r"\fbox{\begin{minipage}{0.94\linewidth}",
            r"\centering",
            r"\textbf{External Sources / Benchmark Warehouse}\\",
            r"PostgreSQL schemas, GML files, or future database connectors\\[0.5em]",
            r"$\Downarrow$\\[0.2em]",
            r"\textbf{Scenario Materialization API}\\",
            r"database inspection, manifest-to-table mapping, relational-to-graph transformation, SOR--SOT--SPEC normalization\\[0.5em]",
            r"$\Downarrow$\\[0.2em]",
            r"\textbf{Scenario Studio}\\",
            r"candidate filters, graph/table review, autosaved duplicate labels, benchmark publication\\[0.5em]",
            r"$\Downarrow$\\[0.2em]",
            r"\textbf{Training and Benchmark Execution}\\",
            r"standard graph input, supervised validation dataset, model artifact, benchmark metrics\\[0.5em]",
            r"$\Downarrow$\\[0.2em]",
            r"\textbf{Publication Backend and Research Package}\\",
            r"MySQL publication tables, model pickle, JSON/CSV evidence, LaTeX, PDF, ZIP",
            r"\end{minipage}}",
            r"\caption{IEEE-style high-level Isomera v2 architecture used in the generated research package.}",
            r"\end{figure}",
        ]
    )


def _software_architecture_rationale_rows() -> list[dict[str, str]]:
    return [
        {
            "component": "Streamlit UI",
            "responsibility": "Provides the interactive workflow for loading scenarios, reviewing candidate pairs, training models, inspecting stores, and exporting research packages.",
            "rationale": "Streamlit keeps the research prototype fast to iterate while still exposing every intermediate artifact needed for paper writing.",
        },
        {
            "component": "Scenario Materialization API",
            "responsibility": "Converts PostgreSQL schemas, GML files, or manual graphs into one normalized graph contract.",
            "rationale": "Centralizes the table-to-graph transformation so UI, training, benchmark, and reports consume the same graph, edge table, adjacency matrix, and metadata.",
        },
        {
            "component": "PostgreSQL Scenario Warehouse",
            "responsibility": "Stores benchmark relational scenarios as database schemas.",
            "rationale": "Represents the external relational environment being analyzed; it is the source of scenario data, not the operational backend.",
        },
        {
            "component": "MySQL Publication Backend",
            "responsibility": "Stores published benchmarks, scenarios, nodes, edges, reviewed pairs, and publication reports.",
            "rationale": "Separates article/research evidence from the benchmark warehouse and prepares the project for a durable backend store.",
        },
        {
            "component": "GML/JSON File Layer",
            "responsibility": "Stores portable graphs, labels, manifests, article captures, and exported package metadata.",
            "rationale": "Provides reproducible files for DOI/data sharing and makes the benchmark portable outside the local database.",
        },
        {
            "component": "Training Pipeline",
            "responsibility": "Transforms normalized graphs and curated duplicate labels into supervised datasets and pickle model artifacts.",
            "rationale": "Keeps model input standardized so future GNN/CNN/other detectors can share the same upstream materialization contract.",
        },
        {
            "component": "Research Report Builder",
            "responsibility": "Generates LaTeX, PDF, ZIP, figures, CSVs, JSONs, and model references from Article Capture evidence.",
            "rationale": "Turns experimental actions into article-ready evidence without manually copying app state into the manuscript.",
        },
    ]


def _normalization_method_rows() -> list[dict[str, str]]:
    return [
        {
            "step": "Layer detection",
            "technical_rule": "Each node is assigned a rank by inspecting node names and metadata: SOR=0, SOT=1, SPEC=2, OTHER=3.",
            "limitation": "If a database uses arbitrary names such as customers, orders, mart_sales without a manifest or mapping, the API cannot know which layer each table belongs to.",
        },
        {
            "step": "Direction scoring",
            "technical_rule": "For every edge, the API compares source_rank and target_rank. Edges with source_rank < target_rank count as downstream; source_rank > target_rank count as upstream.",
            "limitation": "The score only measures consistency with known layer ranks. It does not infer business semantics by itself.",
        },
        {
            "step": "Graph reversal",
            "technical_rule": "If upstream_edges_before is greater than downstream_edges_before, all edges are reversed. Otherwise the graph is copied as-is.",
            "limitation": "Mixed or ambiguous graphs can be partially incorrect if the source does not expose layer semantics or a reliable manifest.",
        },
        {
            "step": "Manifest mode",
            "technical_rule": "When a benchmark manifest is available, it provides node, table_name, semantic_name, type/layer, domain, and explicit lineage edges.",
            "limitation": "This is the preferred article-grade mode, but it requires preparing or importing a mapping contract.",
        },
        {
            "step": "Foreign-key-only mode",
            "technical_rule": "Without a manifest, the API can inspect tables and foreign keys to build a graph, then apply the same direction heuristic.",
            "limitation": "Foreign keys are physical constraints, not necessarily transformation lineage. This mode is exploratory unless validated by the user.",
        },
    ]


def _tpcds_domain_rows() -> list[dict[str, str]]:
    return [
        {
            "domain": "D1",
            "practical_context": "Customer, catalog, and warehouse-performance context.",
            "examples": "customer, customer_demographics, catalog_performance, warehouse_logistics.",
            "extension_rule": "Keep D1 when the business view is customer/catalog performance.",
        },
        {
            "domain": "D2",
            "practical_context": "Store, geography, customer attributes, and order summary context.",
            "examples": "nation, store, customer_attr, customer_orders, customer_summary.",
            "extension_rule": "Use the same pattern for another geography/store/customer domain.",
        },
        {
            "domain": "D3",
            "practical_context": "Item, promotion, catalog sales, and analytical reuse context.",
            "examples": "item, promotion, catalog_sales, time_analysis.",
            "extension_rule": "Use for product/promotion/catalog-sales analytical scenarios.",
        },
        {
            "domain": "D4",
            "practical_context": "Date, time, customer orders, and warehouse stock context.",
            "examples": "date_dim, time_dim, customer_orders, warehouse_stock.",
            "extension_rule": "Use for temporal and inventory-history scenarios.",
        },
        {
            "domain": "D5",
            "practical_context": "Income band, warehouse, store sales, and store-sales summary context.",
            "examples": "income_band, warehouse, store_sales, store_sales_summary.",
            "extension_rule": "Use for income/warehouse/store-sales scenarios.",
        },
        {
            "domain": "D6+",
            "practical_context": "Future user-defined domain.",
            "examples": "Any new business domain introduced by the user.",
            "extension_rule": "Add a manifest/mapping contract defining domain name, SOR tables, SOT tables, SPEC outputs, and lineage edges.",
        },
    ]


def _api_io_contract_rows() -> list[dict[str, str]]:
    return [
        {
            "artifact": "normalized_graph",
            "description": "NetworkX directed graph with canonical edge direction when layer semantics are available.",
            "consumer": "Scenario Studio, graph visualization, candidate filtering, training.",
        },
        {
            "artifact": "lineage_structure",
            "description": "Node table with domain, layer, node, source table, semantic name, in-degree, and out-degree.",
            "consumer": "Research Reports, Admin inspection, article tables.",
        },
        {
            "artifact": "edge_table",
            "description": "Directed edge table with origin, destination, and edge type.",
            "consumer": "Report package, DOI export, future semantic edge extensions.",
        },
        {
            "artifact": "adjacency_matrix",
            "description": "Binary adjacency matrix aligned to the normalized graph.",
            "consumer": "Graph diagnostics, report figures, future CNN/image-based detector experiments.",
        },
        {
            "artifact": "source_metadata",
            "description": "Database URL, schema, build mode, manifest usage, manifest path, table count, and graph build steps.",
            "consumer": "Article Capture, package manifest, reproducibility section.",
        },
    ]


def _filter_catalog_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    filters = dict(summary.get("filters") or {})
    selected_scopes = ", ".join(filters.get("scope_layers") or []) or "not recorded"
    selected_rules = ", ".join(filters.get("constraints") or []) or "not recorded"
    return [
        {
            "filter": "Lineage scope",
            "setting": selected_scopes,
            "effect": "Chooses which node layers are eligible for pair generation. SPEC uses complete upstream lineage, not only the final SPEC node.",
        },
        {
            "filter": "Same layer",
            "setting": "enabled when selected",
            "effect": "Keeps only pairs from the same semantic layer to avoid comparing SOR with SOT or SPEC directly.",
        },
        {
            "filter": "Same domain",
            "setting": "enabled when selected",
            "effect": "Keeps only pairs whose domain identifier is equal, reducing cross-domain candidate explosion.",
        },
        {
            "filter": "Same input count",
            "setting": "enabled when selected",
            "effect": "Keeps only pairs with the same number of upstream parents.",
        },
        {
            "filter": "Same output count",
            "setting": "enabled when selected",
            "effect": "Keeps only pairs with the same number of downstream children.",
        },
        {
            "filter": "Same parent signature",
            "setting": "enabled when selected",
            "effect": "Keeps only pairs with compatible upstream lineage signatures.",
        },
        {
            "filter": "Same child signature",
            "setting": "enabled when selected",
            "effect": "Keeps only pairs with compatible downstream lineage signatures.",
        },
        {
            "filter": "Selected structural constraints",
            "setting": selected_rules,
            "effect": "Defines the final reviewed subset and must be reported as part of the ground-truth protocol.",
        },
    ]


def _normalize_filter_rows(rows: list[dict[str, Any]], summary: dict[str, Any]) -> list[dict[str, Any]]:
    if not rows:
        return _filter_catalog_rows(summary)
    if rows and {"filter", "setting", "effect"} <= set(rows[0]):
        return rows
    descriptions = {
        "scope_sor": "Includes SOR source-of-record nodes in the review scope.",
        "scope_sot": "Includes SOT transformation nodes in the review scope.",
        "scope_spec": "Includes SPEC output nodes with complete upstream lineage.",
        "same_layer_only": "Keeps only pairs from the same semantic layer.",
        "same_domain_only": "Keeps only pairs inside the same domain.",
        "same_input_count": "Keeps only pairs with the same number of upstream inputs.",
        "same_output_count": "Keeps only pairs with the same number of downstream outputs.",
        "same_parent_signature": "Keeps only pairs with compatible upstream signatures.",
        "same_child_signature": "Keeps only pairs with compatible downstream signatures.",
    }
    normalized = []
    for row in rows:
        filter_name = str(row.get("filter", "filter"))
        enabled = bool(row.get("enabled"))
        normalized.append(
            {
                "filter": filter_name,
                "setting": "enabled" if enabled else "disabled",
                "effect": descriptions.get(filter_name, "Recorded filter setting used to define the reviewed candidate set."),
            }
        )
    return normalized


def _metric_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    metrics = summary.get("benchmark_metrics") or summary.get("metrics") or {}
    if isinstance(metrics, list):
        return [row for row in metrics if isinstance(row, dict)]
    if not isinstance(metrics, dict) or not metrics:
        return [
            {"algorithm": "pending", "accuracy": "pending benchmark execution", "jaccard": "-", "sf_jaccard": "-", "sf_accuracy": "-", "ET": "-"},
        ]
    return [{"algorithm": key, "accuracy": value, "jaccard": "-", "sf_jaccard": "-", "sf_accuracy": "-", "ET": "-"} for key, value in metrics.items()]


def _benchmark_formula_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "metric": "Accuracy",
            "formula": "(TP + TN) / (TP + TN + FP + FN)",
            "interpretation": "Fraction of duplicate and non-duplicate pair decisions classified correctly.",
        },
        {
            "metric": "Jaccard",
            "formula": "TP / (TP + FP + FN)",
            "interpretation": "Overlap between predicted duplicate pairs and validated duplicate pairs.",
        },
        {
            "metric": "ET",
            "formula": "median(t_i), i = 1..runs",
            "interpretation": "Median wall-clock execution time for the detector on the scenario.",
        },
        {
            "metric": "SF_accuracy",
            "formula": "Accuracy * N_pairs / ET",
            "interpretation": "Throughput-like rate of correct pair decisions per second.",
        },
        {
            "metric": "SF_jaccard",
            "formula": "Jaccard * N_pairs / ET",
            "interpretation": "Jaccard-adjusted rate of successful duplicate-pair overlap per second.",
        },
    ]


def _model_artifact_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    training = dict(summary.get("training_summary") or {})
    hyperparameters = dict(summary.get("resolved_hyperparameters") or summary.get("hyperparameters") or {})
    loss_summary = dict(training.get("loss") or summary.get("loss") or {})
    balance_summary = dict(training.get("balance_summary") or hyperparameters.get("balance_summary") or {})
    return [
        {"field": "model_family", "value": summary.get("model_family_name", "")},
        {"field": "model_name", "value": summary.get("model_name", "")},
        {"field": "model_path", "value": summary.get("model_path", "")},
        {"field": "optimizer", "value": summary.get("optimizer_label") or summary.get("optimizer_name") or summary.get("optimizer", "")},
        {"field": "loss", "value": loss_summary.get("loss_label") or summary.get("loss_label") or summary.get("loss_name", "")},
        {"field": "effective_loss_function", "value": loss_summary.get("loss_name") or summary.get("loss_name", "")},
        {"field": "activation", "value": "ReLU in GIN/MLP hidden layers; sigmoid/logit interpretation at binary output"},
        {"field": "train_ratio", "value": hyperparameters.get("train_ratio", "")},
        {"field": "test_ratio", "value": hyperparameters.get("test_ratio", "")},
        {"field": "balance_strategy", "value": hyperparameters.get("balance_strategy_label") or hyperparameters.get("balance_strategy", "")},
        {"field": "balance_operation", "value": balance_summary.get("operation", "")},
        {"field": "pos_weight", "value": loss_summary.get("pos_weight", "")},
        {"field": "epochs", "value": hyperparameters.get("epochs", "")},
        {"field": "hidden_channels", "value": hyperparameters.get("hidden_channels", "")},
        {"field": "negative_ratio", "value": hyperparameters.get("negative_ratio", "")},
        {"field": "train_size", "value": training.get("train_size", "")},
        {"field": "validation_size", "value": training.get("val_size", training.get("validation_size", ""))},
    ]


def _training_option_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for group, options in [
        ("optimizer", TRAINING_OPTIMIZER_OPTIONS),
        ("loss", TRAINING_LOSS_OPTIONS),
        ("balancing", TRAINING_BALANCE_OPTIONS),
    ]:
        for key, meta in options.items():
            rows.append(
                {
                    "group": group,
                    "friendly_name": meta.get("label", key),
                    "technical_function": meta.get("technical_name", key),
                    "formula": meta.get("formula", ""),
                    "use": meta.get("description", ""),
                }
            )
    return rows


def _key_value_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, value in payload.items():
        if isinstance(value, (dict, list, tuple)):
            rendered = json.dumps(value, ensure_ascii=True)
        else:
            rendered = value
        rows.append({"field": key, "value": rendered})
    return rows


def _selected_training_option_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    hyperparameters = dict(summary.get("resolved_hyperparameters") or summary.get("hyperparameters") or {})
    training = dict(summary.get("training_summary") or {})
    loss_summary = dict(training.get("loss") or summary.get("loss") or {})
    balance_summary = dict(training.get("balance_summary") or hyperparameters.get("balance_summary") or {})
    return [
        {
            "setting": "optimizer",
            "selected": summary.get("optimizer_label") or summary.get("optimizer_name") or summary.get("optimizer", ""),
            "technical": summary.get("optimizer_name") or summary.get("optimizer", ""),
            "effect_in_run": "updates GIN and pair-classifier parameters",
        },
        {
            "setting": "loss",
            "selected": loss_summary.get("loss_label") or summary.get("loss_label") or summary.get("loss_name", ""),
            "technical": loss_summary.get("loss_name") or summary.get("loss_name", ""),
            "effect_in_run": f"pos_weight={loss_summary.get('pos_weight', '-')}, alpha={loss_summary.get('alpha', '-')}, gamma={loss_summary.get('gamma', '-')}",
        },
        {
            "setting": "balancing",
            "selected": hyperparameters.get("balance_strategy_label") or hyperparameters.get("balance_strategy", ""),
            "technical": hyperparameters.get("balance_strategy", ""),
            "effect_in_run": balance_summary.get("operation", ""),
        },
        {
            "setting": "train_distribution",
            "selected": training.get("train_distribution", ""),
            "technical": "target counts after balancing",
            "effect_in_run": f"validation/test distribution={training.get('val_distribution', '')}",
        },
    ]


def _training_strategy_theory_rows() -> list[dict[str, Any]]:
    return [
        {
            "strategy": "Weighted BCE",
            "technical_function": "torch.nn.BCEWithLogitsLoss(pos_weight)",
            "formula": "L = -[w_p y log(sigmoid(z)) + (1-y) log(1-sigmoid(z))]",
            "interpretation": "Keeps all validated pairs and increases the cost of missing rare duplicate pairs. This is the preferred first strategy when positives are scarce.",
        },
        {
            "strategy": "Focal Loss",
            "technical_function": "custom sigmoid focal loss",
            "formula": "FL(p_t) = -alpha(1-p_t)^gamma log(p_t)",
            "interpretation": "Down-weights easy examples and concentrates gradient on hard or misclassified pairs. It is useful when the model otherwise learns only the dominant negative class.",
        },
        {
            "strategy": "Hard Negative Mining",
            "technical_function": "structural hard-negative sampler + BCEWithLogitsLoss",
            "formula": "score = |nodes_a-nodes_b| + |edges_a-edges_b|",
            "interpretation": "Keeps non-duplicate pairs that look structurally similar to positives. This tests whether the model can separate difficult near-matches instead of only easy negatives.",
        },
    ]


def _hyperparameter_grid_rows() -> list[dict[str, Any]]:
    return [
        {
            "parameter": "training strategy",
            "values": "Weighted BCE; Focal Loss; Hard Negatives",
            "count": 3,
            "reason": "Compares the main imbalance-handling families used by the GNN pipeline.",
        },
        {
            "parameter": "learning rate",
            "values": "0.001; 0.005; 0.010",
            "count": 3,
            "reason": "Controls optimizer step size and training stability.",
        },
        {
            "parameter": "hidden channels",
            "values": "16; 32",
            "count": 2,
            "reason": "Controls embedding capacity while keeping the search lightweight.",
        },
        {
            "parameter": "dropout",
            "values": "0.0; 0.1",
            "count": 2,
            "reason": "Tests whether regularization improves generalization on scarce positives.",
        },
        {
            "parameter": "inference threshold",
            "values": "0.4; 0.5; 0.6",
            "count": 3,
            "reason": "Moves the decision boundary between conservative and recall-oriented duplicate detection.",
        },
    ]


def _hyperparameter_protocol_rows() -> list[dict[str, Any]]:
    return [
        {
            "stage": "screening_5_scenarios",
            "scope": "3 benchmarks x 5 representative scenarios x 108 configs",
            "trainings": 1620,
            "selection_rule": "Rank configurations by SF-Jaccard, then retain top 5 per benchmark.",
            "protocol_output": "Documents broad search behavior without paying the cost of a full exhaustive grid.",
        },
        {
            "stage": "full_validation_20_scenarios",
            "scope": "3 benchmarks x 20 scenarios x top 5 configs",
            "trainings": 300,
            "selection_rule": "Retrain and evaluate only the top configurations across the complete benchmark suite.",
            "protocol_output": "Produces final results with complete scenario coverage and controlled compute cost.",
        },
        {
            "stage": "benchmark_final",
            "scope": "Best GNN configurations vs VF2, Node Match, GNN TPC-DS v1, GNN GenAI v1, and GNN GenAI v2",
            "trainings": 0,
            "selection_rule": "Report detector-family metrics by scenario and aggregate family.",
            "protocol_output": "Separates model-selection evidence from final detector-family comparison.",
        },
    ]


def _training_step_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    hyperparameters = dict(summary.get("resolved_hyperparameters") or summary.get("hyperparameters") or {})
    training = dict(summary.get("training_summary") or {})
    loss_summary = dict(training.get("loss") or summary.get("loss") or {})
    balance_summary = dict(training.get("balance_summary") or hyperparameters.get("balance_summary") or {})
    return [
        {
            "step": "1. Normalize graph input",
            "operation": "Load the curated scenario graph and normalize direction to SOR -> SOT -> SPEC.",
            "real_value": f"scenarios={training.get('scenarios', [])}",
        },
        {
            "step": "2. Build node-centered subgraphs",
            "operation": "For each candidate node, extract a local subgraph. SPEC nodes use upstream lineage; SOR nodes use downstream lineage; SOT nodes use both directions.",
            "real_value": "subgraphs generated from normalized NetworkX graph",
        },
        {
            "step": "3. Encode graph tensors",
            "operation": "Convert each subgraph into node feature matrix x and edge_index. Current baseline uses one scalar node feature per node.",
            "real_value": "x = ones(num_nodes, 1)",
        },
        {
            "step": "4. Sample supervised pairs",
            "operation": "Use the supervised validation table when available. In legacy-compatible runs, curated duplicate pairs define positives and negatives are sampled from non-labeled graph pairs.",
            "real_value": f"negative_ratio={hyperparameters.get('negative_ratio', '')}, generated_rows={training.get('dataset_rows', '')}",
        },
        {
            "step": "5. Split train/test",
            "operation": "Split the supervised dataset into train and validation/test partitions.",
            "real_value": f"train_ratio={hyperparameters.get('train_ratio', '')}, test_ratio={hyperparameters.get('test_ratio', '')}, train_size={training.get('train_size', '')}, val_size={training.get('val_size', '')}",
        },
        {
            "step": "6. Balance training distribution",
            "operation": "Apply the selected imbalance strategy only to the training partition. The validation/test partition keeps its observed label distribution.",
            "real_value": f"strategy={hyperparameters.get('balance_strategy_label') or hyperparameters.get('balance_strategy', '')}, operation={balance_summary.get('operation', '')}",
        },
        {
            "step": "7. GIN embedding layers",
            "operation": "Apply Graph Isomorphism Network aggregation to produce one embedding per subgraph.",
            "real_value": f"hidden_channels={hyperparameters.get('hidden_channels', '')}",
        },
        {
            "step": "8. Pair classifier",
            "operation": "Concatenate two subgraph embeddings and classify the pair with an MLP binary head.",
            "real_value": "output logit interpreted through sigmoid for duplicate probability",
        },
        {
            "step": "9. Optimization",
            "operation": "Optimize the configured loss with the selected optimizer over the configured epochs.",
            "real_value": f"loss={loss_summary.get('loss_name') or summary.get('loss_name', '')}, epochs={hyperparameters.get('epochs', '')}, learning_rate={hyperparameters.get('learning_rate', '')}, dropout={hyperparameters.get('dropout', '')}",
        },
    ]


def _formula_rows(summary: dict[str, Any], formula_mapping: dict[str, Any]) -> list[dict[str, Any]]:
    hyperparameters = dict(summary.get("resolved_hyperparameters") or summary.get("hyperparameters") or {})
    training = dict(summary.get("training_summary") or {})
    loss_summary = dict(training.get("loss") or summary.get("loss") or {})
    balance_summary = dict(training.get("balance_summary") or hyperparameters.get("balance_summary") or {})
    rows = [
        {
            "formula": "h_v^(k) = MLP^(k)((1 + eps^(k)) h_v^(k-1) + sum_{u in N(v)} h_u^(k-1))",
            "meaning": "GIN layer update. Neighbor messages are summed and transformed by an MLP.",
            "values_in_run": f"hidden_channels={hyperparameters.get('hidden_channels', '')}",
        },
        {
            "formula": "z_G = mean_pool({h_v^(K)})",
            "meaning": "Subgraph embedding. Node embeddings are pooled into one vector.",
            "values_in_run": f"embedding dimension={hyperparameters.get('hidden_channels', '')}",
        },
        {
            "formula": "y_hat = sigmoid(MLP([z_G1 || z_G2]))",
            "meaning": "Pair classifier. Two subgraph embeddings are concatenated and classified.",
            "values_in_run": "binary target: duplicate=1, not_duplicate=0",
        },
        {
            "formula": str(loss_summary.get("formula") or TRAINING_LOSS_OPTIONS.get(str(loss_summary.get("loss_key", "bce_with_logits")), TRAINING_LOSS_OPTIONS["bce_with_logits"])["formula"]),
            "meaning": f"Configured training loss: {loss_summary.get('loss_label') or summary.get('loss_label') or summary.get('loss_name', '')}.",
            "values_in_run": f"optimizer={summary.get('optimizer_name') or summary.get('optimizer', '')}, learning_rate={hyperparameters.get('learning_rate', '')}, pos_weight={loss_summary.get('pos_weight', '-')}",
        },
        {
            "formula": str(TRAINING_BALANCE_OPTIONS.get(str(hyperparameters.get("balance_strategy", "negative_sampling")), TRAINING_BALANCE_OPTIONS["negative_sampling"])["formula"]),
            "meaning": f"Selected imbalance strategy: {hyperparameters.get('balance_strategy_label') or hyperparameters.get('balance_strategy', '')}.",
            "values_in_run": f"operation={balance_summary.get('operation', '')}",
        },
    ]
    rows.extend({"formula": str(key), "meaning": "Recorded run parameter.", "values_in_run": value} for key, value in formula_mapping.items())
    return rows


def _benchmark_interpretation_rows(metric_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not metric_rows:
        return rows
    best_algorithm = ""
    try:
        best_algorithm = str(max(metric_rows, key=lambda row: float(row.get("sf_jaccard") or 0.0)).get("algorithm", ""))
    except Exception:
        best_algorithm = ""
    for row in metric_rows:
        algorithm = str(row.get("algorithm", ""))
        try:
            sf_jaccard = float(row.get("sf_jaccard") or 0.0)
            jaccard = float(row.get("jaccard") or 0.0)
            accuracy = float(row.get("accuracy") or 0.0)
            et = float(row.get("ET") or row.get("median_time") or 0.0)
        except Exception:
            sf_jaccard = jaccard = accuracy = et = 0.0
        if algorithm == best_algorithm:
            interpretation = "Best primary metric in this run; use as the current article candidate configuration."
        elif accuracy >= 0.70 and jaccard <= 0.02:
            interpretation = "High accuracy is mainly explained by true negatives; this is weak duplicate detection under imbalance."
        elif jaccard > 0.0 and sf_jaccard > 0.0:
            interpretation = "Detected some duplicate overlap; compare against the best strategy using SF-Jaccard and ET."
        else:
            interpretation = "No duplicate overlap was detected; useful as a negative baseline but not as the final detector."
        rows.append(
            {
                "algorithm": algorithm,
                "observed_result": f"SF-Jaccard={sf_jaccard:.6g}; Jaccard={jaccard:.6g}; Accuracy={accuracy:.6g}; ET={et:.6g}",
                "interpretation": interpretation,
                "article_takeaway": "SF-Jaccard is primary; accuracy is diagnostic because negatives dominate the candidate table.",
            }
        )
    return rows


def _training_history_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    training = dict(summary.get("training_summary") or {})
    history = list(training.get("history") or [])
    return [
        {
            "epoch": row.get("epoch"),
            "train_loss": row.get("train_loss"),
            "train_accuracy": row.get("train_accuracy"),
            "val_loss": row.get("val_loss"),
            "val_accuracy": row.get("val_accuracy"),
            "epoch_seconds": row.get("epoch_seconds"),
        }
        for row in history
    ]


def _tex_asset_path(asset_path: str | None, package_dir: Path) -> str:
    if not asset_path:
        return ""
    path = Path(asset_path)
    try:
        return path.relative_to(package_dir).as_posix()
    except ValueError:
        return path.name


def _run_tectonic(tex_path: Path, package_dir: Path, tectonic_path: str) -> list[dict[str, Any]]:
    """Compile a report with Tectonic, falling back to shell execution when direct subprocess panics."""
    attempts: list[dict[str, Any]] = []
    pdf_path = tex_path.with_suffix(".pdf")

    def _record(method: str, result: subprocess.CompletedProcess[str] | None, error: str | None = None) -> None:
        attempts.append(
            {
                "method": method,
                "returncode": result.returncode if result else None,
                "stdout_tail": (result.stdout or "")[-4000:] if result else "",
                "stderr_tail": (result.stderr or "")[-4000:] if result else "",
                "error": error,
                "pdf_exists_after": pdf_path.exists(),
            }
        )

    try:
        direct = subprocess.run(
            [tectonic_path, tex_path.name],
            cwd=str(package_dir),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
        )
        _record("direct_subprocess", direct)
        if pdf_path.exists():
            return attempts
    except Exception as exc:  # noqa: BLE001
        _record("direct_subprocess", None, str(exc))

    shell_path = shutil.which("zsh") or "/bin/zsh"
    shell_env = os.environ.copy()
    shell_env.setdefault("HOME", str(Path.home()))
    shell_env.setdefault("USER", os.environ.get("USER", ""))
    shell_env["PATH"] = os.environ.get("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/opt/homebrew/opt/tectonic/bin")
    command = f"{shlex.quote(tectonic_path)} {shlex.quote(tex_path.name)}"
    try:
        fallback = subprocess.run(
            [shell_path, "-lc", command],
            cwd=str(package_dir),
            env=shell_env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
        _record("zsh_login_shell_fallback", fallback)
    except Exception as exc:  # noqa: BLE001
        _record("zsh_login_shell_fallback", None, str(exc))
    return attempts


def _run_latex_engine(tex_path: Path, package_dir: Path) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    pdf_path = tex_path.with_suffix(".pdf")
    for engine in ("xelatex", "pdflatex"):
        engine_path = shutil.which(engine)
        if not engine_path:
            attempts.append({"method": engine, "available": False, "pdf_exists_after": pdf_path.exists()})
            continue
        try:
            result = subprocess.run(
                [engine_path, "-interaction=nonstopmode", "-halt-on-error", tex_path.name],
                cwd=str(package_dir),
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=180,
            )
            attempts.append(
                {
                    "method": engine,
                    "available": True,
                    "returncode": result.returncode,
                    "stdout_tail": (result.stdout or "")[-4000:],
                    "stderr_tail": (result.stderr or "")[-4000:],
                    "pdf_exists_after": pdf_path.exists(),
                }
            )
            if pdf_path.exists():
                return attempts
        except Exception as exc:  # noqa: BLE001
            attempts.append(
                {
                    "method": engine,
                    "available": True,
                    "returncode": None,
                    "error": str(exc),
                    "pdf_exists_after": pdf_path.exists(),
                }
            )
    return attempts


def _pdf_escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap_text(text: str, width: int = 96) -> list[str]:
    words = str(text).replace("\n", " ").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _native_pdf_report_lines(payload: dict[str, Any]) -> list[str]:
    summary = dict(payload.get("summary") or {})
    publication_tables = dict(payload.get("publication_tables") or {})
    lines = [
        "Isomera v2 Research Report",
        f"Captured at: {payload.get('captured_at', '')}",
        f"Report type: {payload.get('report_type', '')}",
        f"Benchmark: {summary.get('benchmark_display_name') or summary.get('benchmark_name', '')}",
        "",
        "Purpose",
        "This PDF was generated by the Isomera native PDF fallback because Tectonic failed inside the Python application process. The LaTeX source remains available in the package for final typesetting.",
        "",
        "Pipeline",
        "source -> normalized graph -> validation dataset -> training dataset -> model artifact -> benchmark results",
        "",
        "Isomera Staged Protocol",
        "The recommended protocol screens a reduced hyperparameter grid, ranks configurations by SF-Jaccard, validates the top configurations across all scenarios, and then runs the final detector-family benchmark.",
        "",
    ]
    for table_name in ("hyperparameter_search_grid", "hyperparameter_search_protocol", "training_strategy_theory", "training_strategy_comparison"):
        rows = list(publication_tables.get(table_name) or [])
        if rows:
            lines.extend([table_name.replace("_", " ").title()])
            for row in rows[:12]:
                lines.append(" | ".join(f"{key}: {value}" for key, value in row.items()))
            lines.append("")
    metric_rows = list(publication_tables.get("benchmark_metrics") or summary.get("benchmark_metrics") or [])
    if metric_rows:
        lines.extend(["Benchmark Metrics"])
        for row in metric_rows:
            lines.append(
                " | ".join(
                    f"{key}: {row.get(key)}"
                    for key in ("algorithm", "sf_jaccard", "jaccard", "ET", "accuracy", "N_pairs")
                    if key in row
                )
            )
        lines.append("")
    interpretation_rows = list(publication_tables.get("benchmark_interpretation") or [])
    if interpretation_rows:
        lines.extend(["Theory, Result, and Interpretation"])
        for row in interpretation_rows:
            lines.append(
                f"{row.get('algorithm')}: {row.get('observed_result')} -> {row.get('interpretation')}"
            )
        lines.append("")
    source_details = list(publication_tables.get("source_details") or [])
    if source_details:
        lines.extend(["Source Details"])
        for row in source_details[:30]:
            lines.append(f"{row.get('field')}: {row.get('value')}")
    return lines


def _write_native_pdf(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wrapped_lines: list[str] = []
    for line in lines:
        if not str(line).strip():
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(_wrap_text(str(line)))

    pages: list[list[str]] = []
    page: list[str] = []
    for line in wrapped_lines:
        if len(page) >= 48:
            pages.append(page)
            page = []
        page.append(line)
    if page:
        pages.append(page)
    if not pages:
        pages = [["Isomera v2 Research Report"]]

    objects: list[bytes] = []
    pages_obj_num = 2
    font_obj_num = 3
    first_page_obj = 4
    first_content_obj = first_page_obj + len(pages)
    kids = " ".join(f"{first_page_obj + index} 0 R" for index in range(len(pages)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("latin-1"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    content_streams: list[bytes] = []
    for index, page_lines in enumerate(pages):
        content_obj = first_content_obj + index
        page_obj = (
            f"<< /Type /Page /Parent {pages_obj_num} 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/Contents {content_obj} 0 R >>"
        )
        objects.append(page_obj.encode("latin-1"))
        content_parts = ["BT", "/F1 10 Tf", "50 750 Td", "14 TL"]
        for line_number, line in enumerate(page_lines):
            if line_number:
                content_parts.append("T*")
            content_parts.append(f"({_pdf_escape(line)}) Tj")
        content_parts.append("ET")
        stream = "\n".join(content_parts).encode("latin-1", errors="replace")
        content_streams.append(b"<< /Length " + str(len(stream)).encode("latin-1") + b" >>\nstream\n" + stream + b"\nendstream")
    objects.extend(content_streams)

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for obj_num, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{obj_num} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("latin-1")
    )
    path.write_bytes(bytes(pdf))


def _build_tex(payload: dict[str, Any], package_dir: Path, assets: dict[str, str | None]) -> str:
    summary = dict(payload.get("summary") or {})
    architecture = dict(payload.get("system_architecture") or {})
    scenario_api = dict(payload.get("scenario_api") or {})
    publication_tables = dict(payload.get("publication_tables") or {})
    pipeline = list(publication_tables.get("pipeline") or [])
    source_details = list(publication_tables.get("source_details") or [])
    validation_dataset = list(publication_tables.get("validation_dataset") or [])
    genai_validation_protocol = list(publication_tables.get("genai_validation_protocol") or [])
    training_dataset = list(publication_tables.get("training_dataset") or [])
    training_strategy_comparison = list(publication_tables.get("training_strategy_comparison") or [])
    training_strategy_theory = list(publication_tables.get("training_strategy_theory") or _training_strategy_theory_rows())
    hyperparameter_search_protocol = list(publication_tables.get("hyperparameter_search_protocol") or _hyperparameter_protocol_rows())
    hyperparameter_search_grid = list(publication_tables.get("hyperparameter_search_grid") or _hyperparameter_grid_rows())
    scenario_details = list(publication_tables.get("scenario_details") or [])
    model_cluster_rows = list(publication_tables.get("model_cluster_summary") or [])
    model_routing_rows = list(publication_tables.get("model_cluster_routing") or [])
    benchmark_per_scenario_rows = list(publication_tables.get("benchmark_per_scenario_metrics") or [])
    benchmark_pickle_rows = list(publication_tables.get("benchmark_pickle_results") or [])
    filter_rows = _normalize_filter_rows(list(publication_tables.get("filters") or []), summary)
    benchmark_metric_rows = list(publication_tables.get("benchmark_metrics") or _metric_rows(summary))
    benchmark_interpretation_rows = list(publication_tables.get("benchmark_interpretation") or _benchmark_interpretation_rows(benchmark_metric_rows))
    mysql_counts = list(publication_tables.get("mysql_row_counts") or summary.get("mysql_row_counts") or [])
    training_history_table = list(publication_tables.get("training_history") or _training_history_rows(summary))
    formula_mapping = dict(payload.get("formula_parameter_mapping") or {})
    graph_summary = dict(payload.get("graph_summary") or {})
    training_summary = dict(summary.get("training_summary") or {})

    lineage_img = _tex_asset_path(assets.get("lineage_png"), package_dir)
    adjacency_img = _tex_asset_path(assets.get("adjacency_png"), package_dir)
    benchmark_accuracy_img = _tex_asset_path(assets.get("benchmark_accuracy_png"), package_dir)
    benchmark_jaccard_img = _tex_asset_path(assets.get("benchmark_jaccard_png"), package_dir)
    benchmark_sf_jaccard_img = _tex_asset_path(assets.get("benchmark_sf_jaccard_png"), package_dir)
    benchmark_sf_jaccard_line_img = _tex_asset_path(assets.get("benchmark_sf_jaccard_line_by_scenario_png"), package_dir)
    benchmark_sf_jaccard_bar_scenario_img = _tex_asset_path(assets.get("benchmark_sf_jaccard_bar_by_scenario_png"), package_dir)
    benchmark_runtime_img = _tex_asset_path(assets.get("benchmark_runtime_png"), package_dir)

    layers = list(architecture.get("layers") or [])
    stores = list(architecture.get("stores") or [])
    api_functions = list(scenario_api.get("functions") or [])
    api_limits = list(scenario_api.get("limits") or [])

    lines = [
        r"\documentclass[11pt]{article}",
        r"\usepackage{graphicx}",
        r"\usepackage{longtable}",
        r"\usepackage{array}",
        r"\usepackage{url}",
        r"\usepackage{xurl}",
        r"\usepackage{ragged2e}",
        r"\usepackage{float}",
        r"\usepackage{placeins}",
        r"\usepackage[margin=1in]{geometry}",
        r"\title{Isomera v2: Scenario Materialization, Curation, and Benchmark Publication Report}",
        rf"\author{{Generated by Isomera v2}}",
        rf"\date{{{_tex_escape(payload.get('captured_at', datetime.now().isoformat()))}}}",
        r"\begin{document}",
        r"\maketitle",
        r"\section*{Abstract}",
        "This report documents an end-to-end Isomera v2 execution: relational scenario selection, lineage graph materialization, manual validation, supervised dataset creation, model training, and benchmark publication. It is generated as a reproducible package containing the article draft, source data, model artifacts, figures, and metadata.",
        r"\section{Introduction}",
        "Isomera v2 supports redundancy analysis in Data Mesh-like architectures by representing data products and transformations as directed lineage graphs. The system combines graph visualization, candidate-pair filtering, manual ground-truth creation, benchmark execution, and GNN-based model training.",
        "The main reproducible path used by this report is database source selection, relational schema loading, lineage graph materialization, candidate-pair reduction, manual duplicate validation, supervised dataset publication, model training, benchmark execution, and article package export.",
        r"\section{Related Work Context}",
        "The report package is designed to support a later IEEE-style article. It connects graph-based lineage modeling, graph isomorphism, duplicate detection, and graph neural networks into one reproducible experimental workflow.",
        r"\section{System Architecture}",
        _tex_escape(architecture.get("overview", "")),
        _architecture_diagram_tex(),
        "The architecture deliberately separates the source benchmark warehouse from the publication backend. PostgreSQL represents the external relational benchmark under analysis. MySQL stores curated publication evidence, reviewed pairs, report summaries, and model references. This split prevents benchmark source data from being mixed with experimental metadata and makes it easier to export a reproducible package.",
        r"\subsection{Component Responsibilities and Rationale}",
        _table_rows(_software_architecture_rationale_rows(), ["component", "responsibility", "rationale"], limit=12),
        r"\subsection{Architectural Layers}",
        _table_rows(layers, ["layer", "responsibility"], limit=10),
        r"\subsection{Data Stores}",
        _table_rows(stores, ["store", "technology", "purpose"], limit=10),
        r"\section{Database Architecture}",
        "The benchmark warehouse is stored in PostgreSQL. Each benchmark scenario is represented by one schema, such as scenario\\_sor2\\_d5\\_seed42. In practical terms, SOR2 means that the scenario was generated with two source-of-record nodes per configured domain group, D5 means that five business domains are present, and seed42 identifies the reproducible random seed/contract variant. If two scenarios are selected, Isomera reads two schemas and produces two normalized graphs, two validation datasets, and then one benchmark-level model/metrics package that references both scenarios.",
        "The MySQL backend is used as the publication/research backend for scenarios, nodes, edges, reviewed pairs, model artifacts, reports, and future operational logs. SQLite is retained only as a local fallback while the backend migration is completed.",
        r"\subsection{TPC-DS Domain Catalog}",
        "The current TPC-DS pilot uses five practical business domains. The D identifiers are not arbitrary visual labels: they identify the domain bucket used to generate SOR, SOT, and SPEC tables and to later filter candidate pairs. Future D6/D7 domains should be added through the same manifest-based contract.",
        _table_rows(_tpcds_domain_rows(), ["domain", "practical_context", "examples", "extension_rule"], limit=10),
        r"\subsection{Source Details}",
        _table_rows(source_details, ["field", "value"], limit=20),
        r"\subsection{Selected Benchmark Scenarios}",
        "When more than one scenario is selected, each PostgreSQL schema is materialized independently and then grouped under the same benchmark-level execution. The full scenario table is exported as CSV inside the package.",
        _table_rows(scenario_details, ["scenario", "schema", "nodes", "edges", "positive_pairs"], limit=20),
        r"\subsection{MySQL Publication Backend Validation}",
        _table_rows(mysql_counts, ["table", "rows"], limit=20),
        r"\section{Scenario Materialization API}",
        _tex_escape(scenario_api.get("purpose", "")),
        "Technically, the API is the reproducibility boundary of Isomera. Every supported source must be transformed into the same materialized contract before visualization, validation, training, benchmarking, or reporting. This avoids having one representation for the UI and another for the model.",
        r"\subsection{API Functions}",
        _table_rows(api_functions, ["function", "input", "output"], limit=10),
        r"\subsection{API Input/Output Contract}",
        _table_rows(_api_io_contract_rows(), ["artifact", "description", "consumer"], limit=10),
        r"\subsection{Normalization Method}",
        "The current normalization is not a general semantic inference engine. It is a deterministic layer-aware graph-direction procedure. It works reliably when the source exposes SOR, SOT, and SPEC semantics through names, node attributes, or a manifest. For arbitrary databases, Isomera needs a mapping contract before it can claim semantic SOR--SOT--SPEC normalization.",
        _table_rows(_normalization_method_rows(), ["step", "technical_rule", "limitation"], limit=10),
        r"\subsection{API Limits}",
        _table_rows([{"limit": item} for item in api_limits], ["limit"], limit=10),
        r"\section{Pipeline}",
        "The pipeline is source $\\rightarrow$ normalized graph $\\rightarrow$ validation dataset $\\rightarrow$ training dataset $\\rightarrow$ model artifact.",
        _table_rows(pipeline, ["stage", "input", "output", "details"], limit=10),
        r"\section{Lineage Graph and Matrix Views}",
        f"The normalized graph contains {_tex_escape(graph_summary.get('node_count', 'unknown'))} nodes and {_tex_escape(graph_summary.get('edge_count', 'unknown'))} directed edges. The direction is normalized to SOR $\\rightarrow$ SOT $\\rightarrow$ SPEC whenever the manifest or table names expose those layers.",
    ]
    if lineage_img:
        lines.extend(
            [
                r"\begin{figure}[h]",
                r"\centering",
                rf"\includegraphics[width=0.95\linewidth]{{{lineage_img}}}",
                r"\caption{Normalized lineage graph generated by the Scenario Materialization API.}",
                r"\end{figure}",
            ]
        )
    if adjacency_img:
        lines.extend(
            [
                r"\begin{figure}[h]",
                r"\centering",
                rf"\includegraphics[width=0.95\linewidth]{{{adjacency_img}}}",
                r"\caption{Binary adjacency matrix of the normalized graph.}",
                r"\end{figure}",
            ]
        )
    lines.extend(
        [
            r"\section{Candidate Filtering and Ground Truth}",
            "The final supervised table is produced by selecting candidate filters, reviewing each pair, and assigning a binary target. The target is 1 for duplicate and 0 for not duplicate. This table is the ground truth used by the training pipeline. A small subset can be used only to smoke-test the MySQL store, but article-grade datasets must come from complete ground-truth review or a documented benchmark label source such as TPC-DS real\\_pairs.",
            _table_rows(
                [
                    {"quantity": "total_pairs", "value": summary.get("total_pairs", "")},
                    {"quantity": "candidate_pairs", "value": summary.get("candidate_pairs", "")},
                    {"quantity": "reviewed_pairs", "value": summary.get("reviewed_pairs", "")},
                    {"quantity": "duplicate_pairs", "value": summary.get("duplicate_pairs", "")},
                ],
                ["quantity", "value"],
                limit=10,
            ),
            r"\subsection{Filter Protocol}",
            _table_rows(filter_rows, ["filter", "setting", "effect"], limit=20),
            *(
                [
                    r"\subsection{GenAI Validation Protocol}",
                    "This benchmark uses a documented GenAI-assisted validation protocol. The report stores the model metadata, reasoning-effort setting, decision rubric, and limitations so the validation process can be cited and audited. Private chain-of-thought is not stored; only the reproducible decision features and final labels are included.",
                    _table_rows(_key_value_rows(genai_validation_protocol[0]), ["field", "value"], limit=20),
                ]
                if genai_validation_protocol and isinstance(genai_validation_protocol[0], dict)
                else []
            ),
            r"\subsection{Supervised Validation Dataset}",
            _table_rows(validation_dataset, ["pair_index", "node_a", "node_b", "decision", "target"], limit=16),
            r"\section{Training Configuration}",
            "The current model family is the Graph Isomorphism Network Pair Classifier. The article-grade path uses a supervised validation dataset with target=1 for duplicate pairs and target=0 for non-duplicate pairs. Legacy-compatible runs can still derive negatives through negative sampling, but the report always records the effective loss, optimizer, split, and balancing strategy used to train the pickle.",
            "The model input is intentionally standardized: any future connector must first produce the same normalized graph, edge table, adjacency matrix, and supervised pair table. This is what allows a pickle trained from one curated benchmark to be evaluated consistently by Benchmark \\& Examples.",
            _table_rows(training_dataset, ["scenario", "positive_pairs", "negative_pairs", "dataset_rows"], limit=10),
            r"\subsection{Available Training Options}",
            "The following options are exposed in Isomera. The friendly name is what the user sees in the application; the technical function is what the backend actually executes or records.",
            _table_rows(_training_option_rows(), ["group", "friendly_name", "technical_function", "formula", "use"], limit=40),
            r"\subsection{Strategy Theory}",
            "The imbalance strategies below are not cosmetic labels. They change either the loss function or the composition of the training examples. This distinction matters for the article because duplicate pairs are rare and high accuracy can be achieved without discovering duplicates.",
            _table_rows(training_strategy_theory, ["strategy", "technical_function", "formula", "interpretation"], limit=10),
            r"\subsection{Isomera Staged Hyperparameter Protocol}",
            "The recommended Isomera protocol is a staged search, not an exhaustive grid. Exhaustive search grows combinatorially and would spend most compute on configurations that are unlikely to survive model selection. The staged protocol first screens representative scenarios, selects the top configurations by SF-Jaccard, and only then runs the complete 20-scenario validation. Users can still bypass this protocol and train a manual configuration when they want a single controlled run.",
            "For the proposed grid, one configuration means one combination of training strategy, learning rate, hidden-channel size, dropout, and inference threshold. The reduced grid has 108 configurations. Across three benchmark variants, screening on five representative scenarios requires 1620 trainings. Final validation of the top five configurations per benchmark over all 20 scenarios adds 300 trainings, for a total of 1920 trainings before the final detector-family benchmark.",
            _table_rows(hyperparameter_search_grid, ["parameter", "values", "count", "reason"], limit=10),
            _table_rows(hyperparameter_search_protocol, ["stage", "scope", "trainings", "selection_rule", "protocol_output"], limit=10),
            r"\subsection{Options Used in This Run}",
            _table_rows(_selected_training_option_rows(summary), ["setting", "selected", "technical", "effect_in_run"], limit=10),
            *(
                [
                    r"\subsection{Balancing Strategy Comparison}",
                    "When multiple GNN clusters are trained from the same supervised validation dataset, this table records the intended methodological contrast. The benchmark section reports the resulting detector-family metrics after applying the explicit inference threshold.",
                    _table_rows(
                        training_strategy_comparison,
                        ["model_family", "balance_strategy", "loss_name", "epochs", "threshold", "training_goal"],
                        limit=20,
                    ),
                ]
                if training_strategy_comparison
                else []
            ),
            r"\subsection{Training Data Flow}",
            _table_rows(_training_step_rows(summary), ["step", "operation", "real_value"], limit=12),
            r"\subsection{Model and Hyperparameters}",
            _table_rows(_model_artifact_rows(summary), ["field", "value"], limit=20),
            r"\subsection{Training Results}",
            "The following table records observed training and validation/test behavior per epoch. The current execution uses a short epoch budget to keep the end-to-end validation fast; article-grade runs can increase the epoch budget while reporting the same table.",
            _table_rows(training_history_table, ["scenario", "epoch", "train_loss", "train_accuracy", "val_loss", "val_accuracy", "epoch_seconds"], limit=30),
            r"\subsection{Formula to Parameter Mapping}",
            _table_rows(_formula_rows(summary, formula_mapping), ["formula", "meaning", "values_in_run"], limit=20),
            r"\section{Model Artifact}",
            "The trained pickle is copied into the report package and also referenced back to its original training location. For article reporting, GNN artifacts are interpreted as a detector family/cluster with scenario-specific artifact routing, not as one benchmark row per pickle.",
            _table_rows(
                [
                    {"field": "original_model_path", "value": summary.get("model_path", "")},
                    {"field": "package_model_path", "value": "models/" + Path(str(summary.get("model_path", "model.pkl"))).name},
                    {"field": "expected_input", "value": "normalized graph plus supervised pair table generated by the Scenario Materialization API"},
                ],
                ["field", "value"],
                limit=10,
            ),
            r"\subsection{Model Family / Cluster Reporting}",
            "The benchmark compares detector families. VF2 and Node Match are deterministic families without pickle artifacts. GNN v1 and GNN v2 are reported as families with scenario-specific pickle routing. This keeps the paper readable: the number of benchmark rows is the number of detector families, while the number of pickle files is reported as artifact count. The routing table is mandatory evidence: a cluster can only be interpreted as complete when every evaluated scenario maps to an explicit pickle artifact.",
            _table_rows(model_cluster_rows, ["model_family", "artifact_count", "scenario_count", "coverage", "reporting_rule"], limit=12),
            r"\subsection{Scenario-Specific Artifact Routing}",
            "The PDF view uses artifact file names to keep the table readable. The exported CSV keeps the full absolute artifact paths for reproducibility.",
            _table_rows(_artifact_display_rows(model_routing_rows), ["model_family", "scenario", "artifact_file", "artifact_role", "route_mode", "route_source"], limit=30),
            r"\section{Benchmark Metrics and Future Runs}",
            "Benchmark metrics are different from training metrics. Training metrics describe how the GNN behaved during supervised fitting. Benchmark metrics compare complete detector outputs against the selected ground truth and also measure runtime. Repetition medians are used because local execution time and stochastic training can vary between runs.",
            "In Isomera v2, ET is the median detector runtime for the evaluated scenario. SF metrics are not copies of Accuracy or Jaccard: they divide the score by ET and scale by the number of evaluated candidate pairs, preserving the original Isomera interpretation of successful pair decisions per second. Detector-family summaries report scenario-level SF values aggregated across the selected benchmark scenarios.",
            "Accuracy is retained as a diagnostic metric, but it is not the primary comparison metric for imbalanced duplicate detection. When most candidate pairs are negative, a detector can obtain high accuracy by correctly rejecting negatives while still failing to find duplicate pairs. For this reason, the report emphasizes SF-Jaccard: it uses Jaccard to focus on duplicate-pair overlap and then normalizes that overlap by execution time and evaluated pair volume.",
            r"\subsection{Benchmark Metric Formulas}",
            _table_rows(_benchmark_formula_rows(summary), ["metric", "formula", "interpretation"], limit=10),
            r"\subsection{Primary View: SF-Jaccard}",
            "The primary table places SF-Jaccard first and keeps Accuracy visible as a secondary diagnostic column. A high Accuracy with Jaccard equal to zero indicates that the detector is mostly benefiting from true negatives rather than detecting validated duplicate pairs.",
            _table_rows(benchmark_metric_rows, ["algorithm", "sf_jaccard", "jaccard", "ET", "accuracy", "sf_accuracy", "N_pairs"], limit=20),
            r"\subsection{Theory, Result, and Interpretation}",
            "This table connects the theoretical expectation of the detector family with the observed benchmark result. It is the paragraph-level bridge that should be used when writing the article discussion section.",
            _table_rows(benchmark_interpretation_rows, ["algorithm", "observed_result", "interpretation", "article_takeaway"], limit=20),
            r"\subsection{Full Benchmark Summary by Detector Family}",
            _table_rows(benchmark_metric_rows, ["algorithm", "accuracy", "jaccard", "sf_jaccard", "sf_accuracy", "ET", "N_pairs"], limit=20),
            r"\subsection{Benchmark Results by Scenario}",
            _table_rows(benchmark_per_scenario_rows, ["scenario", "algorithm", "accuracy", "jaccard", "sf_jaccard", "sf_accuracy", "ET", "N_pairs", "runs"], limit=40),
            r"\subsection{Per-Pickle Benchmark Results}",
            "This table links each GNN result to the exact pickle artifact used for that scenario. It is the table to cite when discussing model clusters, because each row is a concrete scenario--pickle--metric execution.",
            "The PDF view uses artifact file names; the full absolute artifact paths are preserved in benchmark\\_pickle\\_results.csv.",
            _table_rows(_artifact_display_rows(benchmark_pickle_rows), ["scenario", "algorithm", "artifact_file", "artifact_role", "route_mode", "sf_jaccard", "jaccard", "ET", "N_pairs"], limit=40),
            r"\subsection{Benchmark Figures}",
            *(
                [
                    r"\begin{figure}[h]",
                    r"\centering",
                    rf"\includegraphics[width=0.82\linewidth]{{{benchmark_sf_jaccard_img}}}",
                    r"\caption{Primary metric: SF-Jaccard by detector family.}",
                    r"\end{figure}",
                ]
                if benchmark_sf_jaccard_img
                else []
            ),
            *(
                [
                    r"\begin{figure}[h]",
                    r"\centering",
                    rf"\includegraphics[width=0.92\linewidth]{{{benchmark_sf_jaccard_line_img}}}",
                    r"\caption{SF-Jaccard line plot by scenario and detector family.}",
                    r"\end{figure}",
                ]
                if benchmark_sf_jaccard_line_img
                else []
            ),
            *(
                [
                    r"\begin{figure}[h]",
                    r"\centering",
                    rf"\includegraphics[width=0.92\linewidth]{{{benchmark_sf_jaccard_bar_scenario_img}}}",
                    r"\caption{SF-Jaccard grouped bars by scenario and detector family.}",
                    r"\end{figure}",
                ]
                if benchmark_sf_jaccard_bar_scenario_img
                else []
            ),
            *(
                [
                    r"\begin{figure}[h]",
                    r"\centering",
                    rf"\includegraphics[width=0.82\linewidth]{{{benchmark_accuracy_img}}}",
                    r"\caption{Benchmark accuracy by detector family.}",
                    r"\end{figure}",
                ]
                if benchmark_accuracy_img
                else []
            ),
            *(
                [
                    r"\begin{figure}[h]",
                    r"\centering",
                    rf"\includegraphics[width=0.82\linewidth]{{{benchmark_jaccard_img}}}",
                    r"\caption{Benchmark Jaccard score by detector family.}",
                    r"\end{figure}",
                ]
                if benchmark_jaccard_img
                else []
            ),
            *(
                [
                    r"\begin{figure}[h]",
                    r"\centering",
                    rf"\includegraphics[width=0.82\linewidth]{{{benchmark_runtime_img}}}",
                    r"\caption{Benchmark ET by detector family.}",
                    r"\end{figure}",
                ]
                if benchmark_runtime_img
                else []
            ),
            r"\section{Reproducibility Package}",
            "The accompanying zip package contains the LaTeX source, compiled PDF when available, source JSON, lineage and adjacency figures, source GML, labels, manifest, exported tables, model pickle, model metadata, and benchmark references.",
            r"\end{document}",
        ]
    )
    return "\n\n".join(lines)


def build_package(capture_path: Path | None = None) -> dict[str, str | None]:
    capture_path = capture_path or _latest_capture()
    payload = json.loads(capture_path.read_text(encoding="utf-8"))
    summary = dict(payload.get("summary") or {})
    scenario = _slug(str(summary.get("scenario") or "scenario"))
    scenario_short = _compact_slug(str(summary.get("scenario") or "scenario"), max_len=28)
    model_name = _slug(str(summary.get("model_name") or "model"))
    model_short = _compact_slug(str(summary.get("model_name") or "model"), max_len=32)
    date_prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    report_name = f"{date_prefix}_{scenario_short}_{model_short}"
    package_dir = MAIN_ROOT / "data" / "research_reports" / report_name
    data_dir = package_dir / "data"
    img_dir = package_dir / "images"
    model_dir = package_dir / "models"
    if package_dir.exists():
        shutil.rmtree(package_dir)
    package_dir.mkdir(parents=True, exist_ok=True)

    package_capture_json = data_dir / capture_path.name
    package_capture_md = data_dir / (capture_path.stem + ".md")
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(capture_path, package_capture_json)
    source_md = Path(str(payload.get("capture_paths", {}).get("markdown", "")))
    if source_md.exists():
        shutil.copy2(source_md, package_capture_md)

    assets: dict[str, str | None] = {}
    assets["lineage_png"] = _copy_if_exists(payload.get("capture_paths", {}).get("lineage_png"), img_dir / "lineage.png")
    assets["adjacency_png"] = _copy_if_exists(payload.get("capture_paths", {}).get("adjacency_png"), img_dir / "adjacency.png")
    assets["benchmark_accuracy_png"] = _copy_if_exists(
        payload.get("capture_paths", {}).get("benchmark_accuracy_png"),
        img_dir / "benchmark_accuracy.png",
    )
    assets["benchmark_jaccard_png"] = _copy_if_exists(
        payload.get("capture_paths", {}).get("benchmark_jaccard_png"),
        img_dir / "benchmark_jaccard.png",
    )
    assets["benchmark_sf_jaccard_png"] = _copy_if_exists(
        payload.get("capture_paths", {}).get("benchmark_sf_jaccard_png"),
        img_dir / "benchmark_sf_jaccard.png",
    )
    assets["benchmark_sf_jaccard_line_by_scenario_png"] = _copy_if_exists(
        payload.get("capture_paths", {}).get("benchmark_sf_jaccard_line_by_scenario_png"),
        img_dir / "benchmark_sf_jaccard_line_by_scenario.png",
    )
    assets["benchmark_sf_jaccard_bar_by_scenario_png"] = _copy_if_exists(
        payload.get("capture_paths", {}).get("benchmark_sf_jaccard_bar_by_scenario_png"),
        img_dir / "benchmark_sf_jaccard_bar_by_scenario.png",
    )
    assets["benchmark_runtime_png"] = _copy_if_exists(
        payload.get("capture_paths", {}).get("benchmark_runtime_png"),
        img_dir / "benchmark_runtime.png",
    )

    publication_tables = dict(payload.get("publication_tables") or {})
    publication_tables.setdefault("training_strategy_theory", _training_strategy_theory_rows())
    publication_tables.setdefault("hyperparameter_search_grid", _hyperparameter_grid_rows())
    publication_tables.setdefault("hyperparameter_search_protocol", _hyperparameter_protocol_rows())
    publication_tables.setdefault(
        "benchmark_interpretation",
        _benchmark_interpretation_rows(list(publication_tables.get("benchmark_metrics") or _metric_rows(summary))),
    )
    for table_name, rows in publication_tables.items():
        if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
            _write_csv(data_dir / f"{_slug(table_name)}.csv", rows)

    source_metadata = dict(payload.get("source_metadata") or {})
    manifest_path = source_metadata.get("manifest_path")
    _copy_if_exists(manifest_path, data_dir / "source_manifest.json")

    scenario_name = str(summary.get("scenario") or "")
    if scenario_name:
        _copy_if_exists(MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "gml" / f"{scenario_name}.gml", data_dir / f"{scenario_name}.gml")
        _copy_if_exists(MAIN_ROOT / "data" / "architectures" / "tpc_ds" / "real_pairs" / f"{scenario_name}.json", data_dir / f"{scenario_name}_real_pairs.json")
    for row in list(publication_tables.get("scenario_details") or []):
        if not isinstance(row, dict):
            continue
        scenario_row_name = str(row.get("scenario") or "")
        _copy_if_exists(row.get("gml_path"), data_dir / f"{scenario_row_name}.gml")
        _copy_if_exists(row.get("labels_path"), data_dir / f"{scenario_row_name}_real_pairs.json")
        _copy_if_exists(row.get("manifest_path"), data_dir / f"{scenario_row_name}_manifest.json")

    model_path = summary.get("model_path")
    copied_model = _copy_if_exists(model_path, model_dir / Path(str(model_path)).name) if model_path else None
    if model_path:
        _copy_if_exists(Path(str(model_path)).with_suffix(".json"), model_dir / Path(str(model_path)).with_suffix(".json").name)
    copied_models = [copied_model] if copied_model else []
    seen_model_paths = {str(model_path)} if model_path else set()
    for row in list(publication_tables.get("model_artifact") or []) + list(publication_tables.get("model_cluster_routing") or []):
        if not isinstance(row, dict):
            continue
        artifact_path = str(row.get("artifact_path") or "")
        if not artifact_path or artifact_path in seen_model_paths:
            continue
        seen_model_paths.add(artifact_path)
        copied = _copy_if_exists(artifact_path, model_dir / Path(artifact_path).name)
        if copied:
            copied_models.append(copied)
            _copy_if_exists(Path(artifact_path).with_suffix(".json"), model_dir / Path(artifact_path).with_suffix(".json").name)

    metadata = {
        "report_name": report_name,
        "naming_policy": "date_scenario_model",
        "full_scenario": scenario,
        "full_model_name": model_name,
        "source_capture": str(capture_path),
        "package_dir": str(package_dir),
        "model_copy": copied_model,
        "model_copies": copied_models,
        "contents": {
            "tex": f"{report_name}.tex",
            "pdf": f"{report_name}.pdf",
            "markdown": f"{report_name}.md",
            "zip": f"{report_name}.zip",
            "data": "data/",
            "images": [
                path
                for path in [
                    "images/lineage.png",
                    "images/adjacency.png",
                    "images/benchmark_accuracy.png",
                    "images/benchmark_jaccard.png",
                    "images/benchmark_sf_jaccard.png",
                    "images/benchmark_sf_jaccard_line_by_scenario.png",
                    "images/benchmark_sf_jaccard_bar_by_scenario.png",
                    "images/benchmark_runtime.png",
                ]
                if (package_dir / path).exists()
            ],
            "models": "models/",
        },
        "tectonic": {
            "attempted": False,
            "pdf_compiled": False,
            "error_log": None,
        },
    }

    tex_path = package_dir / f"{report_name}.tex"
    tex_text = _build_tex(payload, package_dir, assets)
    tex_path.write_text(tex_text, encoding="utf-8")

    def _tex_to_markdown_preview(text: str) -> str:
        text = re.sub(r"\\documentclass.*?\\begin\{document\}", "", text, flags=re.S)
        text = re.sub(r"\\end\{document\}", "", text)
        text = re.sub(r"\\title\{([^}]*)\}", r"# \1", text)
        text = re.sub(r"\\section\{([^}]*)\}", r"\n## \1\n", text)
        text = re.sub(r"\\subsection\{([^}]*)\}", r"\n### \1\n", text)
        text = re.sub(r"\\subsubsection\{([^}]*)\}", r"\n#### \1\n", text)
        text = re.sub(r"\\textbf\{([^}]*)\}", r"**\1**", text)
        text = re.sub(r"\\emph\{([^}]*)\}", r"*\1*", text)
        text = re.sub(r"\\begin\{itemize\}|\\end\{itemize\}", "", text)
        text = re.sub(r"\\item\s+", "- ", text)
        text = re.sub(r"\\begin\{[^}]+\}|\\end\{[^}]+\}", "", text)
        text = re.sub(r"\\[a-zA-Z]+(?:\[[^]]*\])?(?:\{[^}]*\})?", "", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"

    md_path = package_dir / f"{report_name}.md"
    md_path.write_text(_tex_to_markdown_preview(tex_text), encoding="utf-8")

    pdf_path = package_dir / f"{report_name}.pdf"
    tectonic_path = shutil.which("tectonic")
    metadata["tectonic"]["binary"] = tectonic_path
    if tectonic_path:
        metadata["tectonic"]["attempted"] = True
        attempts = _run_tectonic(tex_path, package_dir, tectonic_path)
        metadata["tectonic"]["attempts"] = attempts
        metadata["tectonic"]["pdf_compiled"] = pdf_path.exists()
        if not pdf_path.exists():
            latex_attempts = _run_latex_engine(tex_path, package_dir)
            metadata["tectonic"]["latex_engine_attempts"] = latex_attempts
            metadata["tectonic"]["pdf_compiled"] = pdf_path.exists()
            if pdf_path.exists():
                successful_engine = next(
                    (
                        attempt.get("method")
                        for attempt in latex_attempts
                        if attempt.get("pdf_exists_after")
                    ),
                    "latex_engine",
                )
                metadata["tectonic"]["native_pdf_fallback"] = False
                metadata["tectonic"]["pdf_compiler"] = successful_engine
            else:
                error_path = package_dir / "tectonic_error.log"
                error_payload = {
                    "tectonic_attempts": attempts,
                    "latex_engine_attempts": latex_attempts,
                }
                error_path.write_text(json.dumps(error_payload, indent=2, ensure_ascii=True), encoding="utf-8")
                metadata["tectonic"]["error_log"] = str(error_path)
                _write_native_pdf(pdf_path, _native_pdf_report_lines(payload))
                metadata["tectonic"]["native_pdf_fallback"] = True
                metadata["tectonic"]["pdf_compiled"] = pdf_path.exists()
                metadata["tectonic"]["pdf_compiler"] = "isomera_native_pdf_fallback"
        else:
            metadata["tectonic"]["native_pdf_fallback"] = False
            metadata["tectonic"]["pdf_compiler"] = "tectonic"
    else:
        metadata["tectonic"]["error_log"] = "Tectonic is not installed. Install it to compile the full LaTeX PDF inside Isomera."
        latex_attempts = _run_latex_engine(tex_path, package_dir)
        metadata["tectonic"]["latex_engine_attempts"] = latex_attempts
        metadata["tectonic"]["pdf_compiled"] = pdf_path.exists()
        if pdf_path.exists():
            successful_engine = next(
                (
                    attempt.get("method")
                    for attempt in latex_attempts
                    if attempt.get("pdf_exists_after")
                ),
                "latex_engine",
            )
            metadata["tectonic"]["native_pdf_fallback"] = False
            metadata["tectonic"]["pdf_compiler"] = successful_engine
        else:
            _write_native_pdf(pdf_path, _native_pdf_report_lines(payload))
            metadata["tectonic"]["native_pdf_fallback"] = True
            metadata["tectonic"]["pdf_compiled"] = pdf_path.exists()
            metadata["tectonic"]["pdf_compiler"] = "isomera_native_pdf_fallback"
    metadata["contents"]["pdf_available"] = pdf_path.exists()

    zip_base = str(package_dir)
    (package_dir / "package_manifest.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=True), encoding="utf-8")
    zip_path = Path(shutil.make_archive(zip_base, "zip", root_dir=package_dir))
    return {
        "package_dir": str(package_dir),
        "tex": str(tex_path),
        "pdf": str(pdf_path) if pdf_path.exists() else None,
        "markdown": str(md_path),
        "zip": str(zip_path),
    }


if __name__ == "__main__":
    capture_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    print(json.dumps(build_package(capture_arg), indent=2, ensure_ascii=True))
