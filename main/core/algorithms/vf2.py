"""VF2 isomorphism algorithm implementation."""
from __future__ import annotations

import networkx as nx

from core.algorithms.base import IsomorphismAlgorithm


def _subgraphs_by_successors(graph: nx.DiGraph) -> list[tuple[str, nx.DiGraph]]:
    subgraphs: list[tuple[str, nx.DiGraph]] = []
    for node in graph.nodes:
        neighbors = list(graph.successors(node))
        subgraph = graph.subgraph([node] + neighbors)
        subgraphs.append((node, subgraph))
    return subgraphs


class VF2Algorithm(IsomorphismAlgorithm):
    name = "VF2"

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        pairs: list[tuple[str, str]] = []
        subgraphs = _subgraphs_by_successors(graph)
        for i in range(len(subgraphs)):
            for j in range(i + 1, len(subgraphs)):
                node_a, sub_a = subgraphs[i]
                node_b, sub_b = subgraphs[j]
                if nx.is_isomorphic(sub_a, sub_b):
                    pairs.append((node_a, node_b))
        return pairs


__all__ = ["VF2Algorithm"]
