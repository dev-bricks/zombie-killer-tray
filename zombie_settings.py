"""Persisted settings for the tray's automatic reap mode (T-20260924-515717640).

Storage location: `zombie_state.json` next to the scripts (``ROOT``) --
this file name was already reserved in `.gitignore` before this feature
existed, in the same directory as the other local runtime artifacts
(`zombie_events.jsonl`, `zombie_tray.log`). Reusing it means no new file
type and no new `.gitignore` entry; the setting lives with the rest of
this tool's local, per-machine state and is never committed.

This module is the single source of truth for the allowed automatic-reap
intervals, the allowed minimum-orphan-age thresholds, and their
persistence. `zombie_tray.ps1` reads both choice lists from here once at
startup (one `python -c` call) instead of keeping a second, driftable
copy of these tables in PowerShell. Loading is fail-safe (a missing,
corrupt, or hand-edited file falls back to the default per field)
because this is a convenience preference, not a security gate -- unlike
the parent-dead/allowlist checks in zombie_killer.py, and unlike the
hard floor `min_age >= 30` / `interval >= 3` that zombie_killer.py's own
argument parser enforces regardless of what this module allows. Every
preset below is comfortably above that floor; this module narrows the
*offered* range, it does not relax the floor.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "zombie_state.json"

DEFAULT_AUTOMATIC = False
DEFAULT_INTERVAL_SECONDS = 1800  # 30 min
DEFAULT_MIN_AGE_SECONDS = 1800  # 30 min -- matches zombie_killer.py's own prior hardcoded default


class Choice(NamedTuple):
    label: str
    seconds: int


# Order matches the tray submenu, top (shortest) to bottom (longest).
INTERVAL_CHOICES: tuple[Choice, ...] = (
    Choice("5 min", 300),
    Choice("10 min", 600),
    Choice("20 min", 1200),
    Choice("30 min", 1800),
    Choice("60 min", 3600),
    Choice("3 h", 10800),
    Choice("5 h", 18000),
    Choice("10 h", 36000),
    Choice("15 h", 54000),
    Choice("20 h", 72000),
    Choice("24 h", 86400),  # = taeglich
)

# How long a candidate process must already have been orphaned before it
# is eligible for termination (zombie_killer.py's --min-age).
MIN_AGE_CHOICES: tuple[Choice, ...] = (
    Choice("5 min", 300),
    Choice("10 min", 600),
    Choice("15 min", 900),
    Choice("30 min", 1800),
    Choice("60 min", 3600),
    Choice("2 h", 7200),
    Choice("6 h", 21600),
    Choice("12 h", 43200),
    Choice("24 h", 86400),
)

ALLOWED_INTERVAL_SECONDS = frozenset(choice.seconds for choice in INTERVAL_CHOICES)
ALLOWED_MIN_AGE_SECONDS = frozenset(choice.seconds for choice in MIN_AGE_CHOICES)

assert DEFAULT_INTERVAL_SECONDS in ALLOWED_INTERVAL_SECONDS
assert DEFAULT_MIN_AGE_SECONDS in ALLOWED_MIN_AGE_SECONDS


def _label_for(choices: tuple[Choice, ...], seconds: int) -> str:
    for choice in choices:
        if choice.seconds == seconds:
            return choice.label
    return f"{seconds}s"


def label_for(interval_seconds: int) -> str:
    """Human-readable label for an interval seconds value (tooltip/log)."""
    return _label_for(INTERVAL_CHOICES, interval_seconds)


def label_for_min_age(min_age_seconds: int) -> str:
    """Human-readable label for a min-age seconds value (tooltip/log)."""
    return _label_for(MIN_AGE_CHOICES, min_age_seconds)


def load_settings(path: Path | None = None) -> dict:
    """Read persisted automode settings, defaulting on any problem.

    A missing file (first run), unreadable/corrupt JSON, or an
    out-of-range interval/min-age each fall back to the safe default for
    that one field individually -- a bad `interval_seconds` does not also
    discard a valid `automatic` flag or `min_age_seconds`, and so on.
    """
    target = path or SETTINGS_PATH
    settings = {
        "automatic": DEFAULT_AUTOMATIC,
        "interval_seconds": DEFAULT_INTERVAL_SECONDS,
        "min_age_seconds": DEFAULT_MIN_AGE_SECONDS,
    }
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
    if raw.get("min_age_seconds") in ALLOWED_MIN_AGE_SECONDS:
        settings["min_age_seconds"] = raw["min_age_seconds"]
    return settings


def save_settings(
    automatic: bool,
    interval_seconds: int,
    min_age_seconds: int,
    path: Path | None = None,
) -> None:
    """Persist automode settings. Rejects an interval or min-age outside
    their fixed preset lists -- there is no free-form input for either
    anywhere in this tool, so an out-of-range value here means a caller
    bug, not user input to sanitize."""
    if interval_seconds not in ALLOWED_INTERVAL_SECONDS:
        raise ValueError(
            f"interval_seconds must be one of {sorted(ALLOWED_INTERVAL_SECONDS)}, "
            f"got {interval_seconds!r}"
        )
    if min_age_seconds not in ALLOWED_MIN_AGE_SECONDS:
        raise ValueError(
            f"min_age_seconds must be one of {sorted(ALLOWED_MIN_AGE_SECONDS)}, "
            f"got {min_age_seconds!r}"
        )
    target = path or SETTINGS_PATH
    target.write_text(
        json.dumps(
            {
                "automatic": bool(automatic),
                "interval_seconds": interval_seconds,
                "min_age_seconds": min_age_seconds,
            }
        ),
        encoding="utf-8",
    )
