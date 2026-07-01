"""Isomorphism analysis utilities."""
from __future__ import annotations

from collections.abc import Iterable

import networkx as nx

from core.algorithms.registry import get_algorithm


def find_isomorphic_pairs(graph: nx.DiGraph, algorithm: str = "VF2") -> list[tuple[str, str]]:
    """Find isomorphic subgraph pairs using the selected algorithm."""
    algo = get_algorithm(algorithm)
    return algo.predict_pairs(graph)


def predict_isomorphic_nodes(graph: nx.DiGraph, algorithm: str = "VF2") -> set[str]:
    """Return the set of nodes that appear in isomorphic pairs."""
    pairs = find_isomorphic_pairs(graph, algorithm=algorithm)
    return {node for pair in pairs for node in pair}


def apply_removals(
    graph: nx.DiGraph,
    nodes_to_remove: Iterable[str],
    protect_prefixes: Iterable[str] | None = None,
    min_remaining_by_prefix: dict[str, int] | None = None,
) -> tuple[nx.DiGraph, list[str], list[str], list[str]]:
    """Remove nodes and return (new_graph, removed, skipped, isolated_removed)."""
    protect_prefixes = list(protect_prefixes or [])
    min_remaining_by_prefix = dict(min_remaining_by_prefix or {})

    remaining_counts = {
        prefix: sum(prefix in node for node in graph.nodes) for prefix in min_remaining_by_prefix
    }

    new_graph = graph.copy()
    removed: list[str] = []
    skipped: list[str] = []

    for node in nodes_to_remove:
        if node not in new_graph:
            continue
        if any(prefix in node for prefix in protect_prefixes):
            skipped.append(node)
            continue

        blocked = False
        for prefix, min_remaining in min_remaining_by_prefix.items():
            if prefix in node and remaining_counts.get(prefix, 0) <= min_remaining:
                blocked = True
                break
        if blocked:
            skipped.append(node)
            continue

        new_graph.remove_node(node)
        removed.append(node)
        for prefix in remaining_counts:
            if prefix in node:
                remaining_counts[prefix] -= 1

    isolated_removed: list[str] = []
    for node in list(new_graph.nodes):
        if new_graph.in_degree(node) == 0 and new_graph.out_degree(node) == 0:
            new_graph.remove_node(node)
            isolated_removed.append(node)

    return new_graph, removed, skipped, isolated_removed
