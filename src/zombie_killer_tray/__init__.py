"""Conservative Windows orphan reaper for MCP and language-server processes.

Installable package form of dev-bricks/zombie-killer-tray
(T-20260926-212716751). The canonical implementation lives in `.killer`
(CLI: `python -m zombie_killer_tray <action>`, same flags as the original
`zombie_killer.py` script) and `.settings` (allowed automatic-reap
intervals/ages). The repository root still ships thin `zombie_killer.py`/
`zombie_settings.py` wrapper scripts for backward compatibility with
`zombie_tray.ps1` and `start-zombie-killer-admin.bat`.
"""
from __future__ import annotations

__version__ = "0.1.0"  # kept in lockstep with pyproject.toml's frozen project.version
