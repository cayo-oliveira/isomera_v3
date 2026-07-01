"""Lineage graph generation utilities."""
from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Iterable

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
import networkx as nx
import numpy as np
import pandas as pd


_DOMAIN_RE = re.compile(r"_D(\d+)", re.IGNORECASE)


def _layer_rank(node_name: str) -> int:
    upper = str(node_name).upper()
    if "SOR" in upper:
        return 0
    if "SOT" in upper:
        return 1
    if "SPEC" in upper:
        return 2
    return 3


def _edge_direction_score(graph: nx.DiGraph) -> tuple[int, int]:
    downstream = 0
    upstream = 0
    for source, target in graph.edges:
        source_rank = _layer_rank(str(source))
        target_rank = _layer_rank(str(target))
        if source_rank < target_rank:
            downstream += 1
        elif source_rank > target_rank:
            upstream += 1
    return downstream, upstream


def normalize_lineage_direction(graph: nx.DiGraph) -> tuple[nx.DiGraph, dict[str, object]]:
    """Normalize graph direction to SOR -> SOT -> SPEC when needed."""
    downstream, upstream = _edge_direction_score(graph)
    if upstream > downstream:
        reversed_graph = nx.DiGraph()
        for node, attrs in graph.nodes(data=True):
            reversed_graph.add_node(node, **attrs)
        for source, target, attrs in graph.edges(data=True):
            reversed_graph.add_edge(target, source, **attrs)
        return reversed_graph, {
            "direction_normalized": True,
            "original_direction": "upstream_to_downstream_reversed",
            "normalized_direction": "SOR_to_SOT_to_SPEC",
            "downstream_edges_before": downstream,
            "upstream_edges_before": upstream,
        }
    return graph.copy(), {
        "direction_normalized": False,
        "original_direction": "SOR_to_SOT_to_SPEC",
        "normalized_direction": "SOR_to_SOT_to_SPEC",
        "downstream_edges_before": downstream,
        "upstream_edges_before": upstream,
    }


def _node_domain(node_name: str) -> str:
    match = _DOMAIN_RE.search(str(node_name))
    if match:
        return f"D{match.group(1)}"
    alt = re.match(r"d(\d+)_", str(node_name), re.IGNORECASE)
    if alt:
        return f"D{alt.group(1)}"
    return "DX"


def _hierarchical_lineage_layout(graph: nx.DiGraph) -> dict[str, tuple[float, float]]:
    nodes = sorted(graph.nodes, key=lambda node: (_layer_rank(str(node)), _node_domain(str(node)), str(node)))
    domains = sorted({_node_domain(str(node)) for node in nodes})
    domain_rank = {domain: index for index, domain in enumerate(domains)}
    grouped: dict[tuple[int, str], list[str]] = {}
    for node in nodes:
        key = (_layer_rank(str(node)), _node_domain(str(node)))
        grouped.setdefault(key, []).append(str(node))

    positions: dict[str, tuple[float, float]] = {}
    domain_gap = 3.8
    row_gap = 0.9
    for (layer, domain), grouped_nodes in grouped.items():
        base_y = -(domain_rank[domain] * domain_gap)
        offset = (len(grouped_nodes) - 1) / 2.0
        for index, node in enumerate(sorted(grouped_nodes)):
            x = float(layer * 4.3)
            y = base_y + ((offset - index) * row_gap)
            positions[node] = (x, y)
    return positions


def generate_lineage_graph(
    num_domains: int,
    min_columns: int,
    max_columns: int,
) -> nx.DiGraph:
    """Generate a lineage graph based on domain configuration."""
    if min_columns > max_columns:
        raise ValueError("Min Columns cannot be greater than Max Columns.")

    graph = nx.DiGraph()

    for domain in range(1, num_domains + 1):
        domain_label = f"Domain {domain}"
        graph.add_node(domain_label)

        for table_type in ["SOR", "SOT", "SPEC"]:
            table_name = f"{domain_label}-{table_type}"
            graph.add_node(table_name)
            graph.add_edge(domain_label, table_name)

            if table_type == "SOT":
                graph.add_edge(f"{domain_label}-SOR", table_name)
            if table_type == "SPEC":
                graph.add_edge(f"{domain_label}-SOT", table_name)

    return graph


def generate_random_lineage_graph(
    num_domains: int,
    num_sors: int,
    min_tables: int,
    max_tables: int,
    seed: int | None = None,
) -> nx.DiGraph:
    """Generate a randomized lineage graph with SOR/SOT/SPEC tiers."""
    if min_tables > max_tables:
        raise ValueError("Min tables cannot be greater than Max tables.")

    rng = random.Random(seed)
    graph = nx.DiGraph()

    sor_nodes = []
    for domain in range(1, num_domains + 1):
        for sor in range(1, num_sors + 1):
            sor_label = f"SOR{sor}_D{domain}_T0"
            graph.add_node(sor_label)
            sor_nodes.append(sor_label)

    total_tables = rng.randint(min_tables, max_tables)
    sot_nodes = []
    sot_seen = set()
    while len(sot_nodes) < total_tables:
        domain = rng.randint(1, num_domains)
        table_label = f"SOT_D{domain}_T{rng.randint(1, total_tables)}"
        if table_label in sot_seen:
            continue
        sot_seen.add(table_label)
        sot_nodes.append(table_label)
        graph.add_node(table_label)

        if sor_nodes:
            connected_sors = rng.sample(sor_nodes, rng.randint(1, min(len(sor_nodes), 3)))
            for sor in connected_sors:
                graph.add_edge(sor, table_label)

    spec_nodes = []
    spec_seen = set()
    spec_count = rng.randint(1, max(1, total_tables))
    while len(spec_nodes) < spec_count and sot_nodes:
        sot = rng.choice(sot_nodes)
        domain = sot.split("_")[1]
        spec_label = f"SPEC_{domain}_T{rng.randint(1, 3)}"
        if spec_label in spec_seen:
            continue
        spec_seen.add(spec_label)
        spec_nodes.append(spec_label)
        graph.add_node(spec_label)

        connected_sots = rng.sample(sot_nodes, rng.randint(1, min(len(sot_nodes), 3)))
        for sot_node in connected_sots:
            graph.add_edge(sot_node, spec_label)

    return graph


def plot_lineage_graph(graph: nx.DiGraph, seed: int | None = None) -> plt.Figure:
    """Render a lineage graph into a matplotlib figure."""
    domains = sorted({_node_domain(str(node)) for node in graph.nodes}) or ["D1"]
    max_bucket = 1
    layer_domain_counts: dict[tuple[int, str], int] = {}
    for node in graph.nodes:
        key = (_layer_rank(str(node)), _node_domain(str(node)))
        layer_domain_counts[key] = layer_domain_counts.get(key, 0) + 1
        max_bucket = max(max_bucket, layer_domain_counts[key])
    fig_width = max(10.0, 5.2 + (4.1 * 3))
    fig_height = max(4.8, 1.9 + (len(domains) * 2.0) + (max_bucket * 0.35))
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))
    fig.patch.set_facecolor("#F5F5F3")
    ax.set_facecolor("#ECECE8")
    pos = _hierarchical_lineage_layout(graph)
    colors = []
    for node in graph.nodes:
        if "SOR" in node:
            colors.append("#A8AAA2")
        elif "SOT" in node:
            colors.append("#91AFA1")
        elif "SPEC" in node:
            colors.append("#6B7A58")
        else:
            colors.append("#C6D1C9")
    node_count = max(1, graph.number_of_nodes())
    font_size = 9 if node_count <= 12 else 8 if node_count <= 24 else 7 if node_count <= 40 else 6
    node_size = 1200 if node_count <= 12 else 980 if node_count <= 24 else 860
    nx.draw_networkx_edges(
        graph,
        pos,
        edge_color="#8E9288",
        width=1.8,
        alpha=0.85,
        arrows=True,
        arrowsize=18,
        ax=ax,
        connectionstyle="arc3,rad=0.05",
    )
    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=colors,
        node_size=node_size,
        edgecolors="#F5F5F3",
        linewidths=1.2,
        ax=ax,
    )
    nx.draw_networkx_labels(
        graph,
        pos,
        font_color="#2F312E",
        font_size=font_size,
        bbox={"facecolor": "#F5F5F3", "edgecolor": "none", "alpha": 0.72, "pad": 0.18},
        ax=ax,
    )
    ax.set_title("Lineage Visualization", color="#2F312E")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig


def save_graph_gml(graph: nx.DiGraph, path: str | Path) -> Path:
    """Save a graph to a .gml file and return the resolved path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_gml(graph, path)
    return path.resolve()


def adjacency_matrix_dataframe(graph: nx.DiGraph) -> pd.DataFrame:
    """Return the adjacency matrix as a DataFrame."""
    nodes = sorted(graph.nodes)
    matrix = nx.to_numpy_array(graph, nodelist=nodes, dtype=int)
    return pd.DataFrame(matrix, index=nodes, columns=nodes)


def plot_adjacency_matrix(graph: nx.DiGraph) -> plt.Figure:
    """Render the adjacency matrix into a readable figure."""
    df = adjacency_matrix_dataframe(graph)
    size = max(6.0, min(18.0, 2.5 + (len(df) * 0.45)))
    fig, ax = plt.subplots(figsize=(size, size))
    fig.patch.set_facecolor("#F5F5F3")
    ax.set_facecolor("#ECECE8")
    binary_cmap = ListedColormap(["#F3F1EB", "#6B7A58"])
    binary_norm = BoundaryNorm(boundaries=[-0.5, 0.5, 1.5], ncolors=binary_cmap.N)
    heatmap = ax.imshow(df.to_numpy(), cmap=binary_cmap, norm=binary_norm)
    tick_font = 8 if len(df) <= 12 else 7 if len(df) <= 20 else 6 if len(df) <= 32 else 5
    ax.set_xticks(np.arange(len(df.columns)))
    ax.set_yticks(np.arange(len(df.index)))
    ax.set_xticklabels(df.columns, fontsize=tick_font, rotation=45, ha="right")
    ax.set_yticklabels(df.index, fontsize=tick_font)
    ax.set_title("Adjacency Matrix", color="#2F312E")
    for i in range(len(df.index)):
        for j in range(len(df.columns)):
            value = int(df.iat[i, j])
            ax.text(
                j,
                i,
                str(value),
                ha="center",
                va="center",
                color="#1F2A1F" if value else "#5E6059",
                fontsize=max(5, tick_font - 1),
            )
    cbar = fig.colorbar(heatmap, ax=ax, fraction=0.046, pad=0.04, ticks=[0, 1])
    cbar.ax.set_yticklabels(["0", "1"])
    fig.tight_layout()
    return fig


def edge_dataframe(graph: nx.DiGraph) -> pd.DataFrame:
    """Return the edges as a DataFrame."""
    return pd.DataFrame(
        [{"origem": source, "destino": target, "aresta": "lineage"} for source, target in graph.edges],
        columns=["origem", "destino", "aresta"],
    )
