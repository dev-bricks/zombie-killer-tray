"""Backward-compatibility wrapper -- the real implementation now lives in
`src/zombie_killer_tray/killer.py` (T-20260926-212716751, packaging for
CareCenter-for-Codex / safe-start-for-codex). Kept so that
`python zombie_killer.py <action> ...` (zombie_tray.ps1,
start-zombie-killer-admin.bat) and any external scheduled task that calls
this file directly keep working unchanged, with or without the package
`pip install`ed.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    # Prepend so a local checkout always wins over any separately
    # pip-installed copy of the same package (single source of truth).
    sys.path.insert(0, str(_SRC))

from zombie_killer_tray.killer import *
from zombie_killer_tray.killer import main

if __name__ == "__main__":
    main()
