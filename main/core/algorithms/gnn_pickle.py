"""GNN pickle-based algorithm adapter."""
from __future__ import annotations

import pickle
import itertools
import os
from pathlib import Path
from typing import Any

import networkx as nx

from core.algorithms.base import IsomorphismAlgorithm
from core.algorithms.gnn_training import (
    collate_graph_batches,
    extract_subgraphs,
    graph_to_batch,
    resolve_gnn_torch_device,
)

_CURRENT_PICKLE_PATH: Path | None = None
_CURRENT_PICKLE_MODULE: str | None = "core.algorithms.gnn_model"
_PICKLE_CACHE: dict[tuple[Path, str | None], Any] = {}


def set_gnn_pickle_path(path: str | Path | None) -> None:
    global _CURRENT_PICKLE_PATH
    _CURRENT_PICKLE_PATH = Path(path) if path else None


def set_gnn_pickle_module(module: str | None) -> None:
    global _CURRENT_PICKLE_MODULE
    _CURRENT_PICKLE_MODULE = module or None


def _resolve_torch_device(torch: Any) -> Any:
    device, _ = resolve_gnn_torch_device(torch)
    return device


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return max(int(os.environ.get(name, default)), 1)
    except (TypeError, ValueError):
        return default


def _metadata_for_pickle(path: Path) -> dict[str, Any]:
    metadata_path = path.with_suffix(".json")
    if not metadata_path.exists():
        return {}
    try:
        import json

        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


class _FallbackUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:  # type: ignore[override]
        if module in {"__main__", "__mp_main__"} and _CURRENT_PICKLE_MODULE:
            module = _CURRENT_PICKLE_MODULE
        return super().find_class(module, name)


def _load_pickle(path: Path) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"Pickle file not found: {path}")
    if not path.is_file():
        raise IsADirectoryError(f"GNN pickle path is not a file: {path}")
    cache_key = (path.resolve(), _CURRENT_PICKLE_MODULE)
    if cache_key in _PICKLE_CACHE:
        return _PICKLE_CACHE[cache_key]

    with path.open("rb") as handle:
        obj = _FallbackUnpickler(handle).load()
    _PICKLE_CACHE[cache_key] = obj
    return obj


def validate_gnn_pickle(path: str | Path | None) -> str | None:
    if path is None:
        return "No pickle selected."
    path = Path(path)
    if not path.exists():
        return "Pickle file not found."
    if not path.is_file():
        return "Pickle path is not a file."
    try:
        _load_pickle(path)
    except Exception as exc:  # noqa: BLE001
        return str(exc)
    return None


def _predict_pairs_tuple_batched(
    graph: nx.DiGraph,
    *,
    gnn: Any,
    clf: Any,
    torch: Any,
    device: Any,
    threshold: float = 0.3,
    chunk_size: int = 4096,
    encoder_batch_size: int = 64,
) -> list[tuple[str, str]]:
    subgraphs = extract_subgraphs(graph)
    nodes = list(subgraphs.keys())
    graph_cache: dict[str, Any] = {}
    for node in nodes:
        data = graph_to_batch(subgraphs[node], torch)
        if data.edge_index.numel() == 0:
            continue
        graph_cache[node] = data
    emb_cache: dict[str, Any] = {}
    with torch.no_grad():
        valid_nodes = [node for node in nodes if node in graph_cache]
        safe_encoder_batch = max(int(encoder_batch_size), 1)
        for start in range(0, len(valid_nodes), safe_encoder_batch):
            node_chunk = valid_nodes[start : start + safe_encoder_batch]
            batch_graph = collate_graph_batches([graph_cache[node] for node in node_chunk], torch).to(device)
            embeddings = gnn(batch_graph.x, batch_graph.edge_index, batch_graph.batch)
            for node, embedding in zip(node_chunk, embeddings):
                emb_cache[node] = embedding

        candidate_pairs = [
            (node_a, node_b)
            for node_a, node_b in itertools.combinations(nodes, 2)
            if node_a in emb_cache and node_b in emb_cache
        ]
        predicted: list[tuple[str, str]] = []
        for start in range(0, len(candidate_pairs), max(int(chunk_size), 1)):
            chunk = candidate_pairs[start : start + max(int(chunk_size), 1)]
            left = torch.stack([emb_cache[node_a] for node_a, _ in chunk], dim=0)
            right = torch.stack([emb_cache[node_b] for _, node_b in chunk], dim=0)
            scores = torch.sigmoid(clf(left, right))
            mask = (scores >= float(threshold)).detach().cpu().tolist()
            predicted.extend(pair for pair, keep in zip(chunk, mask) if bool(keep))
    return predicted


def _predict_pairs_from_pickle(
    graph: nx.DiGraph,
    *,
    pickle_path: Path,
    pickle_module: str | None,
) -> list[tuple[str, str]]:
    global _CURRENT_PICKLE_MODULE
    previous_module = _CURRENT_PICKLE_MODULE
    _CURRENT_PICKLE_MODULE = pickle_module
    try:
        obj = _load_pickle(pickle_path)
    finally:
        _CURRENT_PICKLE_MODULE = previous_module

    if hasattr(obj, "predict_pairs"):
        pairs = obj.predict_pairs(graph)
    elif isinstance(obj, tuple) and len(obj) == 2:
        try:
            import torch
        except Exception as exc:  # noqa: BLE001
            raise ValueError(
                "Torch nao disponivel para inferencia GNN."
            ) from exc

        gnn, clf = obj
        metadata = _metadata_for_pickle(pickle_path)
        if metadata.get("device") and "ISOMERA_GNN_DEVICE" not in os.environ:
            os.environ["ISOMERA_GNN_DEVICE"] = str(metadata.get("device", {}).get("requested_device") or metadata.get("requested_device") or "cpu")
            if os.environ["ISOMERA_GNN_DEVICE"] != "cpu":
                os.environ["ISOMERA_ENABLE_ACCELERATOR"] = "1"
        device = _resolve_torch_device(torch)
        gnn = gnn.to(device)
        clf = clf.to(device)
        gnn.eval()
        clf.eval()

        metadata_batched = bool(metadata.get("batched_inference"))
        metadata_batch_size = int(metadata.get("inference_batch_size") or 4096)
        metadata_encoder_batch_size = int(metadata.get("encoder_batch_size") or 64)
        if _env_flag("ISOMERA_GNN_BATCHED", default=metadata_batched):
            pairs = _predict_pairs_tuple_batched(
                graph,
                gnn=gnn,
                clf=clf,
                torch=torch,
                device=device,
                chunk_size=_env_int("ISOMERA_GNN_BATCH_SIZE", metadata_batch_size),
                encoder_batch_size=_env_int("ISOMERA_GNN_ENCODER_BATCH_SIZE", metadata_encoder_batch_size),
            )
        else:
            subgraphs = extract_subgraphs(graph)
            nodes = list(subgraphs.keys())
            pairs = []
            for u, v in itertools.combinations(nodes, 2):
                g1_data = graph_to_batch(subgraphs[u], torch)
                g2_data = graph_to_batch(subgraphs[v], torch)
                if g1_data.edge_index.numel() == 0 or g2_data.edge_index.numel() == 0:
                    continue
                g1 = g1_data.to(device)
                g2 = g2_data.to(device)
                g1.batch = torch.zeros(g1.num_nodes, dtype=torch.long).to(device)
                g2.batch = torch.zeros(g2.num_nodes, dtype=torch.long).to(device)
                with torch.no_grad():
                    emb1 = gnn(g1.x, g1.edge_index, g1.batch)
                    emb2 = gnn(g2.x, g2.edge_index, g2.batch)
                    score = torch.sigmoid(clf(emb1, emb2))
                    if score.item() >= 0.3:
                        pairs.append((u, v))
    elif isinstance(obj, dict) and "pairs" in obj:
        pairs = obj["pairs"]
    elif isinstance(obj, list):
        pairs = obj
    else:
        raise ValueError("Unsupported pickle format for GNN predictions.")

    return [tuple(pair) for pair in pairs]


class GNNPickleAlgorithm(IsomorphismAlgorithm):
    name = "GIN/GNN (Pickle)"

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        if _CURRENT_PICKLE_PATH is None:
            raise ValueError("GNN pickle path not configured.")

        try:
            return _predict_pairs_from_pickle(
                graph,
                pickle_path=_CURRENT_PICKLE_PATH,
                pickle_module=_CURRENT_PICKLE_MODULE,
            )
        except AttributeError as exc:
            raise ValueError(
                "Failed to load pickle. If the model class lives in a module, "
                "set the module path in the UI so it can be imported."
            ) from exc


class BoundGNNPickleAlgorithm(IsomorphismAlgorithm):
    def __init__(self, name: str, pickle_path: str | Path, pickle_module: str | None = "core.algorithms.gnn_model") -> None:
        self.name = name
        self._pickle_path = Path(pickle_path)
        self._pickle_module = pickle_module

    def predict_pairs(self, graph: nx.DiGraph) -> list[tuple[str, str]]:
        return _predict_pairs_from_pickle(
            graph,
            pickle_path=self._pickle_path,
            pickle_module=self._pickle_module,
        )


__all__ = [
    "BoundGNNPickleAlgorithm",
    "GNNPickleAlgorithm",
    "set_gnn_pickle_path",
    "set_gnn_pickle_module",
    "validate_gnn_pickle",
]
