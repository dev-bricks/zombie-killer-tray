# Contributing to zombie-killer-tray / Mitwirken an zombie-killer-tray

[English](#english) | [Deutsch](#deutsch)

---

<a id="english"></a>
## English

Thank you for your interest in contributing to **zombie-killer-tray** (`dev-bricks/zombie-killer-tray`), a conservative Windows system tray utility for safely cleaning up orphaned Model Context Protocol (MCP) and language server processes without blanket process-tree kills.

### 1. Architectural Principles & 10 Governance Invariants

All contributions must strictly adhere to our core architectural and governance invariants:

1. **Local-First & Zero Egress (`INV-LOCAL-01`)**: 100% offline-ready operations. The process scanner, Win32 handle engine, and tray execution run completely locally with zero outbound telemetry, analytical trackers, cloud API calls, or external network sockets. Pure air-gap execution.
2. **Unprivileged Mode for Inspection (`INV-SEC-02`)**: Pure `RunAsInvoker` user-mode operation for read-only inspection (`--check`, `--list`, automated test suites) without requiring administrator elevation or UAC prompts. Elevated privileges are only requested when launching the tray daemon to allow terminating orphaned system/service processes.
3. **Dead-Parent Verification (`INV-PARENT-03`)**: A process is only classified as an eligible orphan if its parent process PID is verified dead in consecutive sampling cycles and immediately before issuing a termination syscall (`Win32.parent_dead(ppid)`).
4. **Two-Sample CPU & Identity Stability (`INV-STABLE-04`)**: Requires two consecutive snapshots separated by an observation interval with zero CPU delta and identical creation timestamps to avoid interfering with active tasks.
5. **PID-Reuse Protection via Pinned Handle (`INV-HANDLE-05`)**: Obtains and retains an explicit Win32 process handle (`OpenProcess`) to lock the kernel object and eliminate PID-reuse race conditions during verification and termination.
6. **Strict Allowlist of Entrypoints (`INV-ALLOW-06`)**: Target processes are strictly restricted to verified MCP servers and language server executables/modules (`classify()` matching `LSP_BINARIES`, `NODE_MCP_INDICATORS`, `PYTHON_MCP_MODULES`). Arbitrary processes or unknown executables are never matched.
7. **No Blanket Process Tree Termination (`INV-NOTREE-07`)**: Never performs recursive blanket `taskkill /T` operations. Every process is verified and terminated individually.
8. **Pre-Termination Audit Logging (`INV-AUDIT-08`)**: Writes an immutable forensic record to local audit logs (`zombie_events.jsonl`) before any termination syscall is issued; if audit logging fails, the process is not terminated (fail-closed).
9. **Minimum Process Age Gate (`INV-AGE-09`)**: Enforces a conservative minimum process age threshold (default: 30 minutes) to avoid interfering with newly spawned processes.
10. **Dual Security Response SLA (`INV-SLA-10`)**: Binding 48-hour initial response SLA and 5-business-day triage commitment for all reported vulnerabilities via `security@dev-bricks.org`, `security@open-bricks.org`, `support@lukasgeiger.com`, and `lukas@open-bricks.org`.

### 2. Plan D Local Development Workflow

In accordance with our cross-system architecture (Plan D), the local git repository at `C:\_Local_DEV\repos\zombie-killer-tray` serves as the authoritative **Source of Truth**. Development, testing, and commits must take place exclusively in the canonical local clone. Cloud mirrors (e.g., OneDrive) serve solely as gitless read projections.

```powershell
# Clone the canonical repository
git clone https://github.com/dev-bricks/zombie-killer-tray.git C:\_Local_DEV\repos\zombie-killer-tray
cd C:\_Local_DEV\repos\zombie-killer-tray

# Create and activate a clean virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install package in editable mode with development dependencies
pip install -e ".[dev]"

# Run complete test suite via pytest
pytest

# Run unit tests directly
python -m unittest -v test_zombie_killer
python -m unittest -v test_broker_detection
python -m unittest -v test_zombie_settings
python -m unittest -v tests/test_metadata.py

# Run static linter
ruff check .

# Verify bytecode compilation
python -m compileall -q .

# Unprivileged launcher preflight check
start-zombie-killer-admin.bat --check
```

### 3. Version Freeze Discipline (`T-20260920-167562623`)

`zombie-killer-tray` operates under strict version-freeze discipline. Version identifiers (`0.1.0` in `pyproject.toml` and metadata) must not be arbitrarily incremented during routine maintenance. All enhancements, bug fixes, and hygiene adjustments are documented under `## [Unreleased]` in `CHANGELOG.md`.

### 4. Quality Gates

Before submitting a pull request or pushing commits, verify all local quality gates:

1. `pytest`: 100% green test execution across all unit, regression, and contract test suites.
2. `ruff check .`: Zero lint errors and formatting violations.
3. `python -m compileall -q .`: Zero bytecode compilation errors.
4. `git diff --check`: Zero trailing whitespace or line-ending anomalies.
5. `git diff -G"version = "` / `git diff -G'"version"'`: Zero unauthorized version bumps.

### 5. Statutory Notice (§ 521 BGB) & Liability Disclaimer

This software is provided free of charge as open-source software under the MIT License. In accordance with statutory German law (§ 521 BGB - Gefälligkeitsrecht), liability for defects in quality and title is strictly limited to intentional misconduct (*Vorsatz*) and gross negligence (*grobe Fahrlässigkeit*).

### 6. Coordinated Vulnerability Disclosure & 48h Security SLA

Security issues must never be submitted via public GitHub issues. Please report vulnerabilities responsibly through private GitHub Security Advisories or directly to:
- `security@dev-bricks.org`
- `security@open-bricks.org`
- `support@lukasgeiger.com`
- `lukas@open-bricks.org`

Initial acknowledgement is guaranteed within 48 hours, followed by risk triage within 5 business days per [`SECURITY.md`](SECURITY.md).

---

<a id="deutsch"></a>
## Deutsch

Vielen Dank für dein Interesse an einer Mitwirkung bei **zombie-killer-tray** (`dev-bricks/zombie-killer-tray`), einem konservativen Windows-System-Tray-Dienstprogramm zur sicheren Bereinigung verwaister Model Context Protocol (MCP) und Language-Server-Hintergrundprozesse ohne pauschale Prozessbaum-Kills.

### 1. Architektur-Prinzipien & 10 Governance-Invarianten

Alle Beiträge müssen unsere verbindlichen Kern- und Governance-Invarianten strikt einhalten:

1. **Local-First & Zero-Egress (`INV-LOCAL-01`)**: Zu 100 % offline-fähige Ausführung. Der Prozess-Scanner, die Win32-Handle-Engine und die Tray-Ausführung arbeiten vollständig lokal ohne ausgehende Telemetrie, Analyse-Tracker, Cloud-API-Aufrufe oder externe Netzwerksockets. Reine Air-Gap-Ausführung.
2. **Rechtefreier Prüfmodus (`INV-SEC-02`)**: Reiner `RunAsInvoker`-Benutzermodus für lesende Prüfungen (`--check`, `--list`, automatisierte Test-Suites) ohne Administratorrechte oder UAC-Aufforderungen. Erhöhte Rechte werden ausschließlich beim Start des Tray-Hintergrunddienstes angefordert, um verwaiste System-/Dienstprozesse beenden zu können.
3. **Dead-Parent-Verifikation (`INV-PARENT-03`)**: Ein Prozess wird nur dann als verwaist eingestuft, wenn die Eltern-PID in aufeinanderfolgenden Abtastzyklen und unmittelbar vor dem Beendigungsaufruf nachweislich tot ist (`Win32.parent_dead(ppid)`).
4. **Zwei-Stichproben-CPU- und Identitätsstabilität (`INV-STABLE-04`)**: Erfordert zwei aufeinanderfolgende Schnappschüsse über ein Beobachtungsintervall mit einem CPU-Delta von exakt 0 und identischen Prozesserstellungszeitstempeln, um aktive Aufgaben niemals zu stören.
5. **PID-Wiederverwendungsschutz via Pinned Handle (`INV-HANDLE-05`)**: Bezieht und hält ein explizites Win32-Prozess-Handle (`OpenProcess`), um das Kernel-Objekt zu sperren und PID-Reuse-Race-Conditions während der Prüfung und Beendigung auszuschließen.
6. **Strikte Allowlist von Einstiegspunkten (`INV-ALLOW-06`)**: Zielprozesse sind strikt auf verifizierte MCP-Server und Language-Server-Binaries/Module beschränkt (`classify()` prüft `LSP_BINARIES`, `NODE_MCP_INDICATORS`, `PYTHON_MCP_MODULES`). Beliebige Prozesse oder unbekannte Programme werden niemals angetastet.
7. **Keine pauschalen Prozessbaum-Kills (`INV-NOTREE-07`)**: Führt niemals rekursive `taskkill /T`-Befehle aus. Jeder Prozess wird einzeln verifiziert und individuell beendet.
8. **Forensische Audit-Protokollierung vor Beendigung (`INV-AUDIT-08`)**: Schreibt einen unveränderlichen Ereignisdatensatz in die lokale Protokolldatei (`zombie_events.jsonl`), bevor ein Beendigungsaufruf erfolgt; schlägt das Schreiben fehl, unterbleibt die Beendigung fail-closed.
9. **Mindestalter-Schranke (`INV-AGE-09`)**: Erzwingt ein konservatives Mindestprozessalter (Standard: 30 Minuten), um neu gestartete Prozesse vor voreiligen Eingriffen zu schützen.
10. **Sicherheits-Response-SLA (`INV-SLA-10`)**: Verbindliche 48-Stunden-Erstantwortgarantie und 5-Werktage-Triage-Zusage für alle gemeldeten Schwachstellen über `security@dev-bricks.org`, `security@open-bricks.org`, `support@lukasgeiger.com` und `lukas@open-bricks.org`.

### 2. Plan D Lokaler Entwicklungsworkflow

Gemäß unserer systemweiten Architektur (Plan D) bildet das lokale Repository unter `C:\_Local_DEV\repos\zombie-killer-tray` die alleinige maßgebliche **Source of Truth**. Entwicklung, Tests und Commits finden ausschließlich im kanonischen lokalen Klon statt. Cloud-Spiegel (z. B. OneDrive) dienen rein als gitlose Leseprojektionen.

```powershell
# Kanonischen Klon verwenden
git clone https://github.com/dev-bricks/zombie-killer-tray.git C:\_Local_DEV\repos\zombie-killer-tray
cd C:\_Local_DEV\repos\zombie-killer-tray

# Saubere virtuelle Umgebung anlegen und aktivieren
python -m venv .venv
.venv\Scripts\Activate.ps1

# Paket im Entwicklungsmodus mit Abhängigkeiten installieren
pip install -e ".[dev]"

# Vollständige Test-Suite via pytest ausführen
pytest

# Einzelne Testmodule direkt ausführen
python -m unittest -v test_zombie_killer
python -m unittest -v test_broker_detection
python -m unittest -v test_zombie_settings
python -m unittest -v tests/test_metadata.py

# Statische Linter-Prüfung
ruff check .

# Bytecode-Kompilierung prüfen
python -m compileall -q .

# Rechtefreie Vorabprüfung des Launchers
start-zombie-killer-admin.bat --check
```

### 3. Version Freeze Disziplin (`T-20260920-167562623`)

`zombie-killer-tray` unterliegt einer strikten Version-Freeze-Disziplin. Versionsnummern (`0.1.0` in `pyproject.toml` und Metadaten) dürfen bei routinemäßiger Wartung nicht eigenmächtig erhöht werden. Sämtliche Erweiterungen, Fehlerkorrekturen und Hygiene-Updates werden unter `## [Unreleased]` in `CHANGELOG.md` dokumentiert.

### 4. Qualitäts-Tore (Quality Gates)

Vor dem Einreichen eines Pull Requests oder dem Pushen von Commits müssen alle lokalen Qualitätstore erfolgreich durchlaufen sein:

1. `pytest`: 100 % grüne Testausführung über alle Test-Suites hinweg.
2. `ruff check .`: 0 Lint-Fehler und Formatierungsverstöße.
3. `python -m compileall -q .`: 0 Bytecode-Kompilierungsfehler.
4. `git diff --check`: 0 Whitespace- oder Zeilenendungsfehler.
5. `git diff -G"version = "` / `git diff -G'"version"'`: 0 unautorisierte Versionsänderungen.

### 5. Gesetzlicher Hinweis (§ 521 BGB) & Haftungsausschluss

Diese Software wird unentgeltlich als Open-Source-Software unter der MIT-Lizenz bereitgestellt. Gemäß § 521 BGB (Gefälligkeitsrecht) ist die Haftung für Sach- und Rechtsmängel auf Vorsatz und grobe Fahrlässigkeit beschränkt.

### 6. Koordinierte Offenlegung von Schwachstellen & 48h SLA

Sicherheitsrelevante Befunde dürfen niemals über öffentliche GitHub-Issues gemeldet werden. Bitte melde Schwachstellen vertraulich über private GitHub Security Advisories oder direkt an:
- `security@dev-bricks.org`
- `security@open-bricks.org`
- `support@lukasgeiger.com`
- `lukas@open-bricks.org`

Eine erste Eingangsbestätigung erfolgt innerhalb von 48 Stunden, gefolgt von einer Risikobewertung innerhalb von 5 Werktagen gemäß [`SECURITY.md`](SECURITY.md).
