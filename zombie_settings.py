"""Persisted settings for the tray's automatic reap mode (T-20260924-515717640).

Storage location: `zombie_state.json` next to the scripts (``ROOT``) --
this file name was already reserved in `.gitignore` before this feature
existed, in the same directory as the other local runtime artifacts
(`zombie_events.jsonl`, `zombie_tray.log`). Reusing it means no new file
type and no new `.gitignore` entry; the setting lives with the rest of
this tool's local, per-machine state and is never committed.

This module is the single source of truth for the allowed automatic-reap
intervals and their persistence. `zombie_tray.ps1` reads the interval
choices from here once at startup (one `python -c` call) instead of
keeping a second, driftable copy of this list in PowerShell. Loading is
fail-safe (a missing, corrupt, or hand-edited file falls back to the
default) because this is a convenience preference, not a security gate
-- unlike the parent-dead/allowlist checks in zombie_killer.py, which
stay fail-closed and are unchanged by this module.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "zombie_state.json"

DEFAULT_AUTOMATIC = False
DEFAULT_INTERVAL_SECONDS = 1800  # 30 min


class IntervalChoice(NamedTuple):
    label: str
    seconds: int


# Order matches the tray submenu, top (shortest) to bottom (longest).
INTERVAL_CHOICES: tuple[IntervalChoice, ...] = (
    IntervalChoice("5 min", 300),
    IntervalChoice("10 min", 600),
    IntervalChoice("20 min", 1200),
    IntervalChoice("30 min", 1800),
    IntervalChoice("60 min", 3600),
    IntervalChoice("3 h", 10800),
    IntervalChoice("5 h", 18000),
    IntervalChoice("10 h", 36000),
    IntervalChoice("15 h", 54000),
    IntervalChoice("20 h", 72000),
    IntervalChoice("24 h (taeglich)", 86400),
)

ALLOWED_INTERVAL_SECONDS = frozenset(choice.seconds for choice in INTERVAL_CHOICES)

assert DEFAULT_INTERVAL_SECONDS in ALLOWED_INTERVAL_SECONDS


def label_for(interval_seconds: int) -> str:
    """Human-readable label for a seconds value, for tooltip/log text."""
    for choice in INTERVAL_CHOICES:
        if choice.seconds == interval_seconds:
            return choice.label
    return f"{interval_seconds}s"


def load_settings(path: Path | None = None) -> dict:
    """Read persisted automode settings, defaulting on any problem.

    A missing file (first run), unreadable/corrupt JSON, or an
    out-of-range interval each fall back to the safe default for that
    one field individually -- a bad `interval_seconds` does not also
    discard a valid `automatic` flag, and vice versa.
    """
    target = path or SETTINGS_PATH
    settings = {"automatic": DEFAULT_AUTOMATIC, "interval_seconds": DEFAULT_INTERVAL_SECONDS}
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return settings
    if not isinstance(raw, dict):
        return settings
    if isinstance(raw.get("automatic"), bool):
        settings["automatic"] = raw["automatic"]
    if raw.get("interval_seconds") in ALLOWED_INTERVAL_SECONDS:
        settings["interval_seconds"] = raw["interval_seconds"]
    return settings


def save_settings(automatic: bool, interval_seconds: int, path: Path | None = None) -> None:
    """Persist automode settings. Rejects an interval outside the fixed
    preset list -- there is no free-form interval input anywhere in this
    tool, so an out-of-range value here means a caller bug, not user
    input to sanitize."""
    if interval_seconds not in ALLOWED_INTERVAL_SECONDS:
        raise ValueError(
            f"interval_seconds must be one of {sorted(ALLOWED_INTERVAL_SECONDS)}, "
            f"got {interval_seconds!r}"
        )
    target = path or SETTINGS_PATH
    target.write_text(
        json.dumps({"automatic": bool(automatic), "interval_seconds": interval_seconds}),
        encoding="utf-8",
    )
