from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

import networkx as nx

REPO_ROOT = Path(__file__).resolve().parents[2]
MAIN_ROOT = REPO_ROOT / "main"
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))

import core.algorithms  # noqa: F401,E402
from core.algorithms.gnn_pickle import BoundGNNPickleAlgorithm  # noqa: E402
from core.algorithms.gnn_training import ScenarioTrainingSpec, train_benchmark_gnn  # noqa: E402
from core.isomorphism import find_isomorphic_pairs  # noqa: E402

import generate_v1_v2_routing_reports as routing  # noqa: E402
from build_research_report_package import build_package  # noqa: E402


BENCHMARK_NAME = "isomerav2_night_test"
REPORT_TYPE = "night_routing_5_model_test"
NEW_SCENARIO = "graph_SOR2_D4_seed42"
SEED = 77


def _log(message: str) -> None:
    print(f"[night_routing_test] {message}", flush=True)


def _copy_scenario(source_arch: str, scenario_name: str, target_root: Path) -> None:
    source_root = MAIN_ROOT / "data/architectures" / source_arch
    for subdir, suffix in (("gml", ".gml"), ("real_pairs", ".json")):
        source_path = source_root / subdir / f"{scenario_name}{suffix}"
        target_path = target_root / subdir / f"{scenario_name}{suffix}"
        if not source_path.exists():
            raise FileNotFoundError(f"Missing source scenario file: {source_path}")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _prepare_benchmark() -> Path:
    root = MAIN_ROOT / "data/architectures" / BENCHMARK_NAME
    for subdir in ("gml", "real_pairs", "models"):
        (root / subdir).mkdir(parents=True, exist_ok=True)
    _copy_scenario("isomerav2_bench", "graph_SOR2_D5_seed42", root)
    _copy_scenario("isomerav2_bench", "graph_SOR8_D5_seed42", root)
    _copy_scenario("tpc_ds", NEW_SCENARIO, root)
    manifest_path = root / "benchmark_manifest.json"
    manifest = {
        "name": BENCHMARK_NAME,
        "display_name": "Isomera v2 Night Routing Test",
        "scenarios": {
            scenario: {
                "gml_path": str(root / "gml" / f"{scenario}.gml"),
                "labels_path": str(root / "real_pairs" / f"{scenario}.json"),
            }
            for scenario in ("graph_SOR2_D5_seed42", "graph_SOR8_D5_seed42", NEW_SCENARIO)
        },
        "models": {},
        "model_clusters": {},
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")
    return root


def _train_quick_model(root: Path) -> tuple[Path, dict[str, Any]]:
    model_path = root / "models" / f"GNN_night_quick_{NEW_SCENARIO}.pkl"
    _log(f"training quick GNN for {NEW_SCENARIO}")

    def _progress(payload: dict[str, Any]) -> None:
        _log(
            "training "
            f"{payload.get('step')} epoch={payload.get('current_epoch', 0)}/{payload.get('epochs', '-')} "
            f"train_loss={payload.get('train_loss', '-')}"
        )

    metadata = train_benchmark_gnn(
        [
            ScenarioTrainingSpec(
                scenario_name=NEW_SCENARIO,
                graph_path=root / "gml" / f"{NEW_SCENARIO}.gml",
                labels_path=root / "real_pairs" / f"{NEW_SCENARIO}.json",
            )
        ],
        model_path=model_path,
        epochs=1,
        learning_rate=0.005,
        hidden_channels=8,
        dropout=0.1,
        negative_ratio=1,
        seed=SEED,
        optimizer_name="adam",
        train_ratio=0.8,
        balance_strategy="negative_sampling",
        progress_callback=_progress,
    )
    return model_path, metadata


def _route_v2_pickles(scenario_names: list[str]) -> dict[str, Path]:
    v2_pickles = routing._isomerav2_pickles()
    if not v2_pickles:
        raise FileNotFoundError("No Isomera v2 pickles available.")
    fallback = v2_pickles[sorted(v2_pickles)[0]]
    return {scenario: v2_pickles.get(scenario, fallback) for scenario in scenario_names}


def _run_benchmark(root: Path, night_model_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    scenarios = routing._load_scenarios(BENCHMARK_NAME)
    scenario_names = sorted(scenarios)
    v1_candidates = sorted(routing.BASELINE_PICKLE_ROOT.glob("*.pkl"))
    v2_routes = _route_v2_pickles(scenario_names)
    selection_rows: list[dict[str, Any]] = []
    per_scenario: list[dict[str, Any]] = []
    routing_rows: list[dict[str, Any]] = []
    for scenario_name in scenario_names:
        graph: nx.DiGraph = scenarios[scenario_name]["graph"]
        labels = scenarios[scenario_name]["labels"]
        _log(f"benchmarking {scenario_name}")
        deterministic = [
            ("VF2", lambda g: find_isomorphic_pairs(g, algorithm="VF2"), "", "deterministic_baseline", "not_applicable", "deterministic_algorithm"),
            ("Node Match", lambda g: find_isomorphic_pairs(g, algorithm="Node Match (Custom)"), "", "deterministic_baseline", "not_applicable", "deterministic_algorithm"),
        ]
        for algorithm, predictor, artifact_path, artifact_role, route_mode, route_source in deterministic:
            predicted, timings = routing._predict_with_timing(predictor, graph, routing.BENCHMARK_RUNS)
            per_scenario.append(
                routing._metric_row(
                    scenario_name=scenario_name,
                    graph=graph,
                    labels=labels,
                    algorithm=algorithm,
                    predicted=predicted,
                    timings=timings,
                    artifact_path=artifact_path,
                    artifact_role=artifact_role,
                    route_mode=route_mode,
                    route_source=route_source,
                )
            )
        best_row, candidate_rows = routing._evaluate_best_of_cluster(
            scenario_name=scenario_name,
            graph=graph,
            labels=labels,
            candidate_paths=v1_candidates,
            algorithm="GNN TPC-DS v1 cluster",
            artifact_role="baseline_tpcds_pickle",
            route_source="night_force_best_of_cluster",
        )
        per_scenario.append(best_row)
        selection_rows.extend(candidate_rows)

        v2_path = v2_routes[scenario_name]
        v2_predictor = BoundGNNPickleAlgorithm(
            f"GNN Isomera v2 [{scenario_name}]",
            v2_path,
            "core.algorithms.gnn_model",
        ).predict_pairs
        predicted, timings = routing._predict_with_timing(v2_predictor, graph, routing.BENCHMARK_RUNS)
        per_scenario.append(
            routing._metric_row(
                scenario_name=scenario_name,
                graph=graph,
                labels=labels,
                algorithm="GNN Isomera v2 cluster",
                predicted=predicted,
                timings=timings,
                artifact_path=str(v2_path),
                artifact_role="new_isomerav2_pickle",
                route_mode="scenario_specific" if v2_path.stem.endswith(scenario_name) else "single_pickle_fallback",
                route_source="night_explicit_mapping",
            )
        )

        night_predictor = BoundGNNPickleAlgorithm(
            f"GNN Night Quick [{scenario_name}]",
            night_model_path,
            "core.algorithms.gnn_model",
        ).predict_pairs
        predicted, timings = routing._predict_with_timing(night_predictor, graph, routing.BENCHMARK_RUNS)
        per_scenario.append(
            routing._metric_row(
                scenario_name=scenario_name,
                graph=graph,
                labels=labels,
                algorithm="GNN Night quick cluster",
                predicted=predicted,
                timings=timings,
                artifact_path=str(night_model_path),
                artifact_role="new_night_quick_pickle",
                route_mode="single_pickle_all_scenarios",
                route_source="night_manual_mapping",
            )
        )

        routing_rows.extend(
            [
                {
                    "model_family": "GNN TPC-DS v1 cluster",
                    "scenario": scenario_name,
                    "artifact_path": best_row["artifact_path"],
                    "artifact_role": "baseline_tpcds_pickle",
                    "route_mode": "best_of_cluster",
                    "route_source": "night_force_best_of_cluster",
                    "selection_metric": routing.SELECTION_METRIC,
                    "selection_candidates": len(v1_candidates),
                },
                {
                    "model_family": "GNN Isomera v2 cluster",
                    "scenario": scenario_name,
                    "artifact_path": str(v2_path),
                    "artifact_role": "new_isomerav2_pickle",
                    "route_mode": "scenario_specific" if v2_path.stem.endswith(scenario_name) else "single_pickle_fallback",
                    "route_source": "night_explicit_mapping",
                },
                {
                    "model_family": "GNN Night quick cluster",
                    "scenario": scenario_name,
                    "artifact_path": str(night_model_path),
                    "artifact_role": "new_night_quick_pickle",
                    "route_mode": "single_pickle_all_scenarios",
                    "route_source": "night_manual_mapping",
                },
            ]
        )
    cluster_rows = [
        {"model_family": "VF2", "artifact_count": 0, "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "deterministic detector"},
        {"model_family": "Node Match", "artifact_count": 0, "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "deterministic detector"},
        {"model_family": "GNN TPC-DS v1 cluster", "artifact_count": len(v1_candidates), "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": f"force best-of by {routing.SELECTION_METRIC}; all candidates are exported"},
        {"model_family": "GNN Isomera v2 cluster", "artifact_count": len(set(v2_routes.values())), "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "explicit/fallback mapping without best-of"},
        {"model_family": "GNN Night quick cluster", "artifact_count": 1, "scenario_count": len(scenario_names), "coverage": f"{len(scenario_names)}/{len(scenario_names)}", "reporting_rule": "one quick pickle applied to all scenarios"},
    ]
    return per_scenario, selection_rows, routing_rows, cluster_rows


def main() -> None:
    started = time.perf_counter()
    root = _prepare_benchmark()
    model_path, metadata = _train_quick_model(root)
    scenarios = routing._load_scenarios(BENCHMARK_NAME)
    per_scenario, selection_rows, routing_rows, cluster_rows = _run_benchmark(root, model_path)
    capture_path = routing._build_capture(
        benchmark_name=BENCHMARK_NAME,
        report_type=REPORT_TYPE,
        architecture_name=BENCHMARK_NAME,
        scenarios=scenarios,
        per_scenario_metrics=per_scenario,
        selection_rows=selection_rows,
        routing_rows=routing_rows,
        cluster_rows=cluster_rows,
    )
    payload = json.loads(capture_path.read_text(encoding="utf-8"))
    payload.setdefault("publication_tables", {})["training_dataset"] = metadata.get("dataset_summary", [])
    payload.setdefault("publication_tables", {})["training_history"] = metadata.get("history", [])
    payload.setdefault("publication_tables", {})["model_artifact"] = [
        {
            "model_name": model_path.stem,
            "artifact_path": str(model_path),
            "artifact_role": "new_night_quick_pickle",
            "route_mode": "single_pickle_all_scenarios",
            "scenario": NEW_SCENARIO,
        }
    ]
    payload["summary"]["model_name"] = "routing_5_detector_families"
    payload["summary"]["model_path"] = str(model_path)
    capture_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    package = build_package(capture_path)
    package["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    print(json.dumps(package, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
