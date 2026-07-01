"""Algorithm registry initialization."""
from __future__ import annotations

from core.algorithms.gnn_pickle import GNNPickleAlgorithm
from core.algorithms.node_match import NodeMatchAlgorithm
from core.algorithms.registry import get_algorithm, list_algorithms, register_algorithm
from core.algorithms.vf2 import VF2Algorithm

register_algorithm(VF2Algorithm())
register_algorithm(NodeMatchAlgorithm())
register_algorithm(GNNPickleAlgorithm())

__all__ = ["get_algorithm", "list_algorithms", "register_algorithm"]
