"""Makes `src/zombie_killer_tray` importable for the test suite without
requiring `pip install -e .` first (T-20260926-212716751).
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = str(Path(__file__).resolve().parent / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
