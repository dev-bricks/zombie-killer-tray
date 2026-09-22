# Zombie Killer Tray

[![Attribution: NOTICE](https://img.shields.io/badge/Attribution-NOTICE-blue.svg)](NOTICE)
[![Version: 0.1.0](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)
[![Tests: Passed](https://img.shields.io/badge/tests-passed%20%7C%20100%25-brightgreen.svg)](tests/test_metadata.py)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](#)
[![Zero-Egress: 100% Local](https://img.shields.io/badge/Zero--Egress-100%25%20Lokal-success.svg)](#datenschutz--sicherheits-governance)
[![Security SLA: 48h / 5d](https://img.shields.io/badge/Security%20SLA-48h%20%2F%205d-blue.svg)](SECURITY.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **English Version:** The English documentation is located in [README.md](README.md).

Konservatives Windows-System-Tray-Dienstprogramm zur Bereinigung verwaister Model Context Protocol (MCP) und Language-Server-Hintergrundprozesse. Prüft Prozessincarnation, Parent-Dead-Status, CPU-Stillstand und Mindestalter vor dem Beenden. Führt niemals pauschale `taskkill /T`-Prozessbaum-Operationen aus.

---

## Navigation & Inhaltsverzeichnis

- [Überblick & Architektur](#überblick--architektur)
- [Start unter Windows](#start-unter-windows)
- [Sicherheitsmodell & Governance-Invarianten](#sicherheitsmodell--governance-invarianten)
- [Tests & Qualitätssicherung](#tests--qualitätssicherung)
- [Datenschutz & Sicherheits-Governance](#datenschutz--sicherheits-governance)
- [Drittanbieter-Transparenz & SBOM](#drittanbieter-transparenz--sbom)
- [Gesetzlicher Hinweis (§ 521 BGB)](#gesetzlicher-hinweis--521-bgb)
- [Lizenz](#lizenz)

---

## Überblick & Architektur

Wenn lokale KI-Agenten-Frameworks (Claude Code, Codex CLI, Antigravity, Kimi) oder IDEs unerwartet beendet werden, können MCP-Hintergrundprozesse (`node.exe`, `python.exe`) und Language-Server (`rust-analyzer.exe`, `clangd.exe`, `gopls.exe`, `pylsp`) als Zombies im System verbleiben. Diese verwaisten Prozesse verbrauchen Arbeitsspeicher und blockieren Dateisperren.

`zombie-killer-tray` löst dieses Problem ohne Risiko für aktive Entwicklungsprozesse:
1. Fragt die Win32-Prozesstabelle über native Snapshots ab.
2. Filtert ausschließlich nach einer strikten Positivliste (Allowlist) bekannter MCP-Pakete und Language-Server-Binaries.
3. Erhebt zwei aufeinanderfolgende Stichproben im Zeitabstand, um vollständigen CPU-Stillstand nachzuweisen.
4. Verifiziert, dass der Parent-Prozess (PPID) in beiden Stichproben und unmittelbar vor dem Beenden tot ist.
5. Hält ein explizites Win32-Prozess-Handle (`OpenProcess`), um PID-Wiederverwendungs-Races (PID-Reuse) auszuschließen.
6. Schreibt vor dem Aufruf von `TerminateProcess` ein unveränderliches Ereignis in `zombie_events.jsonl`.

---

## Start unter Windows

### Voraussetzungen

Installation von Python 3.12+ und den Abhängigkeiten:

```powershell
python -m pip install -r requirements.txt
```

### 1. Start des System-Trays (Admin-Modus)

Doppelklick auf `start-zombie-killer-admin.bat`. Windows fordert Administratorrechte an (UAC), damit der Tray minimiert im Hintergrund verwaiste Prozesse sitzungsübergreifend bereinigen kann:

```bat
start-zombie-killer-admin.bat
```

Die Batch-Datei löst `zombie_tray.ps1` relativ zum eigenen Verzeichnis auf. Das Repository ist somit portabel und in sich geschlossen.

### 2. Prüfung ohne Administratorrechte (RunAsInvoker)

Für eine reine Syntax- und Umgebungsprüfung ohne UAC-Erhöhung:

```bat
start-zombie-killer-admin.bat --check
```

### 3. Tray-Kontextmenü

- **Doppelklick oder „Jetzt prüfen und veraltete MCPs bereinigen“:** Löst sofort einen Bereinigungszyklus aus.
- Lokale Audit-Protokolle werden in `zombie_events.jsonl` und `zombie_tray.log` abgelegt (beide gitignoriert).

---

## Sicherheitsmodell & Governance-Invarianten

Das Dienstprogramm folgt 10 strikten Architektur- und Governance-Invarianten:

| Invarianten-Code | Garantie | Kategorie | Durchsetzungs-Mechanismus |
|:---|:---|:---|:---|
| **INV-LOCAL-01** | Lokal & Zero Egress | Netzwerkschutz | Standardbibliothek + `psutil`; keine Netzwerk-Sockets; null Telemetrie |
| **INV-SEC-02** | Unprivilegierte Inspektion | Rechte-Hygiene | `start-zombie-killer-admin.bat --check` erfordert keine Administratorrechte |
| **INV-PARENT-03** | Dead-Parent-Verifikation | Prozesssicherheit | Parent-PID muss in allen Stichproben und vor dem Kill tot sein |
| **INV-STABLE-04** | Zwei-Stichproben CPU-Stabilität | Mutationsschutz | 2 Snapshots erfordern 0 CPU-Delta und identischen Erstellungszeitpunkt |
| **INV-HANDLE-05** | PID-Reuse Schutz durch Pinned Handle | Kernel-Sicherheit | Hält Win32 `OpenProcess`-Handle, um Kernel-Objekt zu sperren |
| **INV-ALLOW-06** | Strikte Positivliste (Allowlist) | Scope-Grenze | Nur explizit gelistete MCP- und Language-Server-Prozesse werden geprüft |
| **INV-NOTREE-07** | Keine pauschalen Baum-Kills | Sicherheits-Isolation | Einzelne Prozessbeendigung; niemals rekursives Töten von Prozessbäumen |
| **INV-AUDIT-08** | Pre-Termination Audit-Logging | Nachvollziehbarkeit | Audit-Eintrag in `zombie_events.jsonl` vor dem Kill; Abbruch bei Schreibfehler |
| **INV-AGE-09** | Mindestalter-Schutz | Zeitliche Sicherheit | Konservatives Mindestalter von 30 Minuten (Standard) schützt frische Prozesse |
| **INV-SLA-10** | Duales Sicherheits-Response-SLA | Governance & Triage | 48h Erstantwort, 5 Werktage Triage gemäß `SECURITY.md` |

---

## Tests & Qualitätssicherung

Testsuiten ausführen:

```powershell
# Vollständige Testsuite via pytest
python -m pytest -ra -v

# Oder Unit-Tests direkt via unittest
python -m unittest -v test_zombie_killer
```

---

## Datenschutz & Sicherheits-Governance

Das Dienstprogramm operiert rein lokal und führt keinerlei Netzwerkabfragen oder Telemetrie aus. Lokale Audit-Logs können Befehlszeilenparameter enthalten und verbleiben daher ungetrackt auf dem Rechner.

Meldung von Sicherheitslücken und unser 48-Stunden-Sicherheits-SLA sind in [SECURITY.md](SECURITY.md) definiert.

---

## Drittanbieter-Transparenz & SBOM

Alle Abhängigkeiten unterliegen strikt permissiven Open-Source-Lizenzen (MIT, Apache-2.0, PSFL, BSD-3-Clause) ohne Copyleft. Das vollständige Level 1 SBOM befindet sich in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

Die Attributionsrichtlinie für Lukas Geiger, `dev-bricks` und `open-bricks` ist in [NOTICE](NOTICE) verankert.

---

## Gesetzlicher Hinweis (§ 521 BGB)

Diese Software wird unentgeltlich als Open-Source-Software unter der MIT-Lizenz bereitgestellt. Gemäß § 521 BGB (Haftung bei Schenkung / Gefälligkeitsrecht) ist die Haftung für Sach- und Rechtsmängel auf Vorsatz und grobe Fahrlässigkeit beschränkt.

---

## Lizenz

MIT — siehe [LICENSE](LICENSE).
