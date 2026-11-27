"""Compatibilidade com o caminho histórico da KAN-27."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from test_prioritization.metrics.apfdc import apfdc  # noqa: E402

__all__ = ["apfdc"]
