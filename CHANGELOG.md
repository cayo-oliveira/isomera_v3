# Changelog

The application version remains in `main/config/version.json`. Launcher changes are versioned independently.

## Unreleased

- Benchmark model choices now require a non-empty local `.pkl` mapping for every scenario; incomplete families remain visible with their coverage but are disabled, preventing a run that cannot supply its selected checkpoint for all scenarios.
- A checkpoint/model error is isolated to its candidate or scenario. The benchmark continues with other models, keeps successful metric rows, and shows failed model, scenario, checkpoint, concise cause, and expandable traceback separately. If a run reaches its global timeout, completed rows and model failures remain visible together; long tracebacks start collapsed.
- `Article Capture` now uses the same white-on-blue information icon as model help. Help panels open to the right of the icon, stay within the viewport vertically, and toggle closed on a second click.
- Checkpoint diagnosis: the D5 VMamba-Mesh-T file is local (14,477,236 bytes, no macOS `dataless` flag) and contains readable weights, but its PairHead input is 1024 while current code expects 1040. Re-downloading from iCloud would not fix this architecture-version mismatch.
- v2 live QA: one-run TPC-DS test with VF2 and VMamba-Mesh-T retained 38 successful rows and reported 2 failed VMamba-Mesh-T scenario/checkpoint combinations separately; no metrics were fabricated for failed cases and no training was run. v3 syntax and live UI checks passed using the installed v2 Python environment; v3's own managed environment still lacks dependencies, which `--check-only` reported without modifying it.
- Benchmark failures now show a concise diagnosis, active benchmark/scenario/model context, and expandable full traceback; run logs record that context. Progress announces the active inference and each timing repeat, preserves success/failure state, and clears a failed progress bar instead of resetting it to zero.
- Logs now auto-select the newest session and current `streamlit_launch_*.log` when a new launch appears, label current versus previous launches, show modification time, and provide an in-page refresh control; the UI explains that Python exceptions live in Session Log rather than the launcher stdout log.
- `smoke_operational` scans only its own catalog plus explicitly registered routes, avoiding cross-benchmark checkpoints with incompatible model schemas.
- Live QA on v2: `smoke_operational` completed 2 scenarios at 1 run with VF2, Node Match, GNN TPC-DS v1, and the VMamba-Mesh adapter (the adapter has no D2 mapping, shown as a missing pickle); the video-route GNN TPC-DS v1 completed 20/20 scenarios at 1 run. A separate VMamba-Mesh-T probe exposed an existing checkpoint incompatibility at D5 (saved PairHead input 1024 vs current 1040); the UI now shows the mismatch and exact checkpoint. No model training was performed.
- Logs QA after relaunch: the latest session JSONL and current `streamlit_launch_*.log` are selected/displayed immediately; launcher output is distinguished from application traceback.
- Fixed the Streamlit top-right `Main menu` icon: replaced the font-dependent Unicode ellipsis that appeared as a white square with three CSS-drawn white dots, matching the v2 fix.

- Reprint the Isomera splash banner when dependencies are ready and when the Streamlit health check succeeds, with explicit Portuguese status messages.
- Open Benchmark & Examples directly on Run Benchmark, move the primary run/stop actions beside model choices, and use a blue-slate/white palette for dropdown and segmented choices with contrast-safe header controls.
- Move the MPS/CPU badge beside the module heading instead of overlaying the Streamlit toolbar; constrain run count to valid positive values.
- Launcher 1.3.0 streams pip output as it arrives, enables pip download progress bars, labels package lookup/download/install phases, and prints a five-second heartbeat with elapsed time during quiet periods.
- Launcher 1.2.0 stores the managed Python environment under `~/Library/Application Support/Isomera/venvs/isomera_v3`, outside the iCloud-synced repository. It reuses a healthy environment and rebuilds only its managed environment if files are dataless; it never tries to download a virtualenv from iCloud.
- Migrate a legacy repository `.venv` only when it contains dataless files and is verified as generated, Git-ignored, and untracked; ordinary repository files are untouched.
- Keep `--check-only` read-only: it reports whether the local environment exists and is healthy without creating or deleting it.
- Added macOS launcher v1.0.0 parity for safe startup checks: detect iCloud/File Provider `dataless` files before imports, record full-session logs, and show nine explicit startup steps.
- Scope stale Streamlit cleanup to this checkout's absolute app path and abort if cleanup cannot be verified; unrelated processes are never killed.
- Select the requested local port or the next available port in a bounded range rather than stopping an unrelated listener.
- Keep `--check-only` free of process/database side effects; start only missing managed databases and stop only databases started by this launcher session.
- Add a single, user-confirmed retry after ordinary startup failure; dataless preflight failures stop without retry.
- Keep product release `2.5.0` unchanged; launcher version is tracked separately as `1.3.0`.
- Live UI behavior verified on Isomera v2 for the shared Benchmark & Examples screen: changed TPC-DS to `smoke_operational` and confirmed the Run button remained visible/enabled (execution not started). UI and launcher updates are mirrored in this repository; v3 was syntax-checked, not launched.
- Refinement mirrored from v2: primary run action is placed above the workflow cards; `.pkl` discovery reports phase/item progress and caches model routing in the current session for 60 seconds; checkbox, info, select-menu, focus ring, and sidebar-toggle contrast use the shared slate/white palette.
- v2 visual QA: the top-right control is Streamlit's Main menu, styled as a white vertical ellipsis on blue; opened choices and checked model boxes were verified with high contrast; `RUN BENCHMARK` remained visible/enabled after choosing `smoke_operational` (execution not started). Select focus uses a blue ring. The Streamlit Skills nudge is optional framework UI, not required by Isomera.
- The live cache replay error was removed by replacing Streamlit's UI-message cache with per-session model-scan caching; progress callbacks remain inside the visible page lifecycle.
