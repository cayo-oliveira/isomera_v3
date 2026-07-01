"""Streamlit application for Isomera."""
from __future__ import annotations

import base64
import html
import json
import atexit
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from collections import deque
import os
import math
import re
import random
import shutil
import signal
import sys
import time
import traceback
from pathlib import Path
import tempfile
from urllib.parse import urlparse

import importlib.util
import subprocess

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

# Ensure project root is importable when running from the `ui` directory.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPT_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

try:
    from isomera_identity import load_identity, terminal_banner
except Exception:  # noqa: BLE001
    def load_identity() -> dict[str, str]:
        return {
            "product": "Isomera",
            "version": "2.5.0",
            "codename": "Trainable Mesh Workbench",
            "release_date": "2026-06-10",
            "author": "Cayo Oliveira",
            "email": "cflo@cin.ufpe.br",
            "summary": "Graph lineage workbench with trainable VMamba-T/VMamba-Mesh-T, Model Interpretability, CPU/MPS controls, Article IV reproducibility, Knowledge Base, reports, and presentation assets.",
        }

    def terminal_banner(title: str = "BOOT") -> str:
        identity = load_identity()
        return f"Isomera v{identity['version']} - {title}"


def _app_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _ensure_matplotlib_config_dir() -> None:
    if os.environ.get("MPLCONFIGDIR"):
        return

    default_dir = Path.home() / ".matplotlib"
    try:
        default_dir.mkdir(parents=True, exist_ok=True)
        probe = default_dir / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return
    except OSError:
        temp_dir = Path(tempfile.gettempdir()) / "isomera-matplotlib"
        temp_dir.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(temp_dir)


_ensure_matplotlib_config_dir()

from core.database import (
    build_lineage_from_db,
    count_table_rows,
    create_database_engine,
    create_sqlite_engine,
    ensure_scenario_validation_store,
    list_available_databases,
    list_database_schemas,
    list_schema_tables,
    list_table_columns,
    preview_table,
    replace_database_in_url,
    run_sql_statement,
    sql_statement_is_read_only,
    test_database_connection,
    upsert_scenario_validation_pair,
)
from core.isomorphism import apply_removals, find_isomorphic_pairs
from core.lineage import (
    adjacency_matrix_dataframe,
    edge_dataframe,
    generate_random_lineage_graph,
    normalize_lineage_direction,
    plot_lineage_graph,
    plot_adjacency_matrix,
    save_graph_gml,
)
from core.scenario_api import (
    graph_structure_rows,
    materialize_database_scenario,
    materialize_gml_scenario,
    materialize_graph,
    scenario_api_contract,
)
from core.genai_validation import (
    OPENAI_PRICING_HINTS,
    default_pair_validation_prompt,
    estimate_cost_usd,
    estimate_pair_validation_usage,
    list_openai_models,
    save_genai_agent_config,
    validate_pair_with_openai,
)
import matplotlib.pyplot as plt
from core.algorithms import list_algorithms, register_algorithm
from core.algorithms.gnn_training import (
    ScenarioTrainingSpec,
    TRAINING_BALANCE_OPTIONS,
    TRAINING_LOSS_OPTIONS,
    TRAINING_OPTIMIZER_OPTIONS,
    train_benchmark_gnn,
)
from core.algorithms.gnn_pickle import (
    BoundGNNPickleAlgorithm,
    set_gnn_pickle_path,
    set_gnn_pickle_module,
    validate_gnn_pickle,
)
from core.algorithms.vmamba_mesh import (
    MAMBA_PAPER_URL,
    VMAMBA_MESH_MODEL_VERSION,
    VMAMBA_PAPER_URL,
    VMAMBA_REPOSITORY_URL,
    VMambaMeshConfig,
    build_vmamba_mesh_study_package,
    install_or_update_vmamba_runtime,
    load_positive_pairs,
    pair_features,
    save_vmamba_mesh_artifact,
    vmamba_runtime_status,
)
from core.algorithms.vmamba_trainable import (
    VMAMBA_CHANNEL_CONTRACT,
    VMAMBA_TRAINABLE_MODEL_VERSION,
    VMAMBA_TRAINABLE_PRESETS,
    VMambaTrainableConfig,
    explain_vmamba_trainable_pair,
    graph_context_tensor,
    resolve_torch_device,
    save_vmamba_trainable_artifact,
    vmamba_trainable_preset_config,
)
from core.article_reproducibility import (
    create_reproduction_package,
    evidence_comparison_rows,
    get_article_spec,
    list_article_specs,
    run_quick_scenario,
)
from core.metrics import canonical_pairs, confusion_metrics_pairs, error_rate, execution_times, metrics_table
from core.persistence import (
    backend_status,
    create_app_session,
    create_label_version,
    create_report,
    create_run,
    default_backend_database_url,
    finalize_run,
    init_backend_database,
    list_recent_logs,
    list_recent_reports,
    list_recent_runs,
    record_log_event,
    register_artifact,
    register_model_artifact,
    touch_app_session,
    upsert_scenario,
)
from core.publication_store import publish_curated_scenario

_TEMP_GML_PATHS: set[Path] = set()
_TERMINAL_LOG_BUFFER: deque[str] = deque(maxlen=400)
_TERMINAL_LOG_HANDLE = None
_TERMINAL_LOG_PATH: Path | None = None
SHUTDOWN_REQUEST_PATH = Path(
    os.environ.get("ISOMERA_SHUTDOWN_REQUEST", str(_app_path("logs/isomera_shutdown.request")))
)


def _format_timeout(seconds: int) -> str:
    minutes = max(1, int(round(seconds / 60)))
    return f"{minutes} minute{'s' if minutes != 1 else ''}"


def _segmented_choice(
    label: str,
    options: list[str],
    key: str,
    default: str | None = None,
    label_visibility: str = "visible",
) -> str:
    default_value = st.session_state.get(key, default or options[0])
    if default_value not in options:
        default_value = options[0]
    if hasattr(st, "segmented_control"):
        value = st.segmented_control(
            label,
            options=options,
            default=default_value,
            key=key,
            label_visibility=label_visibility,
        )
        return str(value or default_value)
    index = options.index(default_value)
    return str(
        st.radio(
            label,
            options=options,
            index=index,
            horizontal=True,
            key=key,
            label_visibility=label_visibility,
        )
    )


def _multi_choice_pills(
    label: str,
    options: list[str],
    *,
    key: str,
    default: list[str] | None = None,
    help: str | None = None,
) -> list[str]:
    selected = list(st.session_state.get(key, default or []))
    selected = [value for value in selected if value in options]
    st.session_state[key] = selected
    header_cols = st.columns([6, 0.6], gap="small")
    header_cols[0].markdown(f"**{label}**")
    with header_cols[1]:
        if help:
            _info_popover(help)
    for start in range(0, len(options), 3):
        row = options[start : start + 3]
        cols = st.columns(len(row), gap="small")
        for col, option in zip(cols, row):
            is_selected = option in st.session_state[key]
            button_type = "primary" if is_selected else "secondary"
            if col.button(
                option,
                key=f"{key}_{option}",
                use_container_width=True,
                type=button_type,
            ):
                current = list(st.session_state.get(key, []))
                if option in current:
                    current.remove(option)
                else:
                    current.append(option)
                st.session_state[key] = current
                st.rerun()
    return list(st.session_state.get(key, []))


def _basic_markdown_html(markdown_text: str) -> str:
    """Render small help text as controlled HTML instead of Streamlit popovers."""
    escaped = html.escape(str(markdown_text or ""))
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    lines: list[str] = []
    in_list = False
    for raw_line in escaped.splitlines():
        line = raw_line.strip()
        if not line:
            if in_list:
                lines.append("</ul>")
                in_list = False
            continue
        if line.startswith("- "):
            if not in_list:
                lines.append("<ul>")
                in_list = True
            lines.append(f"<li>{line[2:]}</li>")
            continue
        if in_list:
            lines.append("</ul>")
            in_list = False
        lines.append(f"<p>{line}</p>")
    if in_list:
        lines.append("</ul>")
    return "\n".join(lines)


def _info_popover(markdown_text: str, *, key: str | None = None) -> None:
    """Render a compact SVG information control with a light, readable panel."""
    body = _basic_markdown_html(markdown_text)
    st.markdown(
        f"""
        <div class="iso-info-wrap" data-key="{html.escape(str(key or 'info'))}">
          <details class="iso-info-details">
            <summary aria-label="More information">
              <svg class="iso-info-svg" viewBox="0 0 20 20" role="img" aria-hidden="true">
                <circle cx="10" cy="10" r="8.5"></circle>
                <text x="10" y="14" text-anchor="middle">i</text>
              </svg>
            </summary>
            <div class="iso-info-panel">{body}</div>
          </details>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _model_help_text(model_label: str) -> str:
    if model_label == "VF2":
        return (
            "**VF2 graph isomorphism**\n\n"
            "Deterministic structural matcher. It compares subgraphs by exact topology and node constraints. "
            "It is useful as a strict baseline because it does not learn from data.\n\n"
            "**Decision idea:** two candidates are duplicates when their lineage subgraphs are structurally isomorphic."
        )
    if model_label.startswith("Node Match"):
        return (
            "**Node Match baseline**\n\n"
            "Deterministic heuristic that compares node attributes such as layer/domain signatures. "
            "It is faster than strict graph matching and useful as a lightweight rule-based baseline.\n\n"
            "**Decision idea:** candidate pairs match when their structural and semantic node signatures are compatible."
        )
    if "GNN" in model_label or "GIN" in model_label:
        return (
            f"**{model_label}**\n\n"
            "Graph Isomorphism Network based pair classifier. Each scenario routes to one or more `.pkl` artifacts. "
            "The benchmark can respect explicit scenario-to-pickle routing or test candidate pickles with a best-of policy.\n\n"
            "**Core formulas:**\n\n"
            "`h_v^(k) = MLP((1 + eps) h_v^(k-1) + sum_{u in N(v)} h_u^(k-1))`\n\n"
            "`z_G = mean_pool({h_v^(K)})`\n\n"
            "`y_hat = sigmoid(MLP([z_G1 || z_G2]))`\n\n"
            "**Use:** compare learned redundancy detection against VF2 and Node Match."
        )
    return (
        f"**{model_label}**\n\n"
        "Detector available for this benchmark. The report records its routing, metrics, timing, and selected artifacts."
    )


class _TeeStream:
    def __init__(self, stream, log_handle, buffer) -> None:
        self._stream = stream
        self._log_handle = log_handle
        self._buffer = buffer
        self._is_isomera_tee = True

    def write(self, data: str) -> int:
        if not data:
            return 0
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        self._stream.write(data)
        self._log_handle.write(data)
        self._log_handle.flush()
        for line in data.splitlines():
            self._buffer.append(line)
        return len(data)

    def flush(self) -> None:
        self._stream.flush()
        self._log_handle.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._stream, "isatty", lambda: False)())


def _init_terminal_logging() -> None:
    global _TERMINAL_LOG_HANDLE, _TERMINAL_LOG_PATH
    if getattr(sys.stdout, "_is_isomera_tee", False):
        return
    log_dir = _app_path("logs/terminal")
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    _TERMINAL_LOG_PATH = log_dir / f"terminal_{timestamp}.log"
    _TERMINAL_LOG_HANDLE = _TERMINAL_LOG_PATH.open("a", encoding="utf-8", errors="replace")

    existing = sorted(log_dir.glob("terminal_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old_path in existing[5:]:
        old_path.unlink(missing_ok=True)

    sys.stdout = _TeeStream(sys.stdout, _TERMINAL_LOG_HANDLE, _TERMINAL_LOG_BUFFER)
    sys.stderr = _TeeStream(sys.stderr, _TERMINAL_LOG_HANDLE, _TERMINAL_LOG_BUFFER)
    atexit.register(_finalize_terminal_log)


def _finalize_terminal_log() -> None:
    if _TERMINAL_LOG_HANDLE is None:
        return
    _TERMINAL_LOG_HANDLE.write("\n=== shutdown snapshot ===\n")
    _TERMINAL_LOG_HANDLE.write(f"timestamp={time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    for line in _TERMINAL_LOG_BUFFER:
        _TERMINAL_LOG_HANDLE.write(f"{line}\n")
    _TERMINAL_LOG_HANDLE.flush()
    _TERMINAL_LOG_HANDLE.close()


def _cleanup_temp_gml() -> None:
    for path in list(_TEMP_GML_PATHS):
        try:
            if path.exists():
                path.unlink()
        except Exception:
            continue


atexit.register(_cleanup_temp_gml)
_init_terminal_logging()


def _render_graph(graph, title: str, seed: int | None) -> None:
    st.subheader(title)
    fig = plot_lineage_graph(graph, seed=seed)
    st.pyplot(fig, clear_figure=True)


def _render_graph_white(graph, title: str, seed: int | None) -> None:
    st.subheader(title)
    fig = plot_lineage_graph(graph, seed=seed)
    if fig.axes:
        fig.axes[0].set_title("")
    fig.patch.set_facecolor("white")
    st.pyplot(fig, clear_figure=True)


def _render_graph_inline_white(graph, seed: int | None) -> None:
    fig = plot_lineage_graph(graph, seed=seed)
    if fig.axes:
        fig.axes[0].set_title("")
    fig.patch.set_facecolor("white")
    st.pyplot(fig, clear_figure=True)


def _draw_lineage_on_axes(ax, graph: nx.DiGraph, seed: int | None = None) -> None:
    pos = nx.spring_layout(graph, seed=seed)
    colors = []
    for node in graph.nodes:
        if "SOR" in node:
            colors.append("gray")
        elif "SOT" in node:
            colors.append("skyblue")
        elif "SPEC" in node:
            colors.append("green")
        else:
            colors.append("lightblue")
    nx.draw(
        graph,
        pos,
        with_labels=False,
        node_color=colors,
        edge_color="gray",
        node_size=120,
        ax=ax,
    )
    ax.set_axis_off()


def _build_benchmark_matrix_figure(
    matrix_map: dict[tuple[int, int], Path],
    sor_values: list[int],
    domain_values: list[int],
) -> plt.Figure:
    rows = len(sor_values)
    cols = len(domain_values)
    fig, axes = plt.subplots(rows, cols, figsize=(3 * cols, 2.4 * rows))
    if rows == 1 and cols == 1:
        axes = [[axes]]
    elif rows == 1:
        axes = [axes]
    elif cols == 1:
        axes = [[ax] for ax in axes]
    for i, sor in enumerate(sor_values):
        for j, domain in enumerate(domain_values):
            ax = axes[i][j]
            gml_path = matrix_map.get((sor, domain))
            if gml_path:
                graph = nx.read_gml(gml_path)
                _draw_lineage_on_axes(ax, graph, seed=42)
                ax.set_title(f"SOR {sor} / D{domain}", fontsize=8)
            else:
                ax.set_axis_off()
    fig.tight_layout()
    fig.patch.set_facecolor("white")
    return fig


def _render_adjacency(graph) -> None:
    st.markdown("Adjacency Matrix")
    fig = plot_adjacency_matrix(graph)
    st.pyplot(fig, clear_figure=True)
    with st.expander("Adjacency matrix table", expanded=False):
        df_adj = adjacency_matrix_dataframe(graph)
        st.table(df_adj)


def _render_edges(graph) -> None:
    st.markdown("Edges")
    edges_df = edge_dataframe(graph)
    st.table(edges_df)


def _step_badge(step: str, label: str, help_text: str) -> str:
    return (
        f"<div class='iso-step-inline'>"
        f"<span class='iso-step-chip'>{step}</span>"
        f"<span class='iso-step-label'>{label}</span>"
        f"<span class='iso-step-help' title='{help_text}'>i</span>"
        f"</div>"
    )


def _render_step_header(step: str, label: str, help_text: str, *, key: str) -> None:
    cols = st.columns([1.6, 7.0, 0.7], gap="small")
    cols[0].markdown(
        f"<div class='iso-step-chip'>{step}</div>",
        unsafe_allow_html=True,
    )
    cols[1].markdown(
        f"<div class='iso-step-label iso-step-label-block'>{label}</div>",
        unsafe_allow_html=True,
    )
    with cols[2]:
        _info_popover(help_text, key=key)


def _pair_context_subgraph(graph: nx.DiGraph, node: str) -> nx.DiGraph:
    layer = _node_layer(node)
    if layer == "SPEC":
        nodes = set(nx.ancestors(graph, node)) | {node}
    elif layer == "SOR":
        nodes = set(nx.descendants(graph, node)) | {node}
    else:
        nodes = set(nx.ancestors(graph, node)) | {node} | set(nx.descendants(graph, node))
    return graph.subgraph(sorted(nodes)).copy()


def _pair_scope_label(node_name: str) -> str:
    layer = _node_layer(node_name)
    if layer == "SPEC":
        return "Full lineage chain from this SPEC"
    if layer == "SOR":
        return "Full lineage chain into this SOR"
    if layer == "SOT":
        return "Full lineage chain around this SOT"
    return "Local lineage"


def _candidate_filter_status(
    graph: nx.DiGraph,
    candidate_pairs: list[tuple[str, str]],
    *,
    include_sor: bool,
    include_sot: bool,
    include_spec: bool,
    same_layer_only: bool,
    same_domain_only: bool,
    same_indegree_only: bool,
    same_outdegree_only: bool,
    same_parent_signature_only: bool,
    same_child_signature_only: bool,
) -> str:
    active_layers = []
    if include_sor:
        active_layers.append("SOR")
    if include_sot:
        active_layers.append("SOT")
    if include_spec:
        active_layers.append("SPEC")
    selected_nodes = [node for node in graph.nodes if _node_layer(node) in set(active_layers)]
    parts = [
        "scope: " + (", ".join(active_layers) if active_layers else "none"),
        f"{len(selected_nodes)} nodes in scope",
        f"{len(candidate_pairs)} candidate pairs",
    ]
    active_rules = []
    if same_layer_only:
        active_rules.append("same layer")
    if same_domain_only:
        active_rules.append("same domain")
    if same_indegree_only:
        active_rules.append("same input count")
    if same_outdegree_only:
        active_rules.append("same output count")
    if same_parent_signature_only:
        active_rules.append("same parent signature")
    if same_child_signature_only:
        active_rules.append("same child signature")
    if active_rules:
        parts.append("rules: " + ", ".join(active_rules))
    if include_spec:
        parts.append("SPEC = upstream lineage")
    return " | ".join(parts)


def _node_table_name(graph: nx.DiGraph, node: str, source_metadata: dict[str, object] | None = None) -> str:
    attrs = graph.nodes[node] if node in graph else {}
    table_name = attrs.get("table_name") or attrs.get("raw_name")
    if table_name:
        return str(table_name)
    manifest_path = Path(str((source_metadata or {}).get("manifest_path") or ""))
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for domain_payload in dict(manifest.get("domains") or {}).values():
                for table in list(domain_payload.get("tables") or []):
                    if str(table.get("node")) == str(node):
                        return str(table.get("table_name") or "")
        except Exception:
            return ""
    return ""


def _extract_table_sql(schema_sql: str, schema_name: str, table_name: str) -> dict[str, str]:
    escaped_schema = re.escape(schema_name)
    escaped_table = re.escape(table_name)
    qualified = rf'"{escaped_schema}"\."{escaped_table}"'
    create_match = re.search(
        rf"(CREATE TABLE IF NOT EXISTS\s+{qualified}\s*\(.*?\);)",
        schema_sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    insert_match = re.search(
        rf"(INSERT INTO\s+{qualified}\s*\(.*?;)",
        schema_sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return {
        "ddl": create_match.group(1).strip() if create_match else "",
        "dml": insert_match.group(1).strip() if insert_match else "",
    }


def _render_subgraph_sql_contract(
    graph: nx.DiGraph,
    subgraph: nx.DiGraph,
    source_metadata: dict[str, object] | None,
) -> None:
    metadata = source_metadata or {}
    schema_name = str(metadata.get("schema") or "")
    manifest_path = Path(str(metadata.get("manifest_path") or ""))
    schema_sql_path = manifest_path.with_name("schema.sql") if manifest_path.is_file() else None
    if not schema_name or not schema_sql_path or not schema_sql_path.is_file():
        st.caption("DDL/DML unavailable. Load this scenario from the PostgreSQL warehouse with a manifest-backed schema to inspect source SQL.")
        return
    schema_sql = schema_sql_path.read_text(encoding="utf-8", errors="replace")
    for node in sorted(subgraph.nodes, key=str):
        table_name = _node_table_name(graph, str(node), metadata)
        if not table_name:
            continue
        sql_blocks = _extract_table_sql(schema_sql, schema_name, table_name)
        with st.expander(f"DDL/DML for {node} -> {table_name}", expanded=False):
            if sql_blocks["ddl"]:
                st.markdown("**DDL**")
                st.code(sql_blocks["ddl"], language="sql")
            else:
                st.caption("DDL block not found in schema.sql.")
            if sql_blocks["dml"]:
                st.markdown("**DML / seed query**")
                st.code(sql_blocks["dml"], language="sql")
            else:
                st.caption("DML seed block not found in schema.sql.")


def _study_node_layer(node: str) -> str:
    upper = str(node).upper()
    if "SPEC" in upper:
        return "SPEC"
    if "SOT" in upper:
        return "SOT"
    if "SOR" in upper:
        return "SOR"
    return "OTHER"


def _study_layer_rank(node: str) -> int:
    return {"SOR": 0, "SOT": 1, "SPEC": 2}.get(_study_node_layer(node), 9)


def _study_hash01(value: str) -> float:
    total = 0
    for index, char in enumerate(str(value), start=1):
        total = (total + index * ord(char)) % 65536
    return round(total / 65535, 4)


def _study_lineage_graph(domains: int, sor_per_domain: int, *, cross_domain: bool) -> nx.DiGraph:
    graph = nx.DiGraph()
    domains = max(1, min(int(domains), 4))
    sor_per_domain = max(1, min(int(sor_per_domain), 5))
    for domain in range(1, domains + 1):
        domain_label = f"D{domain}"
        sots = [
            f"SOT_customer_orders_{domain_label}",
            f"SOT_catalog_sales_{domain_label}",
        ]
        specs = [
            f"SPEC_customer_summary_{domain_label}",
            f"SPEC_catalog_performance_{domain_label}",
        ]
        for sot in sots:
            graph.add_node(sot, layer="SOT", domain=domain_label)
        for spec in specs:
            graph.add_node(spec, layer="SPEC", domain=domain_label)
        for sor_index in range(1, sor_per_domain + 1):
            sor = f"SOR_source_{sor_index}_{domain_label}"
            graph.add_node(sor, layer="SOR", domain=domain_label)
            graph.add_edge(sor, sots[(sor_index - 1) % len(sots)], edge_type="lineage", weight=1.0)
            if sor_index % 2 == 0:
                graph.add_edge(sor, sots[1], edge_type="lineage", weight=1.0)
        graph.add_edge(sots[0], specs[0], edge_type="lineage", weight=1.0)
        graph.add_edge(sots[1], specs[0], edge_type="lineage", weight=1.0)
        graph.add_edge(sots[1], specs[1], edge_type="lineage", weight=1.0)
    if cross_domain and domains > 1:
        for domain in range(1, domains):
            graph.add_edge(
                f"SOT_catalog_sales_D{domain}",
                f"SPEC_catalog_performance_D{domain + 1}",
                edge_type="cross_domain_lineage",
                weight=1.0,
            )
    return graph


def _study_order_nodes(graph: nx.DiGraph, *, canon_sort: bool) -> list[str]:
    nodes = [str(node) for node in graph.nodes]
    if not canon_sort:
        return nodes
    return sorted(
        nodes,
        key=lambda node: (
            _study_layer_rank(node),
            -int(graph.out_degree(node)),
            -int(graph.in_degree(node)),
            str(graph.nodes[node].get("domain") or ""),
            node,
        ),
    )


def _study_lineage_matrix(
    graph: nx.DiGraph,
    *,
    resolution: int,
    canon_sort: bool,
    diag_fp: bool,
) -> tuple[list[list[float]], list[str], dict[str, int]]:
    resolution = max(8, int(resolution))
    nodes = _study_order_nodes(graph, canon_sort=canon_sort)
    visible_nodes = nodes[:resolution]
    index = {node: position for position, node in enumerate(visible_nodes)}
    matrix = [[0.0 for _ in range(resolution)] for _ in range(resolution)]
    dropped_edges = 0
    for source, target in graph.edges:
        source = str(source)
        target = str(target)
        if source not in index or target not in index:
            dropped_edges += 1
            continue
        matrix[index[source]][index[target]] = 1.0
    if diag_fp:
        for node, position in index.items():
            matrix[position][position] = max(matrix[position][position], _study_hash01(node))
    metadata = {
        "nodes_total": graph.number_of_nodes(),
        "edges_total": graph.number_of_edges(),
        "nodes_visible": len(visible_nodes),
        "dropped_nodes": max(0, graph.number_of_nodes() - len(visible_nodes)),
        "dropped_edges": dropped_edges,
    }
    return matrix, visible_nodes, metadata


def _study_route_coordinates(size: int, route: str) -> list[tuple[int, int]]:
    coords: list[tuple[int, int]] = []
    if route == "rows_backward":
        for row in range(size):
            for col in reversed(range(size)):
                coords.append((row, col))
    elif route == "cols_forward":
        for col in range(size):
            for row in range(size):
                coords.append((row, col))
    elif route == "cols_backward":
        for col in range(size):
            for row in reversed(range(size)):
                coords.append((row, col))
    else:
        for row in range(size):
            for col in range(size):
                coords.append((row, col))
    return coords


def _study_scan_once(
    matrix: list[list[float]],
    *,
    route: str,
    decay: float,
    input_gain: float,
    sparse_gate: float,
    threshold: float = 0.02,
) -> list[list[float]]:
    size = len(matrix)
    context = [[0.0 for _ in range(size)] for _ in range(size)]
    h_state = 0.0
    base_decay = max(0.0, min(float(decay), 0.995))
    input_gain = max(0.0, float(input_gain))
    sparse_gate = max(0.0, min(float(sparse_gate), 1.0))
    for row, col in _study_route_coordinates(size, route):
        value = float(matrix[row][col])
        active = value > threshold
        if active:
            h_state = base_decay * h_state + input_gain * value * (1.0 + sparse_gate)
        else:
            h_state = base_decay * (1.0 - 0.55 * sparse_gate) * h_state
        context[row][col] = abs(h_state)
    return context


def _study_average_context(contexts: list[list[list[float]]]) -> list[list[float]]:
    if not contexts:
        return []
    size = len(contexts[0])
    merged = [[0.0 for _ in range(size)] for _ in range(size)]
    for context in contexts:
        for row in range(size):
            for col in range(size):
                merged[row][col] += context[row][col] / len(contexts)
    return merged


def _study_selective_scan(
    matrix: list[list[float]],
    *,
    route: str,
    decay: float,
    input_gain: float,
    sparse_gate: float,
) -> list[list[float]]:
    routes = ["rows_forward", "rows_backward", "cols_forward", "cols_backward"] if route == "cross_scan_4" else [route]
    contexts = [
        _study_scan_once(
            matrix,
            route=item,
            decay=decay,
            input_gain=input_gain,
            sparse_gate=sparse_gate,
        )
        for item in routes
    ]
    return _study_average_context(contexts)


def _study_matrix_metrics(matrix: list[list[float]], context: list[list[float]]) -> dict[str, float]:
    active_values = []
    empty_values = []
    for row_index, row in enumerate(matrix):
        for col_index, value in enumerate(row):
            target = active_values if value > 0.02 else empty_values
            target.append(float(context[row_index][col_index]))
    active_mean = sum(active_values) / len(active_values) if active_values else 0.0
    empty_mean = sum(empty_values) / len(empty_values) if empty_values else 0.0
    contrast = active_mean / empty_mean if empty_mean else active_mean
    return {
        "active_context_mean": round(active_mean, 4),
        "empty_context_mean": round(empty_mean, 4),
        "active_empty_contrast": round(contrast, 4),
        "active_cells": float(len(active_values)),
        "empty_cells": float(len(empty_values)),
    }


def _study_heatmap_figure(
    values: list[list[float]],
    title: str,
    labels: list[str] | None = None,
    *,
    colorscale: str = "Greens",
) -> go.Figure:
    size = len(values)
    display_labels = None
    if labels and size <= 24:
        display_labels = list(labels[:size]) + [f"pad_{index}" for index in range(len(labels), size)]
    fig = go.Figure(
        data=go.Heatmap(
            z=values,
            x=display_labels,
            y=display_labels,
            colorscale=colorscale,
            colorbar={"title": "value"},
            hovertemplate="row=%{y}<br>col=%{x}<br>value=%{z:.4f}<extra></extra>",
        )
    )
    fig.update_layout(
        title=title,
        height=520,
        margin={"l": 40, "r": 20, "t": 58, "b": 40},
        paper_bgcolor="#F7F6F2",
        plot_bgcolor="#F7F6F2",
        font={"color": "#2F312E"},
    )
    if display_labels:
        fig.update_xaxes(tickangle=45, tickfont={"size": 9})
        fig.update_yaxes(tickfont={"size": 9})
    return fig


def _study_vmamba_code_blocks() -> dict[str, dict[str, str]]:
    return {
        "Patch embedding": {
            "where": "VMamba classification backbone, before VSS blocks.",
            "why": "Converts an image-like tensor into hidden channels. In Isomera this input is not a photo; it is a lineage tensor.",
            "snippet": (
                "x = patch_embed(lineage_tensor)       # [B, H, W, C]\n"
                "x = dropout_or_norm(x)\n"
                "for stage in vmamba_stages:\n"
                "    x = stage(x)"
            ),
            "mesh": "Replace raw image input with CanonSort + SOR/SOT/SPEC block channels + DiagFP before patch embedding.",
        },
        "VSS block": {
            "where": "Repeated visual state-space block in the VMamba backbone.",
            "why": "The VSS block plays the role that attention blocks play in a transformer-like vision model.",
            "snippet": (
                "residual = x\n"
                "x = norm(x)\n"
                "x = ss2d(x)               # global context through selective scan\n"
                "x = residual + drop_path(x)\n"
                "x = x + mlp(norm2(x))"
            ),
            "mesh": "Keep the block structure. Change the SS2D internals so lineage layers can initialize each other.",
        },
        "SS2D cross scan": {
            "where": "Core VMamba operation: 2D feature map -> multiple 1D routes -> selective scan -> merge.",
            "why": "Images do not have one natural sequence order. Four routes let the model collect context from different directions.",
            "snippet": (
                "routes = cross_scan(x)     # rows forward/backward, cols forward/backward\n"
                "routes = selective_scan(routes, A, B, C, Delta)\n"
                "x = cross_merge(routes)"
            ),
            "mesh": "Add MeshSS2D: hierarchical SOR->SOT->SPEC initialization and SparseGate on mostly-empty lineage cells.",
        },
        "Selective scan state update": {
            "where": "Inside SS2D after features are linearized into routes.",
            "why": "This is the learned memory recurrence that decides what to keep and what to forget.",
            "snippet": (
                "for t in route:\n"
                "    Delta_t, B_t, C_t = parameterize(x_t)\n"
                "    h_t = A_bar(Delta_t) * h_{t-1} + B_bar(Delta_t, B_t) * x_t\n"
                "    y_t = C_t * h_t"
            ),
            "mesh": "Make Delta sensitive to lineage activity and initialize channel states from upstream semantic layers.",
        },
    }


def _study_mesh_changes() -> list[dict[str, str]]:
    return [
        {
            "change": "CanonSort",
            "where": "Before patch embedding, inside the graph-to-image encoder.",
            "why": "Adjacency images depend on node order. CanonSort makes equivalent lineage subgraphs visually comparable.",
            "impact": "Less artificial variation, easier learning, better reproducibility.",
            "run": "Toggle CanonSort and compare adjacency layout plus dropped edges.",
        },
        {
            "change": "Block SOR-SOT-SPEC encoding",
            "where": "Graph-to-image encoder channels.",
            "why": "VMamba sees pixels. We need it to see lineage layer semantics.",
            "impact": "SOR->SOT and SOT->SPEC dependencies become stable matrix regions.",
            "run": "Use the same graph with and without canonical layer ordering.",
        },
        {
            "change": "DiagFP",
            "where": "Diagonal of the adjacency tensor before patch embedding.",
            "why": "The diagonal is mostly unused by lineage. It can carry table/schema identity.",
            "impact": "Can reduce false positives when graphs look structurally similar but represent different tables.",
            "run": "Toggle DiagFP and inspect diagonal intensity.",
        },
        {
            "change": "HierInit",
            "where": "Inside SS2D state initialization.",
            "why": "Data Mesh lineage is causal: SOR informs SOT, SOT informs SPEC.",
            "impact": "The state-space scan starts each layer with upstream semantic memory.",
            "run": "Compare context propagation when downstream blocks inherit upstream state.",
        },
        {
            "change": "SparseGate",
            "where": "Inside selective scan step-size/gate calculation.",
            "why": "Lineage matrices are sparse; empty cells should not dominate memory propagation.",
            "impact": "Expected lower noise on empty regions and better SF-Jaccard when ET stays controlled.",
            "run": "Increase SparseGate and compare active/empty context contrast.",
        },
    ]


def _study_vmamba_runtime_root() -> Path:
    return _app_path("external/VMamba")


def _study_vmamba_mesh_flow_html() -> str:
    return """
    <div class="iso-loading-card">
      <strong>VMamba -> VMamba-Mesh operational delta</strong>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:10px;">
        <div style="border:1px solid #d5d1c7;border-radius:14px;padding:12px;background:#fffdf7;">
          <b>Official VMamba</b>
          <p style="margin:8px 0 0 0;">Image -> patch embedding -> VSS blocks -> SS2D cross scan -> classifier.</p>
          <p style="margin:8px 0 0 0;"><b>Assumption:</b> dense visual texture and spatial locality.</p>
        </div>
        <div style="border:1px solid #9eb8ab;border-radius:14px;padding:12px;background:#f3faf6;">
          <b>VMamba-Mesh</b>
          <p style="margin:8px 0 0 0;">Lineage graph -> canonical pair tensor -> lineage-aware scan -> duplicate-pair head.</p>
          <p style="margin:8px 0 0 0;"><b>Assumption:</b> sparse SOR -> SOT -> SPEC causality and schema fingerprints.</p>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:12px;font-size:0.88rem;">
        <div style="padding:8px;border-radius:12px;background:#eef4f0;"><b>1 CanonSort</b><br/>Stable node order.</div>
        <div style="padding:8px;border-radius:12px;background:#eef4f0;"><b>2 Pair tensor</b><br/>A, B, diff, masks.</div>
        <div style="padding:8px;border-radius:12px;background:#eef4f0;"><b>3 DiagFP</b><br/>Schema identity.</div>
        <div style="padding:8px;border-radius:12px;background:#eef4f0;"><b>4 HierInit</b><br/>Upstream memory.</div>
        <div style="padding:8px;border-radius:12px;background:#eef4f0;"><b>5 SparseGate</b><br/>Ignore empty cells.</div>
      </div>
    </div>
    """


def _study_install_commands(runtime_root: Path) -> str:
    return "\n".join(
        [
            f"mkdir -p {runtime_root.parent}",
            f"git clone --depth 1 {VMAMBA_REPOSITORY_URL} {runtime_root}",
            f"{sys.executable} -m pip install -r {runtime_root}/requirements.txt",
        ]
    )


def _deep_learning_model_families() -> list[str]:
    return [
        "Vanilla VMamba baseline",
        "VMamba-Mesh Isomera adapter",
        "GNN Pair Classifier",
        "Custom/future model",
    ]


def _kb_root() -> Path:
    return PROJECT_ROOT.parent / ".github" / "knowledge_bases"


def _study_kb_files() -> list[tuple[str, Path, str]]:
    root = _kb_root()
    return [
        ("VMamba Foundation", root / "vmamba_foundation.md", "Mamba, VMamba, SS2D, VSSM, cross scan and forward types."),
        ("VMamba-Mesh Encoding", root / "vmamba_mesh_encoding.md", "CanonSort, tensorization, DiagFP, MeshSS2D, HierInit and SparseGate."),
        ("Reproducibility", root / "vmamba_mesh_reproducibility.md", "Benchmarks, article evidence, metrics and expected values."),
        ("Interpretability", root / "vmamba_mesh_interpretability.md", "ERF, SS2D routes, tensor channels and sensitivity views."),
        ("VMamba-T Video Runbook", root / "vmamba_trainable_video_runbook.md", "Validated trainable reports, hyperparameters, video steps and pending GPU campaign."),
    ]


def _render_study_knowledge_base() -> None:
    st.subheader("Knowledge Base")
    st.caption("Curated local KBs used by the Deep Learning Workbench and article reproducibility flow.")
    rows = []
    for title, path, summary in _study_kb_files():
        rows.append(
            {
                "topic": title,
                "path": str(path.relative_to(PROJECT_ROOT.parent)) if path.exists() else str(path),
                "available": path.exists(),
                "summary": summary,
            }
        )
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    selected_title = st.selectbox(
        "Open KB",
        options=[title for title, _, _ in _study_kb_files()],
        key="study_kb_select",
    )
    selected_path = next(path for title, path, _ in _study_kb_files() if title == selected_title)
    if selected_path.exists():
        st.markdown(selected_path.read_text(encoding="utf-8"))
    else:
        st.warning(f"KB file not found: {selected_path}")
    st.markdown("**Primary evidence paths**")
    st.markdown(
        """
        - `main/data/article_evidence/vmamba_mesh_genai_benchmark/`
        - `main/data/architectures/tpc_ds_genai_spec_v2/`
        - `main/data/architectures/tpc_ds_genai_full_lineage/`
        - `main/data/research_reports/`
        - `main/docs/presentations/vmamba_mesh_assets/`
        """
    )


def _model_family_status(model_family: str) -> str:
    if model_family == "Custom/future model":
        return "not_available"
    return "registered"


def _render_deep_learning_workbench() -> None:
    st.subheader("Deep Learning Workbench")
    st.caption("Compare model families over the same benchmark scenario and keep the result compatible with the Isomera benchmark contract.")
    model_family = st.selectbox(
        "Model family",
        options=_deep_learning_model_families(),
        key="dl_workbench_family",
    )
    if model_family == "Custom/future model":
        st.info("Custom/future model is reserved until a model registers a `predict_pairs(graph)` contract.")
    st.markdown(
        """
        <div class="iso-loading-card">
          <strong>Workbench contract</strong>
          <p>Every runnable model must expose <code>predict_pairs(graph)</code>. The app records operational trace data: parameters, files, model artifact, metrics and comparison status.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    study_architectures = [arch for arch in _list_architectures() if (Path(arch["root"]) / "gml").exists()]
    arch_names = [str(arch["name"]) for arch in study_architectures]
    default_arch = "tpc_ds_genai_spec_v2" if "tpc_ds_genai_spec_v2" in arch_names else (arch_names[0] if arch_names else "")
    config_cols = st.columns([1.0, 1.0, 0.75], gap="small")
    with config_cols[0]:
        selected_benchmark = st.selectbox(
            "Benchmark",
            options=arch_names,
            index=arch_names.index(default_arch) if default_arch in arch_names else 0,
            key="dl_workbench_benchmark",
            disabled=not arch_names,
        )
    benchmark_root = Path(_get_architecture(selected_benchmark)["root"]) if arch_names and _get_architecture(selected_benchmark) else DEFAULT_ARCH_ROOT
    scenario_options = sorted(path.stem for path in (benchmark_root / "gml").glob("*.gml"))
    default_scenario = "graph_SOR16_D1_seed42" if "graph_SOR16_D1_seed42" in scenario_options else (scenario_options[0] if scenario_options else "")
    with config_cols[1]:
        selected_scenario = st.selectbox(
            "Scenario",
            options=scenario_options,
            index=scenario_options.index(default_scenario) if default_scenario in scenario_options else 0,
            key="dl_workbench_scenario",
            disabled=not scenario_options,
        )
    with config_cols[2]:
        runs = st.number_input("Runs", min_value=1, max_value=25, value=1, key="dl_workbench_runs")

    if not arch_names or not scenario_options:
        st.warning("No benchmark scenarios are available.")
        return

    graph_path = benchmark_root / "gml" / f"{selected_scenario}.gml"
    labels_path = benchmark_root / "real_pairs" / f"{selected_scenario}.json"
    graph = nx.read_gml(graph_path)
    positive_pairs = load_positive_pairs(labels_path)
    pair_labels = [f"{a} <-> {b}" for a, b in positive_pairs]
    pair_cols = st.columns([1.25, 1.0, 1.0], gap="small")
    with pair_cols[0]:
        selected_pair_label = st.selectbox(
            "Duplicate pair",
            options=pair_labels or ["No validated duplicate pair"],
            key="dl_workbench_pair",
            disabled=not pair_labels,
        )
    model_options = _deep_learning_model_families()[:-1]
    with pair_cols[1]:
        model_a = st.selectbox("Model A", options=model_options, index=0, key="dl_workbench_model_a")
    with pair_cols[2]:
        model_b = st.selectbox("Model B", options=model_options, index=1, key="dl_workbench_model_b")

    if pair_labels:
        pair_index = pair_labels.index(selected_pair_label)
        node_a, node_b = positive_pairs[pair_index]
    else:
        node_a = node_b = ""

    graph_cols = st.columns([1.2, 1.0], gap="large")
    with graph_cols[0]:
        st.markdown("**Scenario graph**")
        fig = plot_lineage_graph(graph, seed=42)
        if fig.axes:
            fig.axes[0].set_title("")
        st.pyplot(fig, clear_figure=True)
    with graph_cols[1]:
        st.markdown("**Selected pair features**")
        if node_a and node_b:
            features = pair_features(graph, node_a, node_b)
            st.dataframe(
                pd.DataFrame(
                    [{"feature": key, "value": round(float(value), 6)} for key, value in sorted(features.items())]
                ),
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Select a validated pair to inspect features.")

    run_clicked = st.button(
        "Compare selected models",
        key="dl_workbench_compare_models",
        type="primary",
        use_container_width=True,
        disabled=model_family == "Custom/future model",
    )
    if run_clicked:
        rows = []
        traces = []
        for selected_model in [model_a, model_b]:
            row, trace = run_quick_scenario(
                PROJECT_ROOT.parent,
                benchmark=selected_benchmark,
                scenario=selected_scenario,
                model_family=selected_model,
                runs=int(runs),
            )
            rows.append(row)
            traces.extend(trace)
        st.session_state.dl_workbench_rows = rows
        st.session_state.dl_workbench_trace = traces
    if st.session_state.get("dl_workbench_rows"):
        st.markdown("**Model comparison**")
        st.dataframe(pd.DataFrame(st.session_state.dl_workbench_rows), width="stretch", hide_index=True)
    if st.session_state.get("dl_workbench_trace"):
        with st.expander("Reproducibility Trace", expanded=True):
            st.dataframe(pd.DataFrame(st.session_state.dl_workbench_trace), width="stretch", hide_index=True)


def _render_article_reproducibility() -> None:
    st.subheader("Article Reproducibility")
    st.caption("Select an article manifest, run a quick or article-level reproduction, and save an auditable trace.")
    specs = list_article_specs()
    labels = [spec.title for spec in specs]
    selected_label = st.selectbox("Article", options=labels, key="article_repro_select")
    spec = specs[labels.index(selected_label)]
    spec_rows = [
        {"field": "article_id", "value": spec.article_id},
        {"field": "status", "value": spec.status},
        {"field": "benchmarks", "value": ", ".join(spec.benchmarks)},
        {"field": "models", "value": ", ".join(spec.models)},
        {"field": "scenarios", "value": ", ".join(spec.scenarios)},
        {"field": "runs", "value": str(spec.runs)},
        {"field": "seeds", "value": ", ".join(str(seed) for seed in spec.seeds)},
    ]
    st.table(pd.DataFrame(spec_rows).astype(str))
    st.markdown(spec.summary)
    with st.expander("Source files and evidence", expanded=False):
        st.markdown("\n".join(f"- `{path}`" for path in spec.source_files))
        if spec.notes:
            st.markdown("**Notes**")
            st.markdown("\n".join(f"- {note}" for note in spec.notes))

    mode_label = _segmented_choice(
        "Mode",
        options=["Quick scenario", "Article evidence", "Complete package"],
        key="article_repro_mode",
        default="Quick scenario",
    )
    mode_map = {
        "Quick scenario": "quick",
        "Article evidence": "article",
        "Complete package": "complete",
    }
    mode = mode_map.get(str(mode_label), "quick")
    config_cols = st.columns(4, gap="small")
    with config_cols[0]:
        benchmark = st.selectbox("Benchmark", options=list(spec.benchmarks), key="article_repro_benchmark")
    with config_cols[1]:
        scenario = st.selectbox("Scenario", options=list(spec.scenarios), key="article_repro_scenario")
    with config_cols[2]:
        model_family = st.selectbox("Model", options=list(spec.models), key="article_repro_model")
    with config_cols[3]:
        runs = st.number_input("Runs", min_value=1, max_value=25, value=1 if mode == "quick" else spec.runs, key="article_repro_runs")

    preview_cols = st.columns([1, 1], gap="large")
    with preview_cols[0]:
        st.markdown("**Expected metric comparisons**")
        comparison_rows = evidence_comparison_rows(PROJECT_ROOT.parent, spec)
        if comparison_rows:
            st.table(pd.DataFrame(comparison_rows).astype(str))
        else:
            st.info("This article does not have frozen expected metrics yet.")
    with preview_cols[1]:
        st.markdown("**Operational trace policy**")
        st.markdown(
            """
            The trace records observable execution facts:

            - parameters and seeds;
            - files read and written;
            - model artifacts;
            - metrics and expected values;
            - comparison status.

            It does not expose hidden model reasoning.
            """
        )

    run_disabled = spec.status != "ready"
    if run_disabled:
        st.warning("This article manifest is planned but not ready for executable reproduction.")
    if st.button(
        "Run Reproduction",
        key="article_repro_run",
        type="primary",
        use_container_width=True,
        disabled=run_disabled,
    ):
        with st.spinner("Running article reproduction and writing trace package..."):
            package = create_reproduction_package(
                PROJECT_ROOT.parent,
                spec=get_article_spec(spec.article_id),
                mode=mode,
                benchmark=benchmark,
                scenario=scenario,
                model_family=model_family,
                runs=int(runs),
            )
        st.session_state.article_repro_last_package = package
        st.success(f"Reproduction package created: {package['package_name']}")
    if st.session_state.get("article_repro_last_package"):
        package = dict(st.session_state.article_repro_last_package)
        st.markdown("**Last reproduction package**")
        st.json(package)
        trace_path = Path(str(package.get("trace", "")))
        metrics_path = Path(str(package.get("metrics", "")))
        if metrics_path.exists():
            st.markdown("**Metrics**")
            st.table(pd.read_csv(metrics_path).astype(str))
        if trace_path.exists():
            st.markdown("**Reproducibility Trace**")
            st.table(pd.read_csv(trace_path).fillna("").astype(str))


def _safe_read_json(path: Path | str | None) -> dict[str, object]:
    if not path:
        return {}
    try:
        candidate = Path(str(path))
        if not candidate.exists():
            return {}
        payload = json.loads(candidate.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _list_vmamba_interpretability_reports() -> list[Path]:
    root = _app_path("data/research_reports")
    if not root.exists():
        return []
    return sorted(
        [
            path
            for path in root.iterdir()
            if path.is_dir()
            and (
                (path / "manifest.json").exists()
                or (path / "package_manifest.json").exists()
                or "vmamba" in path.name.lower()
                or "article_reproduction" in path.name.lower()
            )
        ],
        key=lambda path: path.name,
        reverse=True,
    )


def _manifest_for_report(report_dir: Path | None) -> dict[str, object]:
    if not report_dir:
        return {}
    for name in ("manifest.json", "package_manifest.json"):
        payload = _safe_read_json(report_dir / name)
        if payload:
            return payload
    return {}


def _list_vmamba_trainable_assets(benchmark_name: str, scenario_name: str | None = None) -> list[dict[str, object]]:
    root = _benchmark_storage_root(benchmark_name)
    assets: list[dict[str, object]] = []
    seen: set[str] = set()
    for model_dir_name, family_label in (("vmamba_mesh_t", "VMamba-Mesh-T"), ("vmamba_t", "VMamba-T")):
        model_root = root / "models" / model_dir_name
        if not model_root.exists():
            continue
        for pickle_path in sorted(model_root.glob("*.pkl")):
            resolved = str(pickle_path.resolve())
            if resolved in seen:
                continue
            metadata_path = pickle_path.with_suffix(".json")
            metadata = _safe_read_json(metadata_path)
            scenarios = metadata.get("scenarios") or metadata.get("source_scenarios") or []
            if isinstance(scenarios, str):
                scenarios = [scenarios]
            scenario_match = not scenario_name or scenario_name in str(pickle_path.name) or scenario_name in [str(item) for item in scenarios]
            if not scenario_match:
                continue
            seen.add(resolved)
            cfg = metadata.get("config") if isinstance(metadata.get("config"), dict) else {}
            label_bits = [
                family_label,
                pickle_path.stem.replace(family_label.replace("-", ""), "").strip("_")[:80],
            ]
            if cfg:
                label_bits.append(f"thr={float(cfg.get('threshold', 0.5)):.3f}")
            assets.append(
                {
                    "label": " | ".join(bit for bit in label_bits if bit),
                    "family": family_label,
                    "pickle_path": pickle_path,
                    "metadata_path": metadata_path if metadata_path.exists() else None,
                    "metadata": metadata,
                }
            )
    return assets


def _best_report_asset(report_manifest: dict[str, object]) -> dict[str, object] | None:
    best = report_manifest.get("best_by_sf_jaccard")
    if not isinstance(best, dict):
        return None
    pickle_path = Path(str(best.get("pickle_path") or ""))
    if not pickle_path.exists():
        return None
    metadata_path = Path(str(best.get("metadata_path") or pickle_path.with_suffix(".json")))
    family = str(best.get("family_base") or best.get("family") or best.get("algorithm") or "VMamba trainable")
    return {
        "label": f"{family} | best from selected report | {pickle_path.stem[:80]}",
        "family": family,
        "pickle_path": pickle_path,
        "metadata_path": metadata_path if metadata_path.exists() else None,
        "metadata": _safe_read_json(metadata_path),
    }


def _as_numpy_tensor(value: object) -> object:
    if hasattr(value, "detach"):
        return value.detach().cpu().numpy()  # type: ignore[union-attr]
    if hasattr(value, "numpy"):
        return value.numpy()  # type: ignore[union-attr]
    return value


def _plot_vmamba_channel_grid(tensor: object, channels: list[str], title: str) -> plt.Figure:
    data = _as_numpy_tensor(tensor)
    rows = 2 if len(channels) > 3 else 1
    cols = max(math.ceil(len(channels) / rows), 1)
    fig, axes = plt.subplots(rows, cols, figsize=(3.0 * cols, 2.6 * rows), squeeze=False)
    fig.suptitle(title, fontsize=12, fontweight="bold")
    for idx, channel in enumerate(channels):
        ax = axes[idx // cols][idx % cols]
        matrix = data[idx] if getattr(data, "ndim", 0) == 3 and idx < data.shape[0] else data
        image = ax.imshow(matrix, cmap="magma", aspect="equal")
        contract = VMAMBA_CHANNEL_CONTRACT.get(str(channel), {})
        ax.set_title(f"{channel} - {contract.get('name', channel)}", fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.03)
    for idx in range(len(channels), rows * cols):
        axes[idx // cols][idx % cols].axis("off")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    return fig


def _plot_vmamba_aggregate_map(tensor: object, title: str, cmap: str = "viridis") -> plt.Figure:
    data = _as_numpy_tensor(tensor)
    if getattr(data, "ndim", 0) == 3:
        matrix = data.sum(axis=0)
    else:
        matrix = data
    fig, ax = plt.subplots(figsize=(6.4, 5.2))
    image = ax.imshow(matrix, cmap=cmap, aspect="equal")
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xticks([])
    ax.set_yticks([])
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.03)
    fig.tight_layout()
    return fig


def _save_vmamba_interpretability_package(
    *,
    benchmark: str,
    scenario: str,
    node_a: str,
    node_b: str,
    model_label: str,
    trace_rows: list[dict[str, object]],
    figures: dict[str, plt.Figure],
    manifest_extra: dict[str, object],
) -> Path:
    stamp = time.strftime("%Y%m%d_%H%M%S")
    safe_scenario = re.sub(r"[^A-Za-z0-9._-]+", "_", scenario)
    package_dir = _app_path("data/research_reports") / f"{stamp}_vmamba_interpretability_{safe_scenario}"
    figures_dir = package_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    figure_paths: dict[str, str] = {}
    for name, fig in figures.items():
        path = figures_dir / f"{name}.png"
        fig.savefig(path, dpi=180, bbox_inches="tight")
        figure_paths[name] = str(path)
    pd.DataFrame(trace_rows).to_csv(package_dir / "interpretability_trace.csv", index=False)
    manifest = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "benchmark": benchmark,
        "scenario": scenario,
        "pair": [node_a, node_b],
        "model_label": model_label,
        "interpretability_contract": [
            "selected report/manifest",
            "benchmark scenario graph",
            "candidate pair",
            "C0-C5 or C0-C1 tensorization",
            "structural channel maps",
            "neural input-gradient saliency when trainable pickle is available",
            "score/threshold/decision trace",
        ],
        "figures": figure_paths,
        **manifest_extra,
    }
    (package_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    (package_dir / "README.md").write_text(
        "\n".join(
            [
                "# VMamba Interpretability Package",
                "",
                f"- Benchmark: `{benchmark}`",
                f"- Scenario: `{scenario}`",
                f"- Pair: `{node_a}` / `{node_b}`",
                f"- Model: `{model_label}`",
                "",
                "This package records observable interpretability artifacts generated inside Isomera: tensors, channel maps, saliency maps when a trainable PyTorch pickle is available, and an auditable trace.",
            ]
        ),
        encoding="utf-8",
    )
    return package_dir


def _render_vmamba_interpretability_lab() -> None:
    st.subheader("Model Interpretability")
    st.caption("Open a completed report, choose a scenario and pair, then generate structural and neural interpretability artifacts.")
    st.info(
        "Article IV reference path: `tpc_ds_genai_spec_v2` / `graph_SOR16_D1_seed42`, "
        "pair `SPEC_customer_summary_D1 <-> SPEC_store_sales_summary_D1`. "
        "Graph, adjacency and C0-C5 channels describe the scenario context; saliency is local to the selected pair and checkpoint.",
    )
    reports = _list_vmamba_interpretability_reports()
    report_options = [None] + reports
    selected_report = st.selectbox(
        "Completed report or manifest",
        options=report_options,
        format_func=lambda path: "Manual selection" if path is None else Path(path).name,
        key="vmamba_interp_report",
    )
    report_manifest = _manifest_for_report(selected_report) if selected_report else {}
    if selected_report:
        st.caption(f"Selected report: `{selected_report}`")
        if report_manifest.get("pipeline_contract"):
            with st.expander("Report pipeline contract", expanded=False):
                st.markdown("\n".join(f"- {item}" for item in report_manifest.get("pipeline_contract", [])))

    benchmark_names = [str(arch["name"]) for arch in _list_architectures() if (Path(arch["root"]) / "gml").exists()]
    manifest_benchmark = str(report_manifest.get("benchmark") or "")
    default_benchmark = manifest_benchmark if manifest_benchmark in benchmark_names else ("tpc_ds_genai_spec_v2" if "tpc_ds_genai_spec_v2" in benchmark_names else (benchmark_names[0] if benchmark_names else ""))
    config_cols = st.columns([1.1, 1.1, 1.25], gap="small")
    with config_cols[0]:
        benchmark = st.selectbox(
            "Benchmark",
            options=benchmark_names,
            index=benchmark_names.index(default_benchmark) if default_benchmark in benchmark_names else 0,
            key="vmamba_interp_benchmark",
            disabled=not benchmark_names,
        )
    if not benchmark_names:
        st.warning("No benchmark with GML scenarios is available.")
        return
    root, _, _ = _scenario_paths_for_study(benchmark, "")
    scenarios = sorted(path.stem for path in (root / "gml").glob("*.gml"))
    manifest_scenarios = [str(item) for item in report_manifest.get("scenarios", [])] if isinstance(report_manifest.get("scenarios"), list) else []
    default_scenario = (
        str((report_manifest.get("best_by_sf_jaccard") or {}).get("scenario") or "")
        if isinstance(report_manifest.get("best_by_sf_jaccard"), dict)
        else ""
    )
    if default_scenario not in scenarios:
        default_scenario = "graph_SOR16_D1_seed42" if "graph_SOR16_D1_seed42" in scenarios else (manifest_scenarios[0] if manifest_scenarios and manifest_scenarios[0] in scenarios else (scenarios[0] if scenarios else ""))
    with config_cols[1]:
        scenario = st.selectbox(
            "Scenario",
            options=scenarios,
            index=scenarios.index(default_scenario) if default_scenario in scenarios else 0,
            key="vmamba_interp_scenario",
            disabled=not scenarios,
        )
    if not scenarios:
        st.warning("No scenarios are available for this benchmark.")
        return

    _, graph_path, labels_path = _scenario_paths_for_study(benchmark, scenario)
    graph = nx.read_gml(graph_path)
    positive_pairs = load_positive_pairs(labels_path)
    pair_options = [f"{a} <-> {b}" for a, b in positive_pairs]
    reference_pair_options = {
        "SPEC_customer_summary_D1 <-> SPEC_store_sales_summary_D1",
        "SPEC_store_sales_summary_D1 <-> SPEC_customer_summary_D1",
    }
    reference_pair_index = next((idx for idx, label in enumerate(pair_options) if label in reference_pair_options), 0)
    with config_cols[2]:
        selected_pair_label = st.selectbox(
            "Pair",
            options=pair_options or ["No validated pair"],
            index=reference_pair_index if pair_options else 0,
            key="vmamba_interp_pair",
            disabled=not pair_options,
        )
    if not positive_pairs:
        st.info("This scenario does not have validated duplicate pairs.")
        return
    node_a, node_b = positive_pairs[pair_options.index(selected_pair_label)]

    report_asset = _best_report_asset(report_manifest)
    assets = _list_vmamba_trainable_assets(benchmark, scenario)
    if report_asset and all(str(asset["pickle_path"]) != str(report_asset["pickle_path"]) for asset in assets):
        assets.insert(0, report_asset)
    model_choices: list[dict[str, object] | None] = [None] + assets
    selected_asset = st.selectbox(
        "Model artifact",
        options=model_choices,
        format_func=lambda item: "Structural C0-C5 explanation (no neural pickle)" if item is None else str(item.get("label")),
        key="vmamba_interp_model_asset",
    )
    run_interpretability = st.button(
        "Run Interpretability",
        key="vmamba_interp_run",
        type="primary",
        use_container_width=True,
    )
    if run_interpretability:
        with st.spinner("Generating channel maps, saliency and interpretability package..."):
            figures: dict[str, plt.Figure] = {}
            trace_rows: list[dict[str, object]] = [
                {"step": "load_report", "value": str(selected_report) if selected_report else "manual"},
                {"step": "load_graph", "value": str(graph_path)},
                {"step": "load_labels", "value": str(labels_path)},
                {"step": "selected_pair", "value": f"{node_a} <-> {node_b}"},
            ]
            if selected_asset is None:
                cfg = VMambaTrainableConfig(variant="vmamba_mesh_t", channels=("C0", "C1", "C2", "C3", "C4", "C5"), resolution=16)
                left_tensor = graph_context_tensor(graph, node_a, config=cfg)
                right_tensor = graph_context_tensor(graph, node_b, config=cfg)
                channels = list(cfg.channels)
                left_np = _as_numpy_tensor(left_tensor)
                right_np = _as_numpy_tensor(right_tensor)
                diff_np = abs(left_np - right_np)
                feature_map = pair_features(
                    graph,
                    node_a,
                    node_b,
                    config=VMambaMeshConfig(scope_layers=("SPEC",), canon_sort=True, diag_fp=True, mesh_ss2d=True, hier_init=True, sparse_gate=True, resolution=16),
                )
                score = sum(float(value) for value in feature_map.values()) / max(len(feature_map), 1)
                threshold = 0.5
                trace_rows.extend(
                    [
                        {"step": "mode", "value": "structural"},
                        {"step": "score", "value": round(score, 6)},
                        {"step": "threshold", "value": threshold},
                        {"step": "decision", "value": "duplicate" if score >= threshold else "not_duplicate"},
                    ]
                )
                figures["left_channels"] = _plot_vmamba_channel_grid(left_np, channels, f"{node_a}: C0-C5 tensor")
                figures["right_channels"] = _plot_vmamba_channel_grid(right_np, channels, f"{node_b}: C0-C5 tensor")
                figures["pair_difference"] = _plot_vmamba_channel_grid(diff_np, channels, "|left - right| by channel")
                figures["structural_influence"] = _plot_vmamba_aggregate_map(left_np + right_np + diff_np, "Structural influence map", cmap="inferno")
                result_payload = {
                    "mode": "structural",
                    "score": score,
                    "threshold": threshold,
                    "decision": "duplicate" if score >= threshold else "not_duplicate",
                    "features": feature_map,
                    "channels": channels,
                }
            else:
                pickle_path = Path(str(selected_asset["pickle_path"]))
                explanation = explain_vmamba_trainable_pair(model_path=pickle_path, graph=graph, node_a=node_a, node_b=node_b)
                channels = [str(item) for item in explanation.get("channels", [])]
                trace_rows.extend(
                    [
                        {"step": "mode", "value": "trainable_gradient"},
                        {"step": "pickle_path", "value": str(pickle_path)},
                        {"step": "resolved_device", "value": explanation.get("resolved_device")},
                        {"step": "logit", "value": round(float(explanation.get("logit", 0.0)), 6)},
                        {"step": "score_sigmoid", "value": round(float(explanation.get("score", 0.0)), 6)},
                        {"step": "threshold", "value": round(float(explanation.get("threshold", 0.5)), 6)},
                        {"step": "decision", "value": explanation.get("decision")},
                    ]
                )
                left_np = explanation["left_tensor"]
                right_np = explanation["right_tensor"]
                diff_np = abs(left_np - right_np)
                figures["left_channels"] = _plot_vmamba_channel_grid(left_np, channels, f"{node_a}: neural input tensor")
                figures["right_channels"] = _plot_vmamba_channel_grid(right_np, channels, f"{node_b}: neural input tensor")
                figures["pair_difference"] = _plot_vmamba_channel_grid(diff_np, channels, "|left - right| by channel")
                figures["neural_saliency"] = _plot_vmamba_channel_grid(explanation["saliency"], channels, "Input-gradient saliency by channel")
                figures["saliency_aggregate"] = _plot_vmamba_aggregate_map(explanation["saliency"], "Neural saliency aggregate", cmap="inferno")
                result_payload = {
                    "mode": "trainable_gradient",
                    "score": explanation.get("score"),
                    "threshold": explanation.get("threshold"),
                    "decision": explanation.get("decision"),
                    "resolved_device": explanation.get("resolved_device"),
                    "channels": channels,
                    "channel_saliency": explanation.get("channel_saliency", []),
                    "pickle_path": str(pickle_path),
                    "metadata_path": str(selected_asset.get("metadata_path") or ""),
                }
            package_dir = _save_vmamba_interpretability_package(
                benchmark=benchmark,
                scenario=scenario,
                node_a=node_a,
                node_b=node_b,
                model_label="Structural C0-C5" if selected_asset is None else str(selected_asset.get("label")),
                trace_rows=trace_rows,
                figures=figures,
                manifest_extra={"result": result_payload, "source_report": str(selected_report) if selected_report else None},
            )
        st.session_state.vmamba_interp_result = {
            "package_dir": str(package_dir),
            "trace_rows": trace_rows,
            "result_payload": result_payload,
            "figure_paths": {name: str(package_dir / "figures" / f"{name}.png") for name in figures},
        }
        st.success(f"Interpretability package saved: {package_dir.name}")

    if st.session_state.get("vmamba_interp_result"):
        payload = dict(st.session_state.vmamba_interp_result)
        st.markdown("**Interpretability summary**")
        summary_cols = st.columns(4, gap="small")
        result_payload = dict(payload.get("result_payload") or {})
        summary_cols[0].metric("Score", f"{float(result_payload.get('score') or 0.0):.4f}")
        summary_cols[1].metric("Threshold", f"{float(result_payload.get('threshold') or 0.0):.4f}")
        summary_cols[2].metric("Decision", str(result_payload.get("decision") or "-"))
        summary_cols[3].metric("Mode", str(result_payload.get("mode") or "-"))
        if result_payload.get("channel_saliency"):
            st.markdown("**Channel saliency**")
            st.dataframe(pd.DataFrame(result_payload["channel_saliency"]), width="stretch", hide_index=True)
        elif result_payload.get("features"):
            st.markdown("**Structural features**")
            st.dataframe(
                pd.DataFrame([{"feature": key, "value": value} for key, value in sorted(dict(result_payload["features"]).items())]),
                width="stretch",
                hide_index=True,
            )
        st.markdown("**Trace**")
        st.dataframe(pd.DataFrame(payload.get("trace_rows", [])), width="stretch", hide_index=True)
        figure_paths = dict(payload.get("figure_paths") or {})
        if figure_paths:
            st.markdown("**Generated figures**")
            figure_tabs = st.tabs([name.replace("_", " ").title() for name in figure_paths])
            for tab, (name, path) in zip(figure_tabs, figure_paths.items()):
                with tab:
                    st.image(path, width="stretch")
        st.caption(f"Package path: `{payload.get('package_dir')}`")


def _scenario_paths_for_study(benchmark_name: str, scenario_name: str) -> tuple[Path, Path, Path]:
    arch = _get_architecture(benchmark_name)
    root = Path(arch["root"]) if arch else _benchmark_root(benchmark_name)
    return (
        root,
        root / "gml" / f"{scenario_name}.gml",
        root / "real_pairs" / f"{scenario_name}.json",
    )


def _render_study_lab() -> None:
    st.caption("Study Workspace")
    st.subheader("Study Lab")
    st.markdown(
        """
        <div class="iso-loading-card">
          <strong>Goal</strong>
          <p>Study deep learning model families, inspect lineage tensors, compare benchmark-compatible outputs, and reproduce article evidence with an auditable trace.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    left_col, right_col = st.columns([0.82, 2.18], gap="large")
    with left_col:
        st.markdown("<div class='iso-scroll-pane'>", unsafe_allow_html=True)
        algorithm = st.selectbox(
            "Study focus",
            options=["Deep Learning Workbench", "VMamba / SS2D", "VMamba-Mesh adaptation"],
            key="study_algorithm_select",
        )
        model_family = st.selectbox(
            "Model family",
            options=_deep_learning_model_families(),
            key="study_model_family_select",
        )
        if _model_family_status(model_family) == "not_available":
            st.caption("This family is reserved for future adapters that register `predict_pairs(graph)`.")
        st.caption("Use this module to study model families, inspect VMamba concepts, train adapters, and register benchmarkable `.pkl` artifacts.")
        st.markdown("**References**")
        st.markdown(
            """
            - VMamba repository: `MzeroMiko/VMamba`
            - VMamba paper: `arXiv:2401.10166`
            - Mamba paper: `arXiv:2312.00752`
            """
        )
        with st.expander("Why this is a simulation first", expanded=False):
            st.markdown(
                """
                The original VMamba stack depends on PyTorch, CUDA/selective-scan kernels, and model configs.
                Loading that directly inside Streamlit would make the app heavy and brittle. This Study Lab starts with a faithful educational simulation:
                cross scan, selective memory, sparse lineage matrices, and the exact VMamba-Mesh changes we plan to implement.
                """
            )
        st.markdown("**Study path**")
        st.markdown(
            """
            1. Compare model families in the Deep Learning Workbench.
            2. Read the original VMamba concepts.
            3. Run the SS2D-style lineage demo.
            4. Toggle adapter changes.
            5. Train a model adapter on an Isomera benchmark and save a `.pkl`.
            6. Open Model Interpretability after a run to inspect C0-C5, saliency and trace artifacts.
            7. Reproduce article evidence through Benchmark & Examples.
            """
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown("<div class='iso-scroll-pane'>", unsafe_allow_html=True)
        tabs = st.tabs([
            "Deep Learning Workbench",
            "Original VMamba",
            "Run SS2D Demo",
            "VMamba-Mesh Changes",
            "Official Runtime",
            "Train Model Adapter",
            "Model Reports",
            "Model Interpretability",
            "Knowledge Base",
        ])

        with tabs[0]:
            _render_deep_learning_workbench()

        with tabs[1]:
            st.subheader("Original VMamba Concepts")
            st.caption("Educational pseudocode mapped to the public VMamba architecture. This avoids copying large external source files into Isomera.")
            code_blocks = _study_vmamba_code_blocks()
            selected_block = st.selectbox(
                "Code part",
                options=list(code_blocks.keys()),
                key="study_vmamba_code_block",
            )
            block = code_blocks[selected_block]
            block_cols = st.columns([1.0, 1.35], gap="large")
            with block_cols[0]:
                st.markdown("**Where in VMamba**")
                st.write(block["where"])
                st.markdown("**What it does**")
                st.write(block["why"])
                st.markdown("**How VMamba-Mesh changes it**")
                st.write(block["mesh"])
            with block_cols[1]:
                st.code(block["snippet"], language="python")
            st.markdown("**VMamba architecture summary**")
            st.table(
                pd.DataFrame(
                    [
                        {"part": "Patch embedding", "role": "Image/tensor to hidden feature map", "we change": "input tensor contract"},
                        {"part": "VSS block", "role": "Residual block around SS2D and MLP", "we change": "mostly keep"},
                        {"part": "SS2D", "role": "Cross scan + selective scan + merge", "we change": "add HierInit and SparseGate"},
                        {"part": "Classification head", "role": "Predict output from embeddings", "we change": "pair classifier head"},
                    ]
                )
            )

        with tabs[2]:
            st.subheader("Run a SS2D-Style Demo on Lineage")
            controls_col, visual_col = st.columns([0.82, 1.72], gap="large")
            with controls_col:
                domains = st.slider("Domains", min_value=1, max_value=4, value=2, key="study_domains")
                sor_per_domain = st.slider("SOR nodes per domain", min_value=1, max_value=5, value=3, key="study_sor_per_domain")
                resolution = st.select_slider("Image resolution", options=[8, 12, 16, 24, 32], value=16, key="study_resolution")
                cross_domain = st.checkbox("Add cross-domain lineage edge", value=True, key="study_cross_domain")
                canon_sort = st.checkbox("CanonSort node order", value=True, key="study_canon_sort")
                diag_fp = st.checkbox("DiagFP on diagonal", value=True, key="study_diag_fp")
                route = st.selectbox(
                    "Scan route",
                    options=[
                        "cross_scan_4",
                        "rows_forward",
                        "rows_backward",
                        "cols_forward",
                        "cols_backward",
                    ],
                    format_func=lambda value: {
                        "cross_scan_4": "Cross scan, 4 routes",
                        "rows_forward": "Rows forward",
                        "rows_backward": "Rows backward",
                        "cols_forward": "Columns forward",
                        "cols_backward": "Columns backward",
                    }[value],
                    key="study_route",
                )
                decay = st.slider("Memory decay", 0.10, 0.98, 0.78, 0.01, key="study_decay")
                input_gain = st.slider("Input gain", 0.10, 2.00, 0.95, 0.05, key="study_input_gain")
                sparse_gate = st.slider("SparseGate strength", 0.00, 1.00, 0.45, 0.05, key="study_sparse_gate")
            graph = _study_lineage_graph(domains, sor_per_domain, cross_domain=cross_domain)
            matrix, node_labels, metadata = _study_lineage_matrix(
                graph,
                resolution=resolution,
                canon_sort=canon_sort,
                diag_fp=diag_fp,
            )
            context = _study_selective_scan(
                matrix,
                route=route,
                decay=decay,
                input_gain=input_gain,
                sparse_gate=sparse_gate,
            )
            metrics = _study_matrix_metrics(matrix, context)
            with visual_col:
                st.markdown("**Lineage graph used in the demo**")
                graph_fig = plot_lineage_graph(graph, seed=42)
                if graph_fig.axes:
                    graph_fig.axes[0].set_title("")
                graph_fig.patch.set_facecolor("white")
                st.pyplot(graph_fig, clear_figure=True)
                metric_cols = st.columns(5, gap="small")
                metric_cols[0].metric("Nodes", metadata["nodes_total"])
                metric_cols[1].metric("Edges", metadata["edges_total"])
                metric_cols[2].metric("Visible", metadata["nodes_visible"])
                metric_cols[3].metric("Dropped nodes", metadata["dropped_nodes"])
                metric_cols[4].metric("Dropped edges", metadata["dropped_edges"])
                heat_tabs = st.tabs(["Lineage image", "SS2D context"])
                with heat_tabs[0]:
                    st.plotly_chart(
                        _study_heatmap_figure(matrix, "Lineage tensor slice", node_labels, colorscale="Greens"),
                        width="stretch",
                    )
                with heat_tabs[1]:
                    st.plotly_chart(
                        _study_heatmap_figure(context, "Selective-scan context intensity", node_labels, colorscale="Blues"),
                        width="stretch",
                    )
                st.markdown("**Scan metrics**")
                st.table(pd.DataFrame([metrics]).astype(str))

        with tabs[3]:
            st.subheader("From VMamba to VMamba-Mesh")
            st.caption("Toggle changes and inspect what each change means before implementing the real model.")
            changes = _study_mesh_changes()
            selected_change = st.selectbox(
                "Change to inspect",
                options=[item["change"] for item in changes],
                key="study_mesh_change_select",
            )
            change = next(item for item in changes if item["change"] == selected_change)
            st.container(border=True).markdown(
                f"""
                **Where:** {change['where']}

                **Why:** {change['why']}

                **Expected impact:** {change['impact']}

                **How to run here:** {change['run']}
                """
            )
            mesh_cols = st.columns(4, gap="small")
            use_canon = mesh_cols[0].checkbox("CanonSort", value=True, key="study_mesh_use_canon")
            use_diag = mesh_cols[1].checkbox("DiagFP", value=True, key="study_mesh_use_diag")
            use_hier = mesh_cols[2].checkbox("HierInit", value=True, key="study_mesh_use_hier")
            use_sparse = mesh_cols[3].checkbox("SparseGate", value=True, key="study_mesh_use_sparse")
            compare_graph = _study_lineage_graph(2, 3, cross_domain=True)
            original_matrix, original_nodes, _ = _study_lineage_matrix(
                compare_graph,
                resolution=16,
                canon_sort=False,
                diag_fp=False,
            )
            mesh_matrix, mesh_nodes, _ = _study_lineage_matrix(
                compare_graph,
                resolution=16,
                canon_sort=use_canon,
                diag_fp=use_diag,
            )
            original_context = _study_selective_scan(
                original_matrix,
                route="cross_scan_4",
                decay=0.78,
                input_gain=0.95,
                sparse_gate=0.0,
            )
            mesh_context = _study_selective_scan(
                mesh_matrix,
                route="cross_scan_4",
                decay=0.83 if use_hier else 0.78,
                input_gain=0.95,
                sparse_gate=0.55 if use_sparse else 0.0,
            )
            original_metrics = {"variant": "VMamba-like", **_study_matrix_metrics(original_matrix, original_context)}
            mesh_metrics = {"variant": "VMamba-Mesh-like", **_study_matrix_metrics(mesh_matrix, mesh_context)}
            compare_df = pd.DataFrame([original_metrics, mesh_metrics])
            st.markdown("**Conceptual effect of the selected changes**")
            st.table(compare_df.astype(str))
            chart_df = compare_df.melt(
                id_vars=["variant"],
                value_vars=["active_context_mean", "empty_context_mean", "active_empty_contrast"],
                var_name="metric",
                value_name="value",
            )
            fig = px.bar(
                chart_df,
                x="metric",
                y="value",
                color="variant",
                barmode="group",
                color_discrete_sequence=["#8D8D82", "#5C7C6F"],
            )
            fig.update_layout(
                height=360,
                paper_bgcolor="#F7F6F2",
                plot_bgcolor="#F7F6F2",
                font={"color": "#2F312E"},
                margin={"l": 20, "r": 20, "t": 30, "b": 40},
            )
            st.plotly_chart(fig, width="stretch")
            st.markdown("**Target implementation sketch**")
            st.code(
                """
pair = extract_lineage_pair(graph, node_a, node_b)
tensor = mesh_encoder(
    pair,
    order="CanonSort",
    channels=["graph_a", "graph_b", "abs_diff", "layer_masks", "diag_fp"],
    resolution="adaptive",
)
embeddings = vmamba_mesh_backbone(
    tensor,
    ss2d="MeshSS2D",
    hier_init=True,
    sparse_gate=True,
)
score = pair_head(embeddings)
                """.strip(),
                language="python",
            )

        with tabs[4]:
            st.subheader("Official VMamba Runtime")
            st.caption("Optional: clone/check the official VMamba repository for source-level study. The benchmarkable Isomera adapter below does not modify the official code.")
            st.markdown(_study_vmamba_mesh_flow_html(), unsafe_allow_html=True)
            runtime_root = _study_vmamba_runtime_root()
            runtime_status = vmamba_runtime_status(runtime_root)
            st.markdown("**Runtime status**")
            st.dataframe(pd.DataFrame([runtime_status]).astype(str), width="stretch", hide_index=True)
            st.markdown("**Manual install command**")
            st.code(_study_install_commands(runtime_root), language="bash")
            install_cols = st.columns([0.45, 0.55], gap="large")
            with install_cols[0]:
                if st.button("Install/update official VMamba runtime", key="study_install_vmamba_runtime", use_container_width=True):
                    with st.spinner("Installing/checking VMamba official runtime. This may take several minutes if dependencies are missing."):
                        ok, install_log = install_or_update_vmamba_runtime(runtime_root, sys.executable)
                    st.session_state.study_vmamba_install_log = install_log
                    if ok:
                        st.success("Official VMamba runtime is available for study.")
                    else:
                        st.error("VMamba runtime install/update failed. See log below.")
            with install_cols[1]:
                st.info(
                    "For the article path, use the official runtime to understand VMamba internals. "
                    "Use the Train Adapter tab to create a comparable `.pkl` over Isomera scenarios."
                )
            if st.session_state.get("study_vmamba_install_log"):
                st.text_area(
                    "Install/check log",
                    value=str(st.session_state.study_vmamba_install_log),
                    height=220,
                    key="study_vmamba_install_log_view",
                )
            st.markdown("**References used by the Study Lab**")
            st.markdown(
                f"- VMamba repository: {VMAMBA_REPOSITORY_URL}\n"
                f"- VMamba paper: {VMAMBA_PAPER_URL}\n"
                f"- Mamba paper: {MAMBA_PAPER_URL}"
            )

        with tabs[5]:
            st.subheader("Train Model Adapter")
            st.caption(
                "This creates a benchmark-compatible `.pkl` with `predict_pairs(graph)`, registers it in the selected benchmark, and optionally generates a research report package. Deterministic adapters and trainable VMamba tensor models share the same benchmark contract."
            )
            study_architectures = _list_architectures()
            study_arch_names = [str(arch["name"]) for arch in study_architectures]
            selected_study_benchmark = st.selectbox(
                "Benchmark source",
                options=study_arch_names,
                key="study_vmamba_benchmark",
            )
            benchmark_root = Path(_get_architecture(selected_study_benchmark)["root"]) if _get_architecture(selected_study_benchmark) else _benchmark_root(selected_study_benchmark)
            gml_root = benchmark_root / "gml"
            scenario_options = sorted(path.stem for path in gml_root.glob("*.gml")) if gml_root.exists() else []
            if not scenario_options:
                st.warning("No GML scenarios found for this benchmark.")
            else:
                selected_study_scenario = st.selectbox(
                    "Scenario",
                    options=scenario_options,
                    key="study_vmamba_scenario",
                )
                _, graph_path, labels_path = _scenario_paths_for_study(selected_study_benchmark, selected_study_scenario)
                positive_pairs = load_positive_pairs(labels_path)
                model_training_family = st.selectbox(
                    "Model implementation",
                    options=[
                        "VMamba-Mesh adapter (deterministic)",
                        "VMamba-T (trainable neural)",
                        "VMamba-Mesh-T (trainable neural)",
                    ],
                    key="study_vmamba_training_family",
                )
                is_trainable_vmamba = "trainable neural" in model_training_family
                trainable_variant = "vmamba_mesh_t" if model_training_family.startswith("VMamba-Mesh-T") else "vmamba_t"
                active_model_version = VMAMBA_TRAINABLE_MODEL_VERSION if is_trainable_vmamba else VMAMBA_MESH_MODEL_VERSION
                source_cols = st.columns(4, gap="small")
                source_cols[0].metric("Graph exists", "yes" if graph_path.exists() else "no")
                source_cols[1].metric("Positive pairs", len(positive_pairs))
                source_cols[2].metric("Labels file", "yes" if labels_path.exists() else "no")
                source_cols[3].metric("Model version", active_model_version)
                with st.expander("Source paths and label preview", expanded=False):
                    st.code(f"graph={graph_path}\nlabels={labels_path}", language="text")
                    st.dataframe(
                        pd.DataFrame(positive_pairs[:25], columns=["node_a", "node_b"]) if positive_pairs else pd.DataFrame(columns=["node_a", "node_b"]),
                        width="stretch",
                        hide_index=True,
                    )
                config_cols = st.columns(3, gap="small")
                with config_cols[0]:
                    scope_layers = st.multiselect(
                        "Scope layers",
                        options=["SOR", "SOT", "SPEC"],
                        default=["SOT", "SPEC"],
                        key="study_vmamba_scope_layers",
                    )
                    negative_ratio = st.number_input(
                        "Negative ratio",
                        min_value=1,
                        max_value=50,
                        value=4,
                        step=1,
                        key="study_vmamba_negative_ratio",
                    )
                with config_cols[1]:
                    seed = st.number_input("Seed", min_value=1, max_value=999999, value=42, step=1, key="study_vmamba_seed")
                    resolution = st.select_slider(
                        "Tensor resolution",
                        options=[16, 24, 32, 48, 64],
                        value=32,
                        key="study_vmamba_resolution",
                    )
                with config_cols[2]:
                    use_canon_sort = st.checkbox("CanonSort", value=True, key="study_train_canon_sort")
                    use_diag_fp = st.checkbox("DiagFP", value=True, key="study_train_diag_fp")
                    use_hier_init = st.checkbox("HierInit", value=True, key="study_train_hier_init")
                    use_sparse_gate = st.checkbox("SparseGate", value=True, key="study_train_sparse_gate")
                if is_trainable_vmamba:
                    st.markdown("**Neural training hyperparameters**")
                    preset_names = sorted(VMAMBA_TRAINABLE_PRESETS)
                    neural_preset = st.selectbox(
                        "VMamba-like preset",
                        options=preset_names,
                        index=preset_names.index("small") if "small" in preset_names else 0,
                        key="study_vmamba_t_preset",
                    )
                    preset_cfg = vmamba_trainable_preset_config(neural_preset)
                    st.caption(str(preset_cfg.get("description", "")))
                    neural_cols = st.columns(4, gap="small")
                    with neural_cols[0]:
                        neural_epochs = st.number_input("Epochs", min_value=1, max_value=2000, value=50 if neural_preset == "base" else 20, step=1, key="study_vmamba_t_epochs")
                        neural_patch_size = st.selectbox("Patch size", options=[1, 2, 4], index=[1, 2, 4].index(int(preset_cfg.get("patch_size", 2))), key="study_vmamba_t_patch")
                    with neural_cols[1]:
                        neural_lr = st.selectbox("Learning rate", options=[1e-3, 5e-4, 1e-4], index=0, format_func=lambda v: f"{v:g}", key="study_vmamba_t_lr")
                        neural_dropout = st.slider("Dropout", min_value=0.0, max_value=0.6, value=0.10, step=0.05, key="study_vmamba_t_dropout")
                    with neural_cols[2]:
                        neural_optimizer = st.selectbox("Optimizer", options=["adamw", "adam"], index=0, key="study_vmamba_t_optimizer")
                        neural_loss = st.selectbox("Loss", options=["weighted_bce", "focal_loss", "bce"], index=0, key="study_vmamba_t_loss")
                    with neural_cols[3]:
                        neural_drop_path = st.slider(
                            "Drop path",
                            min_value=0.0,
                            max_value=0.6,
                            value=float(preset_cfg.get("drop_path_rate", 0.10)),
                            step=0.05,
                            key="study_vmamba_t_drop_path",
                        )
                        neural_weight_decay = st.selectbox("Weight decay", options=[0.0, 0.01, 0.05, 0.10], index=2, key="study_vmamba_t_weight_decay")
                    neural_hard_negative_mining = st.checkbox(
                        "Hard-negative mining",
                        value=False,
                        key="study_vmamba_t_hard_negative_mining",
                        help="Select difficult non-duplicate pairs for training. Use the LLM manifest option to prioritize Codex-reviewed pairs.",
                    )
                    default_llm_hard_negative_manifest = PROJECT_ROOT / "data" / "vmamba_manifests" / "llm_hard_negatives_article_iv_20260604.json"
                    if neural_hard_negative_mining:
                        hardneg_cols = st.columns([0.38, 0.62], gap="small")
                        with hardneg_cols[0]:
                            neural_hard_negative_strategy = st.selectbox(
                                "Hard-negative source",
                                options=[
                                    "structural_similarity",
                                    "structural_plus_llm_manifest",
                                ],
                                index=1,
                                format_func=lambda value: "Structural miner" if value == "structural_similarity" else "Structural + LLM manifest",
                                key="study_vmamba_t_hard_negative_strategy",
                                help="The LLM manifest was curated by Codex/GPT-5 and is stored as an auditable JSON file; no hidden LLM call happens during training.",
                            )
                        with hardneg_cols[1]:
                            neural_hard_negative_manifest_path = st.text_input(
                                "LLM hard-negative manifest",
                                value=str(default_llm_hard_negative_manifest),
                                key="study_vmamba_t_hard_negative_manifest_path",
                                disabled=neural_hard_negative_strategy == "structural_similarity",
                            )
                            st.caption("Suggested by Codex/GPT-5 for Article IV. Edit this JSON path to use a different reviewed hard-negative list.")
                    else:
                        neural_hard_negative_strategy = "structural_similarity"
                        neural_hard_negative_manifest_path = ""
                    replay_cols = st.columns(4, gap="small")
                    with replay_cols[0]:
                        neural_false_positive_replay_rounds = st.number_input(
                            "FP replay rounds",
                            min_value=0,
                            max_value=5,
                            value=0,
                            step=1,
                            key="study_vmamba_t_fp_replay_rounds",
                            help="After initial training, reinforce high-score negative pairs that the model is likely to confuse as duplicates.",
                        )
                    with replay_cols[1]:
                        neural_false_positive_replay_top_k = st.number_input(
                            "FP replay top-k",
                            min_value=0,
                            max_value=5000,
                            value=0,
                            step=10,
                            key="study_vmamba_t_fp_replay_top_k",
                            help="0 means automatic: roughly two replay negatives per positive pair.",
                        )
                    with replay_cols[2]:
                        neural_false_positive_replay_weight = st.number_input(
                            "FP replay weight",
                            min_value=1,
                            max_value=20,
                            value=2,
                            step=1,
                            key="study_vmamba_t_fp_replay_weight",
                        )
                    with replay_cols[3]:
                        neural_false_positive_replay_epochs = st.number_input(
                            "FP replay epochs",
                            min_value=1,
                            max_value=50,
                            value=2,
                            step=1,
                            key="study_vmamba_t_fp_replay_epochs",
                        )
                    threshold_cols = st.columns([0.50, 0.50], gap="small")
                    with threshold_cols[0]:
                        neural_threshold_policy = st.selectbox(
                            "Threshold policy",
                            options=["jaccard", "precision_guard", "precision", "f1"],
                            index=0,
                            key="study_vmamba_t_threshold_policy",
                            help="precision_guard selects the best Jaccard threshold among thresholds that satisfy the precision floor.",
                        )
                    with threshold_cols[1]:
                        neural_threshold_precision_floor = st.slider(
                            "Precision floor",
                            min_value=0.0,
                            max_value=1.0,
                            value=0.0,
                            step=0.05,
                            disabled=neural_threshold_policy != "precision_guard",
                            key="study_vmamba_t_threshold_precision_floor",
                        )
                    arch_cols = st.columns(4, gap="small")
                    with arch_cols[0]:
                        neural_depths_text = st.text_input(
                            "Depths",
                            value=",".join(str(item) for item in preset_cfg.get("depths", (2, 2, 4, 2))),
                            key="study_vmamba_t_depths",
                        )
                    with arch_cols[1]:
                        neural_dims_text = st.text_input(
                            "Dims",
                            value=",".join(str(item) for item in preset_cfg.get("dims", (64, 128, 256, 512))),
                            key="study_vmamba_t_dims",
                        )
                    with arch_cols[2]:
                        neural_hidden = st.selectbox(
                            "Pair head hidden",
                            options=[64, 128, 256, 384, 512, 768],
                            index=[64, 128, 256, 384, 512, 768].index(int(preset_cfg.get("hidden_dim", 256))) if int(preset_cfg.get("hidden_dim", 256)) in [64, 128, 256, 384, 512, 768] else 2,
                            key="study_vmamba_t_hidden",
                        )
                    with arch_cols[3]:
                        neural_embedding = st.selectbox(
                            "Embedding dim",
                            options=[64, 128, 256, 384, 512, 768],
                            index=[64, 128, 256, 384, 512, 768].index(int(preset_cfg.get("embedding_dim", 256))) if int(preset_cfg.get("embedding_dim", 256)) in [64, 128, 256, 384, 512, 768] else 2,
                            key="study_vmamba_t_embedding",
                        )
                    neural_device = st.selectbox(
                        "Device",
                        options=["auto", "mps", "cpu"],
                        index=0,
                        help="auto uses MPS when PyTorch can allocate a Metal tensor; otherwise it falls back to CPU and records the reason in metadata.",
                        key="study_vmamba_t_device",
                    )
                    neural_inference_batch_size = int(
                        st.selectbox(
                            "Inference batch",
                            options=[256, 1024, 4096, 8192, 16384],
                            index=2,
                            help="Number of candidate pairs evaluated together by the saved predict_pairs(graph) artifact.",
                            key="study_vmamba_t_inference_batch_size",
                        )
                    )
                    neural_encoder_batch_size = int(
                        st.selectbox(
                            "Encoder batch",
                            options=[8, 16, 32, 64, 128],
                            index=3,
                            help="Number of graph-context tensors encoded together by the VMamba-style backbone during predict_pairs(graph).",
                            key="study_vmamba_t_encoder_batch_size",
                        )
                    )
                    try:
                        device_probe = resolve_torch_device(str(neural_device))
                    except Exception as exc:
                        device_probe = {
                            "resolved_device": "cpu",
                            "fallback_reason": f"{type(exc).__name__}: {exc}",
                        }
                    device_label = str(device_probe.get("resolved_device", "cpu")).upper()
                    if device_label == "MPS":
                        st.success("This training run is configured to use MPS/Metal when launched from this Streamlit session.")
                    else:
                        st.warning(f"This training run will use CPU. Fallback: {device_probe.get('fallback_reason') or 'MPS not requested/available'}.")
                    channel_cols = st.columns([0.55, 0.45], gap="small")
                    with channel_cols[0]:
                        if trainable_variant == "vmamba_mesh_t":
                            neural_channels = st.multiselect(
                                "Channels",
                                options=["C0", "C1", "C2", "C3", "C4", "C5"],
                                default=["C0", "C1", "C2", "C3", "C4", "C5"],
                                key="study_vmamba_t_channels",
                            )
                        else:
                            neural_channels = ["C0", "C1"]
                            st.caption("VMamba-T baseline uses C0/C1 structural channels only.")
                    with channel_cols[1]:
                        st.markdown("**Article-grade recommendation**")
                        st.markdown(
                            """
                            - SPEC v2: `scope=SPEC`, preset `article_cpu` for the validated local campaign.
                            - Full Lineage: `scope=SOR,SOT,SPEC`, preset `article_cpu` locally; reserve `base` for a GPU/MPS campaign.
                            - Compare `weighted_bce` and `focal_loss` in the next factorial campaign.
                            """
                        )
                    st.info(
                        "VMamba-T and VMamba-Mesh-T now use a VMamba-like native PyTorch architecture: patch embedding, staged VSS-style blocks, bidirectional row/column SS2D-style scans, drop path, pair head, saved threshold and hyperparameters. The official CUDA/Triton VMamba remains the external reference implementation."
                    )
                else:
                    neural_epochs = 0
                    neural_hidden = 64
                    neural_embedding = 64
                    neural_lr = 1e-3
                    neural_dropout = 0.10
                    neural_optimizer = "adamw"
                    neural_loss = "weighted_bce"
                    neural_channels = ["C0", "C1", "C2", "C3", "C4", "C5"]
                    neural_preset = "adapter"
                    neural_patch_size = 2
                    neural_depths_text = "2,2,4,2"
                    neural_dims_text = "64,128,256,512"
                    neural_drop_path = 0.10
                    neural_weight_decay = 0.05
                    neural_device = "auto"
                    neural_inference_batch_size = 4096
                    neural_encoder_batch_size = 64
                    neural_hard_negative_mining = False
                    neural_hard_negative_strategy = "structural_similarity"
                    neural_hard_negative_manifest_path = ""
                    neural_false_positive_replay_rounds = 0
                    neural_false_positive_replay_top_k = 0
                    neural_false_positive_replay_weight = 2
                    neural_false_positive_replay_epochs = 2
                    neural_threshold_policy = "jaccard"
                    neural_threshold_precision_floor = 0.0
                family_slug = "VMambaMeshT" if trainable_variant == "vmamba_mesh_t" and is_trainable_vmamba else ("VMambaT" if is_trainable_vmamba else "VMambaMesh")
                default_model_name = f"{family_slug}_{neural_preset}_{_sanitize_benchmark_name(selected_study_scenario)}"
                model_name = st.text_input(
                    "Model artifact name",
                    value=default_model_name,
                    key="study_vmamba_model_name",
                )
                register_model = st.checkbox(
                    "Register model in Benchmark & Examples",
                    value=True,
                    key="study_vmamba_register_model",
                )
                compile_report_pdf = st.checkbox(
                    "Compile study report PDF if Tectonic is available",
                    value=True,
                    key="study_vmamba_compile_pdf",
                )
                run_cols = st.columns([0.35, 0.65], gap="large")
                with run_cols[0]:
                    train_clicked = st.button(
                        "Train and save model pickle" if is_trainable_vmamba else "Train and save VMamba-Mesh pickle",
                        key="study_vmamba_train",
                        type="primary",
                        use_container_width=True,
                        disabled=not graph_path.exists() or not labels_path.exists() or not positive_pairs,
                    )
                with run_cols[1]:
                    st.info(
                        "The saved pickle is comparable with VF2, Node Match and GNN clusters because it returns predicted duplicate pairs over the same graph."
                    )
                if train_clicked:
                    graph = nx.read_gml(graph_path)
                    model_dir_name = trainable_variant if is_trainable_vmamba else "vmamba_mesh"
                    model_dir = benchmark_root / "models" / model_dir_name
                    model_dir.mkdir(parents=True, exist_ok=True)
                    safe_model_name = _sanitize_benchmark_name(model_name)
                    model_path = model_dir / f"{safe_model_name}.pkl"
                    metadata_path = model_dir / f"{safe_model_name}.json"
                    spinner_text = "Training neural VMamba tensor model, selecting threshold, and saving pickle." if is_trainable_vmamba else "Training VMamba-Mesh adapter, calibrating threshold, saving pickle, and creating report package."
                    with st.spinner(spinner_text):
                        if is_trainable_vmamba:
                            def parse_int_tuple(raw: str, fallback: tuple[int, ...]) -> tuple[int, ...]:
                                try:
                                    parsed = tuple(int(part.strip()) for part in str(raw).split(",") if part.strip())
                                    return parsed or fallback
                                except ValueError:
                                    return fallback

                            neural_depths = parse_int_tuple(neural_depths_text, tuple(int(item) for item in preset_cfg.get("depths", (2, 2, 4, 2))))
                            neural_dims = parse_int_tuple(neural_dims_text, tuple(int(item) for item in preset_cfg.get("dims", (64, 128, 256, 512))))
                            cfg_t = VMambaTrainableConfig(
                                variant=trainable_variant,
                                scope_layers=tuple(scope_layers or ["SOT", "SPEC"]),
                                resolution=int(resolution),
                                channels=tuple(neural_channels or ["C0", "C1"]),
                                architecture="vss_torch",
                                preset=str(neural_preset),
                                patch_size=int(neural_patch_size),
                                depths=neural_depths,
                                dims=neural_dims,
                                hidden_dim=int(neural_hidden),
                                embedding_dim=int(neural_embedding),
                                mlp_ratio=4.0,
                                dropout=float(neural_dropout),
                                drop_path_rate=float(neural_drop_path),
                                negative_ratio=int(negative_ratio),
                                hard_negative_mining=bool(neural_hard_negative_mining),
                                hard_negative_strategy=str(neural_hard_negative_strategy),
                                hard_negative_agent="codex_gpt5_llm_hard_negative_reviewer" if "llm_manifest" in str(neural_hard_negative_strategy) else "isomera_structural_hard_negative_miner",
                                hard_negative_manifest_path=str(neural_hard_negative_manifest_path),
                                hard_negative_manifest_id="llm_hard_negatives_article_iv_20260604" if "llm_manifest" in str(neural_hard_negative_strategy) else "",
                                false_positive_replay_rounds=int(neural_false_positive_replay_rounds),
                                false_positive_replay_top_k=int(neural_false_positive_replay_top_k),
                                false_positive_replay_weight=int(neural_false_positive_replay_weight),
                                false_positive_replay_epochs=int(neural_false_positive_replay_epochs),
                                inference_batch_size=int(neural_inference_batch_size),
                                encoder_batch_size=int(neural_encoder_batch_size),
                                seed=int(seed),
                                epochs=int(neural_epochs),
                                learning_rate=float(neural_lr),
                                loss_name=str(neural_loss),
                                threshold_policy=str(neural_threshold_policy),
                                threshold_precision_floor=float(neural_threshold_precision_floor),
                                optimizer_name=str(neural_optimizer),
                                weight_decay=float(neural_weight_decay),
                                forward_type="v05",
                                device=str(neural_device),
                            )
                            metadata = save_vmamba_trainable_artifact(
                                graph=graph,
                                positive_pairs=positive_pairs,
                                model_path=model_path,
                                metadata_path=metadata_path,
                                config=cfg_t,
                                benchmark_name=selected_study_benchmark,
                                scenario_name=selected_study_scenario,
                                source_graph_path=graph_path,
                                source_labels_path=labels_path,
                            )
                        else:
                            cfg = VMambaMeshConfig(
                                scope_layers=tuple(scope_layers or ["SOT", "SPEC"]),
                                canon_sort=use_canon_sort,
                                diag_fp=use_diag_fp,
                                hier_init=use_hier_init,
                                sparse_gate=use_sparse_gate,
                                negative_ratio=int(negative_ratio),
                                seed=int(seed),
                                resolution=int(resolution),
                            )
                            metadata = save_vmamba_mesh_artifact(
                                graph=graph,
                                positive_pairs=positive_pairs,
                                model_path=model_path,
                                metadata_path=metadata_path,
                                config=cfg,
                                benchmark_name=selected_study_benchmark,
                                scenario_name=selected_study_scenario,
                                source_graph_path=graph_path,
                                source_labels_path=labels_path,
                            )
                        if register_model:
                            _register_benchmark_model(
                                benchmark_name=selected_study_benchmark,
                                model_name=safe_model_name,
                                pickle_path=model_path,
                                metadata_path=metadata_path,
                                source_scenarios=[selected_study_scenario],
                                model_version=active_model_version,
                            )
                        package = build_vmamba_mesh_study_package(
                            reports_root=_app_path("data/research_reports"),
                            metadata=metadata,
                            compile_pdf=compile_report_pdf,
                        )
                    st.session_state.study_vmamba_last_metadata = metadata
                    st.session_state.study_vmamba_last_package = package
                    st.success("Model pickle saved and registered.")
                    _record_article_report(
                        "vmamba_study_training",
                        {
                            "benchmark_name": selected_study_benchmark,
                            "scenario": selected_study_scenario,
                            "model_name": safe_model_name,
                            "model_version": active_model_version,
                            "model_family": metadata.get("model_family"),
                            "pickle_path": str(model_path),
                            "metadata_path": str(metadata_path),
                            "report_package": package,
                            "training_summary": metadata.get("training_summary"),
                        },
                    )
                if st.session_state.get("study_vmamba_last_metadata"):
                    st.markdown("**Last VMamba-Mesh training result**")
                    metadata = dict(st.session_state.study_vmamba_last_metadata)
                    summary = dict(metadata.get("training_summary") or {})
                    st.dataframe(
                        pd.DataFrame(
                            [
                                {
                                    "pickle_path": metadata.get("pickle_path"),
                                    "pickle_module": metadata.get("pickle_module"),
                                    "threshold": summary.get("selected_threshold"),
                                    "positive_pairs": summary.get("positive_pairs"),
                                    "negative_pairs": summary.get("negative_pairs"),
                                    "jaccard": dict(summary.get("selected_metrics") or {}).get("jaccard"),
                                }
                            ]
                        ).astype(str),
                        width="stretch",
                        hide_index=True,
                    )

        with tabs[6]:
            st.subheader("Model Reports")
            st.caption("Use this tab to confirm what changed, where the report package was saved, and how the trainable VMamba family was evaluated.")
            if st.session_state.get("study_vmamba_last_package"):
                st.markdown("**Last generated study package**")
                st.json(st.session_state.study_vmamba_last_package)
            with st.expander("Run trainable VMamba ablation campaign", expanded=False):
                st.caption("Use quick mode to validate the pipeline. Article-grade mode trains VMamba-T on C0-C1 and VMamba-Mesh-T on the full C0-C5 tensor after CanonSort/DiagFP/route-bias/sparse-mask encoding.")
                ablation_cols = st.columns(4, gap="small")
                with ablation_cols[0]:
                    ablation_benchmark = st.selectbox(
                        "Benchmark",
                        options=["tpc_ds_genai_spec_v2", "tpc_ds_genai_full_lineage"],
                        key="study_ablation_benchmark",
                    )
                    ablation_scope = ["SPEC"] if ablation_benchmark == "tpc_ds_genai_spec_v2" else ["SOR", "SOT", "SPEC"]
                with ablation_cols[1]:
                    ablation_mode = st.selectbox("Mode", options=["quick", "article-grade"], key="study_ablation_mode")
                    ablation_scenarios = ["graph_SOR2_D1_seed42"] if ablation_mode == "quick" else ["--article-scenarios"]
                with ablation_cols[2]:
                    ablation_variants = st.multiselect(
                        "Trainable models",
                        options=["vmamba_t", "vmamba_mesh_t"],
                        default=["vmamba_t", "vmamba_mesh_t"],
                        format_func=lambda item: "VMamba-T" if item == "vmamba_t" else "VMamba-Mesh-T",
                        key="study_ablation_variants",
                    )
                    ablation_presets = st.multiselect(
                        "Presets",
                        options=sorted(VMAMBA_TRAINABLE_PRESETS),
                        default=["tiny"] if ablation_mode == "quick" else ["article_cpu"],
                        key="study_ablation_presets",
                    )
                    ablation_losses = st.multiselect(
                        "Losses",
                        options=["weighted_bce", "focal_loss", "bce"],
                        default=["weighted_bce"],
                        key="study_ablation_losses",
                    )
                with ablation_cols[3]:
                    article_default_epochs = 10 if ablation_benchmark == "tpc_ds_genai_spec_v2" else 3
                    ablation_epochs = st.number_input("Epochs", min_value=1, max_value=2000, value=1 if ablation_mode == "quick" else article_default_epochs, step=1, key="study_ablation_epochs")
                    ablation_batch_size = st.number_input("Batch size", min_value=1, max_value=128, value=8 if ablation_mode == "quick" else 16, step=1, key="study_ablation_batch_size")
                    ablation_resolution = st.multiselect(
                        "Resolution",
                        options=[16, 32, 48, 64],
                        default=[16],
                        key="study_ablation_resolution",
                    )
                st.markdown("**Hyperparameter sweep controls**")
                hp_cols = st.columns(8, gap="small")
                with hp_cols[0]:
                    ablation_learning_rates = st.multiselect(
                        "Learning rates",
                        options=[1e-3, 5e-4, 1e-4],
                        default=[1e-3] if ablation_mode == "quick" else ([1e-3, 5e-4] if ablation_benchmark == "tpc_ds_genai_spec_v2" else [1e-3]),
                        format_func=lambda value: f"{value:g}",
                        key="study_ablation_learning_rates",
                    )
                with hp_cols[1]:
                    ablation_negative_ratio = st.number_input(
                        "Negative ratio",
                        min_value=1,
                        max_value=64,
                        value=4 if ablation_benchmark == "tpc_ds_genai_full_lineage" else 16,
                        step=1,
                        key="study_ablation_negative_ratio",
                    )
                with hp_cols[2]:
                    ablation_dropout = st.slider("Dropout", min_value=0.0, max_value=0.6, value=0.10, step=0.05, key="study_ablation_dropout")
                with hp_cols[3]:
                    ablation_drop_path = st.slider("Drop path", min_value=0.0, max_value=0.5, value=0.15 if ablation_mode == "article-grade" else 0.05, step=0.05, key="study_ablation_drop_path")
                with hp_cols[4]:
                    ablation_weight_decay = st.selectbox("Weight decay", options=[0.0, 0.01, 0.05, 0.10], index=2, key="study_ablation_weight_decay")
                with hp_cols[5]:
                    ablation_device = st.selectbox(
                        "Device",
                        options=["auto", "mps", "cpu"],
                        index=0,
                        help="auto resolves to MPS when PyTorch/Metal is available in the running app session.",
                        key="study_ablation_device",
                    )
                with hp_cols[6]:
                    ablation_inference_batch_size = st.selectbox(
                        "Inference batch",
                        options=[256, 1024, 4096, 8192, 16384],
                        index=2,
                        key="study_ablation_inference_batch_size",
                    )
                with hp_cols[7]:
                    ablation_encoder_batch_size = st.selectbox(
                        "Encoder batch",
                        options=[8, 16, 32, 64, 128],
                        index=3,
                        key="study_ablation_encoder_batch_size",
                    )
                ablation_hard_negative_mining = st.checkbox(
                    "Hard-negative mining",
                    value=False,
                    key="study_ablation_hard_negative_mining",
                    help="Use difficult non-duplicate pairs instead of random negatives in VMamba-T/Mesh-T training.",
                )
                default_ablation_llm_manifest = PROJECT_ROOT / "data" / "vmamba_manifests" / "llm_hard_negatives_article_iv_20260604.json"
                if ablation_hard_negative_mining:
                    hardneg_report_cols = st.columns([0.38, 0.62], gap="small")
                    with hardneg_report_cols[0]:
                        ablation_hard_negative_strategy = st.selectbox(
                            "Hard-negative source",
                            options=["structural_similarity", "structural_plus_llm_manifest"],
                            index=1,
                            format_func=lambda value: "Structural miner" if value == "structural_similarity" else "Structural + LLM manifest",
                            key="study_ablation_hard_negative_strategy",
                            help="The LLM manifest is an auditable Codex/GPT-5 reviewed list. The training command records the file, agent and manifest id.",
                        )
                    with hardneg_report_cols[1]:
                        ablation_hard_negative_manifest_path = st.text_input(
                            "LLM hard-negative manifest",
                            value=str(default_ablation_llm_manifest),
                            key="study_ablation_hard_negative_manifest_path",
                            disabled=ablation_hard_negative_strategy == "structural_similarity",
                        )
                        st.caption("Default suggestion: Codex/GPT-5 manifest. You can replace it with another agent-reviewed JSON before running.")
                else:
                    ablation_hard_negative_strategy = "structural_similarity"
                    ablation_hard_negative_manifest_path = ""
                st.markdown("**Precision improvement controls**")
                improve_cols = st.columns(6, gap="small")
                with improve_cols[0]:
                    ablation_fp_replay_rounds = st.number_input(
                        "FP replay rounds",
                        min_value=0,
                        max_value=5,
                        value=0,
                        step=1,
                        key="study_ablation_fp_replay_rounds",
                    )
                with improve_cols[1]:
                    ablation_fp_replay_top_k = st.number_input(
                        "FP replay top-k",
                        min_value=0,
                        max_value=5000,
                        value=0,
                        step=10,
                        key="study_ablation_fp_replay_top_k",
                        help="0 means automatic: roughly two replay negatives per positive pair.",
                    )
                with improve_cols[2]:
                    ablation_fp_replay_weight = st.number_input(
                        "FP replay weight",
                        min_value=1,
                        max_value=20,
                        value=2,
                        step=1,
                        key="study_ablation_fp_replay_weight",
                    )
                with improve_cols[3]:
                    ablation_fp_replay_epochs = st.number_input(
                        "FP replay epochs",
                        min_value=1,
                        max_value=50,
                        value=2,
                        step=1,
                        key="study_ablation_fp_replay_epochs",
                    )
                with improve_cols[4]:
                    ablation_threshold_policy = st.selectbox(
                        "Threshold policy",
                        options=["jaccard", "precision_guard", "precision", "f1"],
                        index=0,
                        key="study_ablation_threshold_policy",
                    )
                with improve_cols[5]:
                    ablation_threshold_precision_floor = st.slider(
                        "Precision floor",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.0,
                        step=0.05,
                        disabled=ablation_threshold_policy != "precision_guard",
                        key="study_ablation_threshold_precision_floor",
                    )
                try:
                    ablation_device_probe = resolve_torch_device(str(ablation_device))
                except Exception as exc:
                    ablation_device_probe = {
                        "resolved_device": "cpu",
                        "mps_available": False,
                        "fallback_reason": f"{type(exc).__name__}: {exc}",
                    }
                if ablation_mode == "article-grade":
                    st.warning(
                        "Article-grade mode trains every selected configuration across the article scenarios. "
                        "On CPU this can take from tens of minutes to hours; with MPS the report records whether Metal was actually used."
                    )
                elif str(ablation_device_probe.get("resolved_device", "cpu")) == "mps":
                    st.success("This ablation is configured to run trainable tensors on MPS/Metal.")
                elif ablation_device == "mps":
                    st.info(f"MPS was requested, but this session resolved CPU: {ablation_device_probe.get('fallback_reason') or 'MPS not available'}.")
                run_ablation = st.button(
                    "Run VMamba-T / VMamba-Mesh-T ablation",
                    key="study_run_trainable_ablation",
                    type="primary",
                    disabled=not ablation_variants or not ablation_presets or not ablation_losses or not ablation_resolution or not ablation_learning_rates,
                )
                if run_ablation:
                    script_path = PROJECT_ROOT / "scripts" / "run_vmamba_trainable_ablation.py"
                    command = [
                        sys.executable,
                        str(script_path),
                        "--benchmark",
                        ablation_benchmark,
                        "--variant",
                        *[str(item) for item in ablation_variants],
                        "--preset",
                        *[str(item) for item in ablation_presets],
                        "--resolution",
                        *[str(item) for item in ablation_resolution],
                        "--epochs",
                        str(int(ablation_epochs)),
                        "--batch-size",
                        str(int(ablation_batch_size)),
                        "--inference-batch-size",
                        str(int(ablation_inference_batch_size)),
                        "--encoder-batch-size",
                        str(int(ablation_encoder_batch_size)),
                        "--learning-rate",
                        *[f"{float(item):g}" for item in ablation_learning_rates],
                        "--negative-ratio",
                        str(int(ablation_negative_ratio)),
                        "--dropout",
                        f"{float(ablation_dropout):g}",
                        "--drop-path-rate",
                        f"{float(ablation_drop_path):g}",
                        "--weight-decay",
                        f"{float(ablation_weight_decay):g}",
                        "--loss",
                        *[str(item) for item in ablation_losses],
                        "--scope-layers",
                        *ablation_scope,
                        "--device",
                        str(ablation_device),
                        "--false-positive-replay-rounds",
                        str(int(ablation_fp_replay_rounds)),
                        "--false-positive-replay-top-k",
                        str(int(ablation_fp_replay_top_k)),
                        "--false-positive-replay-weight",
                        str(int(ablation_fp_replay_weight)),
                        "--false-positive-replay-epochs",
                        str(int(ablation_fp_replay_epochs)),
                        "--threshold-policy",
                        str(ablation_threshold_policy),
                        "--threshold-precision-floor",
                        f"{float(ablation_threshold_precision_floor):g}",
                    ]
                    experiment_tag = ""
                    if ablation_hard_negative_mining:
                        manifest_tag = "llmhardneg" if "llm_manifest" in str(ablation_hard_negative_strategy) else "hardneg"
                        experiment_tag = f"{manifest_tag}-{ablation_device}"
                        command.extend([
                            "--hard-negative-mining",
                            "--hard-negative-strategy",
                            str(ablation_hard_negative_strategy),
                            "--hard-negative-agent",
                            "codex_gpt5_llm_hard_negative_reviewer" if "llm_manifest" in str(ablation_hard_negative_strategy) else "isomera_structural_hard_negative_miner",
                            "--hard-negative-manifest-path",
                            str(ablation_hard_negative_manifest_path),
                            "--hard-negative-manifest-id",
                            "llm_hard_negatives_article_iv_20260604" if "llm_manifest" in str(ablation_hard_negative_strategy) else "",
                        ])
                    if int(ablation_fp_replay_rounds) > 0:
                        experiment_tag = f"{experiment_tag + '-' if experiment_tag else ''}fpreplay"
                    if str(ablation_threshold_policy) != "jaccard":
                        experiment_tag = f"{experiment_tag + '-' if experiment_tag else ''}{ablation_threshold_policy}"
                    if experiment_tag:
                        command.extend(["--experiment-tag", experiment_tag])
                    if ablation_scenarios == ["--article-scenarios"]:
                        command.append("--article-scenarios")
                    else:
                        command.extend(["--scenario", *ablation_scenarios])
                    env = os.environ.copy()
                    env["PYTHONPATH"] = str(PROJECT_ROOT)
                    env["MPLCONFIGDIR"] = str(_app_path("data/.mplconfig"))
                    Path(env["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)
                    progress_bar = st.progress(0, text="Preparing trainable ablation command...")
                    with st.spinner("Running trainable VMamba ablation. Article-grade mode can take a long time."):
                        progress_bar.progress(15, text=f"Running on requested device={ablation_device}. Waiting for subprocess output...")
                        result = subprocess.run(command, cwd=str(PROJECT_ROOT.parent), env=env, capture_output=True, text=True, timeout=None)
                        progress_bar.progress(90, text="Subprocess finished. Parsing result...")
                    if result.returncode == 0:
                        progress_bar.progress(100, text="Ablation completed.")
                        st.success("Ablation completed. Select the newest report below to inspect metrics and figures.")
                    else:
                        progress_bar.progress(100, text="Ablation failed. Check log below.")
                        st.error("Ablation failed.")
                    st.text_area("Ablation log", value=(result.stdout + "\n" + result.stderr).strip(), height=220)
            trainable_ablation_dirs = sorted(
                [
                    path
                    for path in _app_path("data/research_reports").glob("*vmamba_trainable_ablation*")
                    if path.is_dir()
                ],
                key=lambda path: path.name,
                reverse=True,
            )
            if trainable_ablation_dirs:
                st.markdown("**Trainable VMamba ablation reports**")
                selected_ablation_dir = st.selectbox(
                    "Ablation report",
                    options=trainable_ablation_dirs,
                    format_func=lambda path: path.name,
                    key="study_vmamba_trainable_ablation_report",
                )
                manifest_path = selected_ablation_dir / "manifest.json"
                metrics_path = selected_ablation_dir / "metrics.csv"
                if manifest_path.exists():
                    try:
                        manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                    except Exception:
                        manifest_payload = {}
                    pipeline_payload = manifest_payload.get("pipeline_contract")
                    if pipeline_payload:
                        st.markdown("**Neural processing contract**")
                        st.caption("This is the auditable path before and inside the trainable model.")
                        st.write(" -> ".join(str(item) for item in pipeline_payload))
                    best_payload = manifest_payload.get("best_by_sf_jaccard")
                    if best_payload:
                        st.markdown("**Best configuration by SF-Jaccard**")
                        st.json(best_payload)
                    article_outputs = manifest_payload.get("article_artifacts") or {}
                    if article_outputs:
                        st.markdown("**Article-ready outputs**")
                        article_rows = [{"artifact": key, "path": value} for key, value in article_outputs.items()]
                        st.dataframe(pd.DataFrame(article_rows), width="stretch", hide_index=True)
                if metrics_path.exists():
                    metrics_df = pd.read_csv(metrics_path)
                    st.markdown("**Ablation metrics**")
                    visible_cols = [
                        col
                        for col in [
                            "benchmark",
                            "scenario",
                            "family",
                            "preset",
                            "jaccard",
                            "sf_jaccard",
                            "precision",
                            "recall",
                            "elapsed_seconds",
                            "loss",
                            "depths",
                            "dims",
                            "threshold",
                        ]
                        if col in metrics_df.columns
                    ]
                    st.dataframe(metrics_df[visible_cols].astype(str), width="stretch", hide_index=True)
                combined_summary_path = selected_ablation_dir / "combined_summary_with_trainable.csv"
                ci_path = selected_ablation_dir / "confidence_intervals_with_trainable.csv"
                if combined_summary_path.exists():
                    combined_df = pd.read_csv(combined_summary_path)
                    st.markdown("**Combined article table with VMamba-T / VMamba-Mesh-T**")
                    combined_cols = [col for col in ["algorithm", "jaccard", "sf_jaccard", "ET", "accuracy", "tp", "fp", "fn", "scenarios"] if col in combined_df.columns]
                    st.dataframe(combined_df[combined_cols].astype(str), width="stretch", hide_index=True)
                if ci_path.exists():
                    ci_df = pd.read_csv(ci_path)
                    st.markdown("**95% confidence intervals**")
                    ci_cols = [col for col in ["algorithm", "jaccard_ci_low", "jaccard_ci_high", "sf_jaccard_ci_low", "sf_jaccard_ci_high", "ET_ci_low", "ET_ci_high"] if col in ci_df.columns]
                    st.dataframe(ci_df[ci_cols].astype(str), width="stretch", hide_index=True)
                figures_dir = selected_ablation_dir / "figures"
                figure_paths = sorted(figures_dir.glob("*.png")) if figures_dir.exists() else []
                if figure_paths:
                    st.markdown("**Article-style figures**")
                    figure_tabs = st.tabs([path.stem.replace("vmamba_t_ablation_", "").replace("_", " ").title() for path in figure_paths])
                    for figure_tab, figure_path in zip(figure_tabs, figure_paths):
                        with figure_tab:
                            st.image(str(figure_path), width="stretch")
            recent_study_reports = [
                package
                for package in _list_research_report_packages(limit=40)
                if "vmamba_mesh_study" in str(package.get("name", ""))
            ]
            if recent_study_reports:
                st.markdown("**Recent VMamba-Mesh study reports**")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "name": package.get("name"),
                                "dir": package.get("dir"),
                                "pdf": package.get("pdf"),
                                "zip": package.get("zip"),
                            }
                            for package in recent_study_reports[:8]
                        ]
                    ),
                    width="stretch",
                    hide_index=True,
                )
            roadmap = pd.DataFrame(
                [
                    {"step": 1, "module": "canon_sort.py", "goal": "Stable SOR/SOT/SPEC node ordering", "validation": "same graph -> same matrix order"},
                    {"step": 2, "module": "mesh_image_encoder.py", "goal": "Pair tensor with graph A/B/diff/layer channels", "validation": "visual tensor and adjacency table"},
                    {"step": 3, "module": "schema_fingerprint.py", "goal": "DiagFP identity channel", "validation": "same schema -> stable diagonal"},
                    {"step": 4, "module": "vmamba_mesh_ss2d.py", "goal": "HierInit and SparseGate around SS2D", "validation": "ablation toggles change metrics"},
                    {"step": 5, "module": "vmamba_mesh.py", "goal": "Export a benchmark-compatible pickle", "validation": "same metrics pipeline as VF2/GNN"},
                    {"step": 6, "module": "benchmark_vmamba_mesh.py", "goal": "Compare SF-Jaccard, ET, Jaccard and ablations", "validation": "Research Reports package"},
                ]
            )
            st.markdown("**Implementation checklist**")
            st.table(roadmap.astype(str))
            st.markdown("**Notebook evidence already available**")
            st.table(
                pd.DataFrame(
                    [
                        {"model": "MLP", "jaccard": 0.1373, "accuracy": 0.9845, "recall": 0.4667, "precision": 0.1628, "false_positives": 72},
                        {"model": "CNN", "jaccard": 0.2812, "accuracy": 0.9959, "recall": 0.3000, "precision": 0.8182, "false_positives": 2},
                    ]
                ).astype(str)
            )
            st.info(
                "The deterministic `.pkl` adapter remains useful for fast reproducibility. VMamba-T and VMamba-Mesh-T are the trainable neural rows: they start after the C0-C5 tensorization step, use a native PyTorch VMamba-like backbone, and save thresholds, hyperparameters and pickles in each ablation report."
            )
        with tabs[7]:
            _render_vmamba_interpretability_lab()
        with tabs[8]:
            _render_study_knowledge_base()
        st.markdown("</div>", unsafe_allow_html=True)


def _pair_payload_for_genai(graph: nx.DiGraph, node_a: str, node_b: str) -> dict[str, object]:
    def summarize(node: str) -> dict[str, object]:
        subgraph = _pair_context_subgraph(graph, node)
        return {
            "anchor": node,
            "layer": _node_layer(node),
            "domain": _node_domain(node),
            "nodes": [
                {
                    "node": str(item),
                    "layer": _node_layer(str(item)),
                    "domain": _node_domain(str(item)),
                    "attrs": {key: str(value) for key, value in dict(subgraph.nodes[item]).items()},
                }
                for item in sorted(subgraph.nodes, key=str)
            ],
            "edges": [
                {"source": str(source), "target": str(target)}
                for source, target in sorted(subgraph.edges, key=lambda edge: (str(edge[0]), str(edge[1])))
            ],
            "node_count": subgraph.number_of_nodes(),
            "edge_count": subgraph.number_of_edges(),
            "parent_signature": sorted(str(parent) for parent in graph.predecessors(node)) if node in graph else [],
            "child_signature": sorted(str(child) for child in graph.successors(node)) if node in graph else [],
        }

    return {
        "task": "structural_duplicate_pair_validation",
        "pair": {"node_a": node_a, "node_b": node_b},
        "subgraph_a": summarize(node_a),
        "subgraph_b": summarize(node_b),
        "expected_output": {
            "decision": "duplicate | not_duplicate",
            "target": "1 for duplicate, 0 for not duplicate",
            "confidence": "0.0 to 1.0",
            "rationale": "short auditable reason",
        },
    }


def _normalize_genai_decision(parsed: dict[str, object]) -> str:
    target_text = str(parsed.get("target") or "").lower().strip()
    decision = str(parsed.get("decision") or "").lower().replace("-", "_").strip()
    not_duplicate_labels = {"not_duplicate", "not duplicate", "non_duplicate", "non duplicate"}
    if target_text in {"0", "false"} or decision in not_duplicate_labels or decision.startswith("not_"):
        return "not_duplicate"
    if target_text in {"1", "true"} or decision == "duplicate":
        return "duplicate"
    raw = str(parsed.get("raw_decision") or "").lower()
    if "not_duplicate" in raw or "not duplicate" in raw:
        return "not_duplicate"
    if '"target": 0' in raw or '"target":0' in raw:
        return "not_duplicate"
    if '"decision": "duplicate"' in raw or '"decision":"duplicate"' in raw:
        return "duplicate"
    if '"target": 1' in raw or '"target":1' in raw:
        return "duplicate"
    return ""


def _genai_decision_label(decision: str) -> str:
    return "Duplicate" if decision == "duplicate" else "Not duplicate" if decision == "not_duplicate" else "Unclear"


def _genai_cost_label(cost: float | None) -> str:
    if cost is None:
        return "pricing unavailable"
    if cost < 0.01:
        return f"${cost:.6f}"
    return f"${cost:.4f}"


def _genai_actual_cost(model: str, usage: dict[str, object]) -> float | None:
    input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    return estimate_cost_usd(model, input_tokens=input_tokens, output_tokens=output_tokens)


def _render_genai_validation_panel(graph: nx.DiGraph, current_pair: tuple[str, str]) -> None:
    with st.expander("GenAI validation terminal", expanded=False):
        st.markdown(
            "<div class='iso-terminal'>Optional assistant for validating the current pair. "
            "Use small batches first: every request can consume paid tokens.</div>",
            unsafe_allow_html=True,
        )
        enabled = st.checkbox("Validate current pair with LLM", key="genai_validate_enabled")
        if not enabled:
            st.caption("Enable this only when you want a GenAI-assisted label for the current pair.")
            return
        api_key = st.text_input("OpenAI API key", type="password", key="genai_openai_key")
        model_rows = st.session_state.get("genai_model_rows", [])
        model_cols = st.columns([1, 1], gap="small")
        if model_cols[0].button("Refresh available models", key="genai_refresh_models", use_container_width=True):
            if not api_key:
                st.warning("Enter the API key first.")
            else:
                try:
                    with st.spinner("Calling OpenAI Models API..."):
                        st.session_state.genai_model_rows = list_openai_models(api_key)
                    st.success(f"Loaded {len(st.session_state.genai_model_rows)} models.")
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
        if model_cols[1].button("Save agent preset", key="genai_save_agent", use_container_width=True):
            config = {
                "name": st.session_state.get("genai_agent_name", "isomera_pair_validator"),
                "model": st.session_state.get("genai_model_select"),
                "prompt": st.session_state.get("genai_prompt_text") or default_pair_validation_prompt(),
                "max_output_tokens": st.session_state.get("genai_max_output_tokens", 900),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            saved = save_genai_agent_config(_app_path("data/genai_agents"), config)
            st.success(f"Agent preset saved: {saved.name}")
        if model_rows:
            model_options = [str(row.get("id")) for row in model_rows if row.get("id")]
        else:
            model_options = sorted(OPENAI_PRICING_HINTS.keys())
        st.text_input("Agent name", value="isomera_pair_validator", key="genai_agent_name")
        selected_model = st.selectbox("Model", options=model_options, key="genai_model_select")
        pricing = OPENAI_PRICING_HINTS.get(selected_model, {})
        if pricing:
            st.caption(
                "Pricing hint from OpenAI pricing page: "
                f"input {pricing.get('input')} | cached {pricing.get('cached_input')} | output {pricing.get('output')}"
            )
        else:
            st.caption("Pricing is not returned by the Models API. Check the OpenAI pricing page before large batches.")
        prompt = st.text_area(
            "Validation prompt",
            value=st.session_state.get("genai_prompt_text") or default_pair_validation_prompt(),
            height=130,
            key="genai_prompt_text",
        )
        st.number_input("Max output tokens", min_value=120, max_value=2000, value=900, step=60, key="genai_max_output_tokens")
        pair_payload = _pair_payload_for_genai(graph, current_pair[0], current_pair[1])
        active_pairs = list(st.session_state.get("scenario_review_pairs") or [current_pair])
        max_tokens = int(st.session_state.get("genai_max_output_tokens", 900))
        current_estimate = estimate_pair_validation_usage(
            prompt=prompt,
            pair_payload=pair_payload,
            max_output_tokens=max_tokens,
            pair_count=1,
        )
        queue_estimate = estimate_pair_validation_usage(
            prompt=prompt,
            pair_payload=pair_payload,
            max_output_tokens=max_tokens,
            pair_count=len(active_pairs),
        )
        current_cost = estimate_cost_usd(
            selected_model,
            input_tokens=current_estimate["estimated_input_tokens"],
            output_tokens=current_estimate["estimated_output_tokens"],
        )
        queue_cost = estimate_cost_usd(
            selected_model,
            input_tokens=queue_estimate["estimated_input_tokens"],
            output_tokens=queue_estimate["estimated_output_tokens"],
        )
        st.markdown("**Token and cost estimate**")
        budget_cols = st.columns(4, gap="small")
        budget_cols[0].metric("Current pair tokens", current_estimate["estimated_total_tokens"])
        budget_cols[1].metric("Current pair cost", _genai_cost_label(current_cost))
        budget_cols[2].metric("Queue pairs", len(active_pairs))
        budget_cols[3].metric("Queue estimate", _genai_cost_label(queue_cost))
        st.caption("Token estimates are local approximations. Actual usage is updated from the OpenAI response after each call.")
        st.markdown("**Pair payload preview**")
        st.code(json.dumps(pair_payload, indent=2, ensure_ascii=True)[:6000], language="json")
        if st.button("Run GenAI validation for current pair", key="genai_run_pair", type="primary", use_container_width=True):
            if not api_key:
                st.warning("Enter the API key first.")
            else:
                try:
                    with st.spinner("Calling OpenAI Responses API for one pair..."):
                        result = validate_pair_with_openai(
                            api_key,
                            model=selected_model,
                            prompt=prompt,
                            pair_payload=pair_payload,
                            max_output_tokens=int(st.session_state.get("genai_max_output_tokens", 600)),
                        )
                    st.session_state.genai_last_result = {
                        "raw_text": result.raw_text,
                        "parsed": result.parsed,
                        "response_id": result.response_id,
                        "model": result.model,
                        "elapsed_seconds": result.elapsed_seconds,
                        "usage": result.usage,
                    }
                    st.success(f"GenAI validation returned in {result.elapsed_seconds}s.")
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
        st.markdown("**Batch validation**")
        st.caption("Use this only after checking the estimate. Isomera validates all pairs in the current review queue and waits for your confirmation before applying the labels.")
        batch_confirm = st.checkbox("I reviewed the estimate and want to run the full queue", key="genai_batch_confirm")
        if st.button(
            f"Run GenAI for all {len(active_pairs)} queue pairs",
            key="genai_run_batch",
            disabled=not batch_confirm or not api_key,
            use_container_width=True,
        ):
            batch_results: list[dict[str, object]] = []
            progress = st.progress(0.0, text="Starting GenAI queue validation...")
            for index, pair in enumerate(active_pairs, start=1):
                payload = _pair_payload_for_genai(graph, pair[0], pair[1])
                progress.progress((index - 1) / max(1, len(active_pairs)), text=f"Validating pair {index}/{len(active_pairs)}")
                try:
                    result = validate_pair_with_openai(
                        api_key,
                        model=selected_model,
                        prompt=prompt,
                        pair_payload=payload,
                        max_output_tokens=max_tokens,
                    )
                    decision = _normalize_genai_decision(result.parsed)
                    batch_results.append(
                        {
                            "node_a": pair[0],
                            "node_b": pair[1],
                            "decision": decision,
                            "confidence": result.parsed.get("confidence"),
                            "rationale": result.parsed.get("rationale"),
                            "raw_text": result.raw_text,
                            "parsed": result.parsed,
                            "response_id": result.response_id,
                            "model": result.model,
                            "elapsed_seconds": result.elapsed_seconds,
                            "usage": result.usage,
                            "actual_cost_usd": _genai_actual_cost(result.model, result.usage),
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    batch_results.append(
                        {
                            "node_a": pair[0],
                            "node_b": pair[1],
                            "decision": "",
                            "confidence": None,
                            "rationale": str(exc),
                            "error": str(exc),
                            "model": selected_model,
                        }
                    )
            progress.progress(1.0, text="GenAI queue validation completed.")
            st.session_state.genai_batch_results = batch_results
            _record_article_report(
                "genai_pair_validation_batch",
                {
                    "scenario": st.session_state.get("curated_scenario_name", "workspace_scenario"),
                    "model": selected_model,
                    "pair_count": len(active_pairs),
                    "estimated_usage": queue_estimate,
                    "estimated_cost_usd": queue_cost,
                    "results": batch_results,
                },
            )
            st.rerun()
        last = st.session_state.get("genai_last_result")
        if last:
            parsed = dict(last.get("parsed") or {})
            normalized_decision = _normalize_genai_decision(parsed)
            st.markdown("**Last GenAI result**")
            result_cols = st.columns(4, gap="small")
            result_cols[0].metric("Decision", _genai_decision_label(normalized_decision))
            result_cols[1].metric("Confidence", parsed.get("confidence", "-"))
            usage = dict(last.get("usage") or {})
            result_cols[2].metric("Actual tokens", usage.get("total_tokens", "-"))
            result_cols[3].metric("Actual cost", _genai_cost_label(_genai_actual_cost(str(last.get("model") or selected_model), usage)))
            if parsed.get("rationale"):
                st.markdown(f"**Rationale**  \n{parsed.get('rationale')}")
            if parsed.get("matching_features") or parsed.get("conflicting_features"):
                feature_cols = st.columns(2, gap="small")
                feature_cols[0].markdown("**Matching features**")
                feature_cols[0].write(parsed.get("matching_features") or [])
                feature_cols[1].markdown("**Conflicting features**")
                feature_cols[1].write(parsed.get("conflicting_features") or [])
            with st.expander("Raw GenAI response", expanded=False):
                st.code(json.dumps(last, indent=2, ensure_ascii=True), language="json")
            if normalized_decision:
                if st.button(f"Confirm GenAI decision: {_genai_decision_label(normalized_decision)}", key="genai_apply_decision", use_container_width=True, type="primary"):
                    _apply_scenario_review_decision(
                        decision=normalized_decision,
                        benchmark_name=st.session_state.get("curated_existing_benchmark_name")
                        if st.session_state.get("curated_benchmark_mode") == "Use existing benchmark"
                        and st.session_state.get("curated_existing_benchmark_name")
                        else st.session_state.get("curated_benchmark_name", "tpc_ds_v2"),
                        scenario_name=st.session_state.get("curated_scenario_name", "workspace_scenario"),
                        node_a=current_pair[0],
                        node_b=current_pair[1],
                        source="genai_single_pair",
                        metadata={
                            "model": last.get("model"),
                            "response_id": last.get("response_id"),
                            "confidence": parsed.get("confidence"),
                            "rationale": parsed.get("rationale"),
                            "usage": usage,
                            "actual_cost_usd": _genai_actual_cost(str(last.get("model") or selected_model), usage),
                        },
                    )
            else:
                st.warning("Isomera could not parse a clear duplicate/not-duplicate decision. Increase max output tokens or refine the prompt.")
        batch_results = list(st.session_state.get("genai_batch_results") or [])
        if batch_results:
            st.markdown("**Batch GenAI summary**")
            summary_df = pd.DataFrame(
                [
                    {
                        "node_a": row.get("node_a"),
                        "node_b": row.get("node_b"),
                        "decision": row.get("decision") or "parse_error",
                        "confidence": row.get("confidence"),
                        "cost_usd": row.get("actual_cost_usd"),
                        "error": row.get("error", ""),
                    }
                    for row in batch_results
                ]
            )
            st.dataframe(summary_df, width="stretch", hide_index=True)
            valid_count = sum(1 for row in batch_results if row.get("decision") in {"duplicate", "not_duplicate"})
            duplicate_count = sum(1 for row in batch_results if row.get("decision") == "duplicate")
            st.caption(f"Parsed decisions: {valid_count}/{len(batch_results)} | duplicates: {duplicate_count}")
            if st.button("Apply GenAI batch decisions to review dataset", key="genai_apply_batch", type="primary", use_container_width=True):
                for row in batch_results:
                    decision = str(row.get("decision") or "")
                    if decision not in {"duplicate", "not_duplicate"}:
                        continue
                    _apply_scenario_review_decision(
                        decision=decision,
                        benchmark_name=st.session_state.get("curated_existing_benchmark_name")
                        if st.session_state.get("curated_benchmark_mode") == "Use existing benchmark"
                        and st.session_state.get("curated_existing_benchmark_name")
                        else st.session_state.get("curated_benchmark_name", "tpc_ds_v2"),
                        scenario_name=st.session_state.get("curated_scenario_name", "workspace_scenario"),
                        node_a=str(row.get("node_a")),
                        node_b=str(row.get("node_b")),
                        source="genai_batch",
                        metadata={
                            "model": row.get("model"),
                            "response_id": row.get("response_id"),
                            "confidence": row.get("confidence"),
                            "rationale": row.get("rationale"),
                            "usage": row.get("usage"),
                            "actual_cost_usd": row.get("actual_cost_usd"),
                        },
                        rerun=False,
                    )
                st.session_state.scenario_curation_message = (
                    "GenAI batch decisions applied. Review the summary and click Finalize scenario to publish/train."
                )
                st.session_state.genai_batch_results = []
                st.rerun()


def _render_pair_preview(
    graph: nx.DiGraph,
    node_a: str,
    node_b: str,
    seed: int | None,
    source_metadata: dict[str, object] | None = None,
) -> None:
    col_a, col_b = st.columns(2)
    subgraph_a = _pair_context_subgraph(graph, node_a)
    subgraph_b = _pair_context_subgraph(graph, node_b)
    with col_a:
        st.caption(f"{node_a} | {_pair_scope_label(node_a)}")
        fig_a = plot_lineage_graph(subgraph_a, seed=seed)
        fig_a.set_size_inches(7.2, 5.2)
        st.pyplot(fig_a, clear_figure=True)
        with st.expander("Table view", expanded=False):
            _render_adjacency(subgraph_a)
            _render_edges(subgraph_a)
            _render_subgraph_sql_contract(graph, subgraph_a, source_metadata)
    with col_b:
        st.caption(f"{node_b} | {_pair_scope_label(node_b)}")
        fig_b = plot_lineage_graph(subgraph_b, seed=seed)
        fig_b.set_size_inches(7.2, 5.2)
        st.pyplot(fig_b, clear_figure=True)
        with st.expander("Table view", expanded=False):
            _render_adjacency(subgraph_b)
            _render_edges(subgraph_b)
            _render_subgraph_sql_contract(graph, subgraph_b, source_metadata)

PAIR_IMAGE_RE = re.compile(r"^pair_\\d+_(.+_D\\d+)_(.+_D\\d+)\\.png$")
DEFAULT_ARCH_NAME = "TPC-DS (default)"
CUSTOM_ARCH_ROOT = _app_path("data/architectures")
DEFAULT_ARCH_ROOT = CUSTOM_ARCH_ROOT / "tpc_ds"
ISOMERA_IDENTITY = load_identity()
VISIBLE_BENCHMARKS = {
    DEFAULT_ARCH_NAME,
    "smoke_operational",
    "tpc_ds_genai_spec",
    "tpc_ds_genai_sot_spec",
    "tpc_ds_genai_sor_sot",
    "tpc_ds_genai_full_lineage",
}
HIDDEN_BENCHMARKS = {
    "cayo_v1",
    "isomerav2_bench",
    "isomerav2_night_test",
    "mysql_validation_demo",
    "tpc_ds_genai_spec_protocol",
    "tpc_ds_genai_spec_v2",
    "tpc_ds_v2",
    "tpc_ds_v22",
}


def _feature_notes_text() -> str:
    path = _app_path("docs/FEATURE_NOTES.md")
    if not path.exists():
        return "Feature notes are not available."
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_pair_filename(filename: str) -> tuple[str, str] | None:
    match = PAIR_IMAGE_RE.match(filename)
    if not match:
        return None
    return match.group(1), match.group(2)


def _list_architectures() -> list[dict[str, object]]:
    architectures: list[dict[str, object]] = [
        {"name": DEFAULT_ARCH_NAME, "root": DEFAULT_ARCH_ROOT, "readonly": True}
    ]
    if CUSTOM_ARCH_ROOT.exists():
        for path in sorted(p for p in CUSTOM_ARCH_ROOT.iterdir() if p.is_dir()):
            if path.name == "tpc_ds":
                continue
            if path.name in HIDDEN_BENCHMARKS:
                continue
            if path.name not in VISIBLE_BENCHMARKS:
                continue
            architectures.append({"name": path.name, "root": path, "readonly": False})
    return architectures


def _all_architecture_model_roots() -> list[Path]:
    roots: list[Path] = []
    if CUSTOM_ARCH_ROOT.exists():
        for path in sorted(p for p in CUSTOM_ARCH_ROOT.iterdir() if p.is_dir()):
            models_root = path / "models"
            if models_root.exists():
                roots.append(models_root)
    return roots


def _family_from_model_path(pickle_path: Path, metadata: dict[str, object], fallback: str) -> str:
    for key in ("model_family_name", "model_family", "family", "cluster_name"):
        value = metadata.get(key)
        if value:
            return str(value)
    parts = set(pickle_path.parts)
    path_text = str(pickle_path).lower()
    if "tpc_ds_genai_spec_protocol" in parts:
        rank_match = re.search(r"rank(\d+)", path_text)
        rank = f" rank {rank_match.group(1)}" if rank_match else ""
        return f"GNN GenAI SPEC Protocol{rank}"
    if "tpc_ds_genai_spec_v2" in parts:
        if "weighted_bce" in parts:
            return "GNN GenAI SPEC v2 Weighted BCE"
        if "focal_loss" in parts:
            return "GNN GenAI SPEC v2 Focal Loss"
        if "hard_negatives" in parts:
            return "GNN GenAI SPEC v2 Hard Negatives"
        return "GNN GenAI SPEC v2 cluster"
    if "tpc_ds_genai_spec" in parts:
        return "GNN GenAI SPEC v1 cluster"
    if "isomerav2_bench" in parts:
        return "GNN Isomera v2 test cluster"
    return fallback


def _get_architecture(name: str) -> dict[str, object] | None:
    for arch in _list_architectures():
        if arch["name"] == name:
            return arch
    return None


def _sanitize_benchmark_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._-")
    return cleaned or "benchmark_v1"


def _benchmark_root(benchmark_name: str) -> Path:
    return CUSTOM_ARCH_ROOT / _sanitize_benchmark_name(benchmark_name)


def _benchmark_storage_root(benchmark_name: str) -> Path:
    arch = _get_architecture(benchmark_name)
    return Path(arch["root"]) if arch else _benchmark_root(benchmark_name)


def _ensure_benchmark_structure(benchmark_name: str) -> Path:
    root = _benchmark_storage_root(benchmark_name)
    for relative in ("gml", "real_pairs", "validations", "models"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    return root


def _benchmark_manifest_path(benchmark_name: str) -> Path:
    return _benchmark_storage_root(benchmark_name) / "benchmark_manifest.json"


def _load_benchmark_manifest(benchmark_name: str) -> dict[str, object]:
    manifest_path = _benchmark_manifest_path(benchmark_name)
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        "benchmark_name": _sanitize_benchmark_name(benchmark_name),
        "display_name": benchmark_name,
        "scenarios": {},
        "models": {},
        "model_clusters": {},
        "updated_at": None,
    }


def _save_benchmark_manifest(benchmark_name: str, manifest: dict[str, object]) -> Path:
    root = _ensure_benchmark_structure(benchmark_name)
    manifest["benchmark_name"] = _sanitize_benchmark_name(benchmark_name)
    manifest["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    manifest_path = root / "benchmark_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def _register_benchmark_scenario(
    *,
    benchmark_name: str,
    scenario_name: str,
    gml_path: Path,
    labels_path: Path,
    source_path: Path | None,
    total_pairs: int,
    candidate_pairs: int,
    reviewed_pairs: int,
    duplicate_pairs: int,
) -> None:
    manifest = _load_benchmark_manifest(benchmark_name)
    scenarios = manifest.setdefault("scenarios", {})
    scenarios[scenario_name] = {
        "gml_path": str(gml_path),
        "labels_path": str(labels_path),
        "source_path": str(source_path) if source_path else None,
        "total_pairs": total_pairs,
        "candidate_pairs": candidate_pairs,
        "reviewed_pairs": reviewed_pairs,
        "duplicate_pairs": duplicate_pairs,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    _save_benchmark_manifest(benchmark_name, manifest)


def _register_benchmark_model(
    *,
    benchmark_name: str,
    model_name: str,
    pickle_path: Path,
    metadata_path: Path,
    source_scenarios: list[str],
    model_version: str,
) -> None:
    manifest = _load_benchmark_manifest(benchmark_name)
    models = manifest.setdefault("models", {})
    models[model_name] = {
        "pickle_path": str(pickle_path),
        "metadata_path": str(metadata_path),
        "source_scenarios": source_scenarios,
        "model_version": model_version,
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "active": True,
    }
    _save_benchmark_manifest(benchmark_name, manifest)


def _list_benchmark_models(benchmark_name: str) -> list[dict[str, object]]:
    root = _benchmark_storage_root(benchmark_name)
    manifest = _load_benchmark_manifest(benchmark_name)
    entries: list[dict[str, object]] = []
    for model_name, payload in sorted((manifest.get("models") or {}).items()):
        pickle_path = Path(str(payload.get("pickle_path", "")))
        if not pickle_path.is_absolute():
            pickle_path = (root / pickle_path).resolve()
        metadata_path = Path(str(payload.get("metadata_path", ""))) if payload.get("metadata_path") else None
        if metadata_path and not metadata_path.is_absolute():
            metadata_path = (root / metadata_path).resolve()
        if not pickle_path.exists():
            continue
        entries.append(
            {
                "name": model_name,
                "pickle_path": pickle_path,
                "metadata_path": str(metadata_path) if metadata_path else None,
                "source_scenarios": payload.get("source_scenarios", []),
                "model_version": payload.get("model_version"),
            }
        )
    return entries


def _available_gnn_pickle_assets() -> list[dict[str, object]]:
    search_roots = [
        _app_path("core/algorithms/pickle/gin_gnn/modelos_gnn_separados"),
        _app_path("data/architectures"),
    ]
    seen: set[str] = set()
    assets: list[dict[str, object]] = []
    for root in search_roots:
        if not root.exists():
            continue
        for pickle_path in sorted(root.rglob("*.pkl")):
            resolved = str(pickle_path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            metadata_path = pickle_path.with_suffix(".json")
            try:
                label_path = pickle_path.relative_to(PROJECT_ROOT)
            except ValueError:
                label_path = pickle_path
            assets.append(
                {
                    "label": str(label_path),
                    "pickle_path": pickle_path,
                    "metadata_path": metadata_path if metadata_path.exists() else None,
                    "size_kb": round(pickle_path.stat().st_size / 1024, 1),
                }
            )
    return assets


def _save_manual_model_routes(
    benchmark_name: str,
    family: str,
    routes: dict[str, Path],
    metadata_path: Path | None,
    route_mode: str,
    candidate_paths: list[Path] | None = None,
    selection_metric: str | None = None,
) -> Path:
    manifest = _load_benchmark_manifest(benchmark_name)
    clusters = manifest.setdefault("model_clusters", {})
    cluster = clusters.setdefault(family, {})
    cluster["family"] = family
    cluster["route_mode"] = route_mode
    cluster["source"] = "manual_manifest"
    cluster["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if selection_metric:
        cluster["selection_metric"] = selection_metric
    if candidate_paths is not None:
        cluster["candidate_paths"] = [
            {
                "pickle_path": str(candidate_path),
                "metadata_path": str(candidate_path.with_suffix(".json"))
                if candidate_path.with_suffix(".json").exists()
                else None,
            }
            for candidate_path in candidate_paths
        ]
    cluster_routes = cluster.setdefault("routes", {})
    for scenario, pickle_path in routes.items():
        cluster_routes[scenario] = {
            "pickle_path": str(pickle_path),
            "metadata_path": str(metadata_path) if metadata_path else None,
            "route_mode": route_mode,
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    return _save_benchmark_manifest(benchmark_name, manifest)


def _clear_manual_model_cluster(benchmark_name: str, family: str) -> Path:
    manifest = _load_benchmark_manifest(benchmark_name)
    clusters = manifest.setdefault("model_clusters", {})
    clusters.pop(family, None)
    return _save_benchmark_manifest(benchmark_name, manifest)


def _should_run_best_of_policy(route_policy: str, candidate_count: int, scenario_count: int) -> bool:
    if candidate_count <= 0:
        return False
    if route_policy == "best_of_cluster":
        return True
    if route_policy == "auto_best_of_when_overcomplete":
        return candidate_count > scenario_count
    return False


def _benchmark_scenario_names(benchmark_name: str) -> list[str]:
    arch = _get_architecture(benchmark_name)
    root = Path(arch["root"]) if arch else _benchmark_root(benchmark_name)
    gml_root = root / "gml"
    return sorted(path.stem for path in gml_root.glob("*.gml")) if gml_root.exists() else []


def _read_model_metadata(metadata_path: str | Path | None) -> dict[str, object]:
    if not metadata_path:
        return {}
    path = Path(str(metadata_path))
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _pickle_module_from_metadata(metadata: dict[str, object]) -> str:
    module = metadata.get("pickle_module") or metadata.get("inference_module")
    if module:
        return str(module)
    return "core.algorithms.gnn_model"


def _pickle_module_for_path(pickle_path: Path, metadata_path: str | Path | None = None) -> str:
    metadata = _read_model_metadata(metadata_path or pickle_path.with_suffix(".json"))
    return _pickle_module_from_metadata(metadata)


def _infer_model_scenarios(
    pickle_path: Path,
    metadata: dict[str, object],
    benchmark_scenarios: list[str],
    explicit_scenarios: list[str] | None = None,
) -> list[str]:
    candidates: list[str] = []
    for source in (explicit_scenarios or [], metadata.get("scenarios") or [], metadata.get("source_scenarios") or []):
        if isinstance(source, str):
            candidates.append(source)
        elif isinstance(source, list):
            candidates.extend(str(item) for item in source)
    if candidates:
        return sorted({scenario for scenario in candidates if scenario in benchmark_scenarios})
    stem = pickle_path.stem
    return sorted([scenario for scenario in benchmark_scenarios if scenario in stem])


def _infer_model_family(pickle_path: Path, scenario_name: str | None, metadata: dict[str, object]) -> str:
    for key in ("model_family_name", "model_family", "family", "cluster_name"):
        value = metadata.get(key)
        if value:
            return str(value)
    stem = pickle_path.stem
    if scenario_name and scenario_name in stem:
        stem = stem.replace(scenario_name, "").strip("_-. ")
    normalized = stem.replace("_", " ").strip()
    if "isomerav2" in normalized.lower():
        return "GNN Isomera v2 cluster"
    if "tpc" in normalized.lower():
        return "GNN TPC-DS v1 cluster"
    return normalized or "GNN custom cluster"


def _benchmark_model_clusters(benchmark_name: str) -> list[dict[str, object]]:
    benchmark_scenarios = _benchmark_scenario_names(benchmark_name)
    clusters: dict[str, dict[str, object]] = {}

    def add_route(
        family: str,
        scenario: str,
        pickle_path: Path,
        metadata_path: str | Path | None,
        source: str,
        route_mode: str,
        pickle_module: str | None = None,
    ) -> None:
        cluster = clusters.setdefault(
            family,
            {
                "family": family,
                "routes": {},
                "metadata_paths": {},
                "pickle_modules": {},
                "route_sources": {},
                "route_modes": {},
                "source": source,
            },
        )
        cluster["routes"][scenario] = pickle_path  # type: ignore[index]
        cluster["route_sources"][scenario] = source  # type: ignore[index]
        cluster["route_modes"][scenario] = route_mode  # type: ignore[index]
        cluster["source"] = source
        if metadata_path:
            cluster["metadata_paths"][scenario] = str(metadata_path)  # type: ignore[index]
        cluster["pickle_modules"][scenario] = pickle_module or _pickle_module_for_path(pickle_path, metadata_path)  # type: ignore[index]

    def add_candidate_cluster(
        family: str,
        candidate_paths: list[Path],
        source: str,
        route_mode: str,
        selection_metric: str,
    ) -> None:
        cluster = clusters.setdefault(
            family,
            {
                "family": family,
                "routes": {},
                "metadata_paths": {},
                "pickle_modules": {},
                "route_sources": {},
                "route_modes": {},
                "source": source,
            },
        )
        cluster["candidate_paths"] = candidate_paths
        cluster["candidate_modules"] = {
            str(candidate_path): _pickle_module_for_path(candidate_path)
            for candidate_path in candidate_paths
        }
        cluster["source"] = source
        cluster["route_policy"] = route_mode
        cluster["selection_metric"] = selection_metric

    baseline_root = _app_path("core/algorithms/pickle/gin_gnn/modelos_gnn_separados")
    if baseline_root.exists():
        for scenario in benchmark_scenarios:
            pickle_path = baseline_root / f"{scenario}.pkl"
            if pickle_path.exists():
                add_route(
                    "GNN TPC-DS v1 cluster",
                    scenario,
                    pickle_path,
                    None,
                    "baseline_tpcds_pickle_dir",
                    "scenario_specific",
                    "core.algorithms.gnn_model",
                )

    seen_paths: set[str] = set()
    for model in _list_benchmark_models(benchmark_name):
        pickle_path = Path(str(model["pickle_path"]))
        seen_paths.add(str(pickle_path.resolve()))
        metadata = _read_model_metadata(model.get("metadata_path"))
        scenarios = _infer_model_scenarios(
            pickle_path,
            metadata,
            benchmark_scenarios,
            [str(item) for item in model.get("source_scenarios", [])],
        )
        family = _infer_model_family(pickle_path, scenarios[0] if scenarios else None, metadata)
        for scenario in scenarios:
            add_route(
                family,
                scenario,
                pickle_path,
                model.get("metadata_path"),
                "benchmark_manifest",
                "scenario_specific",
                _pickle_module_from_metadata(metadata),
            )

    arch = _get_architecture(benchmark_name)
    root = Path(arch["root"]) if arch else _benchmark_root(benchmark_name)
    model_roots = [root / "models"]
    for global_models_root in _all_architecture_model_roots():
        if global_models_root not in model_roots:
            model_roots.append(global_models_root)
    for models_root in model_roots:
        if models_root.exists():
            pickle_iter = sorted(models_root.rglob("*.pkl"))
        else:
            pickle_iter = []
        for pickle_path in pickle_iter:
            resolved = str(pickle_path.resolve())
            if resolved in seen_paths:
                continue
            metadata_path = pickle_path.with_suffix(".json")
            metadata = _read_model_metadata(metadata_path)
            scenarios = _infer_model_scenarios(pickle_path, metadata, benchmark_scenarios)
            if not scenarios:
                continue
            family = _family_from_model_path(
                pickle_path,
                metadata,
                _infer_model_family(pickle_path, scenarios[0] if scenarios else None, metadata),
            )
            for scenario in scenarios:
                add_route(
                    family,
                    scenario,
                    pickle_path,
                    metadata_path if metadata_path.exists() else None,
                    "models_directory",
                    "scenario_specific",
                    _pickle_module_from_metadata(metadata),
                )

    manifest = _load_benchmark_manifest(benchmark_name)
    for family, payload in sorted((manifest.get("model_clusters") or {}).items()):
        if not isinstance(payload, dict):
            continue
        candidate_payloads = payload.get("candidate_paths") or []
        if isinstance(candidate_payloads, list):
            candidate_paths: list[Path] = []
            for candidate_payload in candidate_payloads:
                if not isinstance(candidate_payload, dict):
                    continue
                candidate_path = Path(str(candidate_payload.get("pickle_path") or ""))
                if not candidate_path.is_absolute():
                    candidate_path = (_benchmark_storage_root(benchmark_name) / candidate_path).resolve()
                if candidate_path.exists():
                    candidate_paths.append(candidate_path)
            if candidate_paths:
                add_candidate_cluster(
                    str(family),
                    candidate_paths,
                    str(payload.get("source") or "manual_manifest"),
                    str(payload.get("route_mode") or "best_of_cluster"),
                    str(payload.get("selection_metric") or "sf_jaccard"),
                )
        route_payloads = payload.get("routes") or {}
        if not isinstance(route_payloads, dict):
            continue
        for scenario, route_payload in route_payloads.items():
            if scenario not in benchmark_scenarios or not isinstance(route_payload, dict):
                continue
            pickle_path = Path(str(route_payload.get("pickle_path") or ""))
            if not pickle_path.is_absolute():
                pickle_path = (_benchmark_storage_root(benchmark_name) / pickle_path).resolve()
            if not pickle_path.exists():
                continue
            metadata_path_raw = route_payload.get("metadata_path")
            metadata_path = Path(str(metadata_path_raw)) if metadata_path_raw else None
            if metadata_path and not metadata_path.is_absolute():
                metadata_path = (_benchmark_storage_root(benchmark_name) / metadata_path).resolve()
            add_route(
                str(family),
                str(scenario),
                pickle_path,
                metadata_path if metadata_path and metadata_path.exists() else None,
                str(payload.get("source") or "manual_manifest"),
                str(route_payload.get("route_mode") or payload.get("route_mode") or "manual"),
                _pickle_module_for_path(pickle_path, metadata_path if metadata_path and metadata_path.exists() else None),
            )

    ordered: list[dict[str, object]] = []
    for family, cluster in sorted(clusters.items()):
        routes = dict(cluster.get("routes") or {})
        candidate_paths = list(cluster.get("candidate_paths") or [])
        route_policy = str(cluster.get("route_policy") or "")
        best_of_active = _should_run_best_of_policy(route_policy, len(candidate_paths), len(benchmark_scenarios))
        covered = len(benchmark_scenarios) if best_of_active else len([scenario for scenario in benchmark_scenarios if scenario in routes])
        ordered.append(
            {
                "family": family,
                "routes": routes,
                "candidate_paths": candidate_paths,
                "candidate_modules": dict(cluster.get("candidate_modules") or {}),
                "metadata_paths": dict(cluster.get("metadata_paths") or {}),
                "pickle_modules": dict(cluster.get("pickle_modules") or {}),
                "route_sources": dict(cluster.get("route_sources") or {}),
                "route_modes": dict(cluster.get("route_modes") or {}),
                "route_policy": cluster.get("route_policy"),
                "selection_metric": cluster.get("selection_metric"),
                "source": cluster.get("source"),
                "covered": covered,
                "total": len(benchmark_scenarios),
                "status": "complete"
                if benchmark_scenarios
                and covered == len(benchmark_scenarios)
                else "partial",
            }
        )
    return ordered


def _benchmark_routing_tables(benchmark_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenario_names = _benchmark_scenario_names(benchmark_name)
    clusters = _benchmark_model_clusters(benchmark_name)
    summary_rows = []
    route_rows = []
    for cluster in clusters:
        routes = dict(cluster.get("routes") or {})
        pickle_modules = dict(cluster.get("pickle_modules") or {})
        route_sources = dict(cluster.get("route_sources") or {})
        route_modes = dict(cluster.get("route_modes") or {})
        candidate_paths = list(cluster.get("candidate_paths") or [])
        route_policy = str(cluster.get("route_policy") or "")
        best_of_active = _should_run_best_of_policy(route_policy, len(candidate_paths), len(scenario_names))
        family = str(cluster["family"])
        summary_rows.append(
            {
                "model_family": family,
                "coverage": f"{cluster.get('covered', 0)}/{cluster.get('total', len(scenario_names))}",
                "status": cluster.get("status"),
                "source": cluster.get("source"),
                "route_policy": route_policy or "explicit_map",
                "selection_metric": cluster.get("selection_metric") or "",
                "candidate_pickles": len(candidate_paths),
                "best_of_active": best_of_active,
            }
        )
        for scenario in scenario_names:
            pickle_path = routes.get(scenario)
            route_rows.append(
                {
                    "scenario": scenario,
                    "model_family": family,
                    "pickle_path": f"best of {len(candidate_paths)} candidates by {cluster.get('selection_metric') or 'sf_jaccard'}"
                    if best_of_active
                    else str(pickle_path)
                    if pickle_path
                    else "",
                    "pickle_module": "best-of-candidate metadata"
                    if best_of_active
                    else str(pickle_modules.get(scenario, "")),
                    "route_mode": route_policy if best_of_active else route_modes.get(scenario, route_policy),
                    "route_source": route_sources.get(scenario, str(cluster.get("source") or "")),
                    "status": "best_of_candidates"
                    if best_of_active
                    else "mapped"
                    if pickle_path
                    else "missing_model",
                }
            )
    return pd.DataFrame(summary_rows), pd.DataFrame(route_rows)


def _training_jobs_root() -> Path:
    root = _app_path("data/training_jobs")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _training_job_paths(job_id: str) -> dict[str, Path]:
    job_root = _training_jobs_root() / job_id
    job_root.mkdir(parents=True, exist_ok=True)
    return {
        "root": job_root,
        "config": job_root / "config.json",
        "progress": job_root / "progress.json",
        "stop": job_root / "stop.flag",
        "stdout": job_root / "stdout.log",
        "stderr": job_root / "stderr.log",
    }


def _training_job_is_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "stat="],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
        if result.returncode != 0:
            return False
        status = result.stdout.strip()
        if not status or "Z" in status:
            return False
    except Exception:
        return True
    return True


def _read_text_tail(path: str | Path | None, max_chars: int = 4000) -> str:
    if not path:
        return ""
    path = Path(str(path))
    if not path.exists():
        return ""
    content = path.read_text(encoding="utf-8", errors="replace")
    return content[-max_chars:]


def _training_option_label(options: dict[str, dict[str, str]], key: str) -> str:
    meta = options.get(str(key), {})
    return str(meta.get("label") or key)


def _training_option_caption(options: dict[str, dict[str, str]], key: str) -> str:
    meta = options.get(str(key), {})
    return str(meta.get("description") or "")


def _render_training_option_docs(title: str, options: dict[str, dict[str, str]]) -> None:
    st.markdown(f"**{title}**")
    for key, meta in options.items():
        st.markdown(f"**{meta.get('label', key)}**")
        st.caption(str(meta.get("description", "")))
        if meta.get("formula"):
            st.code(str(meta["formula"]), language="text")


def _training_options_markdown(title: str, options: dict[str, dict[str, str]]) -> str:
    lines = [f"**{title}**"]
    for key, meta in options.items():
        lines.append(f"- **{meta.get('label', key)}**: {meta.get('description', '')}")
        if meta.get("formula"):
            lines.append(f"  Formula: `{meta['formula']}`")
    return "\n".join(lines)


def _model_family_help_markdown(model_family: dict[str, object]) -> str:
    docs = dict(model_family.get("docs") or {})
    lines = [
        f"**{model_family.get('official_name')}**",
        f"Version: `{model_family.get('version')}`",
        "",
        str(docs.get("overview", "")),
        "",
        str(docs.get("theory", "")),
        "",
        "**Formulas**",
    ]
    lines.extend(f"- `{formula}`" for formula in list(docs.get("formulas") or []))
    lines.append("")
    lines.append("**Layers**")
    lines.extend(f"- {item}" for item in list(docs.get("layers") or []))
    lines.append("")
    lines.append("**How to use**")
    lines.extend(f"- {item}" for item in list(docs.get("how_to_use") or []))
    lines.append("")
    lines.append(_training_options_markdown("Loss options", TRAINING_LOSS_OPTIONS))
    lines.append("")
    lines.append(_training_options_markdown("Balancing options", TRAINING_BALANCE_OPTIONS))
    lines.append("")
    lines.append(_training_options_markdown("Optimizer options", TRAINING_OPTIMIZER_OPTIONS))
    return "\n".join(lines)


def _training_protocol_help_markdown() -> str:
    grid = "; ".join(f"{row['parameter']}={row['values']}" for row in _article_hyperparameter_grid_rows())
    stages = "; ".join(f"{row['stage']}: {row['scope']}" for row in _article_hyperparameter_protocol_rows())
    return (
        "**Isomera Staged Protocol**\n\n"
        "Use this when you want a reproducible model-selection process instead of choosing parameters by hand.\n\n"
        "**Manual path**\n\n"
        "Select `Manual configuration` when you already know the exact hyperparameters you want.\n\n"
        "**Why staged search?**\n\n"
        "A full grid across strategies, epochs, learning rates, hidden sizes, dropout, thresholds, splits, "
        "negative ratios, and seeds quickly reaches hundreds of thousands of trainings. The staged protocol "
        "first screens a reduced grid, then fully validates only the best configurations.\n\n"
        f"**Reduced grid:** {grid}\n\n"
        f"**Protocol stages:** {stages}"
    )


TRAINING_PROTOCOL_OPTIONS: dict[str, dict[str, object]] = {
    "single_configuration": {
        "label": "Manual configuration",
        "description": "Train exactly the configuration selected on this screen. Use this when you want full manual control.",
    },
    "isomera_staged_protocol": {
        "label": "Isomera Staged Protocol",
        "description": (
            "Guided reproducible protocol: screen a reduced grid, select top configurations by SF-Jaccard, "
            "then validate the best configurations on all scenarios."
        ),
    },
}


def _article_hyperparameter_grid_rows() -> list[dict[str, object]]:
    return [
        {"parameter": "Training strategy", "values": "Weighted BCE; Focal Loss; Hard Negatives", "count": 3},
        {"parameter": "Learning rate", "values": "0.001; 0.005; 0.010", "count": 3},
        {"parameter": "Hidden channels", "values": "16; 32", "count": 2},
        {"parameter": "Dropout", "values": "0.0; 0.1", "count": 2},
        {"parameter": "Inference threshold", "values": "0.4; 0.5; 0.6", "count": 3},
    ]


def _article_hyperparameter_protocol_rows() -> list[dict[str, object]]:
    return [
        {
            "stage": "screening_5_scenarios",
            "scope": "3 benchmarks x 5 scenarios x 108 configs",
            "trainings": 1620,
            "decision": "Keep top 5 configs per benchmark by SF-Jaccard.",
        },
        {
            "stage": "full_validation_20_scenarios",
            "scope": "3 benchmarks x 20 scenarios x top 5 configs",
            "trainings": 300,
            "decision": "Validate selected configs on complete scenario coverage.",
        },
        {
            "stage": "benchmark_final",
            "scope": "Best configs vs VF2, Node Match, GNN TPC-DS v1, GNN GenAI v1, GNN GenAI v2",
            "trainings": 0,
            "decision": "Report detector-family, per-scenario, and artifact-routing metrics.",
        },
    ]


def _render_hyperparameter_protocol_info() -> None:
    st.markdown("**Isomera Staged Protocol**")
    st.write(
        "Use this when you want a reproducible model-selection process instead of choosing parameters by hand. "
        "It can support an article, an internal benchmark, or any repeatable experiment."
    )
    st.markdown("**Manual path**")
    st.write(
        "If you already know the hyperparameters you want, select `Manual configuration` and train only the "
        "configuration shown on the screen."
    )
    st.markdown("**Why staged search instead of exhaustive search?**")
    st.write(
        "A full grid across strategies, epochs, learning rates, hidden sizes, dropout, thresholds, splits, "
        "negative ratios, and seeds quickly reaches hundreds of thousands of trainings. The staged protocol "
        "first screens a reduced grid, then fully validates only the best configurations."
    )
    st.markdown("**Reduced grid**")
    st.dataframe(pd.DataFrame(_article_hyperparameter_grid_rows()), width="stretch", hide_index=True)
    st.markdown("**Protocol**")
    st.dataframe(pd.DataFrame(_article_hyperparameter_protocol_rows()), width="stretch", hide_index=True)


MODEL_FAMILIES: dict[str, dict[str, object]] = {
    "GNN (GIN Pair Classifier) v1": {
        "key": "gnn_gin_pair_v1",
        "description": "Encoder GIN sobre subgrafos locais e classificador binário de pares.",
        "version": "gin_pair_v1",
        "notes": "Entrada padronizada: cenário convertido em grafo dirigido e pares curados como ground truth.",
        "official_name": "Graph Isomorphism Network Pair Classifier",
        "short_blurb": "Modelo supervisionado para classificar pares de subgrafos como duplicados ou não. Usa embeddings GIN por subgrafo e uma MLP binária sobre a concatenação das embeddings.",
        "docs": {
            "overview": "A entrada é um cenário convertido em subgrafos locais por nó. Cada subgrafo recebe uma embedding via camadas GIN e, em seguida, um classificador binário decide se dois subgrafos representam duplicidade estrutural.",
            "theory": "GIN aproxima o poder discriminativo do teste de Weisfeiler-Lehman ao agregar vizinhança e aplicar uma MLP por camada. O classificador final aprende um limite supervisionado sobre pares positivos e negativos.",
            "formulas": [
                "h_v^(k) = MLP^(k) ((1 + eps^(k)) * h_v^(k-1) + sum_{u in N(v)} h_u^(k-1))",
                "z_G = mean_pool({h_v^(K)})",
                "y_hat = sigma(MLP([z_G1 || z_G2]))",
            ],
            "how_to_use": [
                "Use quando o cenário já foi curado e possui tabela supervisionada com target=1 para duplicado e target=0 para não duplicado.",
                "Ajuste `epochs`, `hidden channels`, `negative ratio` e `learning rate` para equilibrar velocidade e qualidade.",
                "O benchmark passa a carregar o `.pkl` salvo para todos os cenários do benchmark publicado.",
            ],
            "layers": [
                "Camada 1: agregação GIN sobre o subgrafo local",
                "Camada 2: nova agregação GIN e projeção para embedding final",
                "Pooling: média global dos nós do subgrafo",
                "Cabeça de classificação: MLP binária sobre as embeddings concatenadas",
            ],
        },
        "parameters": [
            {"key": "epochs", "label": "Epochs", "help": "Número de passagens completas pelo conjunto de treino.", "min": 1, "max": 200, "value": 8},
            {"key": "hidden_channels", "label": "Hidden channels", "help": "Dimensão interna das embeddings do GNN.", "min": 4, "max": 256, "value": 32},
            {"key": "negative_ratio", "label": "Negative ratio", "help": "Quantos pares negativos são amostrados para cada par duplicado.", "min": 1, "max": 10, "value": 2},
            {"key": "learning_rate_scaled", "label": "Learning rate x1e-4", "help": "Taxa de aprendizado do otimizador.", "min": 1, "max": 1000, "value": 50},
            {"key": "dropout_pct", "label": "Dropout %", "help": "Reserva para regularização do classificador.", "min": 0, "max": 90, "value": 20},
            {"key": "batch_size", "label": "Batch size", "help": "Quantidade de pares processados por passo de treino.", "min": 1, "max": 256, "value": 16},
            {"key": "seed", "label": "Seed", "help": "Semente para reprodutibilidade.", "min": 0, "max": 9999, "value": 42},
        ],
        "optimizers": ["adam", "adamw", "sgd"],
    }
}


def _list_scenarios(root: Path) -> list[str]:
    gml_root = root / "gml"
    if gml_root.exists():
        return [p.stem for p in sorted(gml_root.glob("*.gml"))]
    validations_root = root / "validations"
    if validations_root.exists():
        return [p.name for p in sorted(p for p in validations_root.iterdir() if p.is_dir())]
    return []


def _save_graph_image(graph: nx.DiGraph, path: Path, seed: int | None) -> None:
    fig = plot_lineage_graph(graph, seed=seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=150)


def _save_adjacency_image(graph: nx.DiGraph, path: Path) -> None:
    fig = plot_adjacency_matrix(graph)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=150)


def _find_gml_for_scenario(root: Path, scenario_name: str, readonly: bool) -> Path | None:
    gml_candidates = [
        root / "gml" / f"{scenario_name}.gml",
        root / "validations" / scenario_name / "graph.gml",
    ]
    return next((p for p in gml_candidates if p.exists()), None)


def _extract_sor_domains(scenario: str) -> tuple[str | None, str | None]:
    match_sor = re.search(r"(?i)SOR(\d+)", scenario)
    match_dom = re.search(r"(?i)_D(\d+)", scenario)
    if match_sor and match_dom:
        return match_sor.group(1), match_dom.group(1)
    parts = scenario.replace("-", "_").split("_")
    sor_val = None
    dom_val = None
    for part in parts:
        if part.lower().startswith("sor"):
            sor_val = part[3:] or sor_val
        if part.lower().startswith("d") and part[1:].isdigit():
            dom_val = part[1:]
    return sor_val, dom_val


def _list_tech_docs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    docs = sorted(p for p in root.rglob("*.md") if p.is_file())
    return docs


def _safe_read_bytes(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except OSError:
        return None


def main() -> None:
    """Entry point for running the Streamlit app via Python."""
    if "streamlit" not in sys.argv[0]:
        from streamlit.web import cli as stcli

        sys.argv = ["streamlit", "run", str(Path(__file__).resolve())]
        raise SystemExit(stcli.main())


st.set_page_config(page_title="Isomera", layout="wide")
st.markdown(
    """
    <style>
    :root {
        --iso-bg: #F5F5F3;
        --iso-surface: #ECECE8;
        --iso-surface-2: #E3E3DE;
        --iso-border: #C9C9C1;
        --iso-text: #2F312E;
        --iso-text-muted: #666A63;
        --iso-accent: #5C7C6F;
        --iso-accent-hover: #4E6B60;
        --iso-ok: #6B7A58;
        --iso-warn: #A27A3F;
        --iso-error: #8A4D4D;
        --iso-sidebar: #E7E7E1;
    }

    html, body, [class*='css'] {
        font-size: 12px;
        color: var(--iso-text);
        overflow-x: hidden;
    }

    .stApp {
        background: var(--iso-bg);
        color: var(--iso-text);
    }

    [data-testid="stSidebar"] {
        background: var(--iso-sidebar);
        border-right: 1px solid var(--iso-border);
    }

    [data-testid="stSidebar"] * {
        color: var(--iso-text);
    }

    [data-testid="stAppViewContainer"] {
        background: var(--iso-bg);
    }

    [data-testid="stHeader"] {
        background: rgba(245, 245, 243, 0.85);
    }

    [data-testid="stToolbar"] {
        right: 1rem;
    }

    .block-container {
        padding-top: 2.6rem;
        background: var(--iso-bg);
    }

    [data-testid="stVerticalBlock"] > [style*="flex-direction: column;"] > [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--iso-surface);
        border: 1px solid var(--iso-border);
        border-radius: 14px;
    }

    [data-testid="stMarkdownContainer"] p,
    [data-testid="stCaptionContainer"],
    label,
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label {
        color: var(--iso-text);
    }

    [data-testid="stInfo"] {
        background: var(--iso-surface);
        border: 1px solid var(--iso-border);
        color: var(--iso-text);
    }

    [data-testid="stAlert"] {
        border-radius: 12px;
    }

    .stButton > button {
        background: var(--iso-surface-2);
        color: var(--iso-text);
        border: 1px solid var(--iso-border);
        border-radius: 10px;
    }

    .stButton > button[kind="primary"] {
        background: var(--iso-accent);
        color: #F8F8F4;
        border: 1px solid var(--iso-accent);
    }

    [data-testid="stButton"],
    [data-testid="stButton"] > div {
        background: transparent !important;
    }

    [data-testid="stBaseButton-primary"],
    [data-testid="stBaseButton-primary"] * {
        background: var(--iso-accent) !important;
        color: #F8F8F4 !important;
        border-color: var(--iso-accent) !important;
    }

    [data-testid="stBaseButton-secondary"],
    [data-testid="stBaseButton-secondary"] * {
        background: #F0EFE9 !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
    }
    .stButton > button[kind="secondary"] {
        background: #F0EFE9 !important;
        color: var(--iso-text) !important;
        border: 1px solid var(--iso-border) !important;
        box-shadow: none !important;
    }
    .stButton > button[kind="secondary"] * {
        color: var(--iso-text) !important;
        fill: var(--iso-text) !important;
    }
    .stButton > button[kind="primary"] * {
        color: #F8F8F4 !important;
        fill: #F8F8F4 !important;
    }

    .stButton > button:hover {
        border-color: var(--iso-accent-hover);
        color: var(--iso-text);
    }

    .stButton > button:active {
        transform: translateY(1px) scale(0.985);
        background: #DDE4DD !important;
        border-color: var(--iso-accent-hover) !important;
        box-shadow: inset 0 2px 6px rgba(47, 49, 46, 0.18) !important;
        transition: transform 80ms ease, background 80ms ease, box-shadow 80ms ease;
    }

    .stButton > button[kind="primary"]:hover {
        background: var(--iso-accent-hover);
        color: #F8F8F4;
    }

    .stRadio > div,
    .stCheckbox > label,
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploaderDropzone"],
    [data-baseweb="tooltip"],
    [role="tooltip"],
    [data-testid="stPopover"] {
        background: var(--iso-surface) !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
    }

    .stRadio label,
    .stCheckbox label,
    [data-testid="stFileUploaderDropzone"] * {
        color: var(--iso-text) !important;
    }

    [data-testid="stRadio"] [role="radiogroup"] {
        gap: 0.45rem;
    }

    [data-testid="stRadio"] label {
        display: inline-flex !important;
        align-items: center !important;
        min-height: 40px;
        padding: 0.35rem 0.7rem;
        border: 1px solid var(--iso-border) !important;
        border-radius: 999px;
        background: #F0EFE9 !important;
        font-size: 0.92rem !important;
        line-height: 1.15 !important;
        white-space: nowrap;
    }

    [data-testid="stRadio"] label[data-selected="true"] {
        background: var(--iso-accent) !important;
        border-color: var(--iso-accent) !important;
    }

    [data-testid="stRadio"] label[data-selected="true"] p,
    [data-testid="stRadio"] label[data-selected="true"] span {
        color: #F8F8F4 !important;
    }

    [data-testid="stRadio"] input + div {
        background: transparent !important;
    }

    [data-testid="stRadio"] svg {
        fill: var(--iso-text) !important;
    }

    [data-testid="stSegmentedControl"] button {
        background: #F0EFE9 !important;
        color: var(--iso-text) !important;
        border: 1px solid var(--iso-border) !important;
        border-radius: 999px !important;
        min-height: 40px !important;
        box-shadow: none !important;
    }

    [data-testid="stSegmentedControl"],
    [data-testid="stSegmentedControl"] > div,
    [data-testid="stSegmentedControl"] [role="radiogroup"] {
        background: transparent !important;
        border: 0 !important;
    }

    [data-testid="stSegmentedControl"] button[aria-pressed="true"] {
        background: var(--iso-accent) !important;
        border-color: var(--iso-accent) !important;
        color: #F8F8F4 !important;
    }

    [data-testid="stSegmentedControl"] button[aria-pressed="true"] * {
        color: #F8F8F4 !important;
        fill: #F8F8F4 !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: #F0EFE9 !important;
        border: 1px dashed var(--iso-border) !important;
        border-radius: 12px !important;
    }

    [data-testid="stFileUploaderDropzoneInstructions"],
    [data-testid="stBaseButton-secondary"],
    [data-testid="stFileUploaderDropzone"] button,
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzone"] span {
        color: var(--iso-text) !important;
        background: #F7F6F2 !important;
        border-color: var(--iso-border) !important;
    }

    [data-baseweb="select"] > div,
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {
        background: #F7F6F2;
        color: var(--iso-text);
        border-color: var(--iso-border);
        min-height: 2.4rem !important;
        font-size: 0.95rem !important;
        line-height: 1.2 !important;
    }

    [data-baseweb="select"] {
        width: 100% !important;
        min-width: 100% !important;
    }

    [data-baseweb="select"] [data-baseweb="single-value"],
    [data-baseweb="select"] [data-baseweb="tag"],
    [data-baseweb="select"] span,
    [data-baseweb="select"] div {
        color: var(--iso-text) !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
    }

    [data-baseweb="select"] *,
    [data-baseweb="menu"] *,
    [role="option"] {
        font-size: 0.95rem !important;
        line-height: 1.25 !important;
        color: var(--iso-text) !important;
    }

    [data-baseweb="menu"],
    [data-baseweb="popover"] [role="listbox"] {
        background: #F7F6F2 !important;
        color: var(--iso-text) !important;
        border: 1px solid var(--iso-border) !important;
        width: auto !important;
        min-width: min(42rem, calc(100vw - 4rem)) !important;
        max-width: min(72rem, calc(100vw - 3rem)) !important;
        box-shadow: 0 12px 32px rgba(47, 49, 46, 0.16) !important;
    }

    [data-baseweb="menu"] [role="option"],
    [data-baseweb="menu"] li,
    [data-baseweb="menu"] div {
        background: #F7F6F2 !important;
        color: var(--iso-text) !important;
    }

    [data-baseweb="menu"] [role="option"],
    [data-baseweb="popover"] [role="option"] {
        width: 100% !important;
        min-height: 2.35rem !important;
        padding: 0.5rem 0.75rem !important;
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        align-items: center !important;
    }

    [data-baseweb="menu"] [role="option"] *,
    [data-baseweb="popover"] [role="option"] * {
        white-space: nowrap !important;
        overflow: visible !important;
        text-overflow: clip !important;
        max-width: none !important;
        color: var(--iso-text) !important;
    }

    [data-baseweb="menu"] [role="option"] svg,
    [data-baseweb="popover"] [role="option"] svg {
        fill: var(--iso-accent) !important;
        stroke: var(--iso-accent) !important;
        width: 0.9rem !important;
        height: 0.9rem !important;
    }

    [data-baseweb="menu"] [role="option"]:hover,
    [data-baseweb="menu"] [aria-selected="true"] {
        background: #E3E3DE !important;
        color: var(--iso-text) !important;
    }

    [data-baseweb="popover"],
    [data-testid="stPopover"] {
        background: #F7F6F2 !important;
        color: var(--iso-text) !important;
        border: 1px solid var(--iso-border) !important;
        box-shadow: 0 12px 32px rgba(47, 49, 46, 0.16) !important;
        max-width: min(42rem, calc(100vw - 3rem)) !important;
    }

    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="popover"] ul,
    [data-baseweb="popover"] li {
        background: #F7F6F2 !important;
        color: var(--iso-text) !important;
        font-size: 0.98rem !important;
        line-height: 1.3 !important;
        min-width: 18rem !important;
    }

    [data-baseweb="popover"] [role="option"]:hover,
    [data-baseweb="popover"] [aria-selected="true"] {
        background: #E3E3DE !important;
        color: var(--iso-text) !important;
    }

    [data-baseweb="tag"] {
        background: var(--iso-surface-2) !important;
        color: var(--iso-text) !important;
    }

    [data-testid="stCheckbox"] > label > div[data-testid="stCheckboxIndicator"] {
        background: #F0EFE9 !important;
        border-color: var(--iso-border) !important;
    }

    [data-testid="stCheckbox"] div[role="checkbox"] {
        background: #F7F6F2 !important;
        border: 1px solid var(--iso-border) !important;
        box-shadow: none !important;
    }

    [data-testid="stCheckbox"] div[role="checkbox"] *,
    [data-testid="stCheckbox"] > label > div[data-testid="stCheckboxIndicator"] * {
        background: transparent !important;
    }

    [data-testid="stCheckbox"] input:checked + div,
    [data-testid="stCheckbox"] div[role="checkbox"][aria-checked="true"] {
        background: var(--iso-accent) !important;
        border-color: var(--iso-accent) !important;
    }

    [data-testid="stCheckbox"] svg,
    [data-testid="stCheckbox"] svg path {
        fill: #F8F8F4 !important;
        stroke: #F8F8F4 !important;
    }

    [data-testid="stDataFrame"],
    [data-testid="stTable"] {
        background: var(--iso-surface);
        border-radius: 12px;
        border: 1px solid var(--iso-border);
    }

    [data-testid="stTable"] *,
    [data-testid="stDataEditor"] input,
    [data-testid="stDataEditor"] textarea,
    [data-testid="stDataEditor"] button {
        color: var(--iso-text) !important;
        background: var(--iso-surface) !important;
        border-color: var(--iso-border) !important;
    }

    [data-testid="stDataFrame"] {
        color: var(--iso-text) !important;
        background: var(--iso-surface) !important;
        border-color: var(--iso-border) !important;
    }

    [data-testid="stMetric"] {
        background: var(--iso-surface);
        border: 1px solid var(--iso-border);
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
    }

    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"],
    [data-testid="stMetricDelta"] {
        color: var(--iso-text) !important;
    }

    pre, code, .stCodeBlock, [data-testid="stCodeBlock"] {
        background: #F0EFE9 !important;
        color: var(--iso-text) !important;
        border: 1px solid var(--iso-border);
        border-radius: 10px;
    }

    [data-testid="stPopoverButton"] button,
    [data-testid="stTooltipHoverTarget"],
    [data-testid="stTooltipHoverTarget"] button {
        width: 1.15rem !important;
        min-width: 1.15rem !important;
        height: 1.15rem !important;
        min-height: 1.15rem !important;
        border-radius: 999px !important;
        padding: 0 !important;
        background: transparent !important;
        color: #2F6FED !important;
        border: 0 !important;
        box-shadow: none !important;
        font-size: 0.72rem !important;
        line-height: 1 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }

    [data-testid="stPopoverButton"] button *,
    [data-testid="stTooltipHoverTarget"] *,
    [data-testid="stTooltipHoverTarget"] svg,
    [data-testid="stTooltipHoverTarget"] svg path {
        color: #2F6FED !important;
        fill: #2F6FED !important;
        stroke: #2F6FED !important;
    }

    [data-testid="stPopoverButton"] button:hover,
    [data-testid="stTooltipHoverTarget"]:hover {
        background: transparent !important;
        border-color: transparent !important;
    }

    .iso-info-wrap {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        position: relative;
        min-width: 1.1rem;
        min-height: 1.1rem;
        z-index: 30;
    }

    .iso-info-details {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }

    .iso-info-details > summary {
        list-style: none;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.05rem;
        height: 1.05rem;
        margin: 0;
        padding: 0;
    }

    .iso-info-details > summary::-webkit-details-marker {
        display: none;
    }

    .iso-info-svg {
        width: 1.0rem;
        height: 1.0rem;
        display: block;
    }

    .iso-info-svg circle {
        fill: #2F6FED;
        stroke: #2F6FED;
    }

    .iso-info-svg text {
        fill: #FFFFFF;
        font-size: 12px;
        font-weight: 800;
        font-family: Georgia, serif;
    }

    .iso-info-panel {
        display: none;
        position: absolute;
        top: 1.45rem;
        right: 0;
        width: min(34rem, calc(100vw - 3rem));
        max-width: min(34rem, calc(100vw - 3rem));
        max-height: 34rem;
        overflow-y: auto;
        background: #F7F6F2;
        color: var(--iso-text);
        border: 1px solid var(--iso-border);
        border-radius: 12px;
        box-shadow: 0 16px 40px rgba(47, 49, 46, 0.22);
        padding: 0.8rem 0.95rem;
        text-align: left;
        z-index: 9999;
    }

    .iso-info-details[open] .iso-info-panel {
        display: block;
    }

    .iso-info-panel,
    .iso-info-panel * {
        background: #F7F6F2 !important;
        color: var(--iso-text) !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
    }

    .iso-info-panel p {
        margin: 0 0 0.55rem 0;
    }

    .iso-info-panel ul {
        margin: 0.25rem 0 0.55rem 1rem;
        padding: 0;
    }

    .iso-info-panel code {
        background: #ECECE8 !important;
        border: 1px solid #D7D4CA;
        border-radius: 5px;
        padding: 0.05rem 0.25rem;
    }

    [data-testid="stPopover"],
    [data-testid="stPopover"] > div,
    [data-testid="stPopover"] section,
    [data-testid="stPopover"] article {
        background: #F7F6F2 !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
    }

    [data-testid="stPopover"] *,
    [role="tooltip"] * {
        background: #F7F6F2 !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
        white-space: normal !important;
        overflow-wrap: anywhere !important;
    }

    [data-testid="stExpander"],
    [data-testid="stExpander"] details,
    [data-testid="stExpander"] summary,
    [data-testid="stExpander"] div {
        background: var(--iso-surface) !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
    }

    [data-testid="stPills"] [role="listbox"] {
        gap: 0.45rem !important;
    }

    [data-testid="stPills"] button,
    [data-testid="stPills"] [role="option"] {
        background: #F0EFE9 !important;
        color: var(--iso-text) !important;
        border: 1px solid var(--iso-border) !important;
        border-radius: 999px !important;
        min-height: 38px !important;
        box-shadow: none !important;
    }

    [data-testid="stPills"] *,
    [data-testid="stPills"] button *,
    [data-testid="stPills"] [role="option"] *,
    [data-testid="stPills"] span,
    [data-testid="stPills"] div,
    [data-testid="stPills"] p {
        color: var(--iso-text) !important;
        background: transparent !important;
        fill: var(--iso-text) !important;
    }

    [data-testid="stPills"] [data-baseweb="tag"],
    [data-testid="stPills"] [data-baseweb="tag"] * {
        background: #F0EFE9 !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
    }

    [data-testid="stPills"] button[aria-selected="true"] {
        background: var(--iso-accent) !important;
        color: #F8F8F4 !important;
        border-color: var(--iso-accent) !important;
    }

    [data-testid="stPills"] button[aria-selected="true"] * {
        color: #F8F8F4 !important;
        fill: #F8F8F4 !important;
    }

    [data-testid="stPills"] button[aria-selected="true"] span,
    [data-testid="stPills"] button[aria-selected="true"] div,
    [data-testid="stPills"] button[aria-selected="true"] p,
    [data-testid="stPills"] button[aria-selected="true"] [data-baseweb="tag"],
    [data-testid="stPills"] button[aria-selected="true"] [data-baseweb="tag"] * {
        background: transparent !important;
        color: #F8F8F4 !important;
        fill: #F8F8F4 !important;
    }

    .iso-source-card,
    .iso-panel {
        background: var(--iso-surface);
        border: 1px solid var(--iso-border);
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
        margin-bottom: 0.75rem;
    }

    .iso-panel-journey {
        background: #E7ECE6;
        border-color: #B9C8BC;
    }

    .iso-panel-step {
        background: #F3F1EB;
        border-color: #D6D1C4;
    }

    .iso-source-card strong,
    .iso-source-card p,
    .iso-panel strong,
    .iso-panel p,
    .iso-field-help {
        color: var(--iso-text) !important;
    }

    .iso-field-help {
        min-height: 2.6rem;
        font-size: 0.83rem;
        line-height: 1.2;
        opacity: 0.9;
        margin: 0.2rem 0 0.5rem 0;
    }

    .iso-step-title {
        font-size: 0.76rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        opacity: 0.7;
        margin-bottom: 0.35rem;
    }

    .iso-step-text {
        margin: 0;
        line-height: 1.35;
    }

    .iso-inline-note {
        margin: 0.2rem 0 0.7rem 0;
        color: var(--iso-text);
        opacity: 0.82;
        font-size: 0.92rem;
        line-height: 1.35;
    }

    .iso-db-summary {
        background: #F7F6F2;
        border: 1px solid var(--iso-border);
        border-radius: 12px;
        padding: 0.7rem 0.85rem;
        margin: 0.2rem 0 0.75rem 0;
    }

    .iso-db-summary strong,
    .iso-db-summary span,
    .iso-db-summary p {
        color: var(--iso-text) !important;
    }

    .iso-source-details-box {
        background: #F7F6F2;
        border: 1px solid var(--iso-border);
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
        margin: 0.4rem 0 0.85rem 0;
    }

    .iso-source-details-box p {
        margin: 0.2rem 0;
        color: var(--iso-text) !important;
        line-height: 1.35;
        overflow-wrap: anywhere;
    }

    .iso-step-inline {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        margin: 0.2rem 0 0.45rem 0;
    }

    .iso-step-chip {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 3.3rem;
        padding: 0.15rem 0.45rem;
        border-radius: 999px;
        background: #E7ECE6;
        border: 1px solid #B9C8BC;
        font-size: 0.72rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        color: var(--iso-text);
        white-space: nowrap;
    }

    .iso-step-label {
        font-weight: 600;
        color: var(--iso-text);
    }

    .iso-step-label-block {
        padding-top: 0.15rem;
    }

    .iso-scenario-leftpane,
    .iso-scenario-rightpane {
        max-height: calc(100vh - 8rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 0.35rem;
    }

    .iso-scenario-rightpane {
        position: sticky;
        top: 5.25rem;
        align-self: start;
    }

    .iso-scroll-pane {
        max-height: calc(100vh - 8rem);
        overflow-y: auto;
        overflow-x: hidden;
        padding-right: 0.45rem;
    }

    .iso-step-help {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.1rem;
        height: 1.1rem;
        border-radius: 999px;
        border: 1px solid #2F6FED;
        background: #2F6FED;
        color: #FFFFFF;
        font-size: 0.75rem;
        cursor: help;
    }

    .iso-loading-card {
        background: #F7F6F2;
        border: 1px solid var(--iso-border);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        margin: 0.75rem 0;
        box-shadow: 0 10px 24px rgba(47, 49, 46, 0.08);
    }

    .iso-loading-card strong,
    .iso-loading-card p,
    .iso-loading-card li {
        color: var(--iso-text) !important;
    }

    .iso-terminal {
        background: #202A25;
        color: #EAF4EE;
        border: 1px solid #395447;
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 0.9rem;
        line-height: 1.35;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.04);
        margin: 0.5rem 0 0.75rem 0;
    }

    .iso-terminal strong,
    .iso-terminal p,
    .iso-terminal span {
        color: #EAF4EE !important;
    }

    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }

    ::-webkit-scrollbar-track {
        background: #E8E6DE;
    }

    ::-webkit-scrollbar-thumb {
        background: #A6A69B;
        border-radius: 999px;
        border: 2px solid #E8E6DE;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #8D8D82;
    }

    textarea,
    [data-testid="stTextArea"] textarea,
    [data-testid="stDataFrame"] {
        scrollbar-color: #A6A69B #E8E6DE;
        scrollbar-width: auto;
    }

    [data-testid="stCheckbox"] label {
        background: transparent !important;
        border: 0 !important;
        padding: 0.1rem 0 !important;
    }

    [data-testid="stCheckbox"] > label > div[data-testid="stCheckboxIndicator"] svg,
    [data-testid="stCheckbox"] > label > div[data-testid="stCheckboxIndicator"] svg path {
        opacity: 0;
    }

    [data-testid="stCheckbox"] input:checked + div svg,
    [data-testid="stCheckbox"] input:checked + div svg path,
    [data-testid="stCheckbox"] div[role="checkbox"][aria-checked="true"] svg,
    [data-testid="stCheckbox"] div[role="checkbox"][aria-checked="true"] svg path {
        opacity: 1;
    }

    [data-testid="stNumberInput"] button,
    [data-testid="stNumberInput"] button svg,
    [data-testid="stNumberInputStepUp"],
    [data-testid="stNumberInputStepDown"] {
        background: #F0EFE9 !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
        fill: var(--iso-text) !important;
    }

    table, thead, tbody, tr, th, td {
        background: var(--iso-surface) !important;
        color: var(--iso-text) !important;
        border-color: var(--iso-border) !important;
    }

    .iso-flow {
        display: grid;
        gap: 0.5rem;
    }

    .iso-flow-step {
        background: var(--iso-surface);
        border: 1px solid var(--iso-border);
        border-radius: 12px;
        padding: 0.7rem 0.85rem;
    }

    .iso-flow-step strong,
    .iso-flow-step span {
        color: var(--iso-text);
    }

    .iso-flow-step.is-done {
        border-color: var(--iso-accent);
        background: #E8EEE9;
    }

    .iso-device-badge {
        position: fixed;
        top: 0.55rem;
        right: 5.25rem;
        z-index: 100000;
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        min-height: 1.85rem;
        padding: 0.25rem 0.65rem;
        border: 1px solid var(--iso-border);
        border-radius: 999px;
        background: rgba(240, 239, 233, 0.96);
        color: var(--iso-text);
        box-shadow: 0 2px 8px rgba(47, 49, 46, 0.10);
        font-size: 0.72rem;
        line-height: 1;
        white-space: nowrap;
    }

    .iso-device-badge strong {
        color: var(--iso-text);
        font-weight: 700;
        letter-spacing: 0;
    }

    .iso-device-badge.is-mps {
        border-color: #5C7C6F;
        background: rgba(232, 238, 233, 0.98);
    }

    .iso-device-badge.is-cpu {
        border-color: #A27A3F;
        background: rgba(247, 241, 229, 0.98);
    }

    h1, h2, h3 {
        color: var(--iso-text);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=30, show_spinner=False)
def _runtime_device_summary() -> dict[str, object]:
    try:
        return dict(resolve_torch_device("auto"))
    except Exception as exc:
        return {
            "requested_device": "auto",
            "resolved_device": "cpu",
            "mps_available": False,
            "fallback_reason": f"{type(exc).__name__}: {exc}",
        }


def _render_runtime_device_badge() -> None:
    summary = _runtime_device_summary()
    resolved = str(summary.get("resolved_device", "cpu")).upper()
    css_class = "is-mps" if resolved == "MPS" else "is-cpu"
    fallback = str(summary.get("fallback_reason") or "")
    title = f"requested=auto; mps_available={summary.get('mps_available')}"
    if fallback:
        title = f"{title}; fallback={fallback}"
    st.markdown(
        f'<div class="iso-device-badge {css_class}" title="{html.escape(title)}">Device <strong>{html.escape(resolved)}</strong></div>',
        unsafe_allow_html=True,
    )


_render_runtime_device_badge()


def _init_session_log() -> None:
    logs_root = _app_path("logs")
    logs_root.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_path = logs_root / f"session_{timestamp}.jsonl"
    st.session_state.session_log_path = log_path

    existing = sorted(logs_root.glob("session_*.jsonl"))
    if len(existing) > 5:
        for old in existing[:-5]:
            old.unlink(missing_ok=True)


def _default_backend_url() -> str:
    return default_backend_database_url(PROJECT_ROOT)


def _default_scenarios_db_url() -> str:
    return os.environ.get(
        "ISOMERA_SCENARIOS_DB_URL",
        "postgresql+psycopg://localhost:5432/isomera_tpcds_benchmark",
    )


def _default_publication_db_url() -> str:
    return os.environ.get("ISOMERA_PUBLICATION_DB_URL", "mysql+pymysql://root@localhost/isomera_publication")


def _psycopg_available() -> bool:
    return importlib.util.find_spec("psycopg") is not None


def _backend_label(database_url: str) -> str:
    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        return "SQLite"
    if parsed.scheme.startswith("postgresql"):
        return "PostgreSQL"
    if parsed.scheme.startswith("mysql"):
        return "MySQL"
    return parsed.scheme or "Database"


def _validate_database_url(database_url: str) -> str:
    cleaned = database_url.strip()
    if not cleaned:
        raise ValueError("Database URL is empty.")
    try:
        engine = create_database_engine(cleaned)
        engine.dispose()
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"Database driver missing: {exc.name}. Install requirements and run Isomera with `.venv`."
        ) from exc
    return cleaned


def _ensure_valid_database_url(
    *,
    db_url_key: str,
    input_key: str,
    default_value: str,
    warning_key: str,
) -> None:
    current_value = str(st.session_state.get(db_url_key, "") or "").strip()
    try:
        validated = _validate_database_url(current_value)
        st.session_state[db_url_key] = validated
        st.session_state[input_key] = st.session_state.get(input_key, validated) or validated
        st.session_state[warning_key] = None
    except Exception as exc:  # noqa: BLE001
        if "Database driver missing" in str(exc):
            fallback = current_value or default_value
            st.session_state[db_url_key] = fallback
            st.session_state[input_key] = fallback
            st.session_state[warning_key] = str(exc)
        else:
            st.session_state[db_url_key] = default_value
            st.session_state[input_key] = default_value
            st.session_state[warning_key] = (
                f"Invalid database URL ignored during bootstrap. Reverted to default. Details: {exc}"
            )


def _apply_database_url(
    *,
    db_url_key: str,
    input_key: str,
    status_key: str,
) -> None:
    candidate = str(st.session_state.get(input_key, "") or "")
    validated = _validate_database_url(candidate)
    st.session_state[db_url_key] = validated
    st.session_state[input_key] = validated
    st.session_state[status_key] = test_database_connection(validated)


def _init_backend_session() -> None:
    database_url = st.session_state.backend_db_url
    if st.session_state.backend_session_id is not None:
        touch_app_session(
            database_url,
            st.session_state.backend_session_id,
            log_path=str(st.session_state.session_log_path) if st.session_state.session_log_path else None,
            terminal_log_path=str(_TERMINAL_LOG_PATH) if _TERMINAL_LOG_PATH else None,
        )
        return
    init_backend_database(database_url)
    st.session_state.backend_session_id = create_app_session(
        database_url,
        log_path=str(st.session_state.session_log_path) if st.session_state.session_log_path else None,
        terminal_log_path=str(_TERMINAL_LOG_PATH) if _TERMINAL_LOG_PATH else None,
        metadata={"ui": "streamlit", "app": "isomera_v2"},
    )
    if st.session_state.session_log_path:
        register_artifact(
            database_url,
            artifact_type="session_log",
            path=str(st.session_state.session_log_path),
            session_id=st.session_state.backend_session_id,
        )
    if _TERMINAL_LOG_PATH:
        register_artifact(
            database_url,
            artifact_type="terminal_log",
            path=str(_TERMINAL_LOG_PATH),
            session_id=st.session_state.backend_session_id,
        )


def _persist_scenario_record(
    *,
    architecture_name: str,
    scenario_name: str,
    source: str,
    gml_path: Path | None = None,
    labels_path: Path | None = None,
    metadata: dict | None = None,
) -> str | None:
    if not st.session_state.backend_enabled:
        return None
    return upsert_scenario(
        st.session_state.backend_db_url,
        architecture_name=architecture_name,
        scenario_name=scenario_name,
        source=source,
        gml_path=str(gml_path) if gml_path else None,
        labels_path=str(labels_path) if labels_path else None,
        metadata=metadata,
    )


def _start_backend_run(
    run_type: str,
    *,
    algorithm: str | None = None,
    scenario_id: str | None = None,
    parameters: dict | None = None,
) -> str | None:
    if not st.session_state.backend_enabled or st.session_state.backend_session_id is None:
        return None
    return create_run(
        st.session_state.backend_db_url,
        session_id=st.session_state.backend_session_id,
        run_type=run_type,
        algorithm=algorithm,
        scenario_id=scenario_id,
        parameters=parameters,
    )


def _active_scenario_id() -> str | None:
    scenario_name = st.session_state.get("validation_scenario")
    architecture_name = st.session_state.get("validation_arch_name")
    if not scenario_name or not architecture_name:
        return None
    return f"{architecture_name}:{scenario_name}"


def _finish_backend_run(run_id: str | None, *, status: str, summary: dict | None = None) -> None:
    if not run_id or not st.session_state.backend_enabled:
        return
    finalize_run(st.session_state.backend_db_url, run_id=run_id, status=status, summary=summary)


def _record_backend_report(run_id: str | None, report_type: str, summary: dict | None = None) -> None:
    if not run_id or not st.session_state.backend_enabled:
        return
    create_report(st.session_state.backend_db_url, run_id=run_id, report_type=report_type, summary=summary)


def _render_sql_result(result: dict[str, object], *, key_prefix: str) -> None:
    if result["type"] == "rows":
        dataframe = result["dataframe"]
        st.success(f"{result['rowcount']} row(s) returned.")
        st.dataframe(dataframe, width="stretch", hide_index=True)
    else:
        st.success(result.get("message", "Statement executed successfully."))
        st.caption(f"Rows affected: {result.get('rowcount')}")


def _render_database_manager(
    *,
    title: str,
    description: str,
    db_url_key: str,
    sql_key: str,
    mutation_key: str,
    history_key: str,
    schema_key: str,
    table_key: str,
    input_key: str,
    preferred_schema_prefix: str | None = None,
) -> None:
    left_col, right_col = st.columns([1, 2], gap="large")
    database_url = st.session_state[db_url_key]
    result_key = f"{sql_key}_result"
    status_key = f"{db_url_key}_status"
    url_widget_key = f"{input_key}_widget"
    sql_widget_key = f"{sql_key}_widget"
    last_table_key = f"{table_key}_last"
    if url_widget_key not in st.session_state:
        st.session_state[url_widget_key] = st.session_state.get(input_key, database_url)
    if sql_widget_key not in st.session_state:
        st.session_state[sql_widget_key] = st.session_state.get(sql_key, "")
    with left_col:
        st.subheader(title)
        st.caption(description)
        st.markdown("**Current connection**")
        st.code(database_url)
        with st.expander("Custom connection"):
            st.text_input("Database URL", key=url_widget_key)
        action_cols = st.columns(3, gap="small")
        apply_clicked = action_cols[0].button("Use this connection", key=f"{db_url_key}_apply")
        test_clicked = action_cols[1].button("Test connection", key=f"{db_url_key}_test")
        refresh_clicked = action_cols[2].button("Reset view", key=f"{db_url_key}_refresh")
        if refresh_clicked:
            st.session_state[status_key] = None
        if apply_clicked:
            try:
                validated = _validate_database_url(st.session_state[url_widget_key])
                st.session_state[db_url_key] = validated
                st.session_state[input_key] = validated
                st.session_state[status_key] = test_database_connection(validated)
                st.success("Connection updated.")
            except Exception as exc:  # noqa: BLE001
                st.session_state[status_key] = {"error": str(exc)}
                st.error(str(exc))
        if test_clicked:
            try:
                st.session_state[status_key] = test_database_connection(
                    _validate_database_url(st.session_state[url_widget_key])
                )
                st.success("Connection OK.")
            except Exception as exc:  # noqa: BLE001
                st.session_state[status_key] = {"error": str(exc)}
                st.error(str(exc))

        status = st.session_state.get(status_key)
        if status:
            if "error" in status:
                st.warning(status["error"])
            else:
                status_rows = [
                    {"field": "dialect", "value": status["dialect"]},
                    {"field": "database", "value": status["database"]},
                    {"field": "user", "value": status["user"]},
                    {"field": "schemas", "value": status["schema_count"]},
                    {"field": "tables", "value": status["table_count"]},
                    {"field": "default_schema", "value": status["default_schema"]},
                ]
                st.table(pd.DataFrame(status_rows).set_index("field"))

        try:
            schemas = list_database_schemas(st.session_state[db_url_key])
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Explorer unavailable: {exc}")
            schemas = []
        if preferred_schema_prefix:
            preferred = [schema for schema in schemas if schema.startswith(preferred_schema_prefix)]
            other = [schema for schema in schemas if not schema.startswith(preferred_schema_prefix)]
            schemas = preferred + other
        if schemas:
            if st.session_state.get(schema_key) not in schemas:
                st.session_state[schema_key] = schemas[0]
            selected_schema = st.selectbox("Schema", options=schemas, key=schema_key)
            tables = list_schema_tables(st.session_state[db_url_key], selected_schema)
            if tables:
                st.caption(f"Tables in schema: {len(tables)}")
                if st.session_state.get(table_key) not in tables:
                    st.session_state[table_key] = tables[0]
                selected_table = st.selectbox(
                    "Tables",
                    options=tables,
                    key=table_key,
                )
                row_count = count_table_rows(st.session_state[db_url_key], selected_schema, selected_table)
                st.caption(f"Rows: {row_count}")
                default_query = f'SELECT * FROM "{selected_schema}"."{selected_table}" LIMIT 50;'
                if st.session_state.get(last_table_key) != selected_table or not st.session_state.get(sql_widget_key):
                    st.session_state[sql_widget_key] = default_query
                    st.session_state[last_table_key] = selected_table
                try:
                    column_df = list_table_columns(st.session_state[db_url_key], selected_schema, selected_table)
                    st.markdown("**Columns**")
                    st.table(column_df.set_index("column"))
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Column metadata unavailable: {exc}")
            else:
                selected_table = None
                st.info("No tables found in the selected schema.")
        else:
            selected_schema = None
            selected_table = None
            st.info("No schemas available.")

    with right_col:
        st.markdown("**SQL Workspace**")
        st.text_area(
            "SQL",
            key=sql_widget_key,
            height=220,
            help="Use one statement at a time. Read-only SQL is safest.",
        )
        st.checkbox(
            "Allow write SQL (DDL/DML)",
            value=st.session_state.get(mutation_key, False),
            key=mutation_key,
            help="Leave this unchecked unless you intentionally want CREATE, INSERT, UPDATE, or DELETE.",
        )
        run_cols = st.columns(2, gap="small")
        if run_cols[0].button("Run SQL", key=f"{sql_key}_run"):
            try:
                sql_text = st.session_state[sql_widget_key]
                st.session_state[sql_key] = sql_text
                result = run_sql_statement(
                    st.session_state[db_url_key],
                    sql_text,
                    allow_mutation=bool(st.session_state[mutation_key]),
                )
                history = st.session_state.setdefault(history_key, [])
                history.insert(
                    0,
                    {
                        "sql": sql_text,
                        "read_only": sql_statement_is_read_only(sql_text),
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
                st.session_state[history_key] = history[:20]
                st.session_state[result_key] = result
            except Exception as exc:  # noqa: BLE001
                st.session_state[result_key] = {"type": "error", "message": str(exc)}
        if run_cols[1].button("Clear SQL Result", key=f"{sql_key}_clear_result"):
            st.session_state[result_key] = None

        result = st.session_state.get(result_key)
        st.markdown("**Query Result**")
        if result:
            if result.get("type") == "error":
                st.error(result.get("message", "Unknown SQL error."))
            else:
                _render_sql_result(result, key_prefix=sql_key)
        else:
            st.info("Run a SQL statement to render results here.")

        st.markdown("**Table Preview**")
        if selected_schema and selected_table:
            try:
                preview_df = preview_table(st.session_state[db_url_key], selected_schema, selected_table, limit=10)
                st.dataframe(preview_df, width="stretch", hide_index=True)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
        else:
            st.info("Select a schema and table to preview.")
        st.markdown("**Recent SQL**")
        history = st.session_state.get(history_key, [])
        if history:
            st.table(pd.DataFrame(history[:10]))
        else:
            st.info("No SQL executed in this manager yet.")


def _apply_plotly_theme(fig) -> None:
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#F5F5F3",
        plot_bgcolor="#ECECE8",
        font_color="#2F312E",
        colorway=["#5C7C6F", "#8A9A86", "#A27A3F", "#7B8FA1", "#8A4D4D"],
        legend=dict(
            bgcolor="#F7F6F2",
            bordercolor="#C9C9C1",
            borderwidth=1,
            font=dict(color="#2F312E", size=12),
            title=dict(font=dict(color="#2F312E", size=12)),
        ),
    )
    fig.update_traces(textfont_color="#2F312E", selector=dict(type="bar"))
    fig.update_xaxes(gridcolor="#D8D6CE", linecolor="#C9C9C1", zerolinecolor="#D8D6CE")
    fig.update_yaxes(gridcolor="#D8D6CE", linecolor="#C9C9C1", zerolinecolor="#D8D6CE")


def _render_benchmark_flow(placeholder, steps) -> None:
    labels = [
        ("Scenario loading", "Load the graph set and validate available ground truth."),
        ("Detector execution", "Run each algorithm over the selected benchmark scenarios."),
        ("Review readiness", "Confirm generated pairs and benchmark artifacts are usable."),
        ("Metrics and export", "Publish ACC, ET, SF-Jaccard and timing summaries."),
    ]
    cards = []
    for (title, detail), ok in zip(labels, steps):
        status = "Done" if ok else "Pending"
        css_class = "iso-flow-step is-done" if ok else "iso-flow-step"
        cards.append(
            f"<div class='{css_class}'><strong>{title}</strong><br><span>{detail} [{status}]</span></div>"
        )
    placeholder.markdown(f"<div class='iso-flow'>{''.join(cards)}</div>", unsafe_allow_html=True)


def _ui_state_flags() -> dict[str, bool]:
    return {
        "step1_ready": st.session_state.initial_graph is not None,
        "step2_ready": bool(st.session_state.get("model_ran")),
        "step3_ready": bool(st.session_state.labeled_pairs),
        "step4_ready": st.session_state.metrics_df is not None,
    }


def _node_layer(node_name: str) -> str:
    upper = str(node_name).upper()
    if upper.startswith("SOR"):
        return "SOR"
    if upper.startswith("SOT"):
        return "SOT"
    if upper.startswith("SPEC"):
        return "SPEC"
    if "SOR" in upper:
        return "SOR"
    if "SOT" in upper:
        return "SOT"
    if "SPEC" in upper:
        return "SPEC"
    return "OTHER"


def _node_domain(node_name: str) -> str | None:
    match = re.search(r"_D(\d+)", str(node_name), re.IGNORECASE)
    if match:
        return match.group(1)
    alt = re.match(r"d(\d+)_", str(node_name), re.IGNORECASE)
    return alt.group(1) if alt else None


def _candidate_validation_pairs(
    graph: nx.DiGraph,
    *,
    include_sor: bool,
    include_sot: bool,
    include_spec: bool,
    same_layer_only: bool,
    same_domain_only: bool,
    same_indegree_only: bool,
    same_outdegree_only: bool,
    same_parent_signature_only: bool,
    same_child_signature_only: bool,
) -> list[tuple[str, str]]:
    allowed_layers = set()
    if include_sor:
        allowed_layers.add("SOR")
    if include_sot:
        allowed_layers.add("SOT")
    if include_spec:
        allowed_layers.add("SPEC")
    candidates = [node for node in graph.nodes if _node_layer(node) in allowed_layers]
    pairs: list[tuple[str, str]] = []
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            node_a = candidates[i]
            node_b = candidates[j]
            if same_layer_only and _node_layer(node_a) != _node_layer(node_b):
                continue
            if same_domain_only and _node_domain(node_a) != _node_domain(node_b):
                continue
            if same_indegree_only and graph.in_degree(node_a) != graph.in_degree(node_b):
                continue
            if same_outdegree_only and graph.out_degree(node_a) != graph.out_degree(node_b):
                continue
            if same_parent_signature_only:
                parent_sig_a = sorted(_node_layer(parent) for parent in graph.predecessors(node_a))
                parent_sig_b = sorted(_node_layer(parent) for parent in graph.predecessors(node_b))
                if parent_sig_a != parent_sig_b:
                    continue
            if same_child_signature_only:
                child_sig_a = sorted(_node_layer(child) for child in graph.successors(node_a))
                child_sig_b = sorted(_node_layer(child) for child in graph.successors(node_b))
                if child_sig_a != child_sig_b:
                    continue
            pairs.append(tuple(sorted((node_a, node_b))))
    return pairs


def _persist_curated_validation(
    *,
    benchmark_name: str,
    scenario_name: str,
    graph: nx.DiGraph,
    reviewed_pairs: dict[tuple[str, str], dict[str, object]],
    source_gml_path: Path | None,
) -> Path:
    target_root = _ensure_benchmark_structure(benchmark_name)
    gml_dir = target_root / "gml"
    real_pairs_dir = target_root / "real_pairs"
    validation_dir = target_root / "validations" / scenario_name
    gml_dir.mkdir(parents=True, exist_ok=True)
    real_pairs_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)

    target_gml = gml_dir / f"{scenario_name}.gml"
    if source_gml_path and source_gml_path.exists():
        shutil.copy2(source_gml_path, target_gml)
    else:
        save_graph_gml(graph, target_gml)

    duplicate_pairs = [
        [pair[0], pair[1]]
        for pair, payload in sorted(reviewed_pairs.items())
        if payload.get("decision") == "duplicate"
    ]
    progress_payload = {
        "scenario": scenario_name,
        "reviewed_pair_count": len(reviewed_pairs),
        "duplicate_pair_count": len(duplicate_pairs),
        "reviewed_pairs": {
            f"{pair[0]}|||{pair[1]}": payload for pair, payload in sorted(reviewed_pairs.items())
        },
    }
    (real_pairs_dir / f"{scenario_name}.json").write_text(json.dumps(duplicate_pairs, indent=2), encoding="utf-8")
    progress_path = validation_dir / "validation_progress.json"
    progress_path.write_text(json.dumps(progress_payload, indent=2), encoding="utf-8")
    _save_graph_image(graph, validation_dir / "graph_full.png", seed=42)
    return progress_path


def _article_capture_enabled() -> bool:
    return bool(st.session_state.get("article_capture_enabled", False))


def _article_capture_root() -> Path:
    root = _app_path("data/article_capture")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _graph_summary_for_article(graph: nx.DiGraph | None) -> dict[str, object]:
    if graph is None:
        return {}
    layer_counts = {
        "SOR": sum(1 for node in graph.nodes if _node_layer(node) == "SOR"),
        "SOT": sum(1 for node in graph.nodes if _node_layer(node) == "SOT"),
        "SPEC": sum(1 for node in graph.nodes if _node_layer(node) == "SPEC"),
        "OTHER": sum(1 for node in graph.nodes if _node_layer(node) == "OTHER"),
    }
    return {
        "node_count": int(graph.number_of_nodes()),
        "edge_count": int(graph.number_of_edges()),
        "layer_counts": layer_counts,
    }


def _graph_structure_table(graph: nx.DiGraph | None) -> list[dict[str, object]]:
    return graph_structure_rows(graph)


def _system_architecture_overview() -> dict[str, object]:
    return {
        "overview": (
            "Isomera v2 is organized as a layered analytical system with one interactive Streamlit workspace, "
            "a lineage ingestion and curation layer, a detector/training layer, and a persistence layer spanning "
            "relational stores, GML assets, and article-ready report artifacts."
        ),
        "layers": [
            {
                "layer": "Presentation Layer",
                "responsibility": "Interactive Streamlit modules such as Benchmark & Examples, Scenario Studio, Model Lab, Production Run, Research Reports, and Admin.",
                "paths": ["main/ui", "main/app"],
            },
            {
                "layer": "Scenario Ingestion Layer",
                "responsibility": "Load scenarios from PostgreSQL warehouse schemas, GML catalog assets, uploads, or manual graph editing.",
                "paths": ["main/core/database.py", "main/data/architectures", "main/data/tpcds_postgres"],
            },
            {
                "layer": "Scenario Materialization API",
                "responsibility": "Reusable API that turns one source scenario into the normalized graph, structured lineage table, adjacency matrix, and edge table consumed by the UI, reports, and training pipeline.",
                "paths": ["main/core/scenario_api.py"],
            },
            {
                "layer": "Lineage Graph Layer",
                "responsibility": "Reconstruct and persist directed lineage graphs, adjacency matrices, and edge views for review and benchmarking.",
                "paths": ["main/core/lineage.py"],
            },
            {
                "layer": "Matching and Training Layer",
                "responsibility": "Execute VF2, Node Match, and GNN-based detectors; train benchmark-specific pickle artifacts from curated labels.",
                "paths": ["main/core/isomorphism.py", "main/core/algorithms"],
            },
            {
                "layer": "Persistence and Reporting Layer",
                "responsibility": "Track runs, logs, reports, models, artifacts, curated labels, benchmark manifests, and article captures.",
                "paths": ["main/core/persistence.py", "main/data/backend", "main/data/article_capture"],
            },
        ],
        "stores": [
            {"store": "Scenario Warehouse", "technology": "PostgreSQL", "purpose": "Relational benchmark schemas and semantic warehouse contracts."},
            {"store": "Publication Backend", "technology": "MySQL", "purpose": "Published scenarios, reports, reviewed pairs, model artifacts, metadata, and future operational logs."},
            {"store": "Local Backend Fallback", "technology": "SQLite", "purpose": "Local development fallback for app metadata until all backend tables are migrated to MySQL."},
            {"store": "Scenario Materialization API", "technology": "Python API", "purpose": "Portable API that normalizes source scenarios into one canonical graph representation."},
            {"store": "Scenario Files", "technology": "GML/JSON", "purpose": "Portable lineage graphs, labels, benchmark manifests, and validation progress."},
            {"store": "Article Capture", "technology": "Markdown/JSON", "purpose": "Narrative-ready evidence for the paper and appendix."},
        ],
        "flow": [
            "User selects one scenario source.",
            "The Scenario Materialization API reconstructs the lineage graph from the warehouse contract or GML asset and normalizes the direction to SOR -> SOT -> SPEC.",
            "User filters candidate pairs and reviews duplicate decisions with autosave.",
            "Curated labels are persisted into benchmark assets and backend tables.",
            "The selected benchmark scenarios are used to train benchmark-specific GNN pickles.",
            "Runs, reports, artifacts, and article captures are exported for analysis and publication.",
        ],
    }


def _article_pipeline_rows(summary: dict[str, object], graph: nx.DiGraph | None, source_metadata: dict[str, object]) -> list[dict[str, object]]:
    graph_summary = _graph_summary_for_article(graph)
    validation_rows = list(summary.get("validation_dataset_rows") or []) if isinstance(summary, dict) else []
    training_summary = dict(summary.get("training_summary") or {}) if isinstance(summary, dict) else {}
    dataset_summary = list(training_summary.get("dataset_summary") or [])
    model_path = (
        summary.get("model_path")
        or training_summary.get("model_path")
        or summary.get("artifact_path")
        or ""
    )
    pipeline_rows = [
        {
            "stage": "source",
            "input": source_metadata.get("mode") or "Workspace graph",
            "output": source_metadata.get("schema") or source_metadata.get("scenario") or source_metadata.get("path") or "Graph source",
            "details": (
                f"database={source_metadata.get('database_name') or '-'} | "
                f"schema={source_metadata.get('schema') or '-'} | "
                f"manifest={source_metadata.get('manifest_used')}"
            ),
        },
        {
            "stage": "normalized_graph",
            "input": "Raw lineage source",
            "output": f"{graph_summary.get('node_count', 0)} nodes / {graph_summary.get('edge_count', 0)} edges",
            "details": (
                f"layers={json.dumps(graph_summary.get('layer_counts', {}), ensure_ascii=True)} | "
                f"build_mode={source_metadata.get('build_mode') or '-'}"
            ),
        },
        {
            "stage": "validation_dataset",
            "input": "Candidate pairs + manual review",
            "output": f"{len(validation_rows)} reviewed rows",
            "details": (
                f"candidate_pairs={summary.get('candidate_pairs', 0)} | "
                f"duplicate_pairs={summary.get('duplicate_pairs', 0)} | "
                f"filters={json.dumps(summary.get('filters', {}), ensure_ascii=True)}"
            ),
        },
    ]
    if dataset_summary or training_summary.get("train_size") or training_summary.get("val_size"):
        pipeline_rows.append(
            {
                "stage": "training_dataset",
                "input": "Normalized graph + validation labels",
                "output": f"train={training_summary.get('train_size', 0)} / val={training_summary.get('val_size', 0)}",
                "details": json.dumps(dataset_summary, ensure_ascii=True),
            }
        )
    if model_path:
        pipeline_rows.append(
            {
                "stage": "model_artifact",
                "input": summary.get("model_family_name") or "Benchmark model training",
                "output": Path(str(model_path)).name,
                "details": str(model_path),
            }
        )
    return pipeline_rows


def _article_capture_payload(report_type: str, summary: dict[str, object]) -> dict[str, object]:
    source_metadata = dict(st.session_state.get("scenario_source_metadata") or {})
    graph = st.session_state.get("initial_graph")
    publication_tables: dict[str, object] = {}
    model_docs = dict(summary.get("model_docs") or {}) if isinstance(summary.get("model_docs"), dict) else {}
    if isinstance(summary.get("filters"), dict):
        publication_tables["filters"] = [
            {"filter": key, "enabled": bool(value)}
            for key, value in dict(summary["filters"]).items()
        ]
    if isinstance(summary.get("hyperparameters"), dict):
        publication_tables["hyperparameters"] = [
            {"parameter": key, "value": value}
            for key, value in dict(summary["hyperparameters"]).items()
        ]
    if model_docs:
        publication_tables["formulas"] = [
            {"formula": formula}
            for formula in list(model_docs.get("formulas") or [])
        ]
        publication_tables["layers"] = [
            {"layer": layer}
            for layer in list(model_docs.get("layers") or [])
        ]
    if isinstance(summary.get("validation_dataset_rows"), list):
        publication_tables["validation_dataset"] = list(summary.get("validation_dataset_rows") or [])
    training_summary = dict(summary.get("training_summary") or {}) if isinstance(summary.get("training_summary"), dict) else {}
    if training_summary.get("dataset_summary"):
        publication_tables["training_dataset"] = list(training_summary.get("dataset_summary") or [])
    if training_summary or summary.get("model_path"):
        publication_tables["model_artifact"] = [
            {
                "model_family": summary.get("model_family_name"),
                "model_name": summary.get("model_name"),
                "artifact_path": summary.get("model_path") or training_summary.get("model_path"),
                "train_size": training_summary.get("train_size"),
                "val_size": training_summary.get("val_size"),
                "status": training_summary.get("status"),
            }
        ]
    if graph is not None:
        publication_tables["lineage_structure"] = _graph_structure_table(graph)
        publication_tables["lineage_edges"] = edge_dataframe(graph).to_dict(orient="records")
        publication_tables["adjacency_matrix"] = (
            adjacency_matrix_dataframe(graph).reset_index().rename(columns={"index": "node"}).to_dict(orient="records")
        )
        publication_tables["source_details"] = [
            {"field": key, "value": value}
            for key, value in source_metadata.items()
            if value is not None
            and key
            in {
                "mode",
                "database_name",
                "database_url",
                "schema",
                "build_mode",
                "manifest_used",
                "manifest_path",
                "table_count",
                "database_table_count",
                "graph_node_count",
                "table_to_graph_validation",
                "table_to_graph_validation_detail",
            }
        ]
    publication_tables["pipeline"] = _article_pipeline_rows(summary, graph, source_metadata)
    if isinstance(summary.get("publication_tables"), dict):
        for table_name, rows in dict(summary["publication_tables"]).items():
            publication_tables[str(table_name)] = rows

    formula_mapping = {}
    if isinstance(summary.get("resolved_hyperparameters"), dict):
        hp = dict(summary["resolved_hyperparameters"])
        formula_mapping = {
            "K (epochs used in optimization loop)": hp.get("epochs"),
            "hidden_channels / embedding dimension": hp.get("hidden_channels"),
            "dropout": hp.get("dropout"),
            "learning_rate": hp.get("learning_rate"),
            "negative_ratio": hp.get("negative_ratio"),
            "train_ratio": hp.get("train_ratio"),
            "test_ratio": hp.get("test_ratio"),
            "balance_strategy": hp.get("balance_strategy"),
            "seed": hp.get("seed"),
        }
    if isinstance(summary.get("formula_parameter_mapping"), dict):
        formula_mapping.update(dict(summary["formula_parameter_mapping"]))

    payload: dict[str, object] = {
        "report_type": report_type,
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "system_architecture": _system_architecture_overview(),
        "scenario_api": scenario_api_contract(),
        "storytelling": {
            "module": st.session_state.get("active_module"),
            "goal": "Trace every decision, parameter, source, and artifact used to build benchmark scenarios and train benchmark-specific models.",
            "source_mode": source_metadata.get("mode") or st.session_state.get("scenario_source_mode"),
            "graph_construction_method": (
                "Selected one relational schema in the Scenario Warehouse, inspected all tables and foreign keys in that schema, "
                "and converted each table into one graph node with directed edges following the FK lineage."
                if source_metadata.get("mode") == "Scenario Warehouse"
                else "Loaded a graph asset directly and moved it into the curation workspace."
            ),
            "graph_build_steps": list(source_metadata.get("graph_build_steps") or []),
        },
        "environment": {
            "python_executable": sys.executable,
            "project_root": str(PROJECT_ROOT),
            "backend_db_url": st.session_state.get("backend_db_url"),
            "scenarios_db_url": st.session_state.get("scenarios_db_url"),
            "session_id": st.session_state.get("backend_session_id"),
        },
        "source_metadata": source_metadata,
        "graph_summary": _graph_summary_for_article(graph),
        "publication_tables": publication_tables,
        "formula_parameter_mapping": formula_mapping,
        "summary": summary,
    }
    return payload


def _article_capture_markdown(payload: dict[str, object]) -> str:
    storytelling = payload.get("storytelling", {})
    environment = payload.get("environment", {})
    source_metadata = payload.get("source_metadata", {})
    graph_summary = payload.get("graph_summary", {})
    architecture = payload.get("system_architecture", {})
    scenario_api = payload.get("scenario_api", {})
    summary = payload.get("summary", {})
    publication_tables = payload.get("publication_tables", {})
    formula_mapping = payload.get("formula_parameter_mapping", {})
    graph_steps = storytelling.get("graph_build_steps") or []
    lines = [
        f"# Isomera Article Capture: {payload.get('report_type')}",
        "",
        f"- Captured at: {payload.get('captured_at')}",
        f"- Active module: {storytelling.get('module')}",
        f"- Python executable: `{environment.get('python_executable')}`",
        f"- Backend DB: `{environment.get('backend_db_url')}`",
        f"- Scenarios DB: `{environment.get('scenarios_db_url')}`",
        "",
        "## Storytelling",
        "",
        f"- Goal: {storytelling.get('goal')}",
        f"- Source mode: {storytelling.get('source_mode')}",
        f"- Graph construction method: {storytelling.get('graph_construction_method')}",
        "",
        "## Source Details",
        "",
    ]
    for key in (
        "mode",
        "database_url",
        "schema",
        "architecture",
        "scenario",
        "path",
        "table_count",
        "database_table_count",
        "graph_node_count",
        "table_to_graph_validation",
        "table_to_graph_validation_detail",
    ):
        value = source_metadata.get(key)
        if value:
            lines.append(f"- {key}: `{value}`")
    if graph_steps:
        lines.extend(["", "## Graph Build Steps", ""])
        for index, step in enumerate(graph_steps, start=1):
            lines.append(f"{index}. {step}")
    if graph_summary:
        lines.extend(
            [
                "",
                "## Graph Summary",
                "",
                f"- Node count: {graph_summary.get('node_count')}",
                f"- Edge count: {graph_summary.get('edge_count')}",
                f"- Layer counts: `{json.dumps(graph_summary.get('layer_counts', {}), ensure_ascii=True)}`",
            ]
        )
        lines.append("- Additional views saved for publication: structured lineage table and full edge table.")
    lines.extend(["", "## Methods for Paper", ""])
    lines.append(
        "The scenario was ingested into Isomera through the selected source path, transformed into a directed lineage graph, filtered into a candidate review queue, manually curated with autosave, and then published into a benchmark-specific catalog."
    )
    lines.append(
        "When the Scenario Warehouse path is used, Isomera connects to PostgreSQL, reads the selected benchmark schema, and reconstructs the lineage graph from the relational contract and warehouse metadata associated with that schema."
    )
    lines.append(
        "All operational metadata, intermediate decisions, and benchmark artifacts are persisted into the backend store and mirrored into article-ready Markdown/JSON captures for later reporting."
    )
    pipeline_rows = publication_tables.get("pipeline") or []
    if pipeline_rows:
        lines.extend(["", "## Pipeline for Paper", ""])
        lines.append("The validated Isomera pipeline for this capture is:")
        for row in pipeline_rows:
            lines.append(
                f"- **{row.get('stage')}**: input={row.get('input')} | output={row.get('output')} | details={row.get('details')}"
            )
    if architecture:
        lines.extend(["", "## Software Architecture", ""])
        lines.append(str(architecture.get("overview", "")))
        layers = architecture.get("layers") or []
        if layers:
            lines.extend(["", "### Architectural Layers", ""])
            for layer in layers:
                lines.append(
                    f"- **{layer.get('layer')}**: {layer.get('responsibility')} "
                    f"(paths: `{', '.join(layer.get('paths', []))}`)"
                )
        stores = architecture.get("stores") or []
        if stores:
            lines.extend(["", "### Data Stores", ""])
            for store in stores:
                lines.append(
                    f"- **{store.get('store')}** [{store.get('technology')}]: {store.get('purpose')}"
                )
        flow = architecture.get("flow") or []
        if flow:
            lines.extend(["", "### Execution Flow", ""])
            for index, step in enumerate(flow, start=1):
                lines.append(f"{index}. {step}")
    if scenario_api:
        lines.extend(["", "## Scenario Materialization API", ""])
        lines.append(str(scenario_api.get("purpose", "")))
        functions = scenario_api.get("functions") or []
        if functions:
            lines.extend(["", "### Public Functions", ""])
            for function in functions:
                lines.append(
                    f"- **{function.get('function')}**: input=`{function.get('input')}` -> output=`{function.get('output')}`"
                )
        guarantees = scenario_api.get("guarantees") or []
        if guarantees:
            lines.extend(["", "### Guarantees", ""])
            for guarantee in guarantees:
                lines.append(f"- {guarantee}")
        limits = scenario_api.get("limits") or []
        if limits:
            lines.extend(["", "### Limits", ""])
            for limit in limits:
                lines.append(f"- {limit}")
    if isinstance(summary, dict) and summary.get("hyperparameters"):
        lines.extend(["", "## Training Configuration", ""])
        lines.append(f"- Model family: {summary.get('model_family_name')}")
        lines.append(f"- Optimizer: {summary.get('optimizer')}")
        lines.append(f"- Loss: {summary.get('loss_name')}")
        for key, value in dict(summary.get("hyperparameters", {})).items():
            lines.append(f"- {key}: `{value}`")
    if isinstance(summary, dict) and summary.get("model_docs"):
        model_docs = dict(summary["model_docs"])
        lines.extend(
            [
                "",
                "## Model Notes",
                "",
                f"- Official name: {model_docs.get('official_name')}",
                f"- Version: {model_docs.get('version')}",
                "",
                str(model_docs.get("overview", "")),
                "",
                str(model_docs.get("theory", "")),
            ]
        )
        formulas = model_docs.get("formulas") or []
        if formulas:
            lines.extend(["", "### Formulas", ""])
            for formula in formulas:
                lines.append(f"- `{formula}`")
        layers = model_docs.get("layers") or []
        if layers:
            lines.extend(["", "### Layers", ""])
            for layer in layers:
                lines.append(f"- {layer}")
    if formula_mapping:
        lines.extend(["", "## Formula to Parameter Mapping", ""])
        for symbol, value in formula_mapping.items():
            lines.append(f"- {symbol}: `{value}`")
    if publication_tables:
        lines.extend(["", "## Publication Tables", ""])
        for table_name, rows in dict(publication_tables).items():
            lines.extend(["", f"### {table_name.title()}", ""])
            lines.append("```json")
            lines.append(json.dumps(rows, indent=2, ensure_ascii=True))
            lines.append("```")
    capture_paths = payload.get("capture_paths", {})
    if capture_paths:
        lines.extend(["", "## Generated Figures", ""])
        if capture_paths.get("lineage_png"):
            lines.append(f"- Lineage figure: `{capture_paths.get('lineage_png')}`")
        if capture_paths.get("adjacency_png"):
            lines.append(f"- Adjacency figure: `{capture_paths.get('adjacency_png')}`")
    lines.extend(
        [
            "",
            "## Structured Summary",
            "",
            "```json",
            json.dumps(summary, indent=2, ensure_ascii=True),
            "```",
        ]
    )
    return "\n".join(lines)


def _write_article_capture(report_type: str, summary: dict[str, object]) -> dict[str, object]:
    payload = _article_capture_payload(report_type, summary)
    benchmark_name = (
        str(summary.get("benchmark_name"))
        if isinstance(summary.get("benchmark_name"), str) and summary.get("benchmark_name")
        else "general"
    )
    scenario_name = (
        str(summary.get("scenario"))
        if isinstance(summary.get("scenario"), str) and summary.get("scenario")
        else str(st.session_state.get("workspace_scenario_name") or "workspace")
    )
    capture_dir = _article_capture_root() / _sanitize_benchmark_name(benchmark_name)
    capture_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"{stamp}_{_sanitize_benchmark_name(report_type)}_{_sanitize_benchmark_name(scenario_name)}"
    json_path = capture_dir / f"{base_name}.json"
    md_path = capture_dir / f"{base_name}.md"
    graph_png_path = capture_dir / f"{base_name}_lineage.png"
    adjacency_png_path = capture_dir / f"{base_name}_adjacency.png"
    graph = st.session_state.get("initial_graph")
    if isinstance(graph, nx.DiGraph):
        _save_graph_image(graph, graph_png_path, seed=st.session_state.get("layout_seed", 42))
        _save_adjacency_image(graph, adjacency_png_path)
    payload["capture_paths"] = {
        "json": str(json_path),
        "markdown": str(md_path),
        "lineage_png": str(graph_png_path),
        "adjacency_png": str(adjacency_png_path),
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    md_path.write_text(_article_capture_markdown(payload), encoding="utf-8")
    return payload


def _list_article_capture_entries(limit: int = 50) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for json_path in sorted(_article_capture_root().glob("*/*.json"), key=lambda path: path.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        capture_paths = payload.get("capture_paths", {})
        entries.append(
            {
                "captured_at": payload.get("captured_at"),
                "report_type": payload.get("report_type"),
                "benchmark_name": payload.get("summary", {}).get("benchmark_name"),
                "scenario": payload.get("summary", {}).get("scenario"),
                "json_path": str(json_path),
                "markdown_path": str(capture_paths.get("markdown", "")),
                "payload": payload,
            }
        )
        if len(entries) >= limit:
            break
    return entries


def _list_research_report_packages(limit: int = 30) -> list[dict[str, object]]:
    root = _app_path("data/research_reports")
    if not root.exists():
        return []
    packages: list[dict[str, object]] = []
    for package_dir in sorted([p for p in root.iterdir() if p.is_dir()], key=lambda path: path.name, reverse=True):
        manifest_path = package_dir / "package_manifest.json"
        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                manifest = {}
        tex_files = sorted(package_dir.glob("*.tex"))
        pdf_files = sorted(package_dir.glob("*.pdf"))
        md_files = (
            sorted(package_dir.glob("*.md"))
            or sorted((package_dir / "data").glob("*.md"))
        )
        zip_files = sorted(package_dir.glob("*.zip")) or sorted(package_dir.parent.glob(f"{package_dir.name}.zip"))
        packages.append(
            {
                "name": package_dir.name,
                "dir": str(package_dir),
                "manifest": manifest,
                "tex": str(tex_files[0]) if tex_files else "",
                "pdf": str(pdf_files[0]) if pdf_files else "",
                "markdown": str(md_files[0]) if md_files else "",
                "zip": str(zip_files[0]) if zip_files else "",
            }
        )
        if len(packages) >= limit:
            break
    return packages


def _generate_research_report_package(capture_json_path: str) -> tuple[bool, str]:
    script_path = _app_path("scripts/build_research_report_package.py")
    mpl_config_dir = _app_path("data/.mplconfig")
    mpl_config_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["MPLCONFIGDIR"] = str(mpl_config_dir)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("MPLBACKEND", "Agg")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), capture_json_path],
            cwd=str(PROJECT_ROOT.parent),
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        return False, f"Report package generation timed out after {exc.timeout} seconds."
    except Exception as exc:  # noqa: BLE001
        return False, f"Report package generation failed before execution: {exc}"
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
    if result.returncode != 0:
        return False, output or f"Report package generation failed with exit code {result.returncode}."
    try:
        package_payload = json.loads(result.stdout.strip())
        pdf_path = package_payload.get("pdf")
        if pdf_path:
            return True, f"Research package generated with PDF: {pdf_path}"
        return True, "Research package generated. PDF was not compiled; check the package manifest for compiler attempts."
    except Exception:
        return True, output or "Report package generated."


def _render_pdf_preview(pdf_path: Path, *, height: int = 720) -> None:
    if not pdf_path.exists():
        st.info("PDF preview unavailable for this package.")
        return
    pdf_b64 = base64.b64encode(pdf_path.read_bytes()).decode("ascii")
    components.html(
        f"""
        <iframe
            src="data:application/pdf;base64,{pdf_b64}"
            width="100%"
            height="{height}"
            style="border: 1px solid #d5d1c7; border-radius: 14px; background: #f7f5ef;"
        ></iframe>
        """,
        height=height + 24,
        scrolling=True,
    )


def _build_graph_from_warehouse_contract(database_url: str, schema_name: str) -> tuple[nx.DiGraph, dict[str, object]]:
    materialized = materialize_database_scenario(
        database_url,
        schema_name,
        manifests_root=_app_path("data/tpcds_postgres"),
    )
    metadata = dict(materialized.source_metadata)
    try:
        database_tables = list_schema_tables(database_url, schema_name)
    except Exception:
        database_tables = list(metadata.get("table_names") or [])
    database_table_count = len(database_tables)
    graph_node_count = int(materialized.graph.number_of_nodes())
    metadata["database_table_count"] = database_table_count
    metadata["graph_node_count"] = graph_node_count
    metadata["table_to_graph_validation"] = "pass" if database_table_count == graph_node_count else "mismatch"
    metadata["table_to_graph_validation_detail"] = (
        f"{database_table_count} warehouse tables -> {graph_node_count} graph vertices"
    )
    steps = list(metadata.get("graph_build_steps") or [])
    steps.append(
        "Validated materialization sanity check: "
        f"{database_table_count} tables in information_schema versus {graph_node_count} graph vertices."
    )
    metadata["graph_build_steps"] = steps
    return materialized.graph, metadata


def _benchmark_algorithm_variants(benchmark_arch: str) -> list[dict[str, object]]:
    variants: list[dict[str, object]] = [
        {"label": "VF2", "kind": "builtin", "algorithm": "VF2"},
        {"label": "Node Match (Custom)", "kind": "builtin", "algorithm": "Node Match (Custom)"},
    ]
    for cluster in _benchmark_model_clusters(benchmark_arch):
        family = str(cluster["family"])
        variants.append(
            {
                "label": family,
                "kind": "routed_gnn_cluster",
                "algorithm": "GIN/GNN (Pickle)",
                "routes": cluster.get("routes", {}),
                "candidate_paths": cluster.get("candidate_paths", []),
                "candidate_modules": cluster.get("candidate_modules", {}),
                "pickle_modules": cluster.get("pickle_modules", {}),
                "route_sources": cluster.get("route_sources", {}),
                "route_modes": cluster.get("route_modes", {}),
                "route_policy": cluster.get("route_policy"),
                "selection_metric": cluster.get("selection_metric") or "sf_jaccard",
                "source": cluster.get("source"),
                "coverage": f"{cluster.get('covered', 0)}/{cluster.get('total', 0)}",
                "coverage_status": cluster.get("status"),
            }
        )
    return variants


def _record_article_report(report_type: str, summary: dict[str, object]) -> None:
    if not _article_capture_enabled():
        return
    enriched = _write_article_capture(report_type, summary)
    st.session_state.last_article_capture = enriched
    if not st.session_state.get("backend_enabled"):
        return
    run_id = _start_backend_run(report_type, scenario_id=_active_scenario_id(), parameters=enriched)
    if run_id:
        _record_backend_report(run_id, report_type, enriched)
        capture_paths = enriched.get("capture_paths", {})
        if isinstance(capture_paths, dict):
            for artifact_type, artifact_path in (
                ("article_capture_json", capture_paths.get("json")),
                ("article_capture_markdown", capture_paths.get("markdown")),
            ):
                if artifact_path:
                    register_artifact(
                        st.session_state.backend_db_url,
                        artifact_type=artifact_type,
                        path=str(artifact_path),
                        session_id=st.session_state.backend_session_id,
                        run_id=run_id,
                        scenario_id=_active_scenario_id(),
                        metadata={"report_type": report_type},
                    )
        _finish_backend_run(run_id, status="completed", summary=enriched)


def _apply_scenario_review_decision(
    *,
    decision: str,
    benchmark_name: str,
    scenario_name: str,
    node_a: str,
    node_b: str,
    source: str = "manual",
    metadata: dict[str, object] | None = None,
    rerun: bool = True,
) -> None:
    reviewed_at = time.strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.scenario_review_status[(node_a, node_b)] = {
        "decision": decision,
        "timestamp": reviewed_at,
        "source": source,
        "metadata": dict(metadata or {}),
    }
    if decision == "duplicate":
        st.session_state.labeled_pairs.add(tuple(sorted((node_a, node_b))))
    else:
        st.session_state.labeled_pairs.discard(tuple(sorted((node_a, node_b))))
    benchmark_arch = _sanitize_benchmark_name(benchmark_name)
    progress_path = _persist_curated_validation(
        benchmark_name=benchmark_arch,
        scenario_name=scenario_name,
        graph=st.session_state.initial_graph,
        reviewed_pairs=st.session_state.scenario_review_status,
        source_gml_path=Path(st.session_state.scenario_validation_source_gml)
        if st.session_state.scenario_validation_source_gml
        else None,
    )
    try:
        upsert_scenario_validation_pair(
            st.session_state.scenarios_db_url,
            scenario_name=scenario_name,
            node_a=node_a,
            node_b=node_b,
            decision=decision,
            reviewed_at=reviewed_at,
            source_gml_path=st.session_state.scenario_validation_source_gml,
        )
    except Exception as exc:  # noqa: BLE001
        _log_event("scenario_validation_pair_store_error", {"error": str(exc)})
    if st.session_state.scenario_review_index < len(st.session_state.scenario_review_pairs) - 1:
        st.session_state.scenario_review_index += 1
    decision_label = "duplicate" if decision == "duplicate" else "non-duplicate"
    st.session_state.scenario_curation_message = f"Saved {decision_label} pair and autosaved progress at {progress_path}"
    if rerun:
        st.rerun()


def _finalize_curated_scenario(
    *,
    benchmark_name: str,
    scenario_name: str,
    total_pairs: int,
    active_pairs: list[tuple[str, str]],
    publish_as_benchmark: bool,
    filters: dict[str, object],
) -> None:
    benchmark_arch = _sanitize_benchmark_name(benchmark_name)
    progress_path = _persist_curated_validation(
        benchmark_name=benchmark_arch,
        scenario_name=scenario_name,
        graph=st.session_state.initial_graph,
        reviewed_pairs=st.session_state.scenario_review_status,
        source_gml_path=Path(st.session_state.scenario_validation_source_gml)
        if st.session_state.scenario_validation_source_gml
        else None,
    )
    if publish_as_benchmark:
        _ensure_benchmark_structure(benchmark_arch)
    target_root = _benchmark_root(benchmark_arch)
    target_gml = target_root / "gml" / f"{scenario_name}.gml"
    target_pairs = target_root / "real_pairs" / f"{scenario_name}.json"
    _register_benchmark_scenario(
        benchmark_name=benchmark_arch,
        scenario_name=scenario_name,
        gml_path=target_gml,
        labels_path=target_pairs,
        source_path=Path(st.session_state.scenario_validation_source_gml)
        if st.session_state.scenario_validation_source_gml
        else None,
        total_pairs=total_pairs,
        candidate_pairs=len(active_pairs),
        reviewed_pairs=len(st.session_state.scenario_review_status),
        duplicate_pairs=len(st.session_state.labeled_pairs),
    )
    scenario_id = _persist_scenario_record(
        architecture_name=benchmark_arch,
        scenario_name=scenario_name,
        source="scenario_studio_validation",
        gml_path=target_gml,
        labels_path=target_pairs,
        metadata={
            "reviewed_pair_count": len(st.session_state.scenario_review_status),
            "candidate_pair_count": len(active_pairs),
            "total_pair_count": total_pairs,
            "published_to_benchmark": publish_as_benchmark,
            "benchmark_name": benchmark_arch,
        },
    )
    if scenario_id and st.session_state.backend_enabled:
        create_label_version(
            st.session_state.backend_db_url,
            scenario_id=scenario_id,
            labels=sorted(st.session_state.labeled_pairs),
            metadata={"source": "scenario_studio_finalize"},
        )
        register_artifact(
            st.session_state.backend_db_url,
            artifact_type="scenario_validation_progress",
            path=str(progress_path),
            session_id=st.session_state.backend_session_id,
            scenario_id=scenario_id,
            metadata={"reviewed_pair_count": len(st.session_state.scenario_review_status)},
        )
    validation_dataset_rows = []
    for index, ((node_a, node_b), payload) in enumerate(sorted(st.session_state.scenario_review_status.items()), start=1):
        decision = str(payload.get("decision", ""))
        validation_dataset_rows.append(
            {
                "pair_index": index,
                "node_a": node_a,
                "node_b": node_b,
                "layer_a": _node_layer(node_a),
                "layer_b": _node_layer(node_b),
                "domain_a": _node_domain(node_a),
                "domain_b": _node_domain(node_b),
                "decision": decision,
                "target": 1 if decision == "duplicate" else 0,
                "reviewed_at": payload.get("timestamp"),
                "review_source": payload.get("source", "manual"),
                "review_model": dict(payload.get("metadata") or {}).get("model", ""),
                "review_confidence": dict(payload.get("metadata") or {}).get("confidence", ""),
            }
        )
    publication_summary = {
        "scenario": scenario_name,
        "benchmark_name": benchmark_arch,
        "total_pairs": total_pairs,
        "candidate_pairs": len(active_pairs),
        "reviewed_pairs": len(st.session_state.scenario_review_status),
        "duplicate_pairs": len(st.session_state.labeled_pairs),
        "published_to_benchmark": publish_as_benchmark,
        "filters": filters,
        "validation_dataset_rows": validation_dataset_rows,
    }
    publication_db_url = str(st.session_state.get("publication_db_url") or "").strip()
    if publish_as_benchmark and publication_db_url:
        try:
            publish_curated_scenario(
                publication_db_url,
                benchmark_name=benchmark_arch,
                scenario_name=scenario_name,
                graph=st.session_state.initial_graph,
                source_metadata=dict(st.session_state.get("scenario_source_metadata") or {}),
                gml_path=str(target_gml),
                labels_path=str(target_pairs),
                reviewed_pairs=dict(st.session_state.scenario_review_status),
                filters=filters,
                summary=publication_summary,
            )
        except Exception as exc:  # noqa: BLE001
            _log_event("publication_store_error", {"error": str(exc), "database_url": publication_db_url})
    _record_article_report(
        "scenario_curation",
        publication_summary,
    )
    st.session_state.scenario_finalized_summary = publication_summary
    st.session_state.scenario_curation_message = (
        f"Curated scenario `{scenario_name}` saved. "
        f"Benchmark publication: {'yes' if publish_as_benchmark else 'no'}."
    )
    st.session_state.benchmark_catalog_name = benchmark_arch
    st.rerun()


def _log_event(event: str, payload: dict | None = None) -> None:
    if st.session_state.session_log_path is None:
        return
    record = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "payload": payload or {},
    }
    st.session_state.session_log_path.parent.mkdir(parents=True, exist_ok=True)
    with st.session_state.session_log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")
    if st.session_state.get("backend_enabled") and st.session_state.get("backend_session_id"):
        try:
            record_log_event(
                st.session_state.backend_db_url,
                session_id=st.session_state.backend_session_id,
                event=event,
                payload=payload,
                run_id=st.session_state.get("backend_active_run_id"),
            )
        except Exception:
            pass


def _request_safe_shutdown() -> Path:
    """Ask the macOS launcher to stop Streamlit and any local databases it started."""
    SHUTDOWN_REQUEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    training_job = st.session_state.get("training_job")
    if training_job:
        if training_job.get("stop_flag_path"):
            Path(str(training_job["stop_flag_path"])).write_text("stop", encoding="utf-8")
        if training_job.get("pid"):
            try:
                os.kill(int(training_job["pid"]), signal.SIGTERM)
            except OSError:
                pass
    st.session_state.cancel_benchmark = True
    st.session_state.benchmark_stopped = True
    st.session_state.cancel_exec = True
    payload = {
        "requested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "pid": os.getpid(),
        "active_module": st.session_state.get("active_module"),
        "session_log_path": str(st.session_state.get("session_log_path") or ""),
        "terminal_log_path": str(_TERMINAL_LOG_PATH or ""),
        "training_job": {
            "model_name": training_job.get("model_name"),
            "pid": training_job.get("pid"),
        }
        if training_job
        else None,
        "message": "Stop requested from Streamlit sidebar. Launcher should terminate Streamlit and managed local databases.",
    }
    SHUTDOWN_REQUEST_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _log_event("safe_shutdown_requested", payload)
    return SHUTDOWN_REQUEST_PATH


def _log_action(
    action: str,
    context: str,
    params: dict | None = None,
    dataframes: list[str] | None = None,
) -> None:
    payload = {
        "context": context,
        "params": params or {},
        "dataframes": dataframes or [],
    }
    _log_event(action, payload)


def _log_exception(context: str, exc: Exception) -> None:
    message = f"{type(exc).__name__}: {exc}"
    trace = traceback.format_exc()
    payload = {"context": context, "error": message, "traceback": trace}
    _log_event("error", payload)
    st.session_state.last_error = f"{message}\n\n{trace}"


def _check_optional_deps() -> None:
    required_map = {
        "matplotlib": "matplotlib",
        "networkx": "networkx",
        "numpy": "numpy",
        "tabulate": "tabulate",
        "scipy": "scipy",
        "pandas": "pandas",
        "plotly": "plotly",
        "kaleido": "kaleido",
        "sqlalchemy": "sqlalchemy",
    }
    optional_map = {
        "torch": "torch",
        "torch-geometric": "torch_geometric",
    }
    missing_required = [
        pkg for pkg, mod in required_map.items() if importlib.util.find_spec(mod) is None
    ]
    missing_optional = [
        pkg for pkg, mod in optional_map.items() if importlib.util.find_spec(mod) is None
    ]
    if missing_required:
        st.error(
            "Required dependencies not found: "
            + ", ".join(missing_required)
            + "."
        )
        if st.button("Install required dependencies", key="install_required"):
            cmd = [sys.executable, "-m", "pip", "install", *missing_required]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                st.success("Dependencies installed. Restart the app.")
                _log_event("install_required_deps", {"deps": missing_required})
            else:
                st.error("Failed to install dependencies.")
                st.code(result.stderr or result.stdout)
    if missing_optional:
        st.warning(
            "Optional dependencies not found: "
            + ", ".join(missing_optional)
            + ". The GIN/GNN benchmark requires these libraries."
        )
        if st.button("Install optional dependencies", key="install_optional"):
            cmd = [sys.executable, "-m", "pip", "install", *missing_optional]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                st.success("Dependencies installed. Restart the app.")
                _log_event("install_optional_deps", {"deps": missing_optional})
            else:
                st.error("Failed to install dependencies.")
                st.code(result.stderr or result.stdout)


def _reset_session_state() -> None:
    training_job = st.session_state.get("training_job")
    if training_job:
        if training_job.get("stop_flag_path"):
            try:
                Path(str(training_job["stop_flag_path"])).write_text("stop", encoding="utf-8")
            except OSError:
                pass
        if training_job.get("pid"):
            try:
                os.kill(int(training_job["pid"]), signal.SIGTERM)
            except OSError:
                pass
    st.session_state.cancel_benchmark = True
    st.session_state.cancel_exec = True
    st.session_state.graph = None
    st.session_state.initial_graph = None
    st.session_state.isomorphic_pairs = []
    st.session_state.removed_nodes = []
    st.session_state.labeled_pairs = set()
    st.session_state.ground_truth_complete = False
    st.session_state.metrics_df = None
    st.session_state.exec_times = None
    st.session_state.exec_times_stats = None
    st.session_state.benchmark_exec_stats = None
    st.session_state.layout_seed = 42
    st.session_state.all_pairs = None
    st.session_state.benchmark_results = None
    st.session_state.validation_scenario = None
    st.session_state.validation_labels = {}
    st.session_state.validation_arch_name = DEFAULT_ARCH_NAME
    st.session_state.manual_nodes_df = pd.DataFrame(columns=["node", "type"])
    st.session_state.manual_edges_df = pd.DataFrame(columns=["from", "to"])
    st.session_state.gnn_pickle_path = None
    st.session_state.graph_source = "Random"
    st.session_state.label_mode = "CSV"
    st.session_state.model_ran = False
    st.session_state.show_logs = False
    st.session_state.benchmark_plot_logged = False
    st.session_state.graph_loading = False
    st.session_state.graph_loading_reset = False
    st.session_state.benchmark_step1 = False
    st.session_state.benchmark_step2 = False
    st.session_state.benchmark_step3 = False
    st.session_state.benchmark_step4 = False
    st.session_state.benchmark_params = None
    st.session_state.benchmark_stopped = False
    st.session_state.active_log = None
    st.session_state.active_terminal_log = None
    st.session_state.show_benchmark_images = False
    st.session_state.show_benchmark_matrix = False
    st.session_state.show_real_pairs = False
    st.session_state.benchmark_white_bg = False
    st.session_state.show_manual_builder = False
    st.session_state.training_job = None


if "session_log_path" not in st.session_state:
    st.session_state.session_log_path = None
if "backend_db_url" not in st.session_state:
    st.session_state.backend_db_url = _default_backend_url()
if "backend_db_url_input" not in st.session_state:
    st.session_state.backend_db_url_input = st.session_state.backend_db_url
if "backend_enabled" not in st.session_state:
    st.session_state.backend_enabled = True
if "backend_session_id" not in st.session_state:
    st.session_state.backend_session_id = None
if "backend_session_started" not in st.session_state:
    st.session_state.backend_session_started = False
if "backend_active_run_id" not in st.session_state:
    st.session_state.backend_active_run_id = None
if "model_registry_synced" not in st.session_state:
    st.session_state.model_registry_synced = set()
if "scenarios_db_url" not in st.session_state:
    st.session_state.scenarios_db_url = _default_scenarios_db_url()
if "scenarios_db_url_input" not in st.session_state:
    st.session_state.scenarios_db_url_input = st.session_state.scenarios_db_url
if "backend_bootstrap_warning" not in st.session_state:
    st.session_state.backend_bootstrap_warning = None
if "scenarios_bootstrap_warning" not in st.session_state:
    st.session_state.scenarios_bootstrap_warning = None
if "backend_sql_text" not in st.session_state:
    st.session_state.backend_sql_text = "SELECT * FROM logs LIMIT 20;"
if "scenarios_sql_text" not in st.session_state:
    st.session_state.scenarios_sql_text = "SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;"
if "backend_allow_mutation" not in st.session_state:
    st.session_state.backend_allow_mutation = False
if "scenarios_allow_mutation" not in st.session_state:
    st.session_state.scenarios_allow_mutation = False
if "backend_sql_history" not in st.session_state:
    st.session_state.backend_sql_history = []
if "scenarios_sql_history" not in st.session_state:
    st.session_state.scenarios_sql_history = []
if "backend_selected_schema" not in st.session_state:
    st.session_state.backend_selected_schema = None
if "backend_selected_table" not in st.session_state:
    st.session_state.backend_selected_table = None
if "scenarios_selected_schema" not in st.session_state:
    st.session_state.scenarios_selected_schema = None
if "scenarios_selected_table" not in st.session_state:
    st.session_state.scenarios_selected_table = None
if "scenario_review_pairs" not in st.session_state:
    st.session_state.scenario_review_pairs = []
if "scenario_review_index" not in st.session_state:
    st.session_state.scenario_review_index = 0
if "scenario_review_status" not in st.session_state:
    st.session_state.scenario_review_status = {}
if "scenario_validation_source_gml" not in st.session_state:
    st.session_state.scenario_validation_source_gml = None
if "scenario_source_metadata" not in st.session_state:
    st.session_state.scenario_source_metadata = {}
if "workspace_scenario_name" not in st.session_state:
    st.session_state.workspace_scenario_name = None
if "article_capture_enabled" not in st.session_state:
    st.session_state.article_capture_enabled = False
if "benchmark_catalog_name" not in st.session_state:
    st.session_state.benchmark_catalog_name = "TPC-DS"
if "scenario_curation_message" not in st.session_state:
    st.session_state.scenario_curation_message = None
if "scenario_finalized_summary" not in st.session_state:
    st.session_state.scenario_finalized_summary = None
if "last_article_capture" not in st.session_state:
    st.session_state.last_article_capture = None
if "show_manual_builder" not in st.session_state:
    st.session_state.show_manual_builder = False
if "scenario_source_mode" not in st.session_state:
    st.session_state.scenario_source_mode = "Scenario Warehouse"
elif st.session_state.scenario_source_mode == "Upload GML":
    st.session_state.scenario_source_mode = "GML Catalog"
if "studio_database_engine" not in st.session_state:
    st.session_state.studio_database_engine = "PostgreSQL"
if "studio_database_name" not in st.session_state:
    parsed_default_db = urlparse(_default_scenarios_db_url()).path.lstrip("/")
    st.session_state.studio_database_name = parsed_default_db or "isomera_tpcds_benchmark"
if "training_job" not in st.session_state:
    st.session_state.training_job = None
if "publication_db_url" not in st.session_state:
    st.session_state.publication_db_url = _default_publication_db_url()

_ensure_valid_database_url(
    db_url_key="backend_db_url",
    input_key="backend_db_url_input",
    default_value=_default_backend_url(),
    warning_key="backend_bootstrap_warning",
)
_ensure_valid_database_url(
    db_url_key="scenarios_db_url",
    input_key="scenarios_db_url_input",
    default_value=_default_scenarios_db_url(),
    warning_key="scenarios_bootstrap_warning",
)

if st.session_state.session_log_path is None:
    _init_session_log()
if st.session_state.backend_enabled:
    try:
        _init_backend_session()
    except Exception as exc:  # noqa: BLE001
        st.session_state.backend_bootstrap_warning = (
            f"Backend bootstrap failed and relational persistence was disabled for this session. Details: {exc}"
        )
        st.session_state.backend_enabled = False
if not st.session_state.backend_session_started:
    _log_event("session_start")
    st.session_state.backend_session_started = True

if "graph" not in st.session_state:
    st.session_state.graph = None
if "initial_graph" not in st.session_state:
    st.session_state.initial_graph = None
if "isomorphic_pairs" not in st.session_state:
    st.session_state.isomorphic_pairs = []
if "removed_nodes" not in st.session_state:
    st.session_state.removed_nodes = []
if "labeled_pairs" not in st.session_state:
    st.session_state.labeled_pairs = set()
if "ground_truth_complete" not in st.session_state:
    st.session_state.ground_truth_complete = False
if "metrics_df" not in st.session_state:
    st.session_state.metrics_df = None
if "exec_times" not in st.session_state:
    st.session_state.exec_times = None
if "exec_times_stats" not in st.session_state:
    st.session_state.exec_times_stats = None
if "benchmark_exec_stats" not in st.session_state:
    st.session_state.benchmark_exec_stats = None
if "layout_seed" not in st.session_state:
    st.session_state.layout_seed = 42
if "all_pairs" not in st.session_state:
    st.session_state.all_pairs = None
if "benchmark_results" not in st.session_state:
    st.session_state.benchmark_results = None
if "benchmark_best_of_selection_results" not in st.session_state:
    st.session_state.benchmark_best_of_selection_results = None
if "validation_scenario" not in st.session_state:
    st.session_state.validation_scenario = None
if "validation_labels" not in st.session_state:
    st.session_state.validation_labels = {}
if "validation_arch_name" not in st.session_state:
    st.session_state.validation_arch_name = DEFAULT_ARCH_NAME
if "manual_nodes_df" not in st.session_state:
    st.session_state.manual_nodes_df = pd.DataFrame(columns=["node", "type"])
if "manual_edges_df" not in st.session_state:
    st.session_state.manual_edges_df = pd.DataFrame(columns=["from", "to"])
if "gnn_pickle_path" not in st.session_state:
    st.session_state.gnn_pickle_path = None
if "graph_source" not in st.session_state:
    st.session_state.graph_source = "Random"
if "label_mode" not in st.session_state:
    st.session_state.label_mode = "CSV"
if "model_ran" not in st.session_state:
    st.session_state.model_ran = False
if "show_logs" not in st.session_state:
    st.session_state.show_logs = False
if "last_error" not in st.session_state:
    st.session_state.last_error = None
if "cancel_benchmark" not in st.session_state:
    st.session_state.cancel_benchmark = False
if "cancel_exec" not in st.session_state:
    st.session_state.cancel_exec = False
if "running_benchmark" not in st.session_state:
    st.session_state.running_benchmark = False
if "benchmark_plot_logged" not in st.session_state:
    st.session_state.benchmark_plot_logged = False
if "graph_loading" not in st.session_state:
    st.session_state.graph_loading = False
if "graph_loading_reset" not in st.session_state:
    st.session_state.graph_loading_reset = False
if "benchmark_step1" not in st.session_state:
    st.session_state.benchmark_step1 = False
if "benchmark_step2" not in st.session_state:
    st.session_state.benchmark_step2 = False
if "benchmark_step3" not in st.session_state:
    st.session_state.benchmark_step3 = False
if "benchmark_step4" not in st.session_state:
    st.session_state.benchmark_step4 = False
if "benchmark_params" not in st.session_state:
    st.session_state.benchmark_params = None
if "benchmark_stopped" not in st.session_state:
    st.session_state.benchmark_stopped = False
if "active_log" not in st.session_state:
    st.session_state.active_log = None
if "active_terminal_log" not in st.session_state:
    st.session_state.active_terminal_log = None
if "show_benchmark_images" not in st.session_state:
    st.session_state.show_benchmark_images = False
if "show_benchmark_matrix" not in st.session_state:
    st.session_state.show_benchmark_matrix = False
if "show_real_pairs" not in st.session_state:
    st.session_state.show_real_pairs = False
if "benchmark_white_bg" not in st.session_state:
    st.session_state.benchmark_white_bg = False
if "benchmark_progress" not in st.session_state:
    st.session_state.benchmark_progress = 0.0
if "benchmark_status" not in st.session_state:
    st.session_state.benchmark_status = ""
if "benchmark_completed" not in st.session_state:
    st.session_state.benchmark_completed = False
if "build_running" not in st.session_state:
    st.session_state.build_running = False
if "cancel_build" not in st.session_state:
    st.session_state.cancel_build = False
if "build_run_id" not in st.session_state:
    st.session_state.build_run_id = 0
if "active_build_run_id" not in st.session_state:
    st.session_state.active_build_run_id = 0
if "build_started" not in st.session_state:
    st.session_state.build_started = False
if "build_params" not in st.session_state:
    st.session_state.build_params = {}
if "build_timeout_secs" not in st.session_state:
    st.session_state.build_timeout_secs = 60
    st.session_state.global_timeout_secs = 120
if "global_timeout_secs" not in st.session_state:
    st.session_state.global_timeout_secs = 120
if "build_progress" not in st.session_state:
    st.session_state.build_progress = 0.0
if "build_status" not in st.session_state:
    st.session_state.build_status = ""
if "build_completed" not in st.session_state:
    st.session_state.build_completed = False
if "review_status" not in st.session_state:
    st.session_state.review_status = {}
if "review_last_pair" not in st.session_state:
    st.session_state.review_last_pair = None
if "removed_pairs_log" not in st.session_state:
    st.session_state.removed_pairs_log = []

_check_optional_deps()

algorithm_options = list_algorithms()
ui_algorithms = [algo for algo in algorithm_options if algo != "GIN/GNN (Pickle)"]

nav_items = [
    "Home",
    "Benchmark & Examples",
    "Scenario Studio",
    "Study Lab",
    "Model Lab",
    "Research Reports",
    "Admin",
    "Logs",
    "Help",
    "About",
]
if "active_module" not in st.session_state or st.session_state.active_module not in nav_items:
    st.session_state.active_module = "Home"

with st.sidebar:
    st.subheader("Isomera v2")
    st.caption(f"v{ISOMERA_IDENTITY['version']} · {ISOMERA_IDENTITY['codename']}")
    st.caption("Workspace navigation")
    primary_modules = ["Home", "Benchmark & Examples", "Scenario Studio", "Study Lab", "Model Lab"]
    support_modules = [module for module in nav_items if module not in primary_modules]

    def _nav_button(module_name: str, key: str) -> None:
        is_active = st.session_state.active_module == module_name
        label = f"• {module_name}" if is_active else module_name
        button_type = "primary" if is_active else "secondary"
        if st.button(label, key=key, use_container_width=True, type=button_type):
            st.session_state.active_module = module_name
            st.rerun()

    st.markdown("**Core Modules**")
    for module_name in primary_modules:
        _nav_button(module_name, f"nav_{module_name.lower().replace(' ', '_').replace('&', 'and')}")

    if support_modules:
        st.markdown("**Support**")
        for module_name in support_modules:
            _nav_button(module_name, f"nav_{module_name.lower().replace(' ', '_')}")

    st.markdown("**App Controls**")
    if st.button("Reset app", key="sidebar_reset_app", use_container_width=True):
        _log_event("reset_app_click")
        _reset_session_state()
        _log_event("reset_app")
        st.rerun()
    st.checkbox(
        "Article Capture",
        value=st.session_state.article_capture_enabled,
        key="article_capture_enabled",
        help="Store structured curation and benchmark summaries for later article/report use.",
    )
    if st.session_state.get("last_article_capture"):
        last_capture = st.session_state["last_article_capture"]
        st.caption(
            f"Last capture: {last_capture.get('report_type')} at {last_capture.get('captured_at')}"
        )
    if not st.session_state.get("shutdown_confirm_visible"):
        if st.button("Stop Isomera", key="sidebar_stop_isomera", use_container_width=True, type="secondary"):
            st.session_state.shutdown_confirm_visible = True
            st.rerun()
    else:
        st.warning("This will stop Streamlit and the local databases started by the launcher.")
        shutdown_cols = st.columns(2, gap="small")
        if shutdown_cols[0].button("Confirm", key="sidebar_confirm_shutdown", use_container_width=True, type="primary"):
            signal_path = _request_safe_shutdown()
            st.success(f"Shutdown requested. Waiting for launcher: {signal_path}")
            time.sleep(1)
            st.stop()
        if shutdown_cols[1].button("Cancel", key="sidebar_cancel_shutdown", use_container_width=True):
            st.session_state.shutdown_confirm_visible = False
            st.rerun()
    training_job = st.session_state.get("training_job")
    if training_job:
        progress_path = Path(str(training_job["progress_path"]))
        progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
        running = _training_job_is_running(training_job.get("pid"))
        st.markdown("**Training Job**")
        st.caption(
            f"{training_job.get('model_name')} | "
            f"{progress.get('status', 'pending')} | "
            f"epoch {progress.get('current_epoch', 0)}/{progress.get('epochs', '-')}"
        )
        st.progress(min(max(float(progress.get("progress", 0.0)), 0.0), 1.0))
        if not running and progress.get("status") in {"completed", "failed", "stopped"}:
            st.caption("Go to `Scenario Studio > Model Training` to inspect or finalize this job.")

    st.caption(f"Active module: {st.session_state.active_module}")

if st.session_state.active_module == "Home":
    left_col, right_col = st.columns([1, 2], gap="large")
    with left_col:
        st.subheader("Home")
        st.caption("One workspace for benchmark execution, scenario design, detector validation, and technical operations.")
        st.markdown("**Start here**")
        st.container(border=True).markdown(
            "**Benchmark & Examples**\n\nRun the curated TPC-DS scenarios and inspect benchmark outputs."
        )
        if st.button("Go to Benchmark & Examples", key="home_open_benchmark", use_container_width=True):
            st.session_state.active_module = "Benchmark & Examples"
            st.rerun()
        st.container(border=True).markdown(
            "**Scenario Studio**\n\nBuild or load custom graphs before sending them to execution."
        )
        if st.button("Go to Scenario Studio", key="home_open_scenario", use_container_width=True):
            st.session_state.active_module = "Scenario Studio"
            st.rerun()
        st.container(border=True).markdown(
            "**Study Lab**\n\nStudy VMamba, run a SS2D-style lineage simulation, and plan VMamba-Mesh changes."
        )
        if st.button("Go to Study Lab", key="home_open_study", use_container_width=True):
            st.session_state.active_module = "Study Lab"
            st.rerun()
        st.container(border=True).markdown(
            "**Admin**\n\nInspect the backend store, scenario warehouse, graph catalog, and runtime settings."
        )
        if st.button("Go to Admin", key="home_open_admin", use_container_width=True):
            st.session_state.active_module = "Admin"
            st.rerun()
    with right_col:
        st.subheader("Current Workspace")
        st.markdown(
            """
            - Use `Benchmark & Examples` when you want the official benchmark.
            - Use `Scenario Studio` when you want to prepare or validate a new scenario.
            - Use `Study Lab` when you want to learn VMamba and prototype VMamba-Mesh changes.
            - Use `Admin` when you need to inspect the stores.
            """
        )
        st.markdown(
            """
            <div class="iso-loading-card">
              <strong>Isomera operational flow</strong>
              <ol>
                <li><strong>Connect</strong>: choose a relational warehouse or GML catalog.</li>
                <li><strong>Materialize</strong>: convert tables/contracts into normalized lineage graphs.</li>
                <li><strong>Validate</strong>: create supervised duplicate/non-duplicate pairs.</li>
                <li><strong>Train</strong>: build GNN pickle clusters from curated scenarios.</li>
                <li><strong>Benchmark</strong>: compare VF2, Node Match, and routed GNN clusters with SF-Jaccard.</li>
                <li><strong>Report</strong>: export PDF/TEX/Markdown/ZIP evidence for the paper.</li>
              </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )

if st.session_state.active_module == "Study Lab":
    _render_study_lab()

if st.session_state.active_module == "Research Reports":
    left_col, right_col = st.columns([1, 2], gap="large")
    report_packages = _list_research_report_packages(limit=40)
    backend_reports = list_recent_reports(st.session_state.backend_db_url, limit=25) if st.session_state.backend_enabled else []

    with left_col:
        st.markdown("<div class='iso-scroll-pane'>", unsafe_allow_html=True)
        st.subheader("Research Reports")
        st.caption("Select a package, open the PDF externally, or read the Markdown narrative on the right.")
        st.markdown(
            """
            <div class="iso-loading-card">
              <strong>How this page works</strong>
              <p>The page lists existing packages first and only reads the selected PDF. Capture scanning is optional to keep navigation fast.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not report_packages:
            selected_package = None
            st.info("No generated report packages found.")
        else:
            package_labels = [str(package["name"]) for package in report_packages]
            selected_package_label = st.selectbox(
                "Report package",
                options=package_labels,
                key="research_report_package_select_fast",
            )
            selected_package = report_packages[package_labels.index(selected_package_label)]
            st.caption(f"Package folder: {selected_package['dir']}")

            pdf_path = Path(str(selected_package.get("pdf") or ""))
            tex_path = Path(str(selected_package.get("tex") or ""))
            zip_path = Path(str(selected_package.get("zip") or ""))
            markdown_path = Path(str(selected_package.get("markdown") or ""))
            manifest_path = Path(str(selected_package["dir"])) / "package_manifest.json"
            if st.button("Open PDF", key=f"open_pdf_{selected_package_label}", use_container_width=True):
                if pdf_path.is_file():
                    try:
                        subprocess.run(["open", str(pdf_path)], check=False)
                        st.success("PDF opened in the macOS viewer.")
                    except Exception as exc:  # noqa: BLE001
                        st.error(f"Could not open PDF: {exc}")
                else:
                    st.warning("This package does not have a PDF file.")
            download_items = [
                ("Download TEX", tex_path, "application/x-tex", "tex"),
                ("Download PDF", pdf_path, "application/pdf", "pdf"),
                ("Download Markdown", markdown_path, "text/markdown", "md"),
                ("Download Manifest", manifest_path, "application/json", "manifest"),
            ]
            for label, path, mime, suffix in download_items:
                if path.is_file():
                    st.download_button(
                        label,
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime=mime,
                        use_container_width=True,
                        key=f"download_{suffix}_{selected_package_label}",
                    )
                else:
                    st.caption(f"{label}: unavailable")
            if zip_path.is_file():
                st.download_button(
                    "Download ZIP",
                    data=zip_path.read_bytes(),
                    file_name=zip_path.name,
                    mime="application/zip",
                    use_container_width=True,
                    key=f"download_zip_{selected_package_label}",
                )
            else:
                if st.button("Build ZIP package", key=f"build_zip_{selected_package_label}", use_container_width=True):
                    package_dir = Path(str(selected_package["dir"]))
                    with st.spinner("Building ZIP from the selected report folder..."):
                        zip_path = Path(shutil.make_archive(str(package_dir), "zip", root_dir=package_dir))
                    st.success(f"ZIP created: {zip_path.name}")
                    st.rerun()

        with st.expander("Generate package from Article Capture", expanded=False):
            capture_entries = _list_article_capture_entries(limit=25)
            if capture_entries:
                capture_labels = [
                    f"{entry.get('scenario') or entry.get('benchmark_name') or 'capture'} | {entry['report_type']} | {entry['captured_at']}"
                    for entry in capture_entries
                ]
                selected_capture_label = st.selectbox(
                    "Capture",
                    options=capture_labels,
                    key="research_report_capture_select_fast",
                )
                selected_capture = capture_entries[capture_labels.index(selected_capture_label)]
                st.caption(f"Source JSON: {selected_capture['json_path']}")
                if st.button("Generate Research Package", key="generate_article_package_fast", use_container_width=True):
                    with st.spinner("Generating package: reading capture, writing TEX/ZIP, then compiling PDF if available..."):
                        ok, message = _generate_research_report_package(str(selected_capture["json_path"]))
                    if ok:
                        st.success(message)
                    else:
                        st.error(message)
            else:
                st.info("No captures found. Enable Article Capture and run curation/training/benchmark first.")

        if backend_reports:
            st.markdown("**Backend report index**")
            st.table(
                pd.DataFrame(
                    [
                        {
                            "id": row["report_id"],
                            "type": row["report_type"],
                            "created_at": row["created_at"],
                            "run_id": row["run_id"],
                        }
                        for row in backend_reports
                    ]
                ).astype(str)
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        st.markdown("<div class='iso-scroll-pane'>", unsafe_allow_html=True)
        st.subheader("Selected Report")
        if selected_package:
            manifest_path = Path(str(selected_package["dir"])) / "package_manifest.json"
            pdf_path = Path(str(selected_package.get("pdf") or ""))
            tex_path = Path(str(selected_package.get("tex") or ""))
            zip_path = Path(str(selected_package.get("zip") or ""))
            markdown_path = Path(str(selected_package.get("markdown") or ""))
            rows = [
                {"field": "package", "value": selected_package["name"]},
                {"field": "folder", "value": selected_package["dir"]},
                {"field": "pdf", "value": str(pdf_path) if pdf_path.is_file() else "unavailable"},
                {"field": "tex", "value": str(tex_path) if tex_path.is_file() else "unavailable"},
                {"field": "zip", "value": str(zip_path) if zip_path.is_file() else "unavailable"},
                {"field": "markdown", "value": str(markdown_path) if markdown_path.is_file() else "unavailable"},
            ]
            st.table(pd.DataFrame(rows).astype(str))
            if markdown_path.is_file():
                markdown_text = markdown_path.read_text(encoding="utf-8", errors="replace")
                report_tabs = st.tabs(["Markdown Viewer", "Raw Markdown"])
                with report_tabs[0]:
                    st.markdown(markdown_text)
                with report_tabs[1]:
                    st.text_area("Raw report markdown (.md)", markdown_text, height=520, key=f"raw_md_{selected_package['name']}")
            elif tex_path.is_file():
                st.markdown("**Markdown narrative unavailable. Showing TEX excerpt instead.**")
                st.code(tex_path.read_text(encoding="utf-8", errors="replace")[:20000], language="tex")
            else:
                st.info("No Markdown or TEX found for this package.")
            if manifest_path.is_file():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                except Exception as exc:  # noqa: BLE001
                    st.warning(f"Manifest could not be read: {exc}")
                    manifest = {}
                with st.expander("Package manifest summary", expanded=False):
                    st.json(manifest, expanded=False)
            elif selected_package:
                st.info("No package manifest found.")
        else:
            st.info("Select a report package on the left.")
        st.markdown("</div>", unsafe_allow_html=True)

if False and st.session_state.active_module == "Research Reports":
    left_col, right_col = st.columns([1, 2], gap="large")
    capture_entries = _list_article_capture_entries(limit=100)
    report_packages = _list_research_report_packages(limit=30)
    backend_reports = list_recent_reports(st.session_state.backend_db_url, limit=50) if st.session_state.backend_enabled else []
    with left_col:
        st.subheader("Research Reports")
        st.caption("Article-ready packages with `.tex`, `.pdf`, `.zip`, source data, images, model artifacts, and metadata.")
        tectonic_binary = shutil.which("tectonic")
        if tectonic_binary:
            st.caption(f"PDF compiler available: `{tectonic_binary}`")
        else:
            st.warning(
                "PDF export requires Tectonic. Isomera will still generate `.tex` and `.zip`; "
                "install Tectonic to compile `.pdf` inside the app."
            )
        st.markdown("**Report packages**")
        if report_packages:
            package_labels = [str(package["name"]) for package in report_packages]
            selected_package_label = st.selectbox("Report package", options=package_labels, key="research_report_package_select")
            selected_package = report_packages[package_labels.index(selected_package_label)]
            st.caption(f"Folder: {selected_package['dir']}")
            download_cols = st.columns(3, gap="small")
            for col, label, path_key, mime in [
                (download_cols[0], "Download PDF", "pdf", "application/pdf"),
                (download_cols[1], "Download TEX", "tex", "application/x-tex"),
                (download_cols[2], "Download ZIP", "zip", "application/zip"),
            ]:
                path_value = str(selected_package.get(path_key) or "")
                path = Path(path_value) if path_value else None
                if path and path.exists():
                    col.download_button(
                        label,
                        data=path.read_bytes(),
                        file_name=path.name,
                        mime=mime,
                        key=f"download_{path_key}_{selected_package_label}",
                    )
                else:
                    col.caption(f"{label}: unavailable")
        else:
            selected_package = None
            st.info("No report packages yet. Generate one from an article capture.")
        st.markdown("**Source captures**")
        if capture_entries:
            labels = [
                f"{entry.get('scenario') or 'scenario'} | {entry['report_type']} | {entry['captured_at']}"
                for entry in capture_entries
            ]
            selected_label = st.selectbox("Capture source", options=labels, key="research_report_select")
            selected_capture = capture_entries[labels.index(selected_label)]
            st.caption(f"JSON: {selected_capture['json_path']}")
            st.caption(f"Markdown: {selected_capture['markdown_path']}")
            generation_status = st.session_state.pop("research_report_generation_status", None)
            if generation_status:
                if generation_status.get("ok"):
                    st.success(str(generation_status.get("message") or "Article package generated."))
                else:
                    st.error(str(generation_status.get("message") or "Article package generation failed."))
            st.caption(
                "Article Capture stores evidence during curation/training. "
                "Generate Research Package writes `.tex`, `.zip`, and a previewable `.pdf`. "
                "The app tries Tectonic first, then xelatex/pdflatex, then the native Isomera PDF fallback."
            )
            if st.button("Generate Research Package", key="generate_article_package", use_container_width=True):
                ok, message = _generate_research_report_package(str(selected_capture["json_path"]))
                st.session_state.research_report_generation_status = {"ok": ok, "message": message}
                st.rerun()
        else:
            selected_capture = None
            st.info("No article captures yet. Enable `Article Capture` and run curation or training steps.")
        st.markdown("**Backend report rows**")
        if backend_reports:
            st.table(
                pd.DataFrame(
                    [
                        {
                            "id": row["report_id"],
                            "type": row["report_type"],
                            "created_at": row["created_at"],
                            "run_id": row["run_id"],
                        }
                        for row in backend_reports[:10]
                    ]
                ).set_index("id")
            )
        else:
            st.info("No backend reports stored yet.")
    with right_col:
        if selected_package:
            manifest_path = Path(str(selected_package["dir"])) / "package_manifest.json"
            if manifest_path.exists():
                st.markdown("**Package manifest**")
                package_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                compiler_info = package_manifest.get("tectonic", {})
                compiler_name = compiler_info.get("pdf_compiler") or "not compiled"
                fallback_used = bool(compiler_info.get("native_pdf_fallback"))
                st.caption(
                    f"PDF compiler: {compiler_name}"
                    + (" | native fallback used for in-app preview" if fallback_used else "")
                )
                st.json(package_manifest, expanded=False)
            pdf_path = Path(str(selected_package.get("pdf") or ""))
            if pdf_path.exists():
                st.markdown("**PDF preview**")
                _render_pdf_preview(pdf_path)
            else:
                st.info("This package has no compiled PDF yet. Generate the package again after installing Tectonic.")
            tex_path = Path(str(selected_package.get("tex") or ""))
            if tex_path.exists():
                st.markdown("**Article TEX preview**")
                st.text_area("TEX source", tex_path.read_text(encoding="utf-8"), height=360, key=f"tex_preview_{selected_package['name']}")
        if capture_entries and selected_capture:
            payload = selected_capture["payload"]
            st.markdown("**Storytelling Summary**")
            story = payload.get("storytelling", {})
            story_rows = [
                {"field": "report_type", "value": payload.get("report_type")},
                {"field": "captured_at", "value": payload.get("captured_at")},
                {"field": "module", "value": story.get("module")},
                {"field": "source_mode", "value": story.get("source_mode")},
                {"field": "graph_construction_method", "value": story.get("graph_construction_method")},
            ]
            st.table(pd.DataFrame(story_rows).set_index("field"))
            if story.get("graph_build_steps"):
                st.markdown("**Graph build steps**")
                for index, step in enumerate(story["graph_build_steps"], start=1):
                    st.caption(f"{index}. {step}")
            st.markdown("**Structured summary**")
            st.json(payload.get("summary", {}), expanded=False)
            if payload.get("publication_tables"):
                st.markdown("**Publication tables**")
                for table_name, rows in dict(payload["publication_tables"]).items():
                    st.markdown(f"`{table_name}`")
                    if isinstance(rows, list) and rows:
                        st.table(pd.DataFrame(rows[:20]))
                    elif isinstance(rows, list):
                        st.caption("No rows in this table.")
                    else:
                        st.json(rows, expanded=False)
                    if rows:
                        st.download_button(
                            f"Download {table_name} CSV",
                            data=pd.DataFrame(rows).to_csv(index=False),
                            file_name=f"{table_name}.csv",
                            mime="text/csv",
                            key=f"download_{table_name}_{selected_capture['captured_at']}",
                        )
            pipeline_rows = payload.get("publication_tables", {}).get("pipeline") if isinstance(payload.get("publication_tables"), dict) else None
            if pipeline_rows:
                st.markdown("**Pipeline view**")
                st.dataframe(pd.DataFrame(pipeline_rows), width="stretch", hide_index=True)
            if payload.get("formula_parameter_mapping"):
                st.markdown("**Formula to parameter mapping**")
                st.table(
                    pd.DataFrame(
                        [
                            {"symbol_or_concept": key, "value": value}
                            for key, value in dict(payload["formula_parameter_mapping"]).items()
                        ]
                    ).set_index("symbol_or_concept")
                )
            markdown_path = Path(str(selected_capture["markdown_path"])) if selected_capture.get("markdown_path") else None
            if markdown_path and markdown_path.exists():
                st.markdown("**Markdown narrative**")
                st.download_button(
                    "Download Methods Appendix (.md)",
                    data=markdown_path.read_text(encoding="utf-8"),
                    file_name=markdown_path.name,
                    mime="text/markdown",
                    key=f"download_md_{selected_capture['captured_at']}",
                )
                st.markdown(markdown_path.read_text(encoding="utf-8"))
            architecture = payload.get("system_architecture")
            if architecture:
                st.markdown("**Architecture view**")
                st.table(pd.DataFrame(architecture.get("layers", [])))
                st.table(pd.DataFrame(architecture.get("stores", [])))
            scenario_api = payload.get("scenario_api")
            if scenario_api:
                st.markdown("**Scenario Materialization API**")
                st.caption(str(scenario_api.get("purpose") or ""))
                if scenario_api.get("functions"):
                    st.table(pd.DataFrame(scenario_api.get("functions", [])))
                if scenario_api.get("guarantees"):
                    st.table(pd.DataFrame({"guarantee": list(scenario_api.get("guarantees", []))}))
                if scenario_api.get("limits"):
                    st.markdown("**API limits**")
                    st.table(pd.DataFrame({"limit": list(scenario_api.get("limits", []))}))
        else:
            st.info("Select one article capture to inspect its narrative, parameters, and stored metadata.")

if st.session_state.active_module in {"Benchmark & Examples", "Scenario Studio"}:
    step1_block = st.container(border=True)
    with step1_block:
        if st.session_state.active_module == "Benchmark & Examples":
            st.caption("Benchmark Workspace")
            st.subheader("Benchmark & Examples")
        else:
            st.subheader("Scenario Studio")
        benchmark_dir = "data/architectures/tpc_ds/gml"
        gml_root = _app_path(benchmark_dir)
        real_pairs_root = DEFAULT_ARCH_ROOT / "real_pairs"
        gml_files = sorted(gml_root.glob("*.gml")) if gml_root.exists() else []

        if st.session_state.active_module == "Benchmark & Examples":
            benchmark_architectures = [arch for arch in _list_architectures() if (Path(arch["root"]) / "gml").exists()]
            benchmark_labels = [arch["name"] for arch in benchmark_architectures]
            preferred_benchmark = st.session_state.get("benchmark_catalog_name", DEFAULT_ARCH_NAME)
            selected_benchmark_arch = st.selectbox(
                "Benchmark to inspect/run",
                options=benchmark_labels,
                index=benchmark_labels.index(preferred_benchmark) if preferred_benchmark in benchmark_labels else (
                    benchmark_labels.index(DEFAULT_ARCH_NAME) if DEFAULT_ARCH_NAME in benchmark_labels else 0
                ),
                key="benchmark_catalog_select",
            )
            st.caption("Select the benchmark dataset first. Run options, model routing, and execution policy appear in the Run tab.")
            selected_benchmark = _get_architecture(selected_benchmark_arch) if benchmark_labels else None
            st.session_state.benchmark_catalog_name = selected_benchmark_arch
            benchmark_root = Path(selected_benchmark["root"]) if selected_benchmark else DEFAULT_ARCH_ROOT
            benchmark_dir = str(benchmark_root / "gml")
            gml_root = benchmark_root / "gml"
            real_pairs_root = benchmark_root / "real_pairs"
            gml_files = sorted(gml_root.glob("*.gml")) if gml_root.exists() else []
            benchmark_algorithm_variants_all = _benchmark_algorithm_variants(selected_benchmark_arch)
            benchmark_algorithm_variants = list(benchmark_algorithm_variants_all)
            bench_section = _segmented_choice(
                "Benchmark section",
                options=["Article Reproducibility", "Run Benchmark", "Concepts"],
                key="benchmark_section_select",
                default="Article Reproducibility",
            )

            if bench_section == "Concepts":
                left_col, right_col = st.columns([1, 2], gap="large")
                with left_col:
                    st.subheader("Benchmark Concepts")
                    st.markdown(
                        """
                        **Benchmark scope**
                        - TPC-DS adapted into Data Mesh lineage graphs.
                        - Each scenario is a controlled architecture with SOR/SOT/SPEC layers.

                        **Scenario naming**
                        - `graph_SOR<k>_D<d>_seed<n>`
                        - SOR = number of sources, D = number of domains.

                        **Research goal**
                        - Compare VF2, Node Match, and GNN on curated ground truth.
                        - Report ACC, ET, Jaccard, SF-Jaccard, and SF-Accuracy for each scenario.
                        """,
                    )
                    st.caption("All benchmark scenarios live in data/architectures/tpc_ds.")
                    routing_summary_df, routing_df = _benchmark_routing_tables(selected_benchmark_arch)
                    st.markdown("**Model routing coverage**")
                    if routing_summary_df.empty:
                        st.info("No GNN pickle cluster is mapped to this benchmark yet.")
                    else:
                        st.table(
                            routing_summary_df[
                                ["model_family", "coverage", "status", "route_policy", "candidate_pickles", "best_of_active"]
                            ].astype(str)
                        )
                        with st.expander("Scenario to pickle routing", expanded=False):
                            if routing_df.empty:
                                st.caption("No scenario routes are available for this benchmark.")
                            else:
                                families = sorted(routing_df["model_family"].astype(str).unique().tolist())
                                selected_route_family = st.selectbox(
                                    "Model family",
                                    options=families,
                                    key="concept_route_family_filter",
                                )
                                route_view = routing_df[
                                    routing_df["model_family"].astype(str) == selected_route_family
                                ].copy()
                                route_view["pickle"] = route_view["pickle_path"].astype(str).map(
                                    lambda value: Path(value).name if value and not value.startswith("best of") else value
                                )
                                st.table(route_view[["scenario", "pickle", "route_mode", "status"]].astype(str))
                with right_col:
                    if not gml_files:
                        st.info("No .gml files found in the benchmark.")
                    else:
                        st.subheader("Benchmark Scenarios (Images)")
                        if st.button("Show scenario images", key="show_benchmark_images_btn"):
                            st.session_state.show_benchmark_images = not st.session_state.show_benchmark_images
                        if st.session_state.show_benchmark_images:
                            for gml_file in gml_files:
                                graph = nx.read_gml(gml_file)
                                _render_graph_white(graph, gml_file.stem, seed=42)

                        st.subheader("Ground Truth Pairs")
                        if st.button("Show real pairs", key="show_real_pairs_btn"):
                            st.session_state.show_real_pairs = not st.session_state.show_real_pairs
                        if st.session_state.show_real_pairs:
                            scenario_names = [p.stem for p in gml_files]
                            selected_scenario = st.selectbox(
                                "Scenario",
                                options=scenario_names,
                                key="concept_pairs_scenario",
                            )
                            gml_path = gml_root / f"{selected_scenario}.gml"
                            graph = nx.read_gml(gml_path)
                            pairs_path = real_pairs_root / f"{selected_scenario}.json"
                            if pairs_path.exists():
                                pairs = json.loads(pairs_path.read_text())
                                pairs = [tuple(pair) for pair in pairs]
                                if pairs:
                                    pair_label = st.selectbox(
                                        "Pair",
                                        options=[f"{a} <-> {b}" for a, b in pairs],
                                        key="concept_pair_select",
                                    )
                                    idx = [f"{a} <-> {b}" for a, b in pairs].index(pair_label)
                                    node_a, node_b = pairs[idx]
                                    _render_pair_preview(graph, node_a, node_b, seed=42)
                                else:
                                    st.info("No labeled pairs for this scenario.")
                            else:
                                st.warning("Ground-truth pairs file not found.")

                        st.subheader("Scenario Matrix (SOR x Domains)")
                        if st.button("Show matrix view", key="show_benchmark_matrix_btn"):
                            st.session_state.show_benchmark_matrix = not st.session_state.show_benchmark_matrix
                        if st.session_state.show_benchmark_matrix:
                            matrix_map: dict[tuple[int, int], Path] = {}
                            for gml_file in gml_files:
                                sor_val, dom_val = _extract_sor_domains(gml_file.stem)
                                if sor_val and dom_val:
                                    matrix_map[(int(sor_val), int(dom_val))] = gml_file
                            sor_values = [2, 4, 8, 16]
                            domain_values = sorted({d for (_, d) in matrix_map.keys()})
                            for sor in sor_values:
                                cols = st.columns(len(domain_values))
                                for idx, domain in enumerate(domain_values):
                                    with cols[idx]:
                                        gml_path = matrix_map.get((sor, domain))
                                        if gml_path:
                                            graph = nx.read_gml(gml_path)
                                            st.caption(f"SOR {sor} / D{domain}")
                                            _render_graph_inline_white(graph, seed=42)
                            if st.button("Save matrix as PNG", key="save_benchmark_matrix"):
                                fig = _build_benchmark_matrix_figure(matrix_map, sor_values, domain_values)
                                export_dir = Path.home() / "Downloads"
                                export_dir.mkdir(parents=True, exist_ok=True)
                                timestamp = time.strftime("%Y%m%d_%H%M%S")
                                out_path = export_dir / f"benchmark_matrix_{timestamp}.png"
                                fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
                                st.success(f"Matrix saved to {out_path}")

            elif bench_section == "Run Benchmark":
                left_col, right_col = st.columns([1, 2], gap="large")
                with right_col:
                    st.subheader("Visualization")
                    bench_progress_slot = st.empty()
                    bench_status_slot = st.empty()
                    bench_content_slot = st.empty()

                with left_col:
                    st.subheader("Benchmark Run")
                    st.caption(f"Benchmark catalog: `{selected_benchmark_arch}`")
                    benchmark_flow_slot = st.empty()
                    _render_benchmark_flow(
                        benchmark_flow_slot,
                        [
                            st.session_state.benchmark_step1,
                            st.session_state.benchmark_step2,
                            st.session_state.benchmark_step3,
                            st.session_state.benchmark_step4,
                        ],
                    )
                    if not gml_root.exists() or not real_pairs_root.exists():
                        st.warning("Ensure .gml and real_pairs exist in data/architectures/tpc_ds.")
                    benchmark_runs = st.number_input(
                        "Executions per algorithm",
                        min_value=-1000,
                        max_value=200,
                        value=10,
                        key="benchmark_runs",
                    )
                    if int(benchmark_runs) < 1:
                        st.warning("Executions per algorithm must be at least 1.")
                    st.markdown("**Models to run**")
                    st.caption("Select detector families for this benchmark run. GNN clusters expose routing policy here because routing affects execution.")
                    selected_variants: list[dict[str, object]] = []
                    for variant_index, variant in enumerate(benchmark_algorithm_variants_all):
                        label = str(variant["label"])
                        safe_label = re.sub(r"[^A-Za-z0-9_]+", "_", label)
                        widget_suffix = f"{selected_benchmark_arch}_{variant_index}_{safe_label}"
                        row_cols = st.columns([0.55, 5.5, 0.45, 3.2], gap="small")
                        enabled = row_cols[0].checkbox(
                            "",
                            value=True,
                            key=f"benchmark_model_enabled_{widget_suffix}",
                            label_visibility="collapsed",
                        )
                        row_cols[1].markdown(f"**{label}**")
                        with row_cols[2]:
                            _info_popover(_model_help_text(label), key=f"benchmark_model_info_{widget_suffix}")
                        variant_copy = dict(variant)
                        if variant.get("kind") == "routed_gnn_cluster":
                            route_choice = row_cols[3].selectbox(
                                "Routing",
                                options=[
                                    "Respect mapped pickles",
                                    "Auto best-of when overcomplete",
                                    "Force best-of cluster",
                                ],
                                index=0,
                                key=f"benchmark_route_policy_{widget_suffix}",
                                label_visibility="collapsed",
                            )
                            candidate_paths = list(variant_copy.get("candidate_paths") or [])
                            if not candidate_paths:
                                candidate_paths = sorted(
                                    {
                                        Path(str(path))
                                        for path in dict(variant_copy.get("routes") or {}).values()
                                        if Path(str(path)).is_file()
                                    },
                                    key=lambda p: str(p),
                                )
                            if route_choice == "Auto best-of when overcomplete":
                                variant_copy["route_policy"] = "auto_best_of_when_overcomplete"
                                variant_copy["candidate_paths"] = candidate_paths
                            elif route_choice == "Force best-of cluster":
                                variant_copy["route_policy"] = "best_of_cluster"
                                variant_copy["candidate_paths"] = candidate_paths
                            else:
                                variant_copy["route_policy"] = ""
                        else:
                            row_cols[3].caption("Deterministic baseline")
                        if enabled:
                            selected_variants.append(variant_copy)
                    benchmark_algorithm_variants = selected_variants
                    if not benchmark_algorithm_variants:
                        st.warning("Select at least one model before running the benchmark.")
                    routing_summary_df, routing_df = _benchmark_routing_tables(selected_benchmark_arch)
                    if not routing_summary_df.empty:
                        st.markdown("**Model routing**")
                        st.table(
                            routing_summary_df[
                                ["model_family", "coverage", "status", "route_policy", "candidate_pickles", "best_of_active"]
                            ].astype(str)
                        )
                        if (routing_df["status"] == "missing_model").any():
                            st.warning(
                                "Some GNN model families do not have a mapped `.pkl` for every scenario in this benchmark. "
                                "When the route policy is `explicit_map`, scenarios without a valid `.pkl` are skipped for that GNN family. "
                                "Choose a best-of policy above if you want the benchmark to test candidate pickles."
                            )
                        with st.expander("Scenario to pickle map", expanded=False):
                            if routing_df.empty:
                                st.caption("No scenario routes are available for this benchmark.")
                            else:
                                families = sorted(routing_df["model_family"].astype(str).unique().tolist())
                                selected_route_family = st.selectbox(
                                    "Model family",
                                    options=families,
                                    key="benchmark_route_family_filter",
                                )
                                route_view = routing_df[
                                    routing_df["model_family"].astype(str) == selected_route_family
                                ].copy()
                                route_view["pickle"] = route_view["pickle_path"].astype(str).map(
                                    lambda value: Path(value).name if value and not value.startswith("best of") else value
                                )
                                st.table(
                                    route_view[["scenario", "pickle", "route_mode", "status"]].astype(str)
                                )
                    with st.expander("Examples of Protocol Contracts", expanded=False):
                        st.markdown(
                            """
                            To reproduce the paper runs inside Isomera, use:

                            - `Executions per algorithm = 10`.
                            - The same benchmark catalog selected above.
                            - VF2 and Node Match enabled as deterministic baselines.
                            - `GNN TPC-DS v1 cluster` for the original TPC-DS-trained pickle family.
                            - `GNN GenAI SPEC v1 cluster` and protocol ranks for the GenAI-validation-trained pickle families.
                            - `Best-of-all cluster selector` only as a diagnostic/oracle-style routing policy unless the policy is frozen before execution.

                            The two learned bases compared in the paper are:

                            - Original TPC-DS family: trained from the original GML/TPC-DS labels.
                            - GenAI validation family: trained from the supervised validation datasets created during Isomera v2 curation.
                            """
                        )
                        article_rows = [
                            {
                                "workload": "TPC-DS Default",
                                "catalog": DEFAULT_ARCH_NAME,
                                "candidate_scope": "all pairs",
                                "runs": 10,
                            },
                            {
                                "workload": "TPC-DS GenAI SPEC",
                                "catalog": "tpc_ds_genai_spec",
                                "candidate_scope": "SPEC upstream lineage",
                                "runs": 10,
                            },
                            {
                                "workload": "TPC-DS GenAI SOT+SPEC",
                                "catalog": "tpc_ds_genai_sot_spec",
                                "candidate_scope": "SOT + SPEC upstream lineage",
                                "runs": 10,
                            },
                            {
                                "workload": "TPC-DS GenAI SOR+SOT",
                                "catalog": "tpc_ds_genai_sor_sot",
                                "candidate_scope": "SOR + SOT lineage",
                                "runs": 10,
                            },
                            {
                                "workload": "TPC-DS GenAI Full Lineage",
                                "catalog": "tpc_ds_genai_full_lineage",
                                "candidate_scope": "SOR + SOT + SPEC lineage",
                                "runs": 10,
                            },
                        ]
                        st.table(pd.DataFrame(article_rows))
                        st.code(
                            "PYTHONPATH=main ./.venv/bin/python main/scripts/run_article_benchmarks.py "
                            "--benchmark tpc_ds_genai_spec --runs 10",
                            language="bash",
                        )
                    bench_cols = st.columns([1, 1], gap="small")
                    run_bench = bench_cols[0].button(
                        "Run",
                        key="run_benchmark",
                        disabled=int(benchmark_runs) < 1 or not benchmark_algorithm_variants,
                    )
                    stop_bench = bench_cols[1].button("Stop", key="stop_benchmark")

                if stop_bench:
                    st.session_state.cancel_benchmark = True
                    st.session_state.benchmark_stopped = True
                    st.session_state.benchmark_status = "Benchmark stopped by the user."
                    st.session_state.benchmark_progress = 0.0
                    bench_progress_slot.empty()
                    bench_status_slot.warning(st.session_state.benchmark_status)
                    _log_action("stop_benchmark", "benchmark.tab", {"runs": int(benchmark_runs)})
                if run_bench:
                    st.session_state.last_error = None
                    if int(benchmark_runs) < 1:
                        bench_status_slot.error("Executions per algorithm must be at least 1.")
                        _log_event("benchmark_invalid_runs", {"runs": int(benchmark_runs)})
                        st.stop()
                    st.session_state.cancel_benchmark = False
                    st.session_state.running_benchmark = True
                    st.session_state.benchmark_stopped = False
                    st.session_state.benchmark_completed = False
                    st.session_state.benchmark_status = "Running benchmark..."
                    st.session_state.benchmark_progress = 0.0
                    bench_progress_slot.progress(0.01)
                    bench_status_slot.info(
                        "Initializing benchmark: validating scenario files, labels, model routing, and execution plan..."
                    )
                    bench_content_slot.empty()
                    st.session_state.graph_source = "TPC-DS Benchmark"
                    st.session_state.benchmark_step1 = False
                    st.session_state.benchmark_step2 = False
                    st.session_state.benchmark_step3 = False
                    st.session_state.benchmark_step4 = False
                    _render_benchmark_flow(
                        benchmark_flow_slot,
                        [
                            st.session_state.benchmark_step1,
                            st.session_state.benchmark_step2,
                            st.session_state.benchmark_step3,
                            st.session_state.benchmark_step4,
                        ],
                    )
                    _log_action(
                        "run_benchmark_click",
                        "benchmark.tab",
                        {
                            "runs": int(benchmark_runs),
                            "benchmark_dir": benchmark_dir,
                            "benchmark_name": selected_benchmark_arch,
                        },
                    )
                    backend_run_id = _start_backend_run(
                        "benchmark",
                        parameters={
                            "runs": int(benchmark_runs),
                            "benchmark_dir": benchmark_dir,
                            "algorithms": [variant["label"] for variant in benchmark_algorithm_variants],
                        },
                    )
                    st.session_state.backend_active_run_id = backend_run_id
                    with st.spinner("Running benchmark..."):
                        try:
                            benchmark_path = _app_path(benchmark_dir)
                            if not benchmark_path.exists():
                                st.warning("Benchmark folder not found.")
                            else:
                                st.session_state.benchmark_params = {
                                    "benchmark_dir": benchmark_dir,
                                    "runs": int(benchmark_runs),
                                    "algorithms": [variant["label"] for variant in benchmark_algorithm_variants],
                                    "benchmark_name": selected_benchmark_arch,
                                }
                                if not gml_files:
                                    st.warning("No .gml files found in the benchmark.")
                                else:
                                    st.session_state.benchmark_step1 = True
                                    _render_benchmark_flow(
                                        benchmark_flow_slot,
                                        [
                                            st.session_state.benchmark_step1,
                                            st.session_state.benchmark_step2,
                                            st.session_state.benchmark_step3,
                                            st.session_state.benchmark_step4,
                                        ],
                                    )
                                    results = []
                                    exec_rows = []
                                    best_of_selection_results = []
                                    missing_pickles = []
                                    missing_real_pairs = []
                                    true_pairs_counts = []
                                    scenario_count_for_work = len(gml_files)
                                    units_per_scenario = 0
                                    for variant in benchmark_algorithm_variants:
                                        if variant.get("kind") == "routed_gnn_cluster" and _should_run_best_of_policy(
                                            str(variant.get("route_policy") or ""),
                                            len(list(variant.get("candidate_paths") or [])),
                                            scenario_count_for_work,
                                        ):
                                            units_per_scenario += len(list(variant.get("candidate_paths") or [])) + 1
                                        else:
                                            units_per_scenario += 1
                                    total_steps = max(len(gml_files) * units_per_scenario, 1)
                                    current_step = 0
                                    bench_start = time.perf_counter()
                                    timeout_secs = int(st.session_state.global_timeout_secs)
                                    gnn_available = True
                                    try:
                                        __import__("torch")
                                    except Exception:
                                        gnn_available = False
                                        st.warning("Torch not installed. GIN/GNN will be skipped.")
                                    for gml_file in gml_files:
                                        _persist_scenario_record(
                                            architecture_name=selected_benchmark_arch,
                                            scenario_name=gml_file.stem,
                                            source="benchmark_tpcds",
                                            gml_path=gml_file,
                                            labels_path=real_pairs_root / f"{gml_file.stem}.json",
                                            metadata={"benchmark": selected_benchmark_arch},
                                        )
                                        if time.perf_counter() - bench_start > timeout_secs:
                                            st.session_state.cancel_benchmark = True
                                            st.session_state.benchmark_stopped = True
                                            timeout_msg = (
                                                f"Operation timed out after {_format_timeout(timeout_secs)}."
                                            )
                                            st.session_state.benchmark_status = timeout_msg
                                            st.session_state.last_error = timeout_msg
                                            _log_event(
                                                "operation_timeout",
                                                {
                                                    "context": "benchmark",
                                                    "timeout_secs": timeout_secs,
                                                    "error": timeout_msg,
                                                },
                                            )
                                            bench_status_slot.error(timeout_msg)
                                            break
                                        if st.session_state.cancel_benchmark:
                                            _log_event("benchmark_cancelled")
                                            break
                                        graph = nx.read_gml(gml_file)
                                        node_count = graph.number_of_nodes()
                                        nodes = list(graph.nodes)
                                        all_pairs = [
                                            (nodes[i], nodes[j])
                                            for i in range(len(nodes))
                                            for j in range(i + 1, len(nodes))
                                        ]
                                        real_pairs_path = real_pairs_root / f"{gml_file.stem}.json"
                                        true_pairs = set()
                                        if real_pairs_path.exists():
                                            raw_pairs = json.loads(real_pairs_path.read_text())
                                            true_pairs = canonical_pairs(raw_pairs)
                                            true_pairs_counts.append(len(true_pairs))
                                        else:
                                            missing_real_pairs.append(gml_file.stem)
                                        for variant in benchmark_algorithm_variants:
                                            algo = str(variant["algorithm"])
                                            if time.perf_counter() - bench_start > timeout_secs:
                                                st.session_state.cancel_benchmark = True
                                                st.session_state.benchmark_stopped = True
                                                timeout_msg = (
                                                    f"Operation timed out after {_format_timeout(timeout_secs)}."
                                                )
                                                st.session_state.benchmark_status = timeout_msg
                                                st.session_state.last_error = timeout_msg
                                                _log_event(
                                                    "operation_timeout",
                                                    {
                                                        "context": "benchmark",
                                                        "timeout_secs": timeout_secs,
                                                        "error": timeout_msg,
                                                    },
                                                )
                                                bench_status_slot.error(timeout_msg)
                                                break
                                            if st.session_state.cancel_benchmark:
                                                _log_event("benchmark_cancelled")
                                                break
                                            selected_pickle_for_row = ""
                                            selected_pickle_module_for_row = ""
                                            route_mode_for_row = ""
                                            route_source_for_row = ""
                                            selection_metric_for_row = ""
                                            selection_candidates_for_row = 0
                                            best_of_selection_rows: list[dict[str, object]] = []
                                            metrics_df: pd.DataFrame | None = None
                                            first_run_elapsed = 0.0
                                            if variant["kind"] == "routed_gnn_cluster":
                                                if not gnn_available:
                                                    current_step += 1
                                                    st.session_state.benchmark_progress = min(
                                                        current_step / total_steps, 1.0
                                                    )
                                                    bench_progress_slot.progress(st.session_state.benchmark_progress)
                                                    continue
                                                route_policy = str(variant.get("route_policy") or "")
                                                candidate_paths = [
                                                    Path(str(path))
                                                    for path in list(variant.get("candidate_paths") or [])
                                                    if Path(str(path)).is_file()
                                                ]
                                                use_best_of = _should_run_best_of_policy(
                                                    route_policy,
                                                    len(candidate_paths),
                                                    len(gml_files),
                                                )
                                                if use_best_of:
                                                    selection_metric = str(variant.get("selection_metric") or "sf_jaccard")
                                                    if not candidate_paths:
                                                        missing_pickles.append(f"{variant['label']}::{gml_file.stem}")
                                                        current_step += 1
                                                        st.session_state.benchmark_progress = min(
                                                            current_step / total_steps, 1.0
                                                        )
                                                        bench_progress_slot.progress(st.session_state.benchmark_progress)
                                                        continue
                                                    total_pairs_count_for_selection = len(all_pairs)
                                                    candidate_modules = dict(variant.get("candidate_modules") or {})
                                                    for candidate_index, candidate_path in enumerate(candidate_paths, start=1):
                                                        if st.session_state.cancel_benchmark:
                                                            _log_event("benchmark_cancelled")
                                                            break
                                                        elapsed = time.perf_counter() - bench_start
                                                        avg_step = elapsed / max(current_step + 1, 1)
                                                        eta = avg_step * max(total_steps - current_step, 0)
                                                        st.session_state.benchmark_status = (
                                                            f"Selecting best pickle for {variant['label']} on {gml_file.stem}: "
                                                            f"candidate {candidate_index}/{len(candidate_paths)}. "
                                                            f"Progress {current_step}/{total_steps}. ETA {_format_timeout(int(eta))}."
                                                        )
                                                        bench_status_slot.info(st.session_state.benchmark_status)
                                                        st.session_state.gnn_pickle_path = str(candidate_path)
                                                        set_gnn_pickle_path(st.session_state.gnn_pickle_path)
                                                        candidate_module = str(
                                                            candidate_modules.get(str(candidate_path))
                                                            or _pickle_module_for_path(candidate_path)
                                                        )
                                                        set_gnn_pickle_module(candidate_module)
                                                        candidate_start = time.perf_counter()
                                                        candidate_df = metrics_table(
                                                            graph,
                                                            true_pairs,
                                                            [algo],
                                                            all_pairs=all_pairs,
                                                        )
                                                        candidate_elapsed = time.perf_counter() - candidate_start
                                                        candidate_row = candidate_df.iloc[0].to_dict()
                                                        c_tp = int(candidate_row.get("tp", 0) or 0)
                                                        c_fp = int(candidate_row.get("fp", 0) or 0)
                                                        c_fn = int(candidate_row.get("fn", 0) or 0)
                                                        c_tn = int(candidate_row.get("tn", 0) or 0)
                                                        c_den = c_tp + c_fp + c_fn
                                                        c_jaccard = (c_tp / c_den) if c_den else 0.0
                                                        c_acc_den = c_tp + c_tn + c_fp + c_fn
                                                        c_acc = float(candidate_row.get("accuracy") or 0.0)
                                                        if not c_acc and c_acc_den:
                                                            c_acc = (c_tp + c_tn) / c_acc_den
                                                        c_sf_jaccard = (
                                                            (c_jaccard * total_pairs_count_for_selection) / candidate_elapsed
                                                            if candidate_elapsed > 0
                                                            else 0.0
                                                        )
                                                        c_sf_accuracy = (
                                                            (c_acc * total_pairs_count_for_selection) / candidate_elapsed
                                                            if candidate_elapsed > 0
                                                            else 0.0
                                                        )
                                                        best_of_selection_rows.append(
                                                            {
                                                                "pickle_path": str(candidate_path),
                                                                "pickle_module": candidate_module,
                                                                "accuracy": c_acc,
                                                                "jaccard": c_jaccard,
                                                                "sf_jaccard": c_sf_jaccard,
                                                                "sf_accuracy": c_sf_accuracy,
                                                                "ET": candidate_elapsed,
                                                                "metrics_df": candidate_df,
                                                            }
                                                        )
                                                        best_of_selection_results.append(
                                                            {
                                                                "scenario": gml_file.stem,
                                                                "algorithm": str(variant["label"]),
                                                                "candidate_index": candidate_index,
                                                                "candidate_count": len(candidate_paths),
                                                                "pickle_path": str(candidate_path),
                                                                "pickle_module": candidate_module,
                                                                "selection_metric": selection_metric,
                                                                "accuracy": c_acc,
                                                                "jaccard": c_jaccard,
                                                                "sf_jaccard": c_sf_jaccard,
                                                                "sf_accuracy": c_sf_accuracy,
                                                                "ET": candidate_elapsed,
                                                            }
                                                        )
                                                        current_step += 1
                                                        st.session_state.benchmark_progress = min(
                                                            current_step / total_steps, 1.0
                                                        )
                                                        bench_progress_slot.progress(st.session_state.benchmark_progress)
                                                    if st.session_state.cancel_benchmark:
                                                        break
                                                    best_selection = max(
                                                        best_of_selection_rows,
                                                        key=lambda row: (
                                                            float(row.get(selection_metric, 0.0) or 0.0),
                                                            float(row.get("jaccard", 0.0) or 0.0),
                                                            -float(row.get("ET", 0.0) or 0.0),
                                                        ),
                                                    )
                                                    pickle_path = Path(str(best_selection["pickle_path"]))
                                                    selected_pickle_module_for_row = str(
                                                        best_selection.get("pickle_module")
                                                        or _pickle_module_for_path(pickle_path)
                                                    )
                                                    metrics_df = best_selection["metrics_df"]  # type: ignore[assignment]
                                                    first_run_elapsed = float(best_selection["ET"])
                                                    route_mode_for_row = "best_of_cluster"
                                                    if route_policy == "auto_best_of_when_overcomplete":
                                                        route_mode_for_row = "auto_best_of_when_overcomplete"
                                                    route_source_for_row = str(variant.get("source") or "manual_manifest")
                                                    selection_metric_for_row = selection_metric
                                                    selection_candidates_for_row = len(candidate_paths)
                                                else:
                                                    routes = dict(variant.get("routes") or {})
                                                    route_value = str(routes.get(gml_file.stem, "") or "")
                                                    pickle_path = Path(route_value) if route_value else Path()
                                                    if not route_value or not pickle_path.is_file():
                                                        missing_pickles.append(f"{variant['label']}::{gml_file.stem}")
                                                        current_step += 1
                                                        st.session_state.benchmark_progress = min(
                                                            current_step / total_steps, 1.0
                                                        )
                                                        bench_progress_slot.progress(st.session_state.benchmark_progress)
                                                        continue
                                                    route_mode_for_row = dict(variant.get("route_modes") or {}).get(
                                                        gml_file.stem, ""
                                                    )
                                                    route_source_for_row = dict(variant.get("route_sources") or {}).get(
                                                        gml_file.stem, ""
                                                    )
                                                    selected_pickle_module_for_row = str(
                                                        dict(variant.get("pickle_modules") or {}).get(gml_file.stem)
                                                        or _pickle_module_for_path(pickle_path)
                                                    )
                                                st.session_state.gnn_pickle_path = str(pickle_path)
                                                set_gnn_pickle_path(st.session_state.gnn_pickle_path)
                                                set_gnn_pickle_module(
                                                    selected_pickle_module_for_row or "core.algorithms.gnn_model"
                                                )
                                                selected_pickle_for_row = str(pickle_path)
                                            if metrics_df is None:
                                                metrics_start = time.perf_counter()
                                                metrics_df = metrics_table(
                                                    graph,
                                                    true_pairs,
                                                    [algo],
                                                    all_pairs=all_pairs,
                                                )
                                                first_run_elapsed = time.perf_counter() - metrics_start
                                            if not st.session_state.benchmark_step2:
                                                st.session_state.benchmark_step2 = True
                                                st.session_state.benchmark_step3 = True
                                                _render_benchmark_flow(
                                                    benchmark_flow_slot,
                                                    [
                                                        st.session_state.benchmark_step1,
                                                        st.session_state.benchmark_step2,
                                                        st.session_state.benchmark_step3,
                                                        st.session_state.benchmark_step4,
                                                    ],
                                                )
                                            metrics_row = metrics_df.iloc[0].to_dict()
                                            tp = int(metrics_row.get("tp", 0) or 0)
                                            fp = int(metrics_row.get("fp", 0) or 0)
                                            fn = int(metrics_row.get("fn", 0) or 0)
                                            tn = int(metrics_row.get("tn", 0) or 0)
                                            denom = tp + fp + fn
                                            jaccard = (tp / denom) if denom else 0.0
                                            accuracy_denom = tp + tn + fp + fn
                                            acc = float(metrics_row.get("accuracy") or 0.0)
                                            if not acc and accuracy_denom:
                                                acc = (tp + tn) / accuracy_denom
                                            err = 1 - acc
                                            et = 0.0
                                            total_pairs_count = len(all_pairs)
                                            metrics_row["scenario"] = gml_file.stem
                                            metrics_row["algorithm"] = str(variant["label"])
                                            if variant["kind"] == "routed_gnn_cluster":
                                                metrics_row["pickle_path"] = selected_pickle_for_row
                                                metrics_row["pickle_module"] = selected_pickle_module_for_row
                                                metrics_row["route_mode"] = route_mode_for_row
                                                metrics_row["route_source"] = route_source_for_row
                                                metrics_row["selection_metric"] = selection_metric_for_row
                                                metrics_row["selection_candidates"] = selection_candidates_for_row
                                            metrics_row["ACC"] = acc
                                            metrics_row["accuracy"] = acc
                                            metrics_row["jaccard"] = jaccard
                                            metrics_row["ERR"] = err
                                            metrics_row["ET"] = et
                                            metrics_row["SF"] = 0.0
                                            metrics_row["sf_accuracy"] = 0.0
                                            metrics_row["sf_jaccard"] = 0.0
                                            metrics_row["N_pairs"] = total_pairs_count
                                            results.append(metrics_row)

                                            extra_runs = max(int(benchmark_runs) - 1, 0)
                                            times = [first_run_elapsed]
                                            if extra_runs:
                                                times.extend(
                                                    execution_times(graph, [algo], runs=extra_runs).get(algo, [])
                                                )
                                            if times:
                                                series = pd.Series(times)
                                                et = float(series.median())
                                                exec_rows.append(
                                                    {
                                                        "scenario": gml_file.stem,
                                                        "algorithm": algo,
                                                        "mean": series.mean(),
                                                        "median": series.median(),
                                                        "std": series.std(ddof=1),
                                                        "min": series.min(),
                                                        "max": series.max(),
                                                        "p95": series.quantile(0.95),
                                                        "p99": series.quantile(0.99),
                                                    }
                                                )
                                            if et > 0 and total_pairs_count > 0:
                                                sf_accuracy = (acc * total_pairs_count) / et
                                                sf_jaccard = (jaccard * total_pairs_count) / et
                                            else:
                                                sf_accuracy = 0.0
                                                sf_jaccard = 0.0
                                            results[-1]["ET"] = et
                                            results[-1]["SF"] = sf_jaccard
                                            results[-1]["sf_accuracy"] = sf_accuracy
                                            results[-1]["sf_jaccard"] = sf_jaccard
                                            current_step += 1
                                            st.session_state.benchmark_progress = min(
                                                current_step / total_steps, 1.0
                                            )
                                            st.session_state.benchmark_status = (
                                                f"Running benchmark... {current_step}/{total_steps} "
                                                f"({(current_step / total_steps) * 100:.1f}%)"
                                            )
                                            bench_progress_slot.progress(st.session_state.benchmark_progress)
                                            bench_status_slot.info(st.session_state.benchmark_status)
                                        if st.session_state.cancel_benchmark:
                                            break
                                    st.session_state.benchmark_results = pd.DataFrame(results)
                                    st.session_state.benchmark_exec_stats = pd.DataFrame(exec_rows)
                                    st.session_state.benchmark_best_of_selection_results = pd.DataFrame(best_of_selection_results)
                                    st.session_state.benchmark_plot_logged = False
                                    st.session_state.benchmark_completed = True
                                    st.session_state.benchmark_step4 = True
                                    _render_benchmark_flow(
                                        benchmark_flow_slot,
                                        [
                                            st.session_state.benchmark_step1,
                                            st.session_state.benchmark_step2,
                                            st.session_state.benchmark_step3,
                                            st.session_state.benchmark_step4,
                                        ],
                                    )
                                    results_df = st.session_state.benchmark_results.copy()
                                    if "scenario" in results_df.columns:
                                        sor_values = []
                                        domain_values = []
                                        for scenario in results_df["scenario"].astype(str):
                                            sor_val, dom_val = _extract_sor_domains(scenario)
                                            sor_values.append(sor_val)
                                            domain_values.append(dom_val)
                                        results_df["sor"] = pd.Series(sor_values)
                                        results_df["domains"] = pd.Series(domain_values)
                                        missing_sor = results_df["sor"].isna().sum()
                                        missing_domains = results_df["domains"].isna().sum()
                                    else:
                                        missing_sor = None
                                        missing_domains = None
                                    _log_event(
                                        "benchmark_summary",
                                        {
                                            "rows": len(results_df),
                                            "missing_sor": int(missing_sor) if missing_sor is not None else None,
                                            "missing_domains": int(missing_domains) if missing_domains is not None else None,
                                            "algorithms": [variant["label"] for variant in benchmark_algorithm_variants],
                                            "scenarios": len(gml_files),
                                            "gnn_available": gnn_available,
                                            "missing_pickles": sorted(set(missing_pickles)),
                                            "missing_real_pairs": sorted(set(missing_real_pairs)),
                                            "true_pairs_min": min(true_pairs_counts) if true_pairs_counts else None,
                                            "true_pairs_max": max(true_pairs_counts) if true_pairs_counts else None,
                                        },
                                    )
                                    if missing_pickles:
                                        st.warning(
                                            "Missing pickle for some scenarios: "
                                            + ", ".join(sorted(set(missing_pickles)))
                                        )
                                    _log_event(
                                        "run_benchmark",
                                        {
                                            "scenarios": len(gml_files),
                                            "runs": int(benchmark_runs),
                                            "benchmark_name": selected_benchmark_arch,
                                        },
                                    )
                                    if benchmark_algorithm_variants:
                                        _log_event(
                                            "benchmark_algorithms",
                                            {
                                                "benchmark_name": selected_benchmark_arch,
                                                "algorithms": [variant["label"] for variant in benchmark_algorithm_variants],
                                            },
                                        )
                                    _record_backend_report(
                                        backend_run_id,
                                        "benchmark_summary",
                                        {
                                            "rows": len(results_df),
                                            "exec_rows": len(exec_rows),
                                            "best_of_selection_rows": len(best_of_selection_results),
                                            "scenarios": len(gml_files),
                                            "algorithms": [variant["label"] for variant in benchmark_algorithm_variants],
                                        },
                                    )
                                    _finish_backend_run(
                                        backend_run_id,
                                        status="completed" if not st.session_state.cancel_benchmark else "cancelled",
                                        summary={
                                            "rows": len(results_df),
                                            "exec_rows": len(exec_rows),
                                            "best_of_selection_rows": len(best_of_selection_results),
                                            "missing_pickles": sorted(set(missing_pickles)),
                                            "missing_real_pairs": sorted(set(missing_real_pairs)),
                                            "benchmark_name": selected_benchmark_arch,
                                        },
                                    )
                                    if not st.session_state.cancel_benchmark:
                                        st.session_state.benchmark_status = "Completed. See results below."
                                    if st.session_state.benchmark_params:
                                        st.session_state.benchmark_params.update(
                                            {
                                                "scenarios": len(gml_files),
                                                "gnn_available": gnn_available,
                                                "missing_pickles": sorted(set(missing_pickles)),
                                                "missing_real_pairs": sorted(set(missing_real_pairs)),
                                                "true_pairs_min": min(true_pairs_counts) if true_pairs_counts else None,
                                                "true_pairs_max": max(true_pairs_counts) if true_pairs_counts else None,
                                                "benchmark_name": selected_benchmark_arch,
                                            }
                                        )
                                        _log_event(
                                            "benchmark_params",
                                            st.session_state.benchmark_params,
                                        )
                        except Exception as exc:  # noqa: BLE001 - show errors to user
                            _finish_backend_run(
                                backend_run_id,
                                status="failed",
                                summary={"error": f"{type(exc).__name__}: {exc}"},
                            )
                            _log_exception("run_benchmark", exc)
                        finally:
                            st.session_state.backend_active_run_id = None
                            st.session_state.running_benchmark = False
                            if not st.session_state.benchmark_stopped:
                                st.session_state.benchmark_status = ""
                            st.session_state.benchmark_progress = 0.0
                if st.session_state.last_error:
                    bench_status_slot.error("Error detected in the last execution.")
                    bench_content_slot.text_area(
                        "Error details",
                        st.session_state.last_error,
                        height=200,
                        key="benchmark_error_details",
                    )
                if st.session_state.running_benchmark:
                    bench_progress_slot.progress(min(max(st.session_state.benchmark_progress, 0.0), 1.0))
                    bench_status_slot.info(st.session_state.benchmark_status or "Running benchmark...")
                elif st.session_state.benchmark_stopped:
                    bench_status_slot.warning(st.session_state.benchmark_status or "Benchmark stopped by the user.")
                elif st.session_state.benchmark_results is None:
                    bench_content_slot.info("Run the benchmark to see results.")
                else:
                    with bench_content_slot.container():
                        if st.session_state.benchmark_completed:
                            bench_status_slot.success(
                                st.session_state.benchmark_status or "Completed. See results below."
                            )
                        table_df = st.session_state.benchmark_results.copy()
                        display_cols = [
                            col
                            for col in ["scenario", "algorithm", "ACC", "jaccard", "ET", "SF", "sf_accuracy", "tp", "fp", "fn"]
                            if col in table_df.columns
                        ]
                        if display_cols:
                            st.dataframe(table_df[display_cols], width="stretch")
                        else:
                            st.dataframe(table_df, width="stretch")
                        if st.session_state.benchmark_exec_stats is not None:
                            st.subheader("Benchmark Execution Stats")
                            st.dataframe(st.session_state.benchmark_exec_stats, width="stretch")
                            st.caption(
                                "Times in seconds. `mean/median/std/min/max/p95/p99` reflect per-run duration."
                            )
                        if (
                            st.session_state.benchmark_best_of_selection_results is not None
                            and not st.session_state.benchmark_best_of_selection_results.empty
                        ):
                            st.subheader("Best-of Cluster Candidate Results")
                            st.caption(
                                "Every candidate pickle tested during best-of routing. "
                                "The selected pickle is the candidate with the highest configured selection metric."
                            )
                            st.dataframe(
                                st.session_state.benchmark_best_of_selection_results,
                                width="stretch",
                                hide_index=True,
                            )
                        results_df = st.session_state.benchmark_results.copy()
                        if not results_df.empty and "scenario" in results_df.columns:
                            scenario_series = results_df["scenario"].astype(str)
                            sor_values = []
                            domain_values = []
                            for scenario in scenario_series:
                                sor_val, dom_val = _extract_sor_domains(scenario)
                                sor_values.append(sor_val)
                                domain_values.append(dom_val)
                            results_df["sor"] = pd.Series(sor_values)
                            results_df["domains"] = pd.Series(domain_values)
                            missing_sor = int(results_df["sor"].isna().sum())
                            missing_domains = int(results_df["domains"].isna().sum())
                            if not st.session_state.benchmark_plot_logged:
                                _log_event(
                                    "benchmark_plot_data",
                                    {
                                        "rows": len(results_df),
                                        "missing_sor": missing_sor,
                                        "missing_domains": missing_domains,
                                        "algorithms": sorted(
                                            results_df.get("algorithm", pd.Series(dtype=str))
                                            .unique()
                                            .tolist()
                                        ),
                                        "sample_scenarios": scenario_series.head(5).tolist(),
                                    },
                                )
                                st.session_state.benchmark_plot_logged = True
                            if missing_sor or missing_domains:
                                st.warning(
                                    "Some scenarios do not follow `SOR<number>_D<number>`. "
                                    "These items are excluded from the charts."
                                )
                            plot_df = results_df.dropna(subset=["sor", "domains"]).copy()
                            plot_df["sor"] = plot_df["sor"].astype(float)
                            plot_df["domains"] = plot_df["domains"].astype(float)
                            if plot_df.empty:
                                st.info("Not enough data to render charts.")
                            else:
                                sor_order = [2, 4, 8, 16]
                                domain_order = sorted(plot_df["domains"].unique().tolist())
                                st.subheader("Execution Time (ET) by SOR")
                                et_fig = px.box(
                                    plot_df,
                                    x="algorithm",
                                    y="ET",
                                    color="algorithm",
                                    facet_col="sor",
                                    category_orders={"sor": sor_order},
                                    color_discrete_sequence=["#5C7C6F", "#8A9A86", "#A27A3F", "#7B8FA1", "#8A4D4D"],
                                )
                                _apply_plotly_theme(et_fig)
                                et_fig.update_layout(yaxis_title="Execution Time (s)")
                                st.plotly_chart(et_fig, use_container_width=True, key="bench_et_box")
                                st.caption("ET: execution time (s). Distribution by algorithm and SOR.")
                                et_csv = plot_df[
                                    ["scenario", "algorithm", "sor", "domains", "ET"]
                                ].to_csv(index=False)
                                st.download_button(
                                    "Download ET data (CSV)",
                                    data=et_csv,
                                    file_name="benchmark_et.csv",
                                    mime="text/csv",
                                    key="download_et",
                                )

                                st.subheader("Accuracy (ACC) by SOR")
                                acc_fig = px.box(
                                    plot_df,
                                    x="algorithm",
                                    y="ACC",
                                    color="algorithm",
                                    facet_col="sor",
                                    category_orders={"sor": sor_order},
                                    color_discrete_sequence=["#5C7C6F", "#8A9A86", "#A27A3F", "#7B8FA1", "#8A4D4D"],
                                )
                                _apply_plotly_theme(acc_fig)
                                acc_fig.update_layout(yaxis_title="Accuracy (ACC)")
                                st.plotly_chart(acc_fig, use_container_width=True, key="bench_acc_box")
                                st.caption("ACC: (TP+TN)/(TP+TN+FP+FN) by algorithm and SOR.")
                                acc_csv = plot_df[
                                    ["scenario", "algorithm", "sor", "domains", "ACC"]
                                ].to_csv(index=False)
                                st.download_button(
                                    "Download ACC data (CSV)",
                                    data=acc_csv,
                                    file_name="benchmark_acc.csv",
                                    mime="text/csv",
                                    key="download_acc",
                                )

                                st.subheader("Success Frequency Jaccard (SF-Jaccard) by Domains")
                                sf_fig = px.line(
                                    plot_df,
                                    x="domains",
                                    y="SF",
                                    color="algorithm",
                                    markers=True,
                                    facet_col="sor",
                                    category_orders={"sor": sor_order, "domains": domain_order},
                                    color_discrete_sequence=["#5C7C6F", "#8A9A86", "#A27A3F", "#7B8FA1", "#8A4D4D"],
                                )
                                _apply_plotly_theme(sf_fig)
                                sf_fig.update_layout(yaxis_title="SF-Jaccard")
                                st.plotly_chart(sf_fig, use_container_width=True, key="bench_sf_line")
                                st.caption("SF-Jaccard: Jaccard * N_pairs / ET. Accuracy remains visible only as a diagnostic under pair imbalance.")
                                sf_csv = plot_df[
                                    ["scenario", "algorithm", "sor", "domains", "SF", "sf_accuracy"]
                                ].to_csv(index=False)
                                st.download_button(
                                    "Download SF-Jaccard data (CSV)",
                                    data=sf_csv,
                                    file_name="benchmark_sf.csv",
                                    mime="text/csv",
                                    key="download_sf",
                                )
                        else:
                            st.info("Results without a scenario column.")
                        if st.session_state.benchmark_params:
                            st.subheader("Experiment Summary")
                            summary_lines = [
                                f"Directory: {st.session_state.benchmark_params.get('benchmark_dir')}",
                                f"Scenarios: {st.session_state.benchmark_params.get('scenarios')}",
                                f"Runs per algorithm: {st.session_state.benchmark_params.get('runs')}",
                                f"Algorithms: {', '.join(st.session_state.benchmark_params.get('algorithms', []))}",
                                f"GNN available: {st.session_state.benchmark_params.get('gnn_available')}",
                                "Missing pickles: "
                                + ", ".join(st.session_state.benchmark_params.get("missing_pickles", [])),
                                "Missing real pairs: "
                                + ", ".join(st.session_state.benchmark_params.get("missing_real_pairs", [])),
                                f"True pairs (min/max): {st.session_state.benchmark_params.get('true_pairs_min')} / "
                                f"{st.session_state.benchmark_params.get('true_pairs_max')}",
                            ]
                            st.markdown("\n".join(f"- {line}" for line in summary_lines))

            elif bench_section == "Article Reproducibility":
                _render_article_reproducibility()

        if st.session_state.active_module == "Scenario Studio":
            left_col, right_col = st.columns([1, 2], gap="large")
            with left_col:
                left_pane = st.container(height=960, border=False)
            with right_col:
                right_pane = st.container(height=960, border=False)

            with left_pane:
                st.caption("Build, review, publish, and train curated benchmark scenarios.")
                st.markdown(
                    "<div class='iso-panel iso-panel-journey'><div class='iso-step-title'>Main Journey</div>"
                    "<p class='iso-step-text'>Choose the source, load the lineage graph, review duplicate pairs, then train and save the benchmark model.</p></div>",
                    unsafe_allow_html=True,
                )
                _render_step_header(
                    "Step 1",
                    "Input method",
                    "Choose how the scenario enters Isomera. Use Scenario Warehouse for the main benchmark workflow. Use the others only when needed.",
                    key="scenario_step_1",
                )
                source_mode = st.selectbox(
                    "Input method",
                    options=[
                        "Scenario Warehouse",
                        "GML Catalog",
                        "Manual Builder",
                    ],
                    key="scenario_source_mode",
                )
                if source_mode == "Scenario Warehouse":
                    st.markdown(
                        "<div class='iso-inline-note'>Primary path. First choose the database engine, then the logical database, then one scenario schema. Each benchmark scenario is stored as its own schema inside the selected database.</div>",
                        unsafe_allow_html=True,
                    )
                    _render_step_header(
                        "Step 1A",
                        "Database engine",
                        "Choose which database engine will provide the scenario warehouse. PostgreSQL is the current production path for the benchmark warehouse.",
                        key="scenario_step_1a_db",
                    )
                    selected_engine = st.selectbox(
                        "Database engine",
                        options=["PostgreSQL"],
                        key="studio_database_engine",
                    )
                    base_database_url = st.session_state.scenarios_db_url
                    _render_step_header(
                        "Step 1B",
                        "Database",
                        "Choose the logical database that contains the scenario schemas. In the current setup, the benchmark warehouse lives in one PostgreSQL database and each scenario is a separate schema inside it.",
                        key="scenario_step_1b_db",
                    )
                    available_databases: list[str] = []
                    selected_database_name = st.session_state.get("studio_database_name", "isomera_tpcds_benchmark")
                    try:
                        available_databases = list_available_databases(base_database_url)
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"Database discovery unavailable: {exc}")
                    if available_databases:
                        if selected_database_name not in available_databases:
                            selected_database_name = available_databases[0]
                            st.session_state.studio_database_name = selected_database_name
                        selected_database_name = st.selectbox(
                            "Database",
                            options=available_databases,
                            index=available_databases.index(selected_database_name),
                            key="studio_database_name",
                        )
                    selected_database_url = replace_database_in_url(base_database_url, selected_database_name)
                    st.markdown(
                        "<div class='iso-db-summary'>"
                        f"<p><strong>Engine:</strong> {selected_engine}</p>"
                        f"<p><strong>Database:</strong> {selected_database_name}</p>"
                        f"<p><strong>Connection URL:</strong> {selected_database_url}</p>"
                        "</div>",
                        unsafe_allow_html=True,
                    )
                    try:
                        connection_status = test_database_connection(selected_database_url)
                        scenario_schema_count = len(
                            [schema for schema in list_database_schemas(selected_database_url) if schema.startswith("scenario_")]
                        )
                        st.table(
                            pd.DataFrame(
                                [
                                    {"field": "dialect", "value": connection_status["dialect"]},
                                    {"field": "database", "value": connection_status["database"]},
                                    {"field": "user", "value": connection_status["user"]},
                                    {"field": "all schemas", "value": connection_status["schema_count"]},
                                    {"field": "scenario schemas", "value": scenario_schema_count},
                                    {"field": "tables", "value": connection_status["table_count"]},
                                ]
                            ).set_index("field")
                        )
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"Database connection unavailable: {exc}")

                    if not _psycopg_available() and _backend_label(selected_database_url) == "PostgreSQL":
                        scenario_schemas = []
                        st.warning(
                            "Scenario Warehouse is unavailable in the current interpreter. "
                            f"Current Python: `{sys.executable}`. Launch Isomera with `.venv/bin/python -m streamlit run main/ui/app.py`."
                        )
                    else:
                        try:
                            scenario_schemas = [
                                schema
                                for schema in list_database_schemas(selected_database_url)
                                if schema.startswith("scenario_")
                            ]
                        except Exception as exc:  # noqa: BLE001
                            scenario_schemas = []
                            st.warning(f"Scenario warehouse unavailable: {exc}")
                    if scenario_schemas:
                        _render_step_header(
                            "Step 1C",
                            "Scenario schema",
                            "Pick one scenario schema from the selected database. Isomera will inspect its tables, use the scenario manifest when available, and rebuild the lineage graph for review.",
                            key="scenario_step_1a",
                        )
                        selected_schema = st.selectbox(
                            "Scenario schema",
                            options=scenario_schemas,
                            key="studio_schema_select",
                        )
                        schema_tables = list_schema_tables(selected_database_url, selected_schema)
                        st.caption(
                            f"Engine: {_backend_label(selected_database_url)} | "
                            f"Database: {selected_database_name} | "
                            f"Schema: {selected_schema} | Tables: {len(schema_tables)} | "
                            "Scenario location: one schema per benchmark scenario"
                        )
                        with st.expander("Schema details", expanded=False):
                            st.table(
                                pd.DataFrame(
                                    [
                                        {"field": "engine", "value": _backend_label(selected_database_url)},
                                        {"field": "database", "value": selected_database_name},
                                        {"field": "connection", "value": selected_database_url},
                                        {"field": "schema", "value": selected_schema},
                                        {"field": "table_count", "value": len(schema_tables)},
                                    ]
                                ).set_index("field")
                            )
                            if schema_tables:
                                st.table(pd.DataFrame({"table": schema_tables}))
                            else:
                                st.info("No tables available in this schema.")
                        if st.button("Load scenario from database", key="studio_load_schema"):
                            st.session_state.last_error = None
                            try:
                                graph, warehouse_contract = _build_graph_from_warehouse_contract(
                                    selected_database_url,
                                    selected_schema,
                                )
                                st.session_state.graph = graph
                                st.session_state.initial_graph = graph.copy()
                                st.session_state.graph_source = "Scenario Warehouse"
                                st.session_state.validation_arch_name = "scenario_warehouse"
                                st.session_state.validation_scenario = selected_schema
                                st.session_state.workspace_scenario_name = selected_schema
                                st.session_state.scenario_source_metadata = {
                                    **warehouse_contract,
                                    "mode": "Scenario Warehouse",
                                    "database_url": selected_database_url,
                                    "database_name": selected_database_name,
                                    "schema": selected_schema,
                                    "table_names": warehouse_contract.get("table_names", schema_tables),
                                    "table_count": warehouse_contract.get("table_count", len(schema_tables)),
                                    "api_module": scenario_api_contract().get("module"),
                                    "api_name": scenario_api_contract().get("name"),
                                }
                                guessed_gml = (
                                    DEFAULT_ARCH_ROOT
                                    / "gml"
                                    / f"{selected_schema.replace('scenario_', 'graph_').replace('_sor', '_SOR').replace('_d', '_D')}.gml"
                                )
                                st.session_state.scenario_validation_source_gml = str(guessed_gml) if guessed_gml.exists() else None
                                st.session_state.isomorphic_pairs = []
                                st.session_state.removed_nodes = []
                                st.session_state.labeled_pairs = set()
                                st.session_state.metrics_df = None
                                st.session_state.exec_times = None
                                st.session_state.model_ran = False
                                st.session_state.scenario_review_pairs = []
                                st.session_state.scenario_review_index = 0
                                st.session_state.scenario_review_status = {}
                                st.session_state.scenario_finalized_summary = None
                                _log_event("load_scenario_warehouse", {"schema": selected_schema})
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                _log_exception("studio_load_schema", exc)
                    else:
                        st.info("No scenario schemas available.")
                elif source_mode == "GML Catalog":
                    st.markdown(
                        "<div class='iso-inline-note'>Optional path. Load a stored GML graph when you want portability or when the scenario was not created from the relational warehouse.</div>",
                        unsafe_allow_html=True,
                    )
                    arch_options = [arch["name"] for arch in _list_architectures()]
                    selected_arch_name = st.selectbox(
                        "Architecture",
                        options=arch_options,
                        key="studio_arch_select",
                    )
                    arch = _get_architecture(selected_arch_name)
                    if arch:
                        scenarios = _list_scenarios(arch["root"])
                        if scenarios:
                            selected_scenario = st.selectbox(
                                "Scenario",
                                options=scenarios,
                                key="studio_scenario_select",
                            )
                            if st.button("Load selected scenario", key="studio_load_scenario"):
                                st.session_state.last_error = None
                                try:
                                    gml_path = _find_gml_for_scenario(
                                        Path(arch["root"]),
                                        selected_scenario,
                                        bool(arch["readonly"]),
                                    )
                                    if gml_path is None:
                                        st.warning("No .gml found for this scenario.")
                                    else:
                                        materialized = materialize_gml_scenario(
                                            gml_path,
                                            source_mode="GML Catalog",
                                            source_metadata={
                                                "architecture": selected_arch_name,
                                                "scenario": selected_scenario,
                                                "graph_build_steps": [
                                                    "Opened the selected GML asset from the catalog.",
                                                    "Parsed nodes and edges from the GML file.",
                                                    "Normalized edge direction to SOR -> SOT -> SPEC.",
                                                    "Loaded the directed lineage graph into the workspace through the Scenario Materialization API.",
                                                ],
                                            },
                                        )
                                        graph = materialized.graph
                                        st.session_state.graph = graph
                                        st.session_state.initial_graph = graph.copy()
                                        st.session_state.graph_source = "GML Catalog"
                                        st.session_state.validation_arch_name = selected_arch_name
                                        st.session_state.validation_scenario = selected_scenario
                                        st.session_state.workspace_scenario_name = selected_scenario
                                        st.session_state.scenario_source_metadata = {
                                            **materialized.source_metadata,
                                            "api_module": scenario_api_contract().get("module"),
                                            "api_name": scenario_api_contract().get("name"),
                                        }
                                        st.session_state.scenario_validation_source_gml = str(gml_path)
                                        st.session_state.isomorphic_pairs = []
                                        st.session_state.removed_nodes = []
                                        st.session_state.labeled_pairs = set()
                                        st.session_state.metrics_df = None
                                        st.session_state.exec_times = None
                                        st.session_state.model_ran = False
                                        st.session_state.scenario_review_pairs = []
                                        st.session_state.scenario_review_index = 0
                                        st.session_state.scenario_review_status = {}
                                        st.session_state.scenario_finalized_summary = None
                                        _log_event(
                                            "load_scenario_studio",
                                            {"architecture": selected_arch_name, "scenario": selected_scenario},
                                        )
                                        st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    _log_exception("studio_load_scenario", exc)
                        else:
                            st.info("No scenarios found in the selected architecture.")
                    with st.expander("Upload a new `.gml` into the catalog", expanded=False):
                        uploaded_gml = st.file_uploader("Upload `.gml` file", type=["gml"], key="studio_gml_upload")
                        uploaded_name = st.text_input("Scenario name", value="uploaded_scenario", key="studio_upload_name")
                        if st.button("Load uploaded GML", key="studio_load_upload", disabled=uploaded_gml is None):
                            st.session_state.last_error = None
                            try:
                                target_dir = _app_path("data/graphs/uploads")
                                target_dir.mkdir(parents=True, exist_ok=True)
                                target_path = target_dir / f"{uploaded_name}.gml"
                                target_path.write_bytes(uploaded_gml.getbuffer())
                                materialized = materialize_gml_scenario(
                                    target_path,
                                    source_mode="Uploaded GML",
                                    source_metadata={
                                        "scenario": uploaded_name,
                                        "graph_build_steps": [
                                            "Saved the uploaded GML file into the local uploads folder.",
                                            "Parsed nodes and edges from the uploaded file.",
                                            "Normalized edge direction to SOR -> SOT -> SPEC.",
                                            "Loaded the directed lineage graph into the workspace through the Scenario Materialization API.",
                                        ],
                                    },
                                )
                                graph = materialized.graph
                                st.session_state.graph = graph
                                st.session_state.initial_graph = graph.copy()
                                st.session_state.graph_source = "Uploaded GML"
                                st.session_state.validation_arch_name = "uploaded"
                                st.session_state.validation_scenario = uploaded_name
                                st.session_state.workspace_scenario_name = uploaded_name
                                st.session_state.scenario_source_metadata = {
                                    **materialized.source_metadata,
                                    "api_module": scenario_api_contract().get("module"),
                                    "api_name": scenario_api_contract().get("name"),
                                }
                                st.session_state.scenario_validation_source_gml = str(target_path)
                                st.session_state.isomorphic_pairs = []
                                st.session_state.removed_nodes = []
                                st.session_state.labeled_pairs = set()
                                st.session_state.metrics_df = None
                                st.session_state.exec_times = None
                                st.session_state.model_ran = False
                                st.session_state.scenario_review_pairs = []
                                st.session_state.scenario_review_index = 0
                                st.session_state.scenario_review_status = {}
                                st.session_state.scenario_finalized_summary = None
                                _log_event("load_uploaded_gml", {"scenario": uploaded_name, "path": str(target_path)})
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                _log_exception("studio_load_upload", exc)
                else:
                    st.markdown(
                        "<div class='iso-inline-note'>Optional path. Define nodes and edges manually only when the scenario does not exist yet in the warehouse or in the GML catalog.</div>",
                        unsafe_allow_html=True,
                    )
                    compact_cols = st.columns([1, 1, 2], gap="small")
                    node_count = compact_cols[0].number_input(
                        "Nodes",
                        min_value=1,
                        max_value=200,
                        value=5,
                        key="manual_nodes_count",
                    )
                    edge_count = compact_cols[1].number_input(
                        "Edges",
                        min_value=0,
                        max_value=400,
                        value=4,
                        key="manual_edges_count",
                    )
                    if compact_cols[2].button("Initialize manual editor", key="manual_init", use_container_width=True):
                        st.session_state.manual_nodes_df = pd.DataFrame(
                            {"node": [f"NODE_{i+1}" for i in range(int(node_count))], "type": ["SOT"] * int(node_count)}
                        )
                        st.session_state.manual_edges_df = pd.DataFrame(
                            {"from": [""] * int(edge_count), "to": [""] * int(edge_count)}
                        )
                    nodes_df = st.data_editor(
                        st.session_state.manual_nodes_df,
                        num_rows="dynamic",
                        width="stretch",
                        key="manual_nodes_editor",
                    )
                    edges_df = st.data_editor(
                        st.session_state.manual_edges_df,
                        num_rows="dynamic",
                        width="stretch",
                        key="manual_edges_editor",
                    )
                    build_cols = st.columns(2, gap="small")
                    if build_cols[0].button("Build manual graph", key="manual_build"):
                        st.session_state.last_error = None
                        st.session_state.graph_source = "Manual"
                        st.session_state.benchmark_results = None
                        st.session_state.benchmark_exec_stats = None
                        st.session_state.benchmark_step1 = False
                        st.session_state.benchmark_step2 = False
                        st.session_state.benchmark_step3 = False
                        st.session_state.benchmark_step4 = False
                        st.session_state.benchmark_stopped = False
                        with st.spinner("Construindo grafo manual..."):
                            try:
                                graph = nx.DiGraph()
                                for _, row in nodes_df.iterrows():
                                    if isinstance(row.get("node"), str) and row["node"].strip():
                                        graph.add_node(row["node"].strip(), type=row.get("type", ""))
                                for _, row in edges_df.iterrows():
                                    src = str(row.get("from", "")).strip()
                                    dst = str(row.get("to", "")).strip()
                                    if src and dst:
                                        graph.add_edge(src, dst)
                                materialized = materialize_graph(
                                    graph,
                                    source_mode="Manual Builder",
                                    source_metadata={
                                        "scenario": st.session_state.get("manual_scenario_name", "manual_scenario"),
                                        "graph_build_steps": [
                                            "Created nodes from the manual editor.",
                                            "Created edges from the manual editor.",
                                            "Normalized the graph through the Scenario Materialization API.",
                                        ],
                                    },
                                )
                                graph = materialized.graph
                                st.session_state.graph = graph
                                st.session_state.initial_graph = graph.copy()
                                st.session_state.layout_seed = 42
                                st.session_state.isomorphic_pairs = []
                                st.session_state.removed_nodes = []
                                st.session_state.labeled_pairs = set()
                                st.session_state.metrics_df = None
                                st.session_state.exec_times = None
                                st.session_state.graph_source = "Manual Builder"
                                st.session_state.validation_scenario = None
                                st.session_state.validation_arch_name = DEFAULT_ARCH_NAME
                                st.session_state.workspace_scenario_name = st.session_state.get(
                                    "manual_scenario_name", "manual_scenario"
                                )
                                st.session_state.scenario_source_metadata = {
                                    **materialized.source_metadata,
                                    "api_module": scenario_api_contract().get("module"),
                                    "api_name": scenario_api_contract().get("name"),
                                }
                                st.session_state.scenario_validation_source_gml = None
                                st.session_state.scenario_review_pairs = []
                                st.session_state.scenario_review_index = 0
                                st.session_state.scenario_review_status = {}
                                st.session_state.model_ran = False
                                _log_event(
                                    "build_manual_graph",
                                    {"nodes": graph.number_of_nodes(), "edges": graph.number_of_edges()},
                                )
                                st.rerun()
                            except Exception as exc:  # noqa: BLE001
                                _log_exception("build_manual_graph", exc)
                    manual_arch_name = build_cols[1].text_input(
                        "Save benchmark name",
                        value="manual_arch",
                        key="manual_arch_name",
                    )
                    manual_scenario_name = st.text_input(
                        "Save scenario name",
                        value="manual_scenario",
                        key="manual_scenario_name",
                    )
                    if st.button("Save manual as architecture", key="manual_save"):
                        st.session_state.last_error = None
                        if st.session_state.graph is None:
                            st.warning("Crie o grafo manual primeiro.")
                        else:
                            try:
                                arch_root = CUSTOM_ARCH_ROOT / manual_arch_name
                                gml_dir = arch_root / "gml"
                                validations_dir = arch_root / "validations" / manual_scenario_name
                                real_pairs_dir = arch_root / "real_pairs"
                                gml_dir.mkdir(parents=True, exist_ok=True)
                                validations_dir.mkdir(parents=True, exist_ok=True)
                                real_pairs_dir.mkdir(parents=True, exist_ok=True)
                                gml_path = gml_dir / f"{manual_scenario_name}.gml"
                                save_graph_gml(st.session_state.graph, gml_path)
                                _save_graph_image(
                                    st.session_state.graph,
                                    validations_dir / "graph_full.png",
                                    seed=st.session_state.layout_seed,
                                )
                                _log_event(
                                    "save_manual_architecture",
                                    {"architecture": manual_arch_name, "scenario": manual_scenario_name},
                                )
                                st.success(f"Saved manual architecture to {arch_root}")
                            except Exception as exc:  # noqa: BLE001
                                _log_exception("save_manual_architecture", exc)

                if st.session_state.initial_graph is not None:
                    _render_step_header(
                        "Step 2",
                        "Candidate filters",
                        "Choose which lineage scopes should be compared and which structural constraints should be applied before the manual review queue is created.",
                        key="scenario_step_2",
                    )
                    scenario_name = (
                        st.session_state.get("workspace_scenario_name")
                        or st.session_state.get("validation_scenario")
                        or "workspace_scenario"
                    )
                    st.markdown("**Candidate Filters**")
                    total_pairs = _candidate_validation_pairs(
                        st.session_state.initial_graph,
                        include_sor=True,
                        include_sot=True,
                        include_spec=True,
                        same_layer_only=False,
                        same_domain_only=False,
                        same_indegree_only=False,
                        same_outdegree_only=False,
                        same_parent_signature_only=False,
                        same_child_signature_only=False,
                    )
                    selected_scopes = _multi_choice_pills(
                        "Lineage scope",
                        ["SOR", "SOT", "SPEC"],
                        key="review_scope_pills",
                        default=["SOT", "SPEC"],
                        help="Choose which kinds of lineage nodes will generate candidate review pairs.",
                    )
                    constraint_options = [
                        "Same layer only",
                        "Same domain only",
                        "Same input count",
                        "Same output count",
                        "Same parent signature",
                        "Same child signature",
                    ]
                    selected_constraints = _multi_choice_pills(
                        "Structural constraints",
                        constraint_options,
                        key="review_constraint_pills",
                        default=["Same layer only"],
                        help="Apply structural constraints before the review queue is generated.",
                    )
                    include_sor = "SOR" in selected_scopes
                    include_sot = "SOT" in selected_scopes
                    include_spec = "SPEC" in selected_scopes
                    same_layer = "Same layer only" in selected_constraints
                    same_domain = "Same domain only" in selected_constraints
                    same_indegree = "Same input count" in selected_constraints
                    same_outdegree = "Same output count" in selected_constraints
                    same_parent_sig = "Same parent signature" in selected_constraints
                    same_child_sig = "Same child signature" in selected_constraints
                    candidate_pairs = _candidate_validation_pairs(
                        st.session_state.initial_graph,
                        include_sor=include_sor,
                        include_sot=include_sot,
                        include_spec=include_spec,
                        same_layer_only=same_layer,
                        same_domain_only=same_domain,
                        same_indegree_only=same_indegree,
                        same_outdegree_only=same_outdegree,
                        same_parent_signature_only=same_parent_sig,
                        same_child_signature_only=same_child_sig,
                    )
                    st.caption(
                        _candidate_filter_status(
                            st.session_state.initial_graph,
                            candidate_pairs,
                            include_sor=include_sor,
                            include_sot=include_sot,
                            include_spec=include_spec,
                            same_layer_only=same_layer,
                            same_domain_only=same_domain,
                            same_indegree_only=same_indegree,
                            same_outdegree_only=same_outdegree,
                            same_parent_signature_only=same_parent_sig,
                            same_child_signature_only=same_child_sig,
                        )
                    )
                    if include_spec:
                        st.caption("SPEC review uses the complete upstream lineage of each SPEC node, not only the final SPEC vertex.")
                    reviewed_count = len(st.session_state.scenario_review_status)
                    summary_cols = st.columns(3, gap="small")
                    summary_cols[0].metric("All pair combinations", len(total_pairs))
                    summary_cols[1].metric("Pairs after filters", len(candidate_pairs))
                    summary_cols[2].metric("Reviewed pairs", reviewed_count)
                    save_name = st.text_input("Curated scenario name", value=scenario_name, key="curated_scenario_name")
                    existing_benchmarks = [arch["name"] for arch in _list_architectures() if arch["name"] != DEFAULT_ARCH_NAME]
                    _render_step_header(
                        "Step 2A",
                        "Benchmark target",
                        "Choose whether this curated scenario should create a new benchmark catalog or be added to an existing one.",
                        key="scenario_step_2a",
                    )
                    benchmark_mode = st.selectbox(
                        "Benchmark target",
                        options=["Create new benchmark", "Use existing benchmark"],
                        key="curated_benchmark_mode",
                    )
                    if benchmark_mode == "Use existing benchmark" and existing_benchmarks:
                        benchmark_name = st.selectbox(
                            "Existing benchmark",
                            options=existing_benchmarks,
                            key="curated_existing_benchmark_name",
                        )
                    else:
                        benchmark_name = st.text_input(
                            "New benchmark name",
                            value=st.session_state.get("curated_benchmark_name", "tpc_ds_v2"),
                            key="curated_benchmark_name",
                        )
                    publish_as_benchmark = st.checkbox("Publish in Benchmark & Examples", value=True, key="publish_curated_benchmark")
                    if st.button("Start pair review", key="review_apply_filters"):
                        st.session_state.scenario_review_pairs = candidate_pairs
                        st.session_state.scenario_review_index = 0
                        st.session_state.scenario_finalized_summary = None
                        _log_event(
                            "scenario_filters_applied",
                            {
                                "scenario": scenario_name,
                                "total_pairs": len(total_pairs),
                                "candidate_pairs": len(candidate_pairs),
                                "filters": {
                                    "include_sor": include_sor,
                                    "include_sot": include_sot,
                                    "include_spec": include_spec,
                                    "same_layer": same_layer,
                                    "same_domain": same_domain,
                                    "same_indegree": same_indegree,
                                    "same_outdegree": same_outdegree,
                                    "same_parent_signature": same_parent_sig,
                                    "same_child_signature": same_child_sig,
                                },
                            },
                        )
                        _record_article_report(
                            "scenario_filtering",
                            {
                                "scenario": scenario_name,
                                "total_pairs": len(total_pairs),
                                "candidate_pairs": len(candidate_pairs),
                                "benchmark_name": benchmark_name,
                                "filters": {
                                    "include_sor": include_sor,
                                    "include_sot": include_sot,
                                    "include_spec": include_spec,
                                    "same_layer": same_layer,
                                    "same_domain": same_domain,
                                    "same_indegree": same_indegree,
                                    "same_outdegree": same_outdegree,
                                    "same_parent_signature": same_parent_sig,
                                    "same_child_signature": same_child_sig,
                                },
                            },
                        )
                        st.rerun()

                    active_pairs = st.session_state.scenario_review_pairs
                    if active_pairs:
                        st.caption(f"Review queue ready: {len(active_pairs)} candidate pairs. Decisions are autosaved after every click.")
                    else:
                        st.info("Select a source, load one scenario, then the review filters will appear here.")

                _render_step_header(
                    "Step 3",
                    "Model training",
                    "Train the benchmark-specific model after publishing at least one curated scenario into a benchmark catalog.",
                    key="scenario_step_3",
                )
                st.subheader("Model Training")
                available_benchmarks = [arch["name"] for arch in _list_architectures() if arch["name"] != DEFAULT_ARCH_NAME]
                if not available_benchmarks:
                    st.info("Finalize and publish at least one curated scenario before training a benchmark-specific GNN.")
                else:
                    model_family_name = st.selectbox(
                        "Model family",
                        options=list(MODEL_FAMILIES.keys()),
                        key="train_model_family",
                    )
                    model_family = MODEL_FAMILIES[model_family_name]
                    title_cols = st.columns([5, 1], gap="small")
                    title_cols[0].markdown(
                        f"**{model_family['official_name']}**  \n"
                        f"{model_family['short_blurb']}"
                    )
                    with title_cols[1]:
                        _info_popover(_model_family_help_markdown(model_family), key="model_family_info")
                    st.caption(str(model_family["notes"]))
                    protocol_options = list(TRAINING_PROTOCOL_OPTIONS.keys())
                    if st.session_state.get("train_experiment_protocol") not in protocol_options:
                        st.session_state.train_experiment_protocol = "single_configuration"
                    protocol_cols = st.columns([5, 1], gap="small")
                    training_protocol = protocol_cols[0].selectbox(
                        "Isomera protocol",
                        options=protocol_options,
                        format_func=lambda key: str(TRAINING_PROTOCOL_OPTIONS[str(key)]["label"]),
                        key="train_experiment_protocol",
                        help="Choose manual training or the reproducible Isomera staged protocol for model selection.",
                    )
                    with protocol_cols[1]:
                        _info_popover(_training_protocol_help_markdown(), key="training_protocol_info")
                    st.caption(str(TRAINING_PROTOCOL_OPTIONS[str(training_protocol)]["description"]))
                    if training_protocol == "isomera_staged_protocol":
                        with st.expander("Isomera Staged Protocol", expanded=True):
                            st.dataframe(pd.DataFrame(_article_hyperparameter_protocol_rows()), width="stretch", hide_index=True)
                            st.caption(
                                "Reduced grid: 108 configs. Screening: 1620 trainings. Final validation: 300 trainings. "
                                "Total before final benchmark: 1920 trainings."
                            )
                            if st.button("Record Isomera protocol", key="record_hypersearch_protocol", use_container_width=True):
                                _record_article_report(
                                    "isomera_staged_protocol",
                                    {
                                        "benchmark_name": st.session_state.get("benchmark_catalog_name") or "general",
                                        "scenario": st.session_state.get("workspace_scenario_name") or "workspace",
                                        "model_family_name": model_family_name,
                                        "experiment_protocol": training_protocol,
                                        "experiment_protocol_label": str(TRAINING_PROTOCOL_OPTIONS[str(training_protocol)]["label"]),
                                        "publication_tables": {
                                            "hyperparameter_search_grid": _article_hyperparameter_grid_rows(),
                                            "hyperparameter_search_protocol": _article_hyperparameter_protocol_rows(),
                                        },
                                        "formula_parameter_mapping": {
                                            "screening_trainings": "3 benchmarks * 5 scenarios * 108 configs = 1620",
                                            "final_validation_trainings": "3 benchmarks * 20 scenarios * 5 top configs = 300",
                                            "selection_metric": "SF-Jaccard",
                                        },
                                    },
                                )
                                st.success("Protocol captured for Research Reports.")
                    st.markdown("**Model configuration**")
                    train_cols = st.columns(3, gap="small")
                    param_values: dict[str, int] = {}
                    parameter_defs = list(model_family["parameters"])
                    for index, param in enumerate(parameter_defs):
                        host_col = train_cols[index % 3]
                        param_values[param["key"]] = int(
                            host_col.number_input(
                                param["label"],
                                min_value=int(param["min"]),
                                max_value=int(param["max"]),
                                value=int(param["value"]),
                                key=f"train_{param['key']}",
                                help=str(param["help"]),
                            )
                        )
                        host_col.markdown(
                            f"<div class='iso-field-help'>{param['help']}</div>",
                            unsafe_allow_html=True,
                        )
                    optimizer = st.selectbox(
                        "Optimizer",
                        options=list(model_family["optimizers"]),
                        format_func=lambda key: _training_option_label(TRAINING_OPTIMIZER_OPTIONS, str(key)),
                        key="train_optimizer_key",
                        help="Algoritmo real usado para atualizar os pesos do modelo.",
                    )
                    st.caption(_training_option_caption(TRAINING_OPTIMIZER_OPTIONS, str(optimizer)))
                    loss_name = st.selectbox(
                        "Loss",
                        options=list(TRAINING_LOSS_OPTIONS.keys()),
                        format_func=lambda key: _training_option_label(TRAINING_LOSS_OPTIONS, str(key)),
                        key="train_loss_key",
                        help="Função de perda real aplicada ao logit produzido pelo classificador binário.",
                    )
                    st.caption(_training_option_caption(TRAINING_LOSS_OPTIONS, str(loss_name)))
                    split_cols = st.columns(2, gap="small")
                    train_split_pct = int(
                        split_cols[0].number_input(
                            "Train split %",
                            min_value=50,
                            max_value=95,
                            value=80,
                            key="train_split_pct",
                            help="Percentual do dataset supervisionado usado para treino. O restante vira validação/teste local.",
                        )
                    )
                    balance_strategy = split_cols[1].selectbox(
                        "Balancing strategy",
                        options=list(TRAINING_BALANCE_OPTIONS.keys()),
                        index=list(TRAINING_BALANCE_OPTIONS.keys()).index("class_weighted_loss"),
                        format_func=lambda key: _training_option_label(TRAINING_BALANCE_OPTIONS, str(key)),
                        key="train_balance_strategy_key",
                        help="Estratégia real usada para reduzir o efeito do desbalanceamento entre target=0 e target=1.",
                    )
                    split_cols[1].caption(_training_option_caption(TRAINING_BALANCE_OPTIONS, str(balance_strategy)))
                    runtime_cols = st.columns(5, gap="small")
                    gnn_device = runtime_cols[0].selectbox(
                        "Device",
                        options=["cpu", "auto", "mps"],
                        index=0,
                        key="train_gnn_device",
                        help="CPU is deterministic default. MPS uses Apple Metal when PyTorch exposes it in this app session.",
                    )
                    gnn_batched_inference = runtime_cols[1].checkbox(
                        "Batched inference",
                        value=True,
                        key="train_gnn_batched_inference",
                        help="Caches one embedding per subgraph and evaluates candidate pairs in chunks during benchmark prediction.",
                    )
                    gnn_inference_batch_size = int(
                        runtime_cols[2].selectbox(
                            "Inference batch",
                            options=[256, 1024, 4096, 8192, 16384],
                            index=2,
                            key="train_gnn_inference_batch_size",
                        )
                    )
                    gnn_encoder_batch_size = int(
                        runtime_cols[3].selectbox(
                            "Encoder batch",
                            options=[8, 16, 32, 64, 128, 256],
                            index=3,
                            key="train_gnn_encoder_batch_size",
                            help="Number of subgraph embeddings computed together before pair classification.",
                        )
                    )
                    runtime_cols[4].caption(
                        "MPS helps only when the batch is large enough to offset Metal dispatch overhead."
                    )

                    st.markdown("**Training data and save destination**")
                    st.caption(
                        "This selects the curated benchmark data used for training and the destination where the generated `.pkl` will be registered."
                    )
                    default_benchmark = st.session_state.get("benchmark_catalog_name")
                    if default_benchmark not in available_benchmarks:
                        default_benchmark = available_benchmarks[0]
                    target_benchmark = st.selectbox(
                        "Benchmark catalog",
                        options=available_benchmarks,
                        index=available_benchmarks.index(default_benchmark),
                        key="train_target_benchmark",
                    )
                    manifest = _load_benchmark_manifest(target_benchmark)
                    benchmark_scenarios = sorted((manifest.get("scenarios") or {}).keys())
                    if not benchmark_scenarios:
                        st.info("This benchmark has no curated scenarios yet.")
                    else:
                        default_training_scenarios = [
                            scenario
                            for scenario in benchmark_scenarios
                            if scenario == st.session_state.get("workspace_scenario_name")
                        ] or benchmark_scenarios[:1]
                        selected_training_scenarios = st.multiselect(
                            "Training scenarios",
                            options=benchmark_scenarios,
                            default=default_training_scenarios,
                            key="train_selected_scenarios",
                        )
                        model_name_default = f"{_sanitize_benchmark_name(target_benchmark)}_gnn"
                        model_name = st.text_input(
                            "Model artifact name",
                            value=model_name_default,
                            key="train_model_name",
                            help="Final `.pkl` name. After training it is registered into the selected benchmark catalog.",
                        )
                        st.caption(
                            f"Save destination after training: benchmark `{target_benchmark}` with {len(selected_training_scenarios)} selected scenario(s)."
                        )
                        job = st.session_state.get("training_job")
                        job_running = bool(job and _training_job_is_running(job.get("pid")))
                        train_action_cols = st.columns(3, gap="small")
                        if train_action_cols[0].button(
                            "Train model",
                            key="scenario_training_run",
                            type="primary",
                            disabled=job_running,
                        ):
                            if not selected_training_scenarios:
                                st.warning("Select at least one curated scenario.")
                            else:
                                try:
                                    benchmark_root = _ensure_benchmark_structure(target_benchmark)
                                    scenario_specs: list[ScenarioTrainingSpec] = []
                                    for scenario in selected_training_scenarios:
	                                        scenario_entry = (manifest.get("scenarios") or {}).get(scenario, {})
	                                        graph_path = Path(str(scenario_entry.get("gml_path", "")))
	                                        labels_path = Path(str(scenario_entry.get("labels_path", "")))
	                                        supervised_labels_path = Path(str(scenario_entry.get("validation_dataset_path", "")))
	                                        if not supervised_labels_path.exists():
	                                            candidate_supervised_path = benchmark_root / "validations" / scenario / "validation_dataset.csv"
	                                            supervised_labels_path = candidate_supervised_path if candidate_supervised_path.exists() else Path()
	                                        if not graph_path.exists() or not labels_path.exists():
	                                            raise FileNotFoundError(
	                                                f"Scenario assets missing for `{scenario}` in benchmark `{target_benchmark}`."
	                                            )
	                                        scenario_specs.append(
	                                            ScenarioTrainingSpec(
	                                                scenario_name=scenario,
	                                                graph_path=graph_path,
	                                                labels_path=labels_path,
	                                                supervised_labels_path=supervised_labels_path if supervised_labels_path.exists() else None,
	                                            )
	                                        )
                                    sanitized_model_name = _sanitize_benchmark_name(model_name)
                                    model_path = benchmark_root / "models" / f"{sanitized_model_name}.pkl"
                                    job_id = f"{_sanitize_benchmark_name(target_benchmark)}_{sanitized_model_name}_{int(time.time())}"
                                    job_paths = _training_job_paths(job_id)
                                    config = {
                                        "job_id": job_id,
                                        "benchmark_name": target_benchmark,
                                        "scenario_names": selected_training_scenarios,
                                        "scenario_specs": [
                                            {
                                                "scenario_name": spec.scenario_name,
                                                "graph_path": str(spec.graph_path),
                                                "labels_path": str(spec.labels_path),
                                                "supervised_labels_path": str(spec.supervised_labels_path) if spec.supervised_labels_path else "",
                                            }
                                            for spec in scenario_specs
                                        ],
                                        "model_family": str(model_family["key"]),
                                        "model_label": model_family_name,
                                        "experiment_protocol": training_protocol,
                                        "experiment_protocol_label": str(TRAINING_PROTOCOL_OPTIONS[str(training_protocol)]["label"]),
                                        "model_name": sanitized_model_name,
                                        "model_path": str(model_path),
                                        "progress_path": str(job_paths["progress"]),
                                        "stop_flag_path": str(job_paths["stop"]),
                                        "epochs": param_values["epochs"],
                                        "learning_rate": param_values["learning_rate_scaled"] / 10000.0,
                                        "hidden_channels": param_values["hidden_channels"],
                                        "dropout": param_values["dropout_pct"] / 100.0,
                                        "negative_ratio": param_values["negative_ratio"],
                                        "batch_size": param_values["batch_size"],
                                        "train_ratio": train_split_pct / 100.0,
                                        "balance_strategy": balance_strategy,
                                        "balance_strategy_label": _training_option_label(TRAINING_BALANCE_OPTIONS, str(balance_strategy)),
                                        "seed": param_values["seed"],
                                        "optimizer_name": optimizer,
                                        "optimizer_label": _training_option_label(TRAINING_OPTIMIZER_OPTIONS, str(optimizer)),
                                        "loss_name": loss_name,
                                        "loss_label": _training_option_label(TRAINING_LOSS_OPTIONS, str(loss_name)),
                                        "device": str(gnn_device),
                                        "batched_inference": bool(gnn_batched_inference),
                                        "inference_batch_size": int(gnn_inference_batch_size),
                                        "encoder_batch_size": int(gnn_encoder_batch_size),
                                    }
                                    job_paths["config"].write_text(json.dumps(config, indent=2), encoding="utf-8")
                                    stdout_handle = job_paths["stdout"].open("w", encoding="utf-8")
                                    stderr_handle = job_paths["stderr"].open("w", encoding="utf-8")
                                    worker_env = os.environ.copy()
                                    worker_env["PYTHONDONTWRITEBYTECODE"] = "1"
                                    worker_env.setdefault("MPLBACKEND", "Agg")
                                    worker_env.setdefault("OMP_NUM_THREADS", "1")
                                    worker_env.setdefault("MKL_NUM_THREADS", "1")
                                    worker_env.setdefault("VECLIB_MAXIMUM_THREADS", "1")
                                    worker_env.setdefault("NUMEXPR_NUM_THREADS", "1")
                                    process = subprocess.Popen(
                                        [
                                            sys.executable,
                                            str(_app_path("core/algorithms/gnn_training_worker.py")),
                                            str(job_paths["config"]),
                                        ],
                                        stdout=stdout_handle,
                                        stderr=stderr_handle,
                                        cwd=str(PROJECT_ROOT),
                                        env=worker_env,
                                    )
                                    stdout_handle.close()
                                    stderr_handle.close()
                                    st.session_state.training_job = {
                                        "job_id": job_id,
                                        "pid": process.pid,
                                        "benchmark_name": target_benchmark,
                                        "model_name": sanitized_model_name,
                                        "model_path": str(model_path),
                                        "progress_path": str(job_paths["progress"]),
                                        "stop_flag_path": str(job_paths["stop"]),
                                        "stdout_path": str(job_paths["stdout"]),
                                        "stderr_path": str(job_paths["stderr"]),
                                        "scenario_names": selected_training_scenarios,
                                        "model_family_name": model_family_name,
                                        "experiment_protocol": training_protocol,
                                        "experiment_protocol_label": str(TRAINING_PROTOCOL_OPTIONS[str(training_protocol)]["label"]),
                                        "optimizer": optimizer,
                                        "optimizer_label": _training_option_label(TRAINING_OPTIMIZER_OPTIONS, str(optimizer)),
                                        "loss_name": loss_name,
                                        "loss_label": _training_option_label(TRAINING_LOSS_OPTIONS, str(loss_name)),
                                        "balance_strategy": balance_strategy,
                                        "balance_strategy_label": _training_option_label(TRAINING_BALANCE_OPTIONS, str(balance_strategy)),
                                    }
                                    _log_event(
                                        "benchmark_gnn_training_started",
                                        {
                                            "benchmark_name": target_benchmark,
                                            "model_name": sanitized_model_name,
                                            "scenario_names": selected_training_scenarios,
                                            "pid": process.pid,
                                        },
                                    )
                                    st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    _log_exception("scenario_training_run", exc)
                        if train_action_cols[1].button(
                            "Refresh status",
                            key="scenario_training_refresh",
                            use_container_width=True,
                        ):
                            st.rerun()
                        if train_action_cols[2].button(
                            "Stop training",
                            key="scenario_training_stop",
                            use_container_width=True,
                            type="secondary",
                            disabled=not job_running,
                        ):
                            if job and job.get("stop_flag_path"):
                                Path(job["stop_flag_path"]).write_text("stop", encoding="utf-8")
                            if job and job.get("progress_path"):
                                progress_file = Path(str(job["progress_path"]))
                                if progress_file.exists():
                                    progress_payload = json.loads(progress_file.read_text(encoding="utf-8"))
                                else:
                                    progress_payload = {}
                                progress_payload["status"] = "stopping"
                                progress_payload["step"] = "stopping"
                                progress_payload["step_detail"] = "Stop requested. Waiting for the worker to finish the current operation."
                                progress_file.write_text(json.dumps(progress_payload, indent=2), encoding="utf-8")
                            if job and job.get("pid"):
                                try:
                                    os.kill(int(job["pid"]), signal.SIGTERM)
                                except OSError:
                                    pass
                            st.rerun()

                        job = st.session_state.get("training_job")
                        if job:
                            progress_path = Path(str(job["progress_path"]))
                            progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {}
                            running = _training_job_is_running(job.get("pid"))
                            status = str(progress.get("status") or ("running" if running else "pending"))
                            current_epoch = int(progress.get("current_epoch", 0))
                            total_epochs = int(progress.get("epochs", param_values["epochs"]))
                            progress_value = float(progress.get("progress", 0.0))
                            st.progress(min(max(progress_value, 0.0), 1.0))
                            avg_epoch_time = None
                            history = progress.get("history", [])
                            if isinstance(history, list) and len(history) >= 2:
                                epoch_times = [float(item.get("epoch_seconds", 0.0)) for item in history if item.get("epoch_seconds")]
                                if epoch_times:
                                    avg_epoch_time = sum(epoch_times) / len(epoch_times)
                            eta_text = ""
                            if avg_epoch_time and current_epoch < total_epochs:
                                eta_secs = avg_epoch_time * (total_epochs - current_epoch)
                                eta_text = f" | ETA ~ {math.ceil(eta_secs)}s"
                            st.caption(
                                f"Model: {job.get('model_name')} | PID: {job.get('pid')} | "
                                f"Status: {status} | Epoch {current_epoch}/{total_epochs}{eta_text}"
                            )
                            st.caption(f"Progress file: {progress_path}")
                            if progress.get("step_detail"):
                                st.caption(str(progress.get("step_detail")))
                            metrics_cols = st.columns(4, gap="small")
                            metrics_cols[0].metric("Train loss", progress.get("train_loss", "-"))
                            metrics_cols[1].metric("Val loss", progress.get("val_loss", "-"))
                            metrics_cols[2].metric("Train acc", progress.get("train_accuracy", "-"))
                            metrics_cols[3].metric("Val acc", progress.get("val_accuracy", "-"))
                            if running:
                                st.info(f"Worker active: {progress.get('step', 'training')}")
                                if progress.get("dataset_summary"):
                                    with st.expander("Training dataset summary", expanded=False):
                                        st.dataframe(pd.DataFrame(progress["dataset_summary"]), width="stretch", hide_index=True)
                                if history:
                                    with st.expander("Epoch history", expanded=True):
                                        st.dataframe(pd.DataFrame(history), width="stretch", hide_index=True)
                                stdout_tail = _read_text_tail(job.get("stdout_path"))
                                stderr_tail = _read_text_tail(job.get("stderr_path"))
                                if stdout_tail or stderr_tail:
                                    with st.expander("Worker logs", expanded=False):
                                        if stdout_tail:
                                            st.code(stdout_tail, language="text")
                                        if stderr_tail:
                                            st.code(stderr_tail, language="text")
                                time.sleep(1)
                                st.rerun()
                            elif progress.get("status") == "completed":
                                model_path = Path(str(job["model_path"]))
                                model_version = register_model_artifact(
                                    st.session_state.backend_db_url,
                                    model_name=str(job["model_name"]),
                                    artifact_path=str(model_path),
                                    metadata={
                                        "benchmark_name": job["benchmark_name"],
                                        "scenario_names": job["scenario_names"],
                                        "training_summary": progress,
                                        "model_family_name": job["model_family_name"],
                                    },
                                )
                                register_artifact(
                                    st.session_state.backend_db_url,
                                    artifact_type="benchmark_model_pickle",
                                    path=str(model_path),
                                    session_id=st.session_state.backend_session_id,
                                    model_version=model_version,
                                    metadata={
                                        "benchmark_name": job["benchmark_name"],
                                        "scenario_names": job["scenario_names"],
                                    },
                                )
                                _register_benchmark_model(
                                    benchmark_name=str(job["benchmark_name"]),
                                    model_name=str(job["model_name"]),
                                    pickle_path=model_path,
                                    metadata_path=model_path.with_suffix(".json"),
                                    source_scenarios=list(job["scenario_names"]),
                                    model_version=model_version,
                                )
                                register_algorithm(
                                    BoundGNNPickleAlgorithm(
                                        f"GNN [{job['model_name']}]",
                                        model_path,
                                        "core.algorithms.gnn_model",
                                    )
                                )
                                _log_event(
                                    "benchmark_gnn_trained",
                                    {
                                        "benchmark_name": job["benchmark_name"],
                                        "model_name": job["model_name"],
                                        "scenario_names": job["scenario_names"],
                                    },
                                )
                                _record_article_report(
                                    "benchmark_gnn_training",
	                                    {
	                                        "benchmark_name": job["benchmark_name"],
	                                        "model_name": job["model_name"],
	                                        "model_path": str(model_path),
	                                        "scenario_names": job["scenario_names"],
	                                        "model_family_name": job["model_family_name"],
	                                        "optimizer": job.get("optimizer"),
	                                        "optimizer_label": job.get("optimizer_label"),
	                                        "optimizer_name": progress.get("optimizer_name"),
	                                        "loss_name": progress.get("loss_name") or job.get("loss_name"),
	                                        "loss_label": job.get("loss_label"),
	                                        "hyperparameters": {
	                                            key: st.session_state.get(f"train_{key}")
	                                            for key in ("epochs", "learning_rate_scaled", "hidden_channels", "dropout_pct", "negative_ratio", "seed")
	                                        },
	                                        "resolved_hyperparameters": {
	                                            "epochs": param_values["epochs"],
	                                            "learning_rate": param_values["learning_rate_scaled"] / 10000.0,
	                                            "hidden_channels": param_values["hidden_channels"],
	                                            "dropout": param_values["dropout_pct"] / 100.0,
                                            "negative_ratio": param_values["negative_ratio"],
                                            "batch_size": param_values["batch_size"],
                                            "train_ratio": train_split_pct / 100.0,
                                            "test_ratio": round(1.0 - train_split_pct / 100.0, 6),
                                            "balance_strategy": job.get("balance_strategy"),
                                            "balance_strategy_label": job.get("balance_strategy_label"),
                                            "balance_summary": progress.get("balance_summary"),
                                            "seed": param_values["seed"],
                                            "device": progress.get("requested_device") or progress.get("device", {}).get("requested_device"),
                                            "resolved_device": progress.get("device", {}).get("resolved_device") if isinstance(progress.get("device"), dict) else None,
                                            "batched_inference": progress.get("batched_inference"),
                                            "inference_batch_size": progress.get("inference_batch_size"),
                                            "encoder_batch_size": progress.get("encoder_batch_size"),
                                        },
                                        "model_docs": {
                                            "official_name": model_family["official_name"],
                                            "version": model_family["version"],
                                            "overview": model_family["docs"]["overview"],
                                            "theory": model_family["docs"]["theory"],
                                            "formulas": model_family["docs"]["formulas"],
                                            "layers": model_family["docs"]["layers"],
                                            "how_to_use": model_family["docs"]["how_to_use"],
                                        },
                                        "training_summary": progress,
                                    },
                                )
                                st.session_state.benchmark_catalog_name = str(job["benchmark_name"])
                                st.session_state.training_job = None
                                st.success(
                                    f"Training completed. Model saved to `{model_path}` and linked to `{job['benchmark_name']}`."
                                )
                            elif progress.get("status") == "failed":
                                st.error(progress.get("error", "Training failed."))
                                stderr_tail = _read_text_tail(job.get("stderr_path"))
                                if stderr_tail:
                                    with st.expander("Worker stderr", expanded=True):
                                        st.code(stderr_tail, language="text")
                            elif progress.get("status") == "stopping":
                                st.warning("Stopping the training job. Waiting for the worker to exit cleanly.")
                            elif progress.get("status") == "stopped":
                                st.warning("Training stopped by the user.")
                            elif status in {"pending", "running", "initializing"}:
                                st.warning(
                                    "The training worker is not active, but the progress file did not finalize. "
                                    "This usually means the subprocess exited before writing a final status."
                                )
                                stdout_tail = _read_text_tail(job.get("stdout_path"))
                                stderr_tail = _read_text_tail(job.get("stderr_path"))
                                if stdout_tail or stderr_tail:
                                    with st.expander("Worker logs", expanded=True):
                                        if stdout_tail:
                                            st.code(stdout_tail, language="text")
                                        if stderr_tail:
                                            st.code(stderr_tail, language="text")
            with right_pane:
                st.subheader("Visualization")
                if st.session_state.last_error:
                    st.error("Error detected in the last execution.")
                    st.text_area(
                        "Error details",
                        st.session_state.last_error,
                        height=200,
                        key="build_error_details",
                    )
                if st.session_state.active_module == "Scenario Studio" and st.session_state.get("scenario_source_metadata"):
                    metadata = st.session_state.scenario_source_metadata
                    st.markdown("**Source details**")
                    detail_rows = []
                    for field in (
                        "mode",
                        "database_name",
                        "database_url",
                        "schema",
                        "build_mode",
                        "manifest_used",
                        "manifest_path",
                        "architecture",
                        "scenario",
                        "path",
                        "table_count",
                        "database_table_count",
                        "graph_node_count",
                        "table_to_graph_validation",
                        "table_to_graph_validation_detail",
                    ):
                        value = metadata.get(field)
                        if value:
                            detail_rows.append({"field": field, "value": value})
                    if detail_rows:
                        st.markdown(
                            "<div class='iso-source-details-box'>"
                            + "".join(
                                f"<p><strong>{html.escape(str(row['field']))}:</strong> {html.escape(str(row['value']))}</p>"
                                for row in detail_rows
                            )
                            + "</div>",
                            unsafe_allow_html=True,
                        )
                    if metadata.get("table_names"):
                        with st.expander("Source tables", expanded=False):
                            st.table(pd.DataFrame({"table": list(metadata["table_names"])}))
                    if st.session_state.initial_graph is not None:
                        with st.expander("Structured lineage", expanded=False):
                            st.table(pd.DataFrame(_graph_structure_table(st.session_state.initial_graph)))
                        with st.expander("Full lineage graph", expanded=False):
                            _render_graph(st.session_state.initial_graph, "Lineage Graph", st.session_state.layout_seed)
                        with st.expander("Full adjacency matrix", expanded=False):
                            _render_adjacency(st.session_state.initial_graph)
                        with st.expander("Full edge table", expanded=False):
                            _render_edges(st.session_state.initial_graph)
                if st.session_state.active_module == "Scenario Studio" and st.session_state.scenario_review_pairs:
                    current_pair = st.session_state.scenario_review_pairs[
                        min(st.session_state.scenario_review_index, len(st.session_state.scenario_review_pairs) - 1)
                    ]
                    st.markdown("**Pair Review Preview**")
                    _render_pair_preview(
                        st.session_state.initial_graph,
                        current_pair[0],
                        current_pair[1],
                        st.session_state.layout_seed,
                        st.session_state.get("scenario_source_metadata"),
                    )
                    _render_genai_validation_panel(st.session_state.initial_graph, current_pair)
                    active_pairs = st.session_state.scenario_review_pairs
                    pair_nav_cols = st.columns(3, gap="small")
                    if pair_nav_cols[0].button("Previous pair", key="review_prev_pair", disabled=st.session_state.scenario_review_index <= 0):
                        st.session_state.scenario_review_index -= 1
                        st.rerun()
                    if pair_nav_cols[1].button(
                        "Next pair",
                        key="review_next_pair",
                        disabled=st.session_state.scenario_review_index >= len(active_pairs) - 1,
                    ):
                        st.session_state.scenario_review_index += 1
                        st.rerun()
                    pair_nav_cols[2].caption(
                        f"Pair {st.session_state.scenario_review_index + 1} of {len(active_pairs)}"
                    )
                    if st.session_state.get("scenario_finalized_summary"):
                        summary = dict(st.session_state["scenario_finalized_summary"])
                        summary_cols = st.columns(4, gap="small")
                        summary_cols[0].metric("Total pairs", summary.get("total_pairs", 0))
                        summary_cols[1].metric("Candidate pairs", summary.get("candidate_pairs", 0))
                        summary_cols[2].metric("Reviewed pairs", summary.get("reviewed_pairs", 0))
                        summary_cols[3].metric("Duplicate pairs", summary.get("duplicate_pairs", 0))
                        st.markdown("**Validated dataset**")
                        st.table(pd.DataFrame(summary.get("validation_dataset_rows", [])))
                        if st.session_state.scenario_curation_message:
                            st.success(st.session_state.scenario_curation_message)
                    else:
                        action_cols = st.columns(3, gap="small")
                        if action_cols[0].button("Duplicate", key="review_mark_duplicate"):
                            _apply_scenario_review_decision(
                                decision="duplicate",
                                benchmark_name=st.session_state.get("curated_existing_benchmark_name")
                                if st.session_state.get("curated_benchmark_mode") == "Use existing benchmark"
                                and st.session_state.get("curated_existing_benchmark_name")
                                else st.session_state.get("curated_benchmark_name", "tpc_ds_v2"),
                                scenario_name=st.session_state.get("curated_scenario_name", "workspace_scenario"),
                                node_a=current_pair[0],
                                node_b=current_pair[1],
                            )
                        if action_cols[1].button("Not duplicate", key="review_mark_not_duplicate"):
                            _apply_scenario_review_decision(
                                decision="not_duplicate",
                                benchmark_name=st.session_state.get("curated_existing_benchmark_name")
                                if st.session_state.get("curated_benchmark_mode") == "Use existing benchmark"
                                and st.session_state.get("curated_existing_benchmark_name")
                                else st.session_state.get("curated_benchmark_name", "tpc_ds_v2"),
                                scenario_name=st.session_state.get("curated_scenario_name", "workspace_scenario"),
                                node_a=current_pair[0],
                                node_b=current_pair[1],
                            )
                        if action_cols[2].button("Finalize scenario", key="review_finalize_curated"):
                            _finalize_curated_scenario(
                                benchmark_name=st.session_state.get("curated_existing_benchmark_name")
                                if st.session_state.get("curated_benchmark_mode") == "Use existing benchmark"
                                and st.session_state.get("curated_existing_benchmark_name")
                                else st.session_state.get("curated_benchmark_name", "tpc_ds_v2"),
                                scenario_name=st.session_state.get("curated_scenario_name", "workspace_scenario"),
                                total_pairs=len(
                                    _candidate_validation_pairs(
                                        st.session_state.initial_graph,
                                        include_sor=True,
                                        include_sot=True,
                                        include_spec=True,
                                        same_layer_only=False,
                                        same_domain_only=False,
                                        same_indegree_only=False,
                                        same_outdegree_only=False,
                                        same_parent_signature_only=False,
                                        same_child_signature_only=False,
                                    )
                                ),
                                active_pairs=active_pairs,
                                publish_as_benchmark=bool(st.session_state.get("publish_curated_benchmark", True)),
                                filters={
                                    "include_sor": "SOR" in st.session_state.get("review_scope_pills", []),
                                    "include_sot": "SOT" in st.session_state.get("review_scope_pills", []),
                                    "include_spec": "SPEC" in st.session_state.get("review_scope_pills", []),
                                    "same_layer": "Same layer only" in st.session_state.get("review_constraint_pills", []),
                                    "same_domain": "Same domain only" in st.session_state.get("review_constraint_pills", []),
                                    "same_indegree": "Same input count" in st.session_state.get("review_constraint_pills", []),
                                    "same_outdegree": "Same output count" in st.session_state.get("review_constraint_pills", []),
                                    "same_parent_signature": "Same parent signature" in st.session_state.get("review_constraint_pills", []),
                                    "same_child_signature": "Same child signature" in st.session_state.get("review_constraint_pills", []),
                                },
                            )
                        if st.session_state.scenario_curation_message:
                            st.success(st.session_state.scenario_curation_message)
                if st.session_state.active_module == "Scenario Studio" and st.session_state.get("scenario_source_metadata"):
                    metadata = st.session_state.scenario_source_metadata
                    steps = metadata.get("graph_build_steps") or []
                    if steps:
                        st.markdown("**Graph build steps**")
                        for index, step in enumerate(steps, start=1):
                            st.caption(f"{index}. {step}")
                    table_names = list(metadata.get("table_names") or [])
                    if table_names:
                        with st.expander("Warehouse tables", expanded=False):
                            st.table(pd.DataFrame({"table": table_names}))
                elif st.session_state.graph_source == "TPC-DS Benchmark":
                    st.info("Use the `TPC-DS Benchmark` tab to execute and visualize the benchmark.")
                else:
                    if st.session_state.build_running:
                        st.progress(min(max(st.session_state.build_progress, 0.0), 1.0))
                        st.info(st.session_state.build_status or "Lineage generation running...")
                    else:
                        if st.session_state.graph is None:
                            if st.session_state.build_status:
                                if st.session_state.build_completed:
                                    st.success(st.session_state.build_status)
                                else:
                                    st.warning(st.session_state.build_status)
                            st.info("Generate or load a lineage to visualize.")
                        else:
                            _render_graph(st.session_state.graph, "Lineage Graph", st.session_state.layout_seed)
                if st.session_state.graph_loading_reset:
                    st.session_state.graph_loading = False
                    st.session_state.graph_loading_reset = False

production_flags = _ui_state_flags()
step1_ready = production_flags["step1_ready"]
step2_ready = production_flags["step2_ready"]
step3_ready = production_flags["step3_ready"]
step4_ready = production_flags["step4_ready"]

if st.session_state.active_module == "Production Run":
    left_col, right_col = st.columns([1, 2], gap="large")
    with left_col:
        step2_block = st.container(border=True)
        with step2_block:
            st.caption("Execution")
            st.subheader("Production Run")
            selected_algorithm = ui_algorithms[0] if ui_algorithms else None
            if not step1_ready:
                st.info("Scenario required: load or generate an architecture first.")
            else:
                selected_algorithm = st.selectbox(
                    "Detector",
                    options=ui_algorithms,
                    key="model_select",
                )
                st.session_state.gnn_pickle_path = None
                set_gnn_pickle_path(None)
                set_gnn_pickle_module(None)

            if st.button(
                "Find isomorphic pairs",
                key="find_pairs",
                disabled=not step1_ready or selected_algorithm is None,
            ):
                st.session_state.last_error = None
                if st.session_state.graph is None:
                    st.warning("Generate a lineage first.")
                else:
                    try:
                        backend_run_id = _start_backend_run(
                            "production_detection",
                            algorithm=selected_algorithm,
                            scenario_id=_active_scenario_id(),
                            parameters={"algorithm": selected_algorithm},
                        )
                        st.session_state.backend_active_run_id = backend_run_id
                        _log_action(
                            "click_find_pairs",
                            "analyze.model",
                            {"algorithm": selected_algorithm},
                        )
                        st.session_state.isomorphic_pairs = find_isomorphic_pairs(
                            st.session_state.graph, algorithm=selected_algorithm
                        )
                        st.session_state.model_ran = True
                        _finish_backend_run(
                            backend_run_id,
                            status="completed",
                            summary={"pairs_found": len(st.session_state.isomorphic_pairs)},
                        )
                        _log_event("find_isomorphic_pairs", {"algorithm": selected_algorithm})
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        _finish_backend_run(
                            st.session_state.get("backend_active_run_id"),
                            status="failed",
                            summary={"error": f"{type(exc).__name__}: {exc}"},
                        )
                        _log_exception("find_isomorphic_pairs", exc)
                    finally:
                        st.session_state.backend_active_run_id = None
    with right_col:
        st.subheader("Visualization")
        if not step1_ready:
            st.info("Waiting for an architecture to visualize.")
        else:
            _render_graph(st.session_state.graph, "Lineage Graph", st.session_state.layout_seed)
            if st.session_state.isomorphic_pairs:
                st.subheader("Isomorphic Pairs")
                pairs_df = pd.DataFrame(
                    st.session_state.isomorphic_pairs, columns=["Node A", "Node B"]
                )
                st.dataframe(pairs_df, width="stretch")

            if st.session_state.removed_nodes:
                st.subheader("Removed Nodes")
                st.dataframe(
                    pd.DataFrame(st.session_state.removed_nodes, columns=["Node"]),
                    width="stretch",
                )
            if st.session_state.removed_pairs_log:
                st.subheader("Removed Pairs (applied)")
                st.dataframe(
                    pd.DataFrame(st.session_state.removed_pairs_log),
                    width="stretch",
                )

if st.session_state.active_module == "Production Run":
    left_col, right_col = st.columns([1, 2], gap="large")
    with left_col:
        step3_block = st.container(border=True)
        with step3_block:
            st.caption("Review")
            st.subheader("Validation")
            if not step2_ready:
                st.info("Step 2 pending: run an algorithm to enable validation.")
            else:
                st.session_state.label_mode = st.radio(
                    "Choose labeling method",
                    options=["CSV", "UI"],
                    horizontal=True,
                    key="label_mode_radio",
                )
                label_in_app = st.session_state.label_mode == "UI"
                label_via_csv = st.session_state.label_mode == "CSV"

                if label_in_app:
                    if st.session_state.isomorphic_pairs:
                        st.caption("Select a pair to preview and decide removal.")
                        pair_map = {
                            f"{a} <-> {b}": (a, b) for a, b in st.session_state.isomorphic_pairs
                        }
                        pair_label = st.selectbox("Pair", options=list(pair_map.keys()), key="pair_selector")
                        node_a, node_b = pair_map[pair_label]
                        selected_pair_key = tuple(sorted((node_a, node_b)))
                        st.session_state.review_last_pair = selected_pair_key
                        status_rows = []
                        table_pairs = {tuple(sorted(pair)) for pair in pair_map.values()}
                        table_pairs.update(st.session_state.review_status.keys())
                        for pair_key in sorted(table_pairs):
                            a, b = pair_key
                            review = st.session_state.review_status.get(pair_key, {})
                            status_value = str(review.get("status", "PENDING")).upper()
                            status_rows.append(
                                {
                                    "pair_a": a,
                                    "pair_b": b,
                                    "status": status_value,
                                    "selected": pair_key == selected_pair_key,
                                    "keep_node": review.get("keep"),
                                    "remove_node": review.get("remove"),
                                }
                            )
                        if status_rows:
                            status_df = pd.DataFrame(status_rows)
                            def _style_row(row):
                                styles = [""] * len(row)
                                if row.get("selected"):
                                    styles = ["background-color: #D8DDD6; color: #2F312E"] * len(row)
                                return styles
                            def _style_cells(row):
                                styles = [""] * len(row)
                                if row.get("status") == "OK" and not row.get("remove_node"):
                                    styles[0] = "background-color: #8EA587; color: #F8F8F4"
                                    styles[1] = "background-color: #8EA587; color: #F8F8F4"
                                if row.get("keep_node") == row.get("pair_a"):
                                    styles[0] = "background-color: #8EA587; color: #F8F8F4"
                                if row.get("remove_node") == row.get("pair_a"):
                                    styles[0] = "background-color: #B56F6F; color: #F8F8F4"
                                if row.get("keep_node") == row.get("pair_b"):
                                    styles[1] = "background-color: #8EA587; color: #F8F8F4"
                                if row.get("remove_node") == row.get("pair_b"):
                                    styles[1] = "background-color: #B56F6F; color: #F8F8F4"
                                if row.get("status") == "OK":
                                    styles[2] = "background-color: #8EA587; color: #F8F8F4"
                                if row.get("status") == "NOK":
                                    styles[2] = "background-color: #B56F6F; color: #F8F8F4"
                                return styles
                            display_df = status_df[["pair_a", "pair_b", "status", "selected"]]
                            styled = display_df.style.apply(_style_cells, axis=1).apply(_style_row, axis=1)
                            st.dataframe(styled, width="stretch", hide_index=True)

                        scenario_dir = None
                        selected_arch_name = st.session_state.validation_arch_name
                        arch = _get_architecture(selected_arch_name) if selected_arch_name else None
                        if arch:
                            scenario_name = st.session_state.validation_scenario
                            if scenario_name:
                                scenario_dir = Path(arch["root"]) / "validations" / scenario_name

                        if scenario_dir:
                            pair_image = None
                            for img_path in scenario_dir.glob("pair_*.png"):
                                parsed = _parse_pair_filename(img_path.name)
                                if parsed and tuple(sorted(parsed)) == selected_pair_key:
                                    pair_image = img_path
                                    break
                            if pair_image:
                                st.image(str(pair_image), width="stretch")
                            else:
                                st.info("Pair image not found; generating a graph preview.")
                                if st.session_state.graph is not None:
                                    _render_pair_preview(
                                        st.session_state.graph,
                                        node_a,
                                        node_b,
                                        st.session_state.layout_seed,
                                    )
                        else:
                            if st.session_state.graph is not None:
                                _render_pair_preview(
                                    st.session_state.graph,
                                    node_a,
                                    node_b,
                                    st.session_state.layout_seed,
                                )

                        choice = st.radio(
                            f"{node_a} <-> {node_b}",
                            options=["Not isomorphic", f"Remove {node_a}", f"Remove {node_b}"],
                            index=0,
                            key=f"pair_choice_{node_a}_{node_b}",
                        )

                        removal_choices = []
                        labeled_pairs = set()
                        if choice != "Not isomorphic":
                            labeled_pairs.add(selected_pair_key)
                            if choice == f"Remove {node_a}":
                                removal_choices.append(node_a)
                            else:
                                removal_choices.append(node_b)

                        enforce_rules = st.checkbox("Protect SOR/SOT/SPEC rules", value=True)
                        st.caption("Keeps at least 1 SOT and 1 SPEC and blocks SOR removal.")
                        protect_prefixes = ["SOR"] if enforce_rules else []
                        min_remaining = {"SOT": 1, "SPEC": 1} if enforce_rules else {}

                        if st.button("Apply", key="apply_removal"):
                            st.session_state.last_error = None
                            graph = st.session_state.graph
                            if graph is None:
                                st.warning("Generate a lineage first.")
                            else:
                                try:
                                    _log_action(
                                        "click_apply_removal",
                                        "analyze.validation",
                                        {
                                            "pairs_selected": len(labeled_pairs),
                                            "label_mode": st.session_state.label_mode,
                                            "protect_rules": enforce_rules,
                                        },
                                    )
                                    (
                                        updated_graph,
                                        removed_nodes,
                                        skipped_nodes,
                                        isolated_removed,
                                    ) = apply_removals(
                                        graph,
                                        removal_choices,
                                        protect_prefixes=protect_prefixes,
                                        min_remaining_by_prefix=min_remaining,
                                    )
                                    st.session_state.graph = updated_graph
                                    st.session_state.removed_nodes = removed_nodes + isolated_removed
                                    st.session_state.labeled_pairs.update(labeled_pairs)
                                    if skipped_nodes:
                                        st.info(f"Skipped by rules: {', '.join(skipped_nodes)}")
                                    st.session_state.isomorphic_pairs = find_isomorphic_pairs(
                                        updated_graph, algorithm=selected_algorithm
                                    )
                                    review_entry = {
                                        "status": "PENDING",
                                        "keep": None,
                                        "remove": None,
                                    }
                                    if choice == "Not isomorphic":
                                        review_entry.update(
                                            {"status": "OK", "keep": None, "remove": None}
                                        )
                                    elif choice == f"Remove {node_a}":
                                        review_entry.update(
                                            {"status": "NOK", "keep": node_b, "remove": node_a}
                                        )
                                    else:
                                        review_entry.update(
                                            {"status": "NOK", "keep": node_a, "remove": node_b}
                                        )
                                    st.session_state.review_status[selected_pair_key] = review_entry
                                    if review_entry["status"] == "NOK":
                                        st.session_state.removed_pairs_log.append(
                                            {
                                                "pair_a": node_a,
                                                "pair_b": node_b,
                                                "removed": review_entry.get("remove"),
                                                "kept": review_entry.get("keep"),
                                            }
                                        )
                                    scenario_id = _active_scenario_id()
                                    if scenario_id and st.session_state.backend_enabled:
                                        create_label_version(
                                            st.session_state.backend_db_url,
                                            scenario_id=scenario_id,
                                            labels=sorted(st.session_state.labeled_pairs),
                                            metadata={
                                                "source": "production_validation",
                                                "removed_nodes": st.session_state.removed_nodes,
                                            },
                                        )
                                    _log_event(
                                        "apply_removal",
                                        {
                                            "removed": st.session_state.removed_nodes,
                                            "skipped": skipped_nodes,
                                            "algorithm": selected_algorithm,
                                        },
                                    )
                                    st.rerun()
                                except Exception as exc:  # noqa: BLE001
                                    _log_exception("apply_removal", exc)
                    else:
                        st.info("Run isomorphic-pair detection to enable labeling.")

                if label_via_csv:
                    st.subheader("Label Pairs via CSV")
                    if st.session_state.initial_graph is None:
                        st.info("Generate a lineage to enable the template.")
                    else:
                        nodes = list(st.session_state.initial_graph.nodes)
                        if st.session_state.all_pairs is None:
                            st.session_state.all_pairs = [
                                (nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))
                            ]
                        template_df = pd.DataFrame(
                            st.session_state.all_pairs, columns=["node_a", "node_b"]
                        )
                        template_df["is_isomorphic"] = 0
                        csv_bytes = template_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Download labeling template",
                            data=csv_bytes,
                            file_name="pair_labels_template.csv",
                            mime="text/csv",
                        )
                        labeled_file = st.file_uploader("Upload labeled CSV", type=["csv"], key="labels_csv")
                        if labeled_file is not None:
                            labeled_df = pd.read_csv(labeled_file)
                            if {"node_a", "node_b", "is_isomorphic"}.issubset(labeled_df.columns):
                                if len(labeled_df) == len(template_df):
                                    st.session_state.ground_truth_complete = True
                                    st.info("Complete ground truth detected from the template.")
                                labeled_df = labeled_df[labeled_df["is_isomorphic"] == 1]
                                st.session_state.labeled_pairs = canonical_pairs(
                                    labeled_df[["node_a", "node_b"]].itertuples(index=False, name=None)
                                )
                            else:
                                st.warning("CSV must have node_a, node_b, is_isomorphic columns.")
    with right_col:
        st.subheader("Visualization")
        if not step1_ready:
            st.info("Waiting for an architecture to visualize.")
        else:
            _render_graph(st.session_state.graph, "Lineage Graph", st.session_state.layout_seed)
            if st.session_state.isomorphic_pairs:
                st.subheader("Isomorphic Pairs")
                pairs_df = pd.DataFrame(
                    st.session_state.isomorphic_pairs, columns=["Node A", "Node B"]
                )
                st.dataframe(pairs_df, width="stretch")

            if st.session_state.removed_nodes:
                st.subheader("Removed Nodes")
                st.dataframe(
                    pd.DataFrame(st.session_state.removed_nodes, columns=["Node"]),
                    width="stretch",
                )

if st.session_state.active_module == "Production Run":
    left_col, right_col = st.columns([1, 2], gap="large")
    with left_col:
        step4_block = st.container(border=True)
        with step4_block:
            st.caption("Analysis")
            st.subheader("Results")
            if not st.session_state.labeled_pairs:
                st.info("Step 3 pending: complete validation to unlock metrics.")
            else:
                st.caption(
                    "Label only isomorphic pairs (positives). TN and accuracy are computed only when all pairs are labeled."
                )
                st.checkbox(
                    "Ground truth complete (all pairs labeled)",
                    value=st.session_state.ground_truth_complete,
                    key="ground_truth_complete",
                )
                st.caption(
                    "When ground truth is complete, non-isomorphic pairs are treated as negatives. "
                    "Otherwise, TN/accuracy are undefined."
                )

            st.subheader("Execution Times")
            runs = st.number_input(
                "Executions per algorithm",
                min_value=-1000,
                max_value=200,
                value=25,
                key="exec_runs",
            )
            if int(runs) < 1:
                st.warning("Executions per algorithm must be at least 1.")
            exec_cols = st.columns([1, 1], gap="small")
            run_exec = exec_cols[0].button(
                "Run metrics evaluation",
                key="run_metrics_eval",
                disabled=int(runs) < 1,
            )
            stop_exec = exec_cols[1].button("Stop execution", key="stop_exec")
            if stop_exec:
                st.session_state.cancel_exec = True
                _log_event("stop_execution_times")
            if run_exec:
                st.session_state.last_error = None
                st.session_state.cancel_exec = False
                _log_action(
                    "run_metrics_eval_click",
                    "analyze.metrics",
                    {"runs": int(runs), "algorithms": ui_algorithms},
                )
                if int(runs) < 1:
                    st.error("Executions per algorithm must be at least 1.")
                    _log_event("execution_times_invalid_runs", {"runs": int(runs)})
                    st.stop()
                elif st.session_state.initial_graph is None:
                    st.warning("Generate a lineage first.")
                else:
                    try:
                        backend_run_id = _start_backend_run(
                            "metrics_evaluation",
                            scenario_id=_active_scenario_id(),
                            parameters={"runs": int(runs), "algorithms": ui_algorithms},
                        )
                        st.session_state.backend_active_run_id = backend_run_id
                        all_pairs = None
                        if st.session_state.ground_truth_complete:
                            nodes = list(st.session_state.initial_graph.nodes)
                            all_pairs = [
                                (nodes[i], nodes[j]) for i in range(len(nodes)) for j in range(i + 1, len(nodes))
                            ]
                        metrics_algorithms = ui_algorithms
                        metrics_df = metrics_table(
                            st.session_state.initial_graph,
                            st.session_state.labeled_pairs,
                            metrics_algorithms,
                            all_pairs=all_pairs,
                        )
                        st.session_state.metrics_df = metrics_df
                        _log_event(
                            "generate_metrics",
                            {"ground_truth_complete": st.session_state.ground_truth_complete},
                        )
                        exec_algorithms = ui_algorithms
                        total_steps = len(exec_algorithms) * int(runs)
                        current_step = 0
                        exec_start = time.perf_counter()
                        timeout_secs = int(st.session_state.global_timeout_secs)
                        progress = st.progress(0)
                        status = st.empty()
                        times: dict[str, list[float]] = {algo: [] for algo in exec_algorithms}
                        for algo in exec_algorithms:
                            if time.perf_counter() - exec_start > timeout_secs:
                                st.session_state.cancel_exec = True
                                timeout_msg = (
                                    f"Operation timed out after {_format_timeout(timeout_secs)}."
                                )
                                st.session_state.last_error = timeout_msg
                                st.error(timeout_msg)
                                _log_event(
                                    "operation_timeout",
                                    {
                                        "context": "metrics_eval",
                                        "timeout_secs": timeout_secs,
                                        "error": timeout_msg,
                                    },
                                )
                                break
                            if st.session_state.cancel_exec:
                                _log_event("execution_times_cancelled")
                                break
                            for _ in range(int(runs)):
                                if time.perf_counter() - exec_start > timeout_secs:
                                    st.session_state.cancel_exec = True
                                    timeout_msg = (
                                        f"Operation timed out after {_format_timeout(timeout_secs)}."
                                    )
                                    st.session_state.last_error = timeout_msg
                                    st.error(timeout_msg)
                                    _log_event(
                                        "operation_timeout",
                                        {
                                            "context": "metrics_eval",
                                            "timeout_secs": timeout_secs,
                                            "error": timeout_msg,
                                        },
                                    )
                                    break
                                if st.session_state.cancel_exec:
                                    _log_event("execution_times_cancelled")
                                    break
                                start = time.perf_counter()
                                find_isomorphic_pairs(st.session_state.initial_graph, algorithm=algo)
                                times[algo].append(time.perf_counter() - start)
                                current_step += 1
                                progress.progress(min(current_step / total_steps, 1.0))
                                status.markdown(
                                    f"Progress: {current_step}/{total_steps} ({(current_step / total_steps) * 100:.1f}%)"
                                )
                        st.session_state.exec_times = times
                        stats_rows = []
                        for algo, tlist in st.session_state.exec_times.items():
                            if not tlist:
                                continue
                            series = pd.Series(tlist)
                            stats_rows.append(
                                {
                                    "algorithm": algo,
                                    "mean": series.mean(),
                                    "median": series.median(),
                                    "std": series.std(ddof=1),
                                    "min": series.min(),
                                    "max": series.max(),
                                    "p95": series.quantile(0.95),
                                    "p99": series.quantile(0.99),
                                }
                            )
                        st.session_state.exec_times_stats = pd.DataFrame(stats_rows)
                        _record_backend_report(
                            backend_run_id,
                            "metrics_summary",
                            {
                                "metrics_rows": len(metrics_df),
                                "timing_rows": len(stats_rows),
                                "ground_truth_complete": bool(st.session_state.ground_truth_complete),
                            },
                        )
                        _finish_backend_run(
                            backend_run_id,
                            status="completed",
                            summary={
                                "metrics_rows": len(metrics_df),
                                "timing_rows": len(stats_rows),
                                "ground_truth_complete": bool(st.session_state.ground_truth_complete),
                            },
                        )
                        _log_event("measure_execution_times", {"runs": int(runs)})
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        _finish_backend_run(
                            st.session_state.get("backend_active_run_id"),
                            status="failed",
                            summary={"error": f"{type(exc).__name__}: {exc}"},
                        )
                        _log_exception("measure_execution_times", exc)
                    finally:
                        st.session_state.backend_active_run_id = None
    with right_col:
        st.subheader("Visualization")
        if not step1_ready:
            st.info("Waiting for an architecture to visualize.")
        else:
            _render_graph(st.session_state.graph, "Lineage Graph", st.session_state.layout_seed)
            if st.session_state.metrics_df is not None:
                st.subheader("Metrics")
                metrics_view = st.session_state.metrics_df.copy()
                if st.session_state.exec_times:
                    node_count = st.session_state.initial_graph.number_of_nodes()
                    pair_count = int(node_count * (node_count - 1) / 2)
                    sf_vals = []
                    for _, row in metrics_view.iterrows():
                        algo = row["algorithm"]
                        median_time = pd.Series(st.session_state.exec_times.get(algo, [])).median()
                        tp = int(row.get("tp", 0) or 0)
                        fp = int(row.get("fp", 0) or 0)
                        fn = int(row.get("fn", 0) or 0)
                        tn = int(row.get("tn", 0) or 0)
                        denom = tp + tn + fp + fn
                        jaccard_denom = tp + fp + fn
                        jaccard = (tp / jaccard_denom) if jaccard_denom else 0.0
                        if pd.isna(median_time) or median_time == 0:
                            sf_vals.append(0.0)
                        else:
                            sf_vals.append((jaccard * pair_count) / median_time)
                    metrics_view["SF"] = sf_vals
                    metrics_view["N_pairs"] = pair_count
                st.dataframe(metrics_view, width="stretch")
                st.caption("SF is SF-Jaccard: Jaccard * N_pairs / ET. Accuracy remains diagnostic.")

            if st.session_state.exec_times:
                st.subheader("Execution Time (ET)")
                exec_rows = []
                for algo, times in st.session_state.exec_times.items():
                    for t in times:
                        exec_rows.append({"algorithm": algo, "ET": t})
                exec_df = pd.DataFrame(exec_rows)
                if not exec_df.empty:
                    et_fig = px.box(
                        exec_df,
                        x="algorithm",
                        y="ET",
                        color="algorithm",
                        color_discrete_sequence=["#5C7C6F", "#8A9A86", "#A27A3F"],
                    )
                    _apply_plotly_theme(et_fig)
                    et_fig.update_layout(yaxis_title="Execution Time (s)")
                    st.plotly_chart(et_fig, use_container_width=True, key="metrics_et_box")
                    st.caption("ET: execution time (s) by algorithm.")

                if st.session_state.metrics_df is not None:
                    acc_rows = []
                    for _, row in st.session_state.metrics_df.iterrows():
                        tp = int(row.get("tp", 0) or 0)
                        fp = int(row.get("fp", 0) or 0)
                        fn = int(row.get("fn", 0) or 0)
                        tn = int(row.get("tn", 0) or 0)
                        denom = tp + tn + fp + fn
                        acc = float(row.get("accuracy") or 0.0)
                        if not acc and denom:
                            acc = (tp + tn) / denom
                        acc_rows.append({"algorithm": row["algorithm"], "ACC": acc})
                    acc_df = pd.DataFrame(acc_rows)
                    st.subheader("Accuracy (ACC)")
                    acc_fig = px.box(
                        acc_df,
                        x="algorithm",
                        y="ACC",
                        color="algorithm",
                        color_discrete_sequence=["#5C7C6F", "#8A9A86", "#A27A3F"],
                    )
                    _apply_plotly_theme(acc_fig)
                    st.plotly_chart(acc_fig, use_container_width=True, key="metrics_acc_box")
                    st.caption("ACC: (TP+TN)/(TP+TN+FP+FN) by algorithm.")

                if st.session_state.metrics_df is not None:
                    sf_scores = []
                    node_count = st.session_state.initial_graph.number_of_nodes()
                    pair_count = int(node_count * (node_count - 1) / 2)
                    for _, row in st.session_state.metrics_df.iterrows():
                        algo = row["algorithm"]
                        median_time = pd.Series(st.session_state.exec_times.get(algo, [])).median()
                        tp = int(row.get("tp", 0) or 0)
                        fp = int(row.get("fp", 0) or 0)
                        fn = int(row.get("fn", 0) or 0)
                        tn = int(row.get("tn", 0) or 0)
                        jaccard_denom = tp + fp + fn
                        jaccard = (tp / jaccard_denom) if jaccard_denom else 0.0
                        if pd.isna(median_time) or median_time == 0:
                            sf_scores.append({"algorithm": algo, "SF": 0.0})
                        else:
                            sf_scores.append({"algorithm": algo, "SF": (jaccard * pair_count) / median_time})
                    sf_df = pd.DataFrame(sf_scores)
                    st.subheader("Success Frequency Jaccard (SF-Jaccard)")
                    sf_fig = px.line(
                        sf_df,
                        x="algorithm",
                        y="SF",
                        color="algorithm",
                        markers=True,
                        color_discrete_sequence=["#5C7C6F", "#8A9A86", "#A27A3F"],
                    )
                    _apply_plotly_theme(sf_fig)
                    st.plotly_chart(sf_fig, use_container_width=True, key="metrics_sf_line")
                    st.caption("SF-Jaccard: Jaccard * N_pairs / ET, using the total evaluated pair count for the active graph.")

if st.session_state.active_module == "Logs":
    left_col, right_col = st.columns([1, 2], gap="large")
    with left_col:
        st.subheader("Logs")
        logs_root = _app_path("logs")
        log_files = sorted(logs_root.glob("session_*.jsonl"), reverse=True)
        if not log_files:
            st.info("No logs found.")
            selected_log = None
        else:
            selected_log = st.selectbox(
                "Select log",
                options=[p.name for p in log_files],
                key="log_select_main",
            )
            if selected_log and selected_log != st.session_state.active_log:
                st.session_state.active_log = selected_log
                _log_event("view_log", {"log": selected_log})
    with right_col:
        log_tabs = st.tabs(["Session Log", "Terminal Logs"])
        with log_tabs[0]:
            st.subheader("Log Viewer")
            if not log_files or not st.session_state.active_log:
                st.info("No logs to display.")
            else:
                log_path = logs_root / st.session_state.active_log
                raw_text = log_path.read_text(encoding="utf-8")
                rows = []
                for line in raw_text.splitlines():
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    payload = entry.get("payload", {})
                    if isinstance(payload, dict):
                        context = payload.get("context")
                        error = payload.get("error")
                        payload_str = json.dumps(payload, ensure_ascii=True)
                    else:
                        context = None
                        error = None
                        payload_str = str(payload)
                    rows.append(
                        {
                            "timestamp": entry.get("timestamp"),
                            "event": entry.get("event"),
                            "context": context,
                            "error": error,
                            "payload": payload_str,
                        }
                    )
                if rows:
                    st.dataframe(pd.DataFrame(rows), width="stretch")
                st.text_area("Raw log (.jsonl)", raw_text, height=240)
        with log_tabs[1]:
            st.subheader("Terminal Logs")
            terminal_root = _app_path("logs/terminal")
            terminal_files = sorted(terminal_root.glob("terminal_*.log"), reverse=True)
            launcher_files = sorted(_app_path("logs").glob("streamlit_launch_*.log"), reverse=True)
            all_terminal_files = [(p.name, p) for p in terminal_files] + [
                (f"launcher/{p.name}", p) for p in launcher_files
            ]
            if not all_terminal_files:
                st.info("No terminal logs found.")
            else:
                label_to_path = dict(all_terminal_files)
                selected_terminal = st.selectbox(
                    "Select terminal log",
                    options=list(label_to_path.keys()),
                    key="terminal_log_select",
                )
                if selected_terminal and selected_terminal != st.session_state.active_terminal_log:
                    st.session_state.active_terminal_log = selected_terminal
                    _log_event("view_terminal_log", {"log": selected_terminal})
            if not all_terminal_files or not st.session_state.active_terminal_log:
                st.info("No terminal log selected.")
            else:
                term_path = dict(all_terminal_files).get(st.session_state.active_terminal_log, terminal_root / st.session_state.active_terminal_log)
                term_text = term_path.read_text(encoding="utf-8", errors="replace")
                st.text_area("Raw log (.log)", term_text, height=360)

def _vmamba_presentation_figures() -> dict[str, Path]:
    root = PROJECT_ROOT / "docs" / "presentations" / "vmamba_mesh_assets"
    final_figures = root / "final_paper_figures"
    return {
        "problem": final_figures / "sor16_lineage_graph.png",
        "pipeline": final_figures / "trainable_decision_pipeline.png",
        "difference": root / "vmamba_vs_vmamba_mesh_difference.png",
        "cross_scan": root / "official_cross_scan_4x4_routes.png",
        "tensor": final_figures / "sor16_tensor_channels_6ch.png",
        "architecture": final_figures / "vmamba_mesh_dual_architecture.png",
        "ablation": root / "vmamba_mesh_ablation_ladder_v2.png",
        "lineage_graph": final_figures / "sor16_lineage_graph.png",
        "adjacency": final_figures / "sor16_adjacency_matrix.png",
        "erf_spec": final_figures / "sor16_neural_saliency.png",
        "routes_spec": final_figures / "trainable_decision_pipeline.png",
        "spec_sf": root / "tpc_ds_genai_spec_v2_vmamba_mesh_combined_sf_jaccard.png",
        "spec_runtime": root / "tpc_ds_genai_spec_v2_vmamba_mesh_combined_quality_runtime.png",
        "full_line": root / "tpc_ds_genai_full_lineage_vmamba_mesh_combined_sf_jaccard_line.png",
        "spec_trainable_sf": final_figures / "spec_v2_sf_jaccard_comparison.png",
        "spec_trainable_runtime": final_figures / "spec_v2_jaccard_comparison.png",
        "full_trainable_sf": root / "trainable_results" / "full_lineage_combined_sf_jaccard_with_trainable.png",
        "full_trainable_runtime": root / "trainable_results" / "full_lineage_quality_runtime_with_trainable.png",
    }


def _vmamba_presentation_metric_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for benchmark, label in [
        ("tpc_ds_genai_spec_v2", "SPEC benchmark"),
        ("tpc_ds_genai_full_lineage", "Full lineage benchmark"),
    ]:
        path = (
            PROJECT_ROOT / "data" / "article_evidence" / "vmamba_mesh_genai_benchmark"
            / benchmark
            / "combined_summary_metrics.csv"
        )
        if not path.exists():
            continue
        df = pd.read_csv(path)
        for source_algorithm, display_algorithm in [
            ("Vanilla VMamba graph-image proxy", "Vanilla VMamba baseline"),
            ("Vanilla VMamba baseline", "Vanilla VMamba baseline"),
            ("VMamba-Mesh Isomera adapter", "VMamba-Mesh Isomera adapter"),
        ]:
            match = df[df["algorithm"].astype(str) == source_algorithm]
            if match.empty:
                continue
            record = match.iloc[0]
            rows.append(
                {
                    "benchmark": label,
                    "model": display_algorithm,
                    "Jaccard": f"{float(record['jaccard']):.6f}",
                    "SF-Jaccard": f"{float(record['sf_jaccard']):.3f}",
                    "ET": f"{float(record['ET']):.6f}s",
                    "scenarios": int(record["scenarios"]),
                    "runs": int(record["runs"]),
                }
            )
    trainable_reports = sorted(
        [
            path
            for path in _app_path("data/research_reports").glob("*vmamba_trainable_ablation*")
            if path.is_dir() and (path / "combined_summary_with_trainable.csv").exists()
        ],
        key=lambda path: path.name,
        reverse=True,
    )
    seen_trainable: set[tuple[str, str]] = set()
    for report_dir in trainable_reports:
        manifest_payload: dict[str, object] = {}
        manifest_path = report_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                manifest_payload = {}
        benchmark_name = str(manifest_payload.get("benchmark") or report_dir.name)
        if "full_lineage" in benchmark_name:
            label = "Full lineage benchmark"
        elif "spec" in benchmark_name:
            label = "SPEC benchmark"
        else:
            continue
        try:
            df = pd.read_csv(report_dir / "combined_summary_with_trainable.csv")
        except Exception:
            continue
        for algorithm in ["VMamba-T", "VMamba-Mesh-T"]:
            key = (label, algorithm)
            if key in seen_trainable:
                continue
            match = df[df["algorithm"].astype(str) == algorithm]
            if match.empty:
                continue
            record = match.iloc[0]
            rows.append(
                {
                    "benchmark": label,
                    "model": algorithm,
                    "Jaccard": f"{float(record['jaccard']):.6f}",
                    "SF-Jaccard": f"{float(record['sf_jaccard']):.3f}",
                    "ET": f"{float(record['ET']):.6f}s",
                    "scenarios": int(record["scenarios"]),
                    "runs": int(record["runs"]),
                }
            )
            seen_trainable.add(key)
    return rows


def _presentation_image(path: Path, caption: str) -> None:
    if path.exists():
        st.image(str(path), caption=caption, width="stretch")
    else:
        st.info(f"Missing figure: `{path.relative_to(PROJECT_ROOT.parent) if path.is_absolute() else path}`")


def _render_vmamba_mesh_presentation() -> None:
    figures = _vmamba_presentation_figures()
    html_path = _app_path("docs/presentations/vmamba_mesh_10min.html")
    st.subheader("VMamba-Mesh Presentation")
    st.caption("Roteiro visual para uma apresentação dinâmica de 10 minutos, com pontos de troca para a ferramenta.")

    hero_cols = st.columns([1.15, 1], gap="large")
    with hero_cols[0]:
        st.markdown(
            """
            **Mensagem central:** o problema não é apenas desenhar grafos de linhagem. O problema é detectar redundância estrutural em Data Mesh de forma reprodutível, comparável e explicável.

            **Estratégia da apresentação:**
            - 2 minutos: problema, contexto e evolução dos artigos.
            - 3 minutos: por que VMamba-Mesh e o que muda.
            - 3 minutos: resultados do Article IV.
            - 2 minutos: demonstração no Isomera.
            """
        )
        if html_path.exists():
            payload = _safe_read_bytes(html_path)
            if payload is not None:
                st.download_button(
                    "Download HTML presentation",
                    data=payload,
                    file_name=html_path.name,
                    mime="text/html",
                    use_container_width=True,
                )
    with hero_cols[1]:
        _presentation_image(figures["problem"], "Input/output contract: lineage graph to duplicate-pair evidence.")

    st.markdown("**Live demo switches**")
    demo_cols = st.columns(3, gap="small")
    if demo_cols[0].button("Open Deep Learning Workbench", use_container_width=True, key="vmamba_present_open_study"):
        st.session_state.active_module = "Study Lab"
        st.session_state.study_algorithm_select = "Deep Learning Workbench"
        st.rerun()
    if demo_cols[1].button("Open Article Reproducibility", use_container_width=True, key="vmamba_present_open_repro"):
        st.session_state.active_module = "Benchmark & Examples"
        st.rerun()
    if demo_cols[2].button("Open Research Reports", use_container_width=True, key="vmamba_present_open_reports"):
        st.session_state.active_module = "Research Reports"
        st.rerun()

    slide_tabs = st.tabs([
        "1. Context",
        "2. Articles I-III",
        "3. Why VMamba-Mesh",
        "4. Article IV Method",
        "5. Benchmarks",
        "6. Results",
        "7. Live Demo Script",
        "8. Technical Q&A",
    ])

    with slide_tabs[0]:
        cols = st.columns([1, 1], gap="large")
        with cols[0]:
            st.markdown(
                """
                ### Problema
                Em arquiteturas Data Mesh, domínios diferentes podem recriar tabelas semanticamente equivalentes. Isso aumenta custo, inconsistência e retrabalho.

                ### Contexto
                O Isomera representa SOR, SOT e SPEC como grafos de linhagem. A pergunta operacional vira: quais pares de nós/tabelas são redundantes?

                ### O que precisa funcionar na apresentação
                Mostrar que os resultados não são só números soltos: eles podem ser reproduzidos dentro da ferramenta.
                """
            )
        with cols[1]:
            _presentation_image(figures["pipeline"], "Isomera pipeline: graph materialization, model execution, reproducible reports.")

    with slide_tabs[1]:
        st.markdown("### Evolução antes do VMamba-Mesh")
        paper_cols = st.columns(3, gap="large")
        with paper_cols[0]:
            st.markdown(
                """
                **Article I / Base**

                Formaliza o problema em grafos de linhagem e isomorfismo estrutural.

                Papel na história: transformar redundância de Data Mesh em um problema computável.
                """
            )
            _presentation_image(PROJECT_ROOT / "docs" / "presentations" / "vmamba_mesh_assets" / "isomera_v2_architecture_layers.png", "SOR/SOT/SPEC layers.")
        with paper_cols[1]:
            st.markdown(
                """
                **Article II / GNN**

                Introduz classificador de pares com GIN/GNN para aprender padrões de duplicidade.

                Papel na história: sair de heurística pura para aprendizado supervisionado.
                """
            )
            _presentation_image(PROJECT_ROOT / "docs" / "presentations" / "vmamba_mesh_assets" / "isomera_v2_gnn_pair_classifier.png", "GNN pair classifier contract.")
        with paper_cols[2]:
            st.markdown(
                """
                **Article III / Isomera v2**

                Consolida benchmark, materialização, treinamento e relatórios reprodutíveis.

                Papel na história: transformar pesquisa em ferramenta executável.
                """
            )
            _presentation_image(PROJECT_ROOT / "docs" / "presentations" / "vmamba_mesh_assets" / "isomera_v2_usage_sequence.png", "Operational sequence inside Isomera.")

    with slide_tabs[2]:
        st.markdown(
            """
            ### Interpretabilidade do tensor
            A adaptação VMamba-Mesh transforma o grafo de linhagem em um tensor canônico e, além de produzir métricas, permite interpretar onde o modelo concentra contexto para decidir se um par é duplicado.
            """
        )
        cols = st.columns([1, 1], gap="large")
        with cols[0]:
            st.markdown(
                """
                **CanonSort:** coloca SOR, SOT e SPEC em uma ordem estável. Isso faz regiões do tensor terem o mesmo significado entre cenários.

                **DiagFP:** usa a diagonal para identidade do nó, como camada e grau. Isso evita que a matriz seja só aresta e zero.

                **MeshSS2D:** adapta o scan 2D para seguir rotas coerentes com a linhagem. É aqui que a leitura deixa de ser imagem genérica e vira leitura de fluxo.

                **SparseGate:** reduz o peso das células vazias. Isso importa porque matrizes de adjacência são quase sempre esparsas.

                **Gancho para a imagem:** depois dessas etapas, o ERF estrutural mostra quais regiões do tensor ficaram mais relevantes para a decisão do par. Na demo final, usamos SOR16-D1 para o grafo/matriz e saliency neural no par `SPEC_customer_summary_D1` contra `SPEC_store_sales_summary_D1`.
                """
            )
        with cols[1]:
            _presentation_image(figures["lineage_graph"], "SOR16 D1 lineage graph: original node-edge view used as the demo context.")
            _presentation_image(figures["adjacency"], "SOR16 adjacency matrix: sparse tensor grid derived from the same graph.")
            _presentation_image(
                figures["erf_spec"],
                "Structural ERF on SOR16 D1 SPEC: graph-native interpretability over the canonical tensor.",
            )

    with slide_tabs[3]:
        st.markdown(
            """
            ### Arquitetura VMamba-Mesh e VMamba-Mesh-T
            A figura abaixo é o mapa geral do que foi implementado: o par de subgrafos entra pelo contrato do Isomera, passa por CanonSort e tensorização C0--C5, e então segue por dois caminhos comparáveis. O VMamba-Mesh adapter calcula features estruturais e um score determinístico; o VMamba-Mesh-T envia os mesmos canais para patch embedding, blocos VSS/SS2D, pooling e head neural antes da decisão.
            """
        )
        _presentation_image(
            figures["architecture"],
            "Architecture path: graph pair, CanonSort, six-channel tensor, deterministic VMamba-Mesh and trainable VMamba-Mesh-T.",
        )
        st.markdown(
            """
            ### Onde o MeshSS2D percorre a linhagem
            O ERF mostra a concentração do contexto; as rotas SS2D mostram como esse contexto é percorrido. No VMamba original, o scan percorre uma imagem por linhas e colunas. No VMamba-Mesh, essas rotas são aplicadas ao tensor canônico e complementadas pela rota guiada pela linhagem SOR -> SOT -> SPEC.

            Aqui aparece a diferença técnica mais importante: `CanonSort` torna a ordem estável, `DiagFP` marca células semanticamente úteis, `MeshSS2D` define a rota de leitura e `SparseGate` reduz o efeito das células vazias. Por isso essas figuras são a ponte entre arquitetura e resultado.
            """
        )
        _presentation_image(
            figures["routes_spec"],
            "SS2D route history on SOR16 D1 SPEC: route-level interpretability over active and empty cells.",
        )

    with slide_tabs[4]:
        st.markdown("### Benchmarks e cenarios usados na historia")
        bench_cols = st.columns([1.2, 1], gap="large")
        with bench_cols[0]:
            st.markdown(
                """
                Os cenarios seguem a familia `graph_SOR{k}_D{d}_seed42`: `k` controla o numero de fontes SOR e `d` controla o numero de dominios. A seed fixa torna a comparacao reproduzivel entre algoritmos, artigos e versoes do Isomera.
                """
            )
            st.table(
                pd.DataFrame(
                    [
                        {
                            "benchmark": "Bench v1 / TPC-DS default",
                            "criacao": "Curadoria inicial baseada em TPC-DS e pares revisados manualmente.",
                            "papel": "Base dos Artigos I-II; prova o metodo, mas tem escopo menor.",
                        },
                        {
                            "benchmark": "Bench v2 manual",
                            "criacao": "Cenarios escolhidos no Isomera e pares revisados manualmente no app.",
                            "papel": "Transicao para Article III; evidenciou custo de rotulagem.",
                        },
                        {
                            "benchmark": "GenAI SPEC v1",
                            "criacao": "LLM propôs pares SPEC semanticamente plausiveis; Isomera materializou e validou.",
                            "papel": "Amplia a avaliacao para camada analitica no Article III.",
                        },
                        {
                            "benchmark": "GenAI SPEC v2",
                            "criacao": "Refino com contratos de prompt, validacao de pares e modelos por cenario.",
                            "papel": "Benchmark principal do Article IV para Vanilla VMamba e VMamba-Mesh.",
                        },
                        {
                            "benchmark": "Full lineage",
                            "criacao": "Uniao de pares SOR/SOT operacionais com pares GenAI SPEC.",
                            "papel": "Stress test do Article IV em todos os niveis da linhagem.",
                        },
                    ]
                ).astype(str)
            )
        with bench_cols[1]:
            st.markdown(
                """
                **Por que o v1 nao bastava?**

                O v1 era bom para demonstrar isomorfismo e GNN, mas tinha poucos contratos revisados e concentrava a avaliacao em parte do problema.

                **Por que usar LLM depois?**

                O LLM acelera a criacao de candidatos semanticamente plausiveis. O Isomera continua sendo a camada de auditoria: grafo, par, metrica, modelo, trace e reproducibilidade.

                **Ligacao com os artigos**

                - Artigos I-II: formalizacao e GNN sobre benchmarks iniciais.
                - Article III: Isomera como ambiente operacional.
                - Article IV: VMamba-Mesh sobre GenAI SPEC v2 e full-lineage.
                """
            )

    with slide_tabs[5]:
        st.markdown("### Resultados que devem ser mostrados")
        metric_rows = _vmamba_presentation_metric_rows()
        if metric_rows:
            st.table(pd.DataFrame(metric_rows).astype(str))
        result_cols = st.columns([1, 1], gap="large")
        with result_cols[0]:
            st.markdown(
                """
                **Adapter rápido.** No GenAI SPEC v2, o VMamba-Mesh adapter melhora o Jaccard de `0,2555` para `0,2748` e o SF-Jaccard de `5.076,80` para `5.464,74` pares identificados corretamente por segundo.

                **Modelo neural treinável.** Na campanha SPEC `article_cpu`, o VMamba-T chegou a Jaccard `0,4815` e o VMamba-Mesh-T a `0,4883`. A qualidade sobe, mas o SF-Jaccard cai para cerca de `201-202`, porque a inferência neural é mais cara.

                **Full Lineage completo.** Com 20 cenários SOR/SOT/SPEC, VMamba-T chegou a Jaccard `0,3326` e SF-Jaccard `590,34`; VMamba-Mesh-T chegou a Jaccard `0,3333` e SF-Jaccard `622,42`. O delta de SF-Jaccard é positivo, mas o IC de Jaccard ainda quase toca zero, então esse workload ainda pede GPU, treino mais longo e mineração de negativos para reduzir falsos positivos.
                """
            )
            _presentation_image(figures["spec_trainable_sf"], "SPEC v2: adapters plus VMamba-T and VMamba-Mesh-T.")
        with result_cols[1]:
            _presentation_image(figures["spec_trainable_runtime"], "SPEC v2: quality/runtime tradeoff with trainable rows.")
            _presentation_image(figures["full_trainable_sf"], "Full Lineage: adapters plus trainable rows.")
            st.markdown(
                """
                **IC 95% por bootstrap de cenários.**

                Nos adapters do SPEC v2, o delta pareado VMamba-Mesh - VMamba fica acima de zero em Jaccard `[0,0008; 0,0485]` e SF-Jaccard `[38,9; 769,6]`.

                Na campanha neural SPEC, os modelos treináveis aumentam Jaccard agregado, mas não superam os adapters em eficiência. No Full Lineage completo, a campanha neural melhora a qualidade, mas ainda deve ser apresentada com cuidado: o ganho de SF-Jaccard é estável, enquanto o IC de Jaccard ainda quase toca zero.
                """
            )

    with slide_tabs[6]:
        st.markdown(
            """
            ### Roteiro de 10 minutos

            | Tempo | Ação | Tela |
            |---|---|---|
            | 0:00-1:00 | Problema: redundância estrutural em Data Mesh | Help -> VMamba-Mesh Presentation -> Context |
            | 1:00-2:00 | Evolução Artigos I, II, III | Articles I-III |
            | 2:00-4:00 | Por que VMamba-Mesh | Why VMamba-Mesh |
            | 4:00-5:30 | Método Article IV | Article IV Method |
            | 5:30-6:30 | Benchmarks e cenários | Benchmarks |
            | 6:30-7:30 | Resultados principais | Results |
            | 7:30-8:30 | Demo comparando Vanilla VMamba vs VMamba-Mesh | Study Lab -> Deep Learning Workbench |
            | 8:30-9:20 | Demo neural: abrir VMamba-T / VMamba-Mesh-T reports | Study Lab -> Model Reports |
            | 9:20-9:40 | Demo de interpretabilidade neural | Study Lab -> Model Interpretability |
            | 9:40-9:55 | Demo de reprodução do artigo | Benchmark & Examples -> Article Reproducibility |
            | 9:55-10:00 | Fechamento: próximos passos | Research Reports / Model Reports |

            ### Sequência da demo ao vivo
            1. Abrir `Study Lab -> Deep Learning Workbench`.
            2. Selecionar `tpc_ds_genai_spec_v2`, cenário `graph_SOR16_D1_seed42`.
            3. Comparar `Vanilla VMamba baseline` vs `VMamba-Mesh Isomera adapter`.
            4. Mostrar grafo, features, métricas e `Reproducibility Trace`.
            5. Ir para `Study Lab -> Model Reports` e abrir o relatório neural SPEC ou Full.
            6. Mostrar o contrato `graph -> CanonSort -> C0-C5 -> VSS/SS2D -> head -> sigmoid -> threshold`.
            7. Ir para `Study Lab -> Model Interpretability`; selecionar `SPEC_customer_summary_D1 <-> SPEC_store_sales_summary_D1` e rodar saliency.
            8. Ir para `Benchmark & Examples -> Article Reproducibility`; selecionar `Article IV - VMamba-Mesh operational study`, usar `Article evidence` e clicar `Run Reproduction`.
            """
        )

    with slide_tabs[7]:
        st.markdown(
            """
            ### VMamba-Mesh: modelo, decisão e hiperparâmetros

            O resultado agora tem duas famílias: adapters determinísticos para eficiência operacional e VMamba-T/VMamba-Mesh-T como modelos neurais treináveis. Em ambos os casos, a entrada nasce primeiro do grafo convertido em tensor; a rede neural começa depois de CanonSort, canais, DiagFP, rota e máscara esparsa.
            """
        )
        tech_cols = st.columns([1, 1], gap="large")
        with tech_cols[0]:
            st.markdown(
                """
                #### Adapter determinístico
                - **Uso:** valida rapidamente tensorização, features, threshold e reprodutibilidade.
                - **Saída operacional:** lista de pares duplicados retornada por `predict_pairs(graph)`.
                - **Threshold:** calibrado por pares positivos/negativos; no adapter VMamba-Mesh usado aqui, `0.62`.
                - **Decisão:** depois do score, `score >= threshold` vira duplicado.
                """
            )
        with tech_cols[1]:
            st.markdown(
                """
                #### VMamba-T / VMamba-Mesh-T
                - **Entrada:** VMamba-T usa C0/C1; VMamba-Mesh-T usa C0-C5.
                - **Backbone:** patch embedding, blocos VSS, SS2D/cross-scan por linhas e colunas, pooling global.
                - **Head:** MLP sobre embeddings dos dois contextos, diferença, produto elemento a elemento e vetor auxiliar estrutural.
                - **Probabilidade:** o head gera logit `z`; `p_dup = sigmoid(z)`.
                - **Decisão:** `p_dup >= threshold` retorna o par em `predict_pairs(graph)`.
                - **Campanha:** preset `article_cpu`, depths `[2,2,8,2]`, dims `[16,32,64,128]`, AdamW, Weighted BCE, resolução `16`.
                """
            )
        st.info(
            "**Passo-a-passo até o score neural:** o Isomera recebe o grafo, aplica CanonSort, monta o tensor C0-C5, "
            "envia cada contexto ao backbone estilo VMamba, combina os embeddings do par no head, gera o logit `z`, "
            "transforma em score com `sigmoid(z)` e aplica o threshold calibrado."
        )


if st.session_state.active_module == "Help":
    help_tabs = st.tabs(["VMamba-Mesh Presentation", "Tech Docs"])
    with help_tabs[0]:
        _render_vmamba_mesh_presentation()
    with help_tabs[1]:
        left_col, right_col = st.columns([1, 2], gap="large")
        tech_root = _app_path("docs/tech_hub")
        tech_docs = _list_tech_docs(tech_root)

        with left_col:
            st.subheader("Help")
            st.caption("Structured notes for architecture, logic, algorithms, pseudocode, and relationships.")
            with st.expander("References and PDFs", expanded=False):
                abnt_refs = [
                    (
                        "OLIVEIRA, Cayo Felipe Lopes de. Uma metodologia baseada em grafos para "
                        "detecção de redundância estrutural em arquiteturas Data Mesh. 2025. "
                        "Dissertação (Mestrado em Ciência da Computação) – Universidade Federal "
                        "de Pernambuco, Recife, 2025."
                    ),
                    (
                        "OLIVEIRA, Cayo de; DANTAS, Jamilson. Learning structural redundancy in "
                        "Data Mesh graphs with graph isomorphism networks. [S.l.: s.n.], s.d."
                    ),
                    (
                        "OLIVEIRA, Cayo de; MATOS, Rubens; ARAUJO, Jean; DANTAS, Jamilson. "
                        "A redundancy detection framework for distributed tables in Data Mesh "
                        "environments. [S.l.: s.n.], s.d."
                    ),
                ]
                st.markdown("\n".join(f"- {ref}" for ref in abnt_refs))
                downloads = [
                    (
                        "Uma metodologia baseada em grafos para detecção de redundância estrutural em arquiteturas Data Mesh",
                        _app_path("docs/dissertacao/cayo_mestrado_dissertacao_vFinal_ata_ficha.pdf"),
                    ),
                    (
                        "A redundancy detection framework for distributed tables in Data Mesh environments",
                        _app_path("docs/dissertacao/grafos_artigo_reduzido_v4.pdf"),
                    ),
                    (
                        "Learning structural redundancy in Data Mesh graphs with Graph Isomorphism Networks",
                        _app_path("docs/dissertacao/II_artigo_gin_gnn-3.pdf"),
                    ),
                ]
                for label, path in downloads:
                    if path.exists():
                        payload = _safe_read_bytes(path)
                        if payload is not None:
                            st.download_button(label, data=payload, file_name=path.name, mime="application/pdf")

            if not tech_root.exists():
                st.info("Folder `docs/tech_hub` not found.")
            elif not tech_docs:
                st.info("No markdown files found in `docs/tech_hub`.")
            else:
                relative_docs = [p.relative_to(tech_root) for p in tech_docs]
                doc_labels = [str(rel) for rel in relative_docs]
                default_doc = "README.md" if "README.md" in doc_labels else doc_labels[0]
                if "techdoc_doc_select" not in st.session_state or st.session_state.techdoc_doc_select not in doc_labels:
                    st.session_state.techdoc_doc_select = default_doc
                st.markdown("**Sections**")
                for doc_label in doc_labels:
                    label = doc_label.replace("_", " ").replace(".md", "")
                    button_type = "primary" if st.session_state.techdoc_doc_select == doc_label else "secondary"
                    if st.button(label, key=f"techdoc_nav_{doc_label}", use_container_width=True, type=button_type):
                        st.session_state.techdoc_doc_select = doc_label
                        st.rerun()
                st.caption(f"Source: {tech_root / st.session_state.techdoc_doc_select}")

        with right_col:
            st.subheader("Viewer")
            if tech_root.exists() and tech_docs:
                selected_rel = st.session_state.get("techdoc_doc_select")
                if selected_rel:
                    selected_path = tech_root / selected_rel
                    if selected_path.exists():
                        content = selected_path.read_text(encoding="utf-8", errors="replace")
                        content = re.sub(r"^> \*\*Navigation:\*\*.*(?:\n|$)", "", content, flags=re.MULTILINE)
                        st.markdown(content)
                    else:
                        st.warning("Selected markdown file no longer exists.")
                else:
                    st.info("Select a document to view.")

if st.session_state.active_module == "About":
    left_col, right_col = st.columns([1, 2], gap="large")
    with left_col:
        st.subheader("About Isomera")
        st.code(terminal_banner("ABOUT"), language="text")
        st.markdown(
            f"""
            **Version:** `{ISOMERA_IDENTITY['version']}`  
            **Codename:** {ISOMERA_IDENTITY['codename']}  
            **Release date:** {ISOMERA_IDENTITY['release_date']}  
            **Author:** {ISOMERA_IDENTITY['author']}  
            **E-mail:** {ISOMERA_IDENTITY['email']}
            """
        )
        st.markdown(
            """
            **Isomera** is derived from the author’s master’s dissertation.
            The tool operationalizes the proposed methodology and supports
            reproducible experimentation with lineage graphs and isomorphism
            validation.
            """
        )
        st.subheader("Creators")
        st.image(str(_app_path("core/img/cayo.jpeg")), width=140)
        st.markdown(
            """
            **MSc. Cayo Felipe Lopes de Oliveira**  
            Data and analytics professional with 8+ years in IT and data management.
            MSc in Computer Science focused on data quality, reliability, and availability.
            Expertise in Data Engineering, Analytics Engineering, Visualization, and ML.
            Experience with Python, Alteryx, Tableau, SQL, Hadoop, and AWS.
            """
        )
        st.markdown("[LinkedIn](https://www.linkedin.com/in/cayo-oliveira/)")

        st.image(str(_app_path("core/img/jamilson.jpeg")), width=140)
        st.markdown(
            """
            **Prof. PhD. Jamilson Ramalho Dantas**  
            Received his BS in Information Systems (2009) and MSc/PhD in Computer Science
            from UFPE (2013, 2017). Research interests include performance and dependability
            evaluation, Markov chains, Petri nets, and formal models for analysis and simulation
            of computer and communication systems. Works on video streaming, cloud systems, and
            network traffic modeling.
            """
        )
        st.markdown("[LinkedIn](https://www.linkedin.com/in/jamilson-dantas-6b1aa397/)")
    with right_col:
        st.subheader("Feature Notes")
        st.markdown(_feature_notes_text())

if st.session_state.active_module == "Model Lab":
    left_col, right_col = st.columns([1, 2], gap="large")
    pickle_root = _app_path("core/algorithms/pickle/gin_gnn/modelos_gnn_separados")
    pickle_files = sorted(pickle_root.glob("*.pkl")) if pickle_root.exists() else []
    if st.session_state.backend_enabled:
        for pickle_path in pickle_files:
            sync_key = f"{pickle_path.name}:{pickle_path.stat().st_mtime_ns}"
            if sync_key in st.session_state.model_registry_synced:
                continue
            model_version = register_model_artifact(
                st.session_state.backend_db_url,
                model_name=pickle_path.stem,
                artifact_path=str(pickle_path),
                metadata={"size_kb": round(pickle_path.stat().st_size / 1024, 1)},
            )
            register_artifact(
                st.session_state.backend_db_url,
                artifact_type="model_pickle",
                path=str(pickle_path),
                session_id=st.session_state.backend_session_id,
                model_version=model_version,
                metadata={"size_kb": round(pickle_path.stat().st_size / 1024, 1)},
            )
            st.session_state.model_registry_synced.add(sync_key)

    with left_col:
        st.subheader("Model Lab")
        st.caption("Model registry and routing workspace for reusable detector families.")
        st.markdown(
            """
            **Current scope**
            - inspect available detectors
            - verify stored `.pkl` assets
            - inspect and edit benchmark-to-pickle routing
            - test one-pickle, scenario-specific, and best-of routing policies
            """
        )
        st.markdown(
            f"""
            - Registered detectors: {", ".join(list_algorithms())}
            - Pickle directory: `{pickle_root}`
            - Pickles found: {len(pickle_files)}
            """
        )
        selected_pickle = st.selectbox(
            "Validate pickle",
            options=[p.name for p in pickle_files] if pickle_files else ["No pickles found"],
            disabled=not pickle_files,
            key="model_lab_pickle_select",
        )
        benchmark_names = [str(arch["name"]) for arch in _list_architectures()]
        selected_routing_benchmark = st.selectbox(
            "Inspect benchmark routing",
            options=benchmark_names,
            index=benchmark_names.index(st.session_state.get("benchmark_catalog_name", DEFAULT_ARCH_NAME))
            if st.session_state.get("benchmark_catalog_name", DEFAULT_ARCH_NAME) in benchmark_names
            else 0,
            key="model_lab_routing_benchmark",
        )
        run_pickle_validation = st.button(
            "Validate selected pickle",
            disabled=not pickle_files,
            key="model_lab_validate_pickle",
        )

    with right_col:
        st.subheader("Artifacts")
        if pickle_files:
            artifact_rows = []
            for pickle_path in pickle_files:
                artifact_rows.append(
                    {
                        "model": pickle_path.stem,
                        "path": str(pickle_path.relative_to(PROJECT_ROOT)),
                        "size_kb": round(pickle_path.stat().st_size / 1024, 1),
                    }
                )
            st.table(pd.DataFrame(artifact_rows).set_index("model"))
        else:
            st.info("No pickles available in the configured directory.")

        st.subheader("Benchmark Model Routing")
        routing_summary_df, routing_df = _benchmark_routing_tables(selected_routing_benchmark)
        if routing_summary_df.empty:
            st.info("No mapped GNN pickle cluster found for this benchmark.")
        else:
            st.table(
                routing_summary_df[
                    ["model_family", "coverage", "status", "route_policy", "candidate_pickles", "best_of_active"]
                ].astype(str)
            )
            routing_families = sorted(routing_df["model_family"].astype(str).unique().tolist())
            selected_model_lab_family = st.selectbox(
                "Model family",
                options=routing_families,
                key="model_lab_route_family_filter",
            )
            model_lab_routes = routing_df[
                routing_df["model_family"].astype(str) == selected_model_lab_family
            ].copy()
            model_lab_routes["pickle"] = model_lab_routes["pickle_path"].astype(str).map(
                lambda value: Path(value).name if value and not value.startswith("best of") else value
            )
            st.table(model_lab_routes[["scenario", "pickle", "route_mode", "status"]].astype(str))
            st.caption(
                "A GNN cluster is executable only for scenarios with status `mapped`. "
                "Execution choices such as best-of routing are configured in Benchmark & Examples."
            )
        st.info(
            "Model Lab is now read-only for routing. Select execution policies such as `Auto best-of` "
            "or `Force best-of` directly in Benchmark & Examples, because those choices change benchmark results."
        )

        if run_pickle_validation and pickle_files:
            selected_path = pickle_root / selected_pickle
            error = validate_gnn_pickle(selected_path)
            if error is None:
                _log_event("validate_pickle", {"path": str(selected_path), "status": "ok"})
                st.success("Pickle loaded successfully.")
            else:
                _log_event("validate_pickle", {"path": str(selected_path), "status": "error", "error": error})
                st.error(error)

        st.info(
            "Use Scenario Studio to train new `.pkl` artifacts. Use Model Lab to inspect existing artifacts "
            "and define how each benchmark scenario is routed to a pickle family before running Benchmark & Examples."
        )

if st.session_state.active_module == "Admin":
        st.subheader("Admin")
        admin_tabs = st.tabs(
            ["Overview", "Backend Store", "Scenario Warehouse", "Neo4j", "Settings"]
        )

        with admin_tabs[0]:
            status = backend_status(st.session_state.backend_db_url)
            try:
                scenario_schema_count = len(
                    [s for s in list_database_schemas(st.session_state.scenarios_db_url) if s.startswith("scenario_")]
                )
                scenario_schema_note = None
            except Exception as exc:  # noqa: BLE001
                scenario_schema_count = 0
                scenario_schema_note = (
                    "Scenario Warehouse is unavailable in this interpreter. "
                    f"Current Python: {sys.executable}"
                ) if "psycopg" in str(exc) else str(exc)
            summary_cols = st.columns(3, gap="small")
            summary_cols[0].metric("Product Store", _backend_label(st.session_state.backend_db_url))
            summary_cols[1].metric("Scenario Schemas", scenario_schema_count)
            summary_cols[2].metric("Backend Runs", status.run_count)
            if st.session_state.backend_bootstrap_warning:
                st.warning(st.session_state.backend_bootstrap_warning)
            if st.session_state.scenarios_bootstrap_warning and "psycopg" not in st.session_state.scenarios_bootstrap_warning:
                st.warning(st.session_state.scenarios_bootstrap_warning)
            if scenario_schema_note:
                st.caption(f"Scenario schema count unavailable: {scenario_schema_note}")
            info_cols = st.columns(2, gap="large")
            with info_cols[0]:
                st.markdown("**Store roles**")
                st.table(
                    pd.DataFrame(
                        [
                            {"store": "Backend Store", "role": "Product metadata, runs, logs, reports, models, and tracked artifacts."},
                            {"store": "Scenario Warehouse", "role": "Relational benchmark schemas such as `scenario_*` in PostgreSQL."},
                            {"store": "Scenario Studio", "role": "GML/manual curation workspace and publication path for curated scenarios."},
                            {"store": "Neo4j", "role": "Reserved for future graph-native exploration."},
                        ]
                    ).set_index("store")
                )
                st.markdown("**Backend entities**")
                backend_entities = pd.DataFrame(
                    [
                        {"entity": "scenarios", "count": status.scenario_count, "meaning": "Scenario metadata mirrored into the product backend."},
                        {"entity": "labels", "count": status.label_count, "meaning": "Saved label versions produced by manual validation."},
                        {"entity": "runs", "count": status.run_count, "meaning": "Tracked benchmark or detector executions."},
                        {"entity": "logs", "count": status.log_count, "meaning": "Structured events emitted by the app."},
                        {"entity": "reports", "count": status.report_count, "meaning": "Execution summaries linked to runs."},
                        {"entity": "models", "count": status.model_count, "meaning": "Registered model artifacts such as pickles."},
                        {"entity": "artifacts", "count": status.artifact_count, "meaning": "Files tracked by the backend, including logs and labels."},
                    ]
                )
                st.table(backend_entities.set_index("entity"))
            with info_cols[1]:
                st.markdown("**Connection profiles**")
                connection_rows = [
                    {
                        "store": "Backend Store",
                        "engine": _backend_label(st.session_state.backend_db_url),
                        "url": st.session_state.backend_db_url,
                    },
                    {
                        "store": "Scenario Warehouse",
                        "engine": _backend_label(st.session_state.scenarios_db_url),
                        "url": st.session_state.scenarios_db_url,
                    },
                    {
                        "store": "Publication Store",
                        "engine": _backend_label(st.session_state.publication_db_url) if st.session_state.publication_db_url else "Not configured",
                        "url": st.session_state.publication_db_url or "(set in Admin > Settings)",
                    },
                ]
                st.table(pd.DataFrame(connection_rows).set_index("store"))
                st.markdown("**External tools**")
                external_tools = pd.DataFrame(
                    [
                        {
                            "tool": "psql",
                            "usage": "/opt/homebrew/opt/postgresql@16/bin/psql -d isomera_tpcds_benchmark",
                        },
                        {"tool": "DBeaver", "usage": "/Applications/DBeaver.app"},
                    ]
                )
                st.table(external_tools.set_index("tool"))
                st.caption(
                    "Default local architecture: Backend Store on SQLite, Scenario Warehouse on PostgreSQL."
                )

        with admin_tabs[1]:
            top_cols = st.columns([2, 1], gap="large")
            with top_cols[0]:
                st.caption(
                    "Operational store for the Isomera application. Use this for product metadata, audit trails, "
                    "model registry, and execution tracking."
                )
            with top_cols[1]:
                st.toggle(
                    "Write app metadata",
                    value=st.session_state.backend_enabled,
                    key="backend_enabled",
                    help="When enabled, Isomera writes runs, logs, reports, models, and artifacts into the Backend Store.",
                )
            init_cols = st.columns(2, gap="small")
            if init_cols[0].button("Create backend tables", key="admin_init_backend"):
                st.session_state.last_error = None
                try:
                    init_backend_database(st.session_state.backend_db_url)
                    if st.session_state.backend_session_id is None:
                        _init_backend_session()
                    _log_event("init_backend_database", {"database_url": st.session_state.backend_db_url})
                    st.success("Backend initialized.")
                except Exception as exc:  # noqa: BLE001
                    _log_exception("init_backend_database", exc)
            if init_cols[1].button("Reset backend view", key="admin_refresh_backend_registry"):
                st.rerun()
            _render_database_manager(
                title="Backend Store",
                description="Single-screen explorer for the Isomera operational backend.",
                db_url_key="backend_db_url",
                input_key="backend_db_url_input",
                sql_key="backend_sql_text",
                mutation_key="backend_allow_mutation",
                history_key="backend_sql_history",
                schema_key="backend_selected_schema",
                table_key="backend_selected_table",
            )

        with admin_tabs[2]:
            st.caption(
                "Relational warehouse for benchmark scenarios. This is where the TPC-DS pilot schemas live today, "
                "and where future benchmark families will also be created."
            )
            _render_database_manager(
                title="Scenario Warehouse",
                description="Single-screen explorer for benchmark schemas, relational tables, and SQL queries.",
                db_url_key="scenarios_db_url",
                input_key="scenarios_db_url_input",
                sql_key="scenarios_sql_text",
                mutation_key="scenarios_allow_mutation",
                history_key="scenarios_sql_history",
                schema_key="scenarios_selected_schema",
                table_key="scenarios_selected_table",
                preferred_schema_prefix="scenario_",
            )

        with admin_tabs[3]:
            st.subheader("Neo4j")
            st.info(
                "Reserved for a later phase. This area will receive the graph-native store, Cypher workspace, "
                "and alternate visualization pipeline for scenario graphs."
            )
            st.table(
                pd.DataFrame(
                    [
                        {"item": "Connection profile", "status": "planned"},
                        {"item": "Cypher query workspace", "status": "planned"},
                        {"item": "GML import pipeline", "status": "planned"},
                        {"item": "Graph preview", "status": "planned"},
                    ]
                ).set_index("item")
            )

        with admin_tabs[4]:
            st.subheader("Settings")
            st.caption("Runtime, timeout, and tooling settings for the current local environment.")
            settings_cols = st.columns(2, gap="large")
            with settings_cols[0]:
                st.number_input(
                    "Global operation timeout (seconds)",
                    min_value=30,
                    max_value=3600,
                    value=int(st.session_state.global_timeout_secs),
                    key="global_timeout_secs",
                )
                st.number_input(
                    "Max lineage generation time (seconds)",
                    min_value=5,
                    max_value=600,
                    value=int(st.session_state.build_timeout_secs),
                    key="build_timeout_secs",
                )
                st.text_input(
                    "Publication Store URL (MySQL)",
                    value=st.session_state.publication_db_url,
                    key="publication_db_url",
                    help="Optional MySQL URL used to persist published benchmark scenarios, nodes, edges, curated pairs, and publication reports.",
                )
            with settings_cols[1]:
                runtime_rows = pd.DataFrame(
                    [
                        {"setting": "Python executable", "value": sys.executable},
                        {"setting": "psycopg available", "value": str(importlib.util.find_spec("psycopg") is not None)},
                        {"setting": "pymysql available", "value": str(importlib.util.find_spec("pymysql") is not None)},
                        {"setting": "Backend engine", "value": _backend_label(st.session_state.backend_db_url)},
                        {"setting": "Scenario engine", "value": _backend_label(st.session_state.scenarios_db_url)},
                        {"setting": "Publication engine", "value": _backend_label(st.session_state.publication_db_url) if st.session_state.publication_db_url else "Not configured"},
                    ]
                )
                st.table(runtime_rows.set_index("setting"))
            st.markdown("**DBeaver**")
            st.code("open -a DBeaver")
            st.markdown("**PostgreSQL CLI**")
            st.code("/opt/homebrew/opt/postgresql@16/bin/psql -d isomera_tpcds_benchmark")
            st.info(
                "Timeouts stop long-running operations and log the reason. "
                "Use `.venv` when launching the app so PostgreSQL drivers such as `psycopg` are available."
            )
