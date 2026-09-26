"""Backward-compatibility wrapper -- the real implementation now lives in
`src/zombie_killer_tray/settings.py` (T-20260926-212716751). Kept so that
`zombie_tray.ps1`'s `import zombie_settings as s` one-liner keeps working
unchanged, with or without the package `pip install`ed.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from zombie_killer_tray.settings import *
