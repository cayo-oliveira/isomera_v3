"""Application entry point.

Preferred:
    streamlit run main/ui/app.py

Fallback:
    python main/app/main.py
"""
from __future__ import annotations

import sys
from pathlib import Path

MAIN_ROOT = Path(__file__).resolve().parents[1]
if str(MAIN_ROOT) not in sys.path:
    sys.path.insert(0, str(MAIN_ROOT))


def main() -> None:
    """Launch the canonical Streamlit entrypoint."""
    from streamlit.web import cli as stcli

    target = str((MAIN_ROOT / "ui" / "app.py").resolve())
    sys.argv = ["streamlit", "run", target, *sys.argv[1:]]
    raise SystemExit(stcli.main())


if __name__ == "__main__":
    main()
