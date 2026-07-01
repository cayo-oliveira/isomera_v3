"""Algorithm interfaces for isomorphism detection."""
from __future__ import annotations

from typing import Protocol

import networkx as nx


class IsomorphismAlgorithm(Protocol):
    name: str

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        """Return predicted isomorphic node pairs."""
        raise NotImplementedError
