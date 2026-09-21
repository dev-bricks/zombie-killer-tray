# Zombie Killer Tray

Conservative Windows tray utility for cleaning up orphaned MCP and language
server processes. It validates the process incarnation, parent state, CPU
stability and minimum age before termination. It never performs blanket
`taskkill` tree operations.

## Start on Windows

Install Python 3.12+ and the dependency:

```powershell
python -m pip install -r requirements.txt
```

Double-click `start-zombie-killer-admin.bat`. Windows requests elevation and
starts the tray hidden with administrator rights. The batch file resolves
`zombie_tray.ps1` relative to its own directory, so the repository can be
copied as a self-contained folder.

Validate without requesting elevation:

```bat
start-zombie-killer-admin.bat --check
```

The tray checks continuously. Its context menu and a double-click provide the
manual action **Jetzt prüfen und veraltete MCPs bereinigen**. Results are kept
locally in `zombie_events.jsonl` and `zombie_tray.log`; both are ignored by Git.

## Safety model

- exact allowlist of MCP and language-server entry points;
- two stable CPU and identity samples;
- dead-parent confirmation in both samples and immediately before termination;
- PID-reuse protection with a retained Windows process handle;
- minimum process age of 30 minutes by default;
- fail-closed behavior for unknown or access-denied parent state;
- audit write before any termination.

Run the tests:

```powershell
python -m unittest -v test_zombie_killer
```

The Windows smoke test terminates only a process created by that test.

## Deutsch

Der Zombie Killer Tray bereinigt ausschließlich eindeutig erkannte, verwaiste
MCP- und Language-Server-Prozesse. Vor dem Beenden prüft er Prozessidentität,
CPU-Stillstand, Parent-Zustand und Mindestalter. Ein pauschales Beenden ganzer
Prozessbäume findet nicht statt.

Zum Start mit Administratorrechten genügt ein Doppelklick auf
`start-zombie-killer-admin.bat`. Über das Tray-Menü oder per Doppelklick auf
das Tray-Symbol lässt sich eine Prüfung sofort manuell auslösen.

## Privacy

The utility is local-only and performs no network requests or telemetry. Audit
logs can include local command-line arguments and therefore remain untracked.

## License

MIT — see `LICENSE`.
