"""Background worker for GNN training jobs."""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.algorithms.gnn_training import ScenarioTrainingSpec, train_benchmark_gnn


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: gnn_training_worker.py <config.json>", file=sys.stderr)
        return 2
    config_path = Path(argv[1]).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    progress_path = Path(config["progress_path"]).resolve()
    stop_flag_path = Path(config["stop_flag_path"]).resolve()
    model_path = Path(config["model_path"]).resolve()

    def on_progress(payload: dict[str, Any]) -> None:
        _write_json(progress_path, payload)

    try:
        requested_device = str(config.get("device") or "cpu")
        os.environ["ISOMERA_GNN_DEVICE"] = requested_device
        if requested_device != "cpu":
            os.environ["ISOMERA_ENABLE_ACCELERATOR"] = "1"
        if config.get("batched_inference"):
            os.environ["ISOMERA_GNN_BATCHED"] = "1"
            os.environ["ISOMERA_GNN_BATCH_SIZE"] = str(config.get("inference_batch_size") or 4096)
            os.environ["ISOMERA_GNN_ENCODER_BATCH_SIZE"] = str(config.get("encoder_batch_size") or 64)
        _write_json(
            progress_path,
            {
                "status": "running",
                "step": "initializing",
                "step_detail": "Starting the training worker and reading the job config.",
                "model_family": config["model_family"],
                "model_label": config["model_label"],
                "benchmark_name": config["benchmark_name"],
                "scenario_names": config["scenario_names"],
                "epochs": config["epochs"],
                "current_epoch": 0,
                "progress": 0.0,
                "optimizer": config.get("optimizer_label") or config.get("optimizer_name"),
                "loss": config.get("loss_label") or config.get("loss_name"),
                "balance_strategy": config.get("balance_strategy_label") or config.get("balance_strategy"),
                "device": requested_device,
                "batch_size": int(config.get("batch_size") or 1),
                "batched_inference": bool(config.get("batched_inference")),
            },
        )
        summary = train_benchmark_gnn(
            [
                ScenarioTrainingSpec(
                    scenario_name=item["scenario_name"],
                    graph_path=Path(item["graph_path"]),
                    labels_path=Path(item["labels_path"]),
                    supervised_labels_path=Path(item["supervised_labels_path"]) if item.get("supervised_labels_path") else None,
                )
                for item in config["scenario_specs"]
            ],
            model_path=model_path,
            epochs=int(config["epochs"]),
            learning_rate=float(config["learning_rate"]),
            hidden_channels=int(config["hidden_channels"]),
            dropout=float(config["dropout"]),
            negative_ratio=int(config["negative_ratio"]),
            seed=int(config["seed"]),
            optimizer_name=str(config["optimizer_name"]),
            train_ratio=float(config.get("train_ratio", 0.8)),
            balance_strategy=str(config.get("balance_strategy", "negative_sampling")),
            loss_name=str(config.get("loss_name", "bce_with_logits")),
            batch_size=int(config.get("batch_size") or 1),
            batched_inference=bool(config.get("batched_inference")),
            inference_batch_size=int(config.get("inference_batch_size") or 4096),
            encoder_batch_size=int(config.get("encoder_batch_size") or 64),
            progress_callback=on_progress,
            stop_flag_path=stop_flag_path,
        )
        summary["requested_device"] = requested_device
        summary["batched_inference"] = bool(config.get("batched_inference"))
        summary["inference_batch_size"] = int(config.get("inference_batch_size") or 4096)
        summary["encoder_batch_size"] = int(config.get("encoder_batch_size") or 64)
        summary["status"] = summary.get("status", "completed")
        _write_json(progress_path, summary)
        return 0
    except Exception as exc:  # noqa: BLE001
        _write_json(
            progress_path,
            {
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
                "model_label": config.get("model_label"),
                "benchmark_name": config.get("benchmark_name"),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
