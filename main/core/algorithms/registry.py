"""Registry for isomorphism algorithms."""
from __future__ import annotations

from core.algorithms.base import IsomorphismAlgorithm

_ALGORITHMS: dict[str, IsomorphismAlgorithm] = {}


def register_algorithm(algorithm: IsomorphismAlgorithm) -> None:
    key = algorithm.name.lower()
    _ALGORITHMS[key] = algorithm


def get_algorithm(name: str) -> IsomorphismAlgorithm:
    key = name.lower()
    if key not in _ALGORITHMS:
        available = ", ".join(sorted(_ALGORITHMS))
        raise KeyError(f"Algorithm '{name}' not found. Available: {available}")
    return _ALGORITHMS[key]


def list_algorithms() -> list[str]:
    return [algo.name for _, algo in sorted(_ALGORITHMS.items())]
