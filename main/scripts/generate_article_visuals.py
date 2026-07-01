from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


REPO_ROOT = Path(__file__).resolve().parents[2]
IMG_DIR = REPO_ROOT / "research" / "img"

BG = "#f6f5ef"
INK = "#28302d"
MUTED = "#69726d"
GREEN = "#557a68"
GREEN_DARK = "#315344"
BLUE = "#2f77b4"
BLUE_LIGHT = "#dbeaf6"
TEAL = "#57b6a5"
ORANGE = "#e0a949"
RED = "#c85d4d"
CARD = "#fbfaf4"
LINE = "#b8b6ac"


def _setup(width: float = 14, height: float = 7):
    fig, ax = plt.subplots(figsize=(width, height), dpi=300)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _box(ax, xy, wh, title, body="", fc=CARD, ec=LINE, title_color=INK, lw=1.3, fs=11):
    x, y = xy
    w, h = wh
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        linewidth=lw,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(patch)
    ax.text(x + 0.018, y + h - 0.034, title, color=title_color, fontsize=fs, fontweight="bold", va="top")
    if body:
        wrapped = []
        for line in body.split("\n"):
            wrapped.extend(wrap(line, width=max(18, int(w * 72))))
        ax.text(
            x + 0.018,
            y + h - 0.072,
            "\n".join(wrapped[:8]),
            color=MUTED,
            fontsize=fs - 2,
            va="top",
            linespacing=1.25,
        )
    return patch


def _arrow(ax, start, end, color=GREEN_DARK, lw=1.8, text=None, text_offset=(0, 0)):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=15,
            linewidth=lw,
            color=color,
            shrinkA=4,
            shrinkB=4,
        )
    )
    if text:
        mx = (start[0] + end[0]) / 2 + text_offset[0]
        my = (start[1] + end[1]) / 2 + text_offset[1]
        ax.text(mx, my, text, color=color, fontsize=8.5, ha="center", va="center", fontweight="bold")


def _title(ax, title, subtitle):
    ax.text(0.03, 0.965, title, fontsize=20, fontweight="bold", color=INK, va="top")
    ax.text(0.03, 0.925, subtitle, fontsize=10.5, color=MUTED, va="top")


def architecture_layers() -> None:
    fig, ax = _setup(14, 7.6)
    _title(
        ax,
        "Isomera v2 software architecture",
        "Layered research workbench: sources become normalized graph contracts, then labels, models, benchmarks, and article packages.",
    )
    layers = [
        ("Client and orchestration", "Streamlit UI\nScenario Studio\nBenchmark & Examples\nModel Lab\nResearch Reports", 0.08, BLUE_LIGHT, BLUE),
        ("Scenario Materialization API", "connect database\nintrospect schema\nload manifest\nnormalize SOR -> SOT -> SPEC\nexport GML/JSON/CSV", 0.265, "#e7f2ea", GREEN),
        ("Core graph and ML services", "NetworkX graph contract\ncandidate generation\nVF2 and Node Match\nGIN training/inference\nrouting policy", 0.45, "#fff0d4", ORANGE),
        ("Stores and artifacts", "PostgreSQL scenario warehouse\nMySQL/SQLite operational backend\nGML, labels, pkl, reports\nLaTeX/PDF/ZIP", 0.635, "#f3e6df", RED),
    ]
    for title, body, y, fc, ec in layers:
        _box(ax, (0.08, y), (0.84, 0.135), title, body, fc=fc, ec=ec, fs=12)
    for y1, y2, label in [(0.215, 0.265, "request / selected source"), (0.40, 0.45, "canonical scenario contract"), (0.585, 0.635, "metrics, models, evidence")]:
        _arrow(ax, (0.5, y1), (0.5, y2), text=label, text_offset=(0.16, 0))
    ax.text(0.075, 0.025, "Draw.io note: keep four horizontal layers and preserve the API as the boundary between UI sources and graph/model services.", color=RED, fontsize=9, fontweight="bold")
    fig.savefig(IMG_DIR / "isomera_v2_architecture_layers.png", bbox_inches="tight", facecolor=BG)
    fig.savefig(IMG_DIR / "isomera_v2_architecture_layers.svg", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def api_flow() -> None:
    fig, ax = _setup(15.5, 8)
    _title(
        ax,
        "Scenario Materialization API pattern",
        "Client/requestor flow used when Isomera connects to PostgreSQL and converts relational tables into lineage graphs.",
    )
    _box(ax, (0.03, 0.62), (0.16, 0.16), "Client", "Researcher chooses engine, database, schema, scope and filters.", fc="#edf4fa", ec=BLUE, fs=11)
    _box(ax, (0.24, 0.62), (0.17, 0.16), "Requestor", "Streamlit validates inputs and calls the materialization service.", fc="#edf4fa", ec=BLUE, fs=11)
    _box(ax, (0.47, 0.58), (0.23, 0.22), "Scenario API", "Stable Python API boundary. It receives the request and returns a scenario contract.", fc="#e7f2ea", ec=GREEN, fs=12)
    _box(ax, (0.77, 0.62), (0.18, 0.16), "PostgreSQL", "TPC-DS v2 schemas, tables, columns, keys and manifest links.", fc="#fff0d4", ec=ORANGE, fs=11)
    steps = [
        (0.08, "1 submit", (0.19, 0.70), (0.24, 0.70)),
        (0.16, "2 validate", (0.41, 0.70), (0.47, 0.70)),
        (0.16, "3 inspect", (0.70, 0.72), (0.77, 0.72)),
        (0.16, "4 metadata", (0.77, 0.66), (0.70, 0.66)),
    ]
    for _, label, s, e in steps:
        _arrow(ax, s, e, text=label, text_offset=(0, 0.04))
    _box(ax, (0.07, 0.32), (0.18, 0.14), "Introspection", "information_schema tables, columns, PKs, FKs", fs=10)
    _box(ax, (0.29, 0.32), (0.18, 0.14), "Manifest loading", "TPC-DS semantic contract when present", fs=10)
    _box(ax, (0.51, 0.32), (0.18, 0.14), "Graph builder", "nodes=tables\nedges=lineage dependencies", fs=10)
    _box(ax, (0.73, 0.32), (0.18, 0.14), "Normalizer", "canonical SOR -> SOT -> SPEC direction", fs=10)
    for x1, x2, txt in [(0.25, 0.29, "schema facts"), (0.47, 0.51, "table map"), (0.69, 0.73, "directed graph")]:
        _arrow(ax, (x1, 0.39), (x2, 0.39), text=txt, text_offset=(0, 0.035))
    _box(ax, (0.12, 0.08), (0.76, 0.13), "Returned scenario contract", "NetworkX graph + GML + adjacency matrix + edge table + candidate pairs + source metadata + report-ready JSON/CSV.", fc="#eef4ef", ec=GREEN, fs=12)
    _arrow(ax, (0.82, 0.32), (0.82, 0.21), text="5 export", text_offset=(0.06, 0))
    ax.text(0.07, 0.025, "Draw.io note: model this as Client -> Requestor -> API -> Database Adapter -> Contract, with numbered messages.", color=RED, fontsize=9, fontweight="bold")
    fig.savefig(IMG_DIR / "isomera_v2_api_flow.png", bbox_inches="tight", facecolor=BG)
    fig.savefig(IMG_DIR / "isomera_v2_api_flow.svg", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def usage_sequence() -> None:
    fig, ax = _setup(15, 7.6)
    _title(ax, "Isomera user workflow and service sequence", "Operational path from user request to report package; optional branches remain explicit.")
    actors = [
        ("User", 0.07),
        ("Streamlit UI", 0.22),
        ("Scenario API", 0.39),
        ("Validation Store", 0.56),
        ("Training Service", 0.72),
        ("Benchmark/Report", 0.88),
    ]
    for name, x in actors:
        ax.text(x, 0.84, name, ha="center", color=INK, fontsize=11, fontweight="bold")
        ax.plot([x, x], [0.12, 0.80], color=LINE, linestyle="--", linewidth=1)
    messages = [
        (0.07, 0.22, 0.74, "choose DB/GML/manual input"),
        (0.22, 0.39, 0.66, "materialize scenario contract"),
        (0.39, 0.22, 0.58, "lineage graph + tables"),
        (0.22, 0.56, 0.50, "autosave pair labels"),
        (0.56, 0.72, 0.42, "supervised dataset"),
        (0.72, 0.56, 0.34, ".pkl + training metrics"),
        (0.56, 0.88, 0.26, "benchmark evidence"),
        (0.88, 0.07, 0.18, "PDF/TEX/ZIP report"),
    ]
    for x1, x2, y, label in messages:
        _arrow(ax, (x1, y), (x2, y), text=label, text_offset=(0, 0.035))
    _box(ax, (0.05, 0.02), (0.9, 0.08), "Reproducibility contract", "Every run stores source metadata, filter settings, validation dataset, model routing, metrics, figures and report package.", fc="#fbfaf4", ec=GREEN, fs=10)
    ax.text(0.05, 0.005, "Draw.io note: redraw as a sequence diagram with request/response labels and persistence points.", color=RED, fontsize=8.5, fontweight="bold")
    fig.savefig(IMG_DIR / "isomera_v2_usage_sequence.png", bbox_inches="tight", facecolor=BG)
    fig.savefig(IMG_DIR / "isomera_v2_usage_sequence.svg", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def gnn_pipeline() -> None:
    fig, ax = _setup(16, 8)
    _title(
        ax,
        "GIN pair classifier used by Isomera",
        "How a database lineage pair becomes tensor input, graph embeddings, a duplicate probability and a routed pickle artifact.",
    )
    # Left graph pair
    nodes_a = [(0.07, 0.64), (0.13, 0.69), (0.13, 0.58), (0.20, 0.64)]
    nodes_b = [(0.07, 0.39), (0.13, 0.45), (0.13, 0.34), (0.20, 0.39)]
    for nodes, label in [(nodes_a, "Subgraph A\nupstream lineage"), (nodes_b, "Subgraph B\ncandidate duplicate")]:
        for x, y in nodes:
            ax.scatter([x], [y], s=190, color=GREEN if x >= 0.20 else "#9ba29b", zorder=3)
        for s, e in [(nodes[0], nodes[1]), (nodes[0], nodes[2]), (nodes[1], nodes[3]), (nodes[2], nodes[3])]:
            _arrow(ax, s, e, color="#7b837c", lw=1.0)
        ax.text(0.045, nodes[0][1] + 0.105, label, fontsize=9, color=INK, fontweight="bold")
    _box(ax, (0.25, 0.48), (0.14, 0.20), "Tensor encoder", "x = ones(|V|,1)\nedge_index = directed edges\nbatch = graph id", fc="#eef4ef", ec=GREEN, fs=10)
    _arrow(ax, (0.205, 0.64), (0.25, 0.60), text="to PyG")
    _arrow(ax, (0.205, 0.39), (0.25, 0.55), text="to PyG")
    # GIN layers as vertical planes
    for i, (x, title, body) in enumerate(
        [
            (0.45, "GIN layer 1", "sum neighbors\nMLP + ReLU\n1 -> h"),
            (0.58, "Dropout / regularize", "optional dropout\ncontrols overfit"),
            (0.71, "GIN layer 2", "sum neighbors\nMLP + ReLU\nh -> h"),
            (0.84, "Mean pool + pair head", "z_G per subgraph\nconcat -> MLP\nlogit -> sigmoid"),
        ]
    ):
        fc = "#e7f2ea" if i in (0, 2) else "#fff0d4"
        ec = GREEN if i in (0, 2) else ORANGE
        _box(ax, (x, 0.46), (0.105, 0.22), title, body, fc=fc, ec=ec, fs=9)
    for x1, x2, label in [(0.39, 0.45, "node features"), (0.555, 0.58, "h_v^(1)"), (0.685, 0.71, "h_v^(1)*"), (0.815, 0.84, "h_v^(2)")]:
        _arrow(ax, (x1, 0.57), (x2, 0.57), text=label, text_offset=(0, 0.045))
    _box(ax, (0.69, 0.12), (0.25, 0.20), "Output controls", "Activation: ReLU in hidden layers\nLoss: BCEWithLogits, Weighted BCE, Focal Loss\nOptimizer: Adam\nOutput: sigmoid probability + threshold tau\nBalancing: negative sampling or hard negatives", fc="#edf4fa", ec=BLUE, fs=10)
    _box(ax, (0.30, 0.12), (0.30, 0.20), "Reality mapping", "Database tables become graph nodes.\nLineage dependencies become directed edges.\nCandidate pairs compare two local upstream lineages.\nThe model learns structural patterns, not raw table rows.", fc="#fbfaf4", ec=LINE, fs=10)
    _arrow(ax, (0.90, 0.46), (0.90, 0.32), text="decision")
    ax.text(0.805, 0.395, "p(duplicate) >= tau", fontsize=11, color=GREEN_DARK, fontweight="bold")
    ax.text(0.06, 0.025, "Draw.io note: preserve the bridge from relational lineage to x/edge_index tensors and then to GIN layers, pooling, loss, optimizer and threshold.", color=RED, fontsize=8.8, fontweight="bold")
    fig.savefig(IMG_DIR / "isomera_v2_gnn_pair_classifier.png", bbox_inches="tight", facecolor=BG)
    fig.savefig(IMG_DIR / "isomera_v2_gnn_pair_classifier.svg", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def protocol_pattern() -> None:
    fig, ax = _setup(15, 7.4)
    _title(ax, "Isomera Staged Protocol as an architecture pattern", "Screen many cheap configurations, select top families, then run complete benchmark with explicit routing.")
    phases = [
        ("Sender", "Researcher defines benchmark, scope, models, time budget", 0.04, "#edf4fa", BLUE),
        ("Protocol controller", "build grid\nestimate cost\nschedule screening", 0.23, "#e7f2ea", GREEN),
        ("Screening workers", "5 representative scenarios\n108 configs\nSF-Jaccard ranking", 0.42, "#fff0d4", ORANGE),
        ("Router", "top-K configs\nscenario -> pickle map\nbest-of policy if requested", 0.61, "#f3e6df", RED),
        ("Receiver", "final benchmark\nfigures, tables, PDF/TEX/ZIP", 0.80, "#edf4fa", BLUE),
    ]
    for title, body, x, fc, ec in phases:
        _box(ax, (x, 0.48), (0.15, 0.24), title, body, fc=fc, ec=ec, fs=10)
    for x1, x2, label in [(0.19, 0.23, "submit protocol"), (0.38, 0.42, "dispatch"), (0.57, 0.61, "rank top-K"), (0.76, 0.80, "execute final")]:
        _arrow(ax, (x1, 0.60), (x2, 0.60), text=label, text_offset=(0, 0.045))
    _box(ax, (0.10, 0.18), (0.28, 0.16), "Manual override", "User may bypass protocol and select a fixed config, fixed pickle route, or best-of cluster.", fs=10)
    _box(ax, (0.44, 0.18), (0.40, 0.16), "Paper evidence", "The report stores all protocol choices: candidate scenarios, configs tested, top-K selection, routing policy, metric used and final results.", fs=10)
    _arrow(ax, (0.31, 0.48), (0.24, 0.34), color=BLUE, text="optional")
    _arrow(ax, (0.66, 0.48), (0.64, 0.34), color=BLUE, text="log")
    ax.text(0.06, 0.035, "Draw.io note: use this as a sender/controller/worker/router/receiver pattern for the methodology figure.", color=RED, fontsize=9, fontweight="bold")
    fig.savefig(IMG_DIR / "isomera_v2_protocol_architecture_pattern.png", bbox_inches="tight", facecolor=BG)
    fig.savefig(IMG_DIR / "isomera_v2_protocol_architecture_pattern.svg", bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def main() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    architecture_layers()
    api_flow()
    usage_sequence()
    gnn_pipeline()
    protocol_pattern()
    print(f"Generated article visuals in {IMG_DIR}")


if __name__ == "__main__":
    main()
