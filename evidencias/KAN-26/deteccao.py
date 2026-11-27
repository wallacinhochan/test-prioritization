"""Compatibilidade com o caminho histórico da KAN-26."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from test_prioritization.metrics.detection import deteccao  # noqa: E402

__all__ = ["deteccao"]
