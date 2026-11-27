"""Compatibilidade com o caminho histórico; use ``scripts/metricas.py``."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from test_prioritization.metrics.cli import *  # noqa: F401,F403,E402
from test_prioritization.metrics.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
