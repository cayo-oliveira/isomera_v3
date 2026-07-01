from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VERSION_PATH = REPO_ROOT / "main" / "config" / "version.json"


def load_identity() -> dict[str, str]:
    default = {
        "product": "Isomera",
        "version": "2.1.0",
        "codename": "Lineage Workbench",
        "release_date": "2026-04-17",
        "author": "Cayo Oliveira",
        "email": "cflo@cin.ufpe.br",
        "summary": "Graph lineage workbench for redundancy detection research.",
    }
    if not VERSION_PATH.exists():
        return default
    try:
        payload = json.loads(VERSION_PATH.read_text(encoding="utf-8"))
    except Exception:
        return default
    return {**default, **{str(k): str(v) for k, v in payload.items()}}


def terminal_banner(title: str = "BOOT") -> str:
    identity = load_identity()
    product = identity["product"]
    version = identity["version"]
    codename = identity["codename"]
    author = identity["author"]
    email = identity["email"]
    release_date = identity["release_date"]
    return f"""
╭──────────────────────────────────────────────────────────────────────╮
│                                                                      │
│     ██╗███████╗ ██████╗ ███╗   ███╗███████╗██████╗  █████╗         │
│     ██║██╔════╝██╔═══██╗████╗ ████║██╔════╝██╔══██╗██╔══██╗        │
│     ██║███████╗██║   ██║██╔████╔██║█████╗  ██████╔╝███████║        │
│     ██║╚════██║██║   ██║██║╚██╔╝██║██╔══╝  ██╔══██╗██╔══██║        │
│     ██║███████║╚██████╔╝██║ ╚═╝ ██║███████╗██║  ██║██║  ██║        │
│     ╚═╝╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝        │
│                                                                      │
│       SOR ─────▶ SOT ─────▶ SPEC                                     │
│        │          │          │                                       │
│        └──── lineage graph ──┘                                       │
│                                                                      │
│   {product} v{version:<10} {codename:<37} │
│   {title:<12} Author: {author:<28} │
│   Contact: {email:<31} Release: {release_date:<10} │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
""".strip("\n")


def compact_identity_line() -> str:
    identity = load_identity()
    return (
        f"{identity['product']} v{identity['version']} "
        f"({identity['codename']}) - {identity['author']} <{identity['email']}>"
    )
