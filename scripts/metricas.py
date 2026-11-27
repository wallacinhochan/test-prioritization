"""Ponto de entrada estável para calcular as métricas KAN-25–27."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from test_prioritization.metrics.cli import main  # noqa: E402


if __name__ == "__main__":
    main()
