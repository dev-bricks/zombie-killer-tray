# Contributing to zombie-killer-tray / Mitwirken an zombie-killer-tray

[English](#english) · [Deutsch](#deutsch)

---

<a id="english"></a>
## English

Thank you for your interest in contributing to **zombie-killer-tray**, a Windows tray application that checks selected orphaned Model Context Protocol (MCP) and language-server processes. It can attempt to end an individual process after its configured checks; it does not terminate a whole process tree.

### 1. Current safeguards and limits

The following behavior is visible in the current source and covered by focused tests. These checks narrow which processes may be considered; they do not make termination risk-free, prove every system condition, or create an operating-system security boundary.

1. **Configured entrypoint matching:** candidate processes must match the configured MCP or language-server entrypoint rules.
2. **Parent-state checks:** parent state is sampled and checked again before an apply attempt.
3. **Separate observations:** the engine compares two process observations rather than relying on one snapshot.
4. **Identity and CPU comparison:** process identity and CPU time are compared across observations.
5. **Minimum process age:** a configured minimum age is measured from process creation time, not from the moment the process became orphaned.
6. **Retained process handle:** the Windows path retains a process handle during checks and the termination attempt to reduce PID-reuse risk.
7. **Individual action:** an apply attempt targets one selected process rather than recursively terminating a process tree.
8. **Pre-termination intent record:** apply mode appends an intent record before attempting termination.
9. **Write-failure handling:** if appending that intent record fails, the corresponding termination attempt is skipped.

The JSONL audit file is an ordinary local append log and is not tamper-evident. The project does not promise zero network traffic at the operating-system or dependency level, a response-time SLA, legal compliance, or error-free operation.

### 2. Development setup

Use a current checkout of this repository and a supported Python interpreter. From a directory where you keep source checkouts:

~~~powershell
git clone https://github.com/dev-bricks/zombie-killer-tray.git
Set-Location zombie-killer-tray
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
~~~

Run the repository's tests and checks from its root:

~~~powershell
python -m pytest -ra -v .
python -m ruff check .
python -m compileall -q .
git diff --check
.\start-zombie-killer-admin.bat --check
~~~

The launcher --check mode parses the PowerShell tray script; it does not run the tray or inspect, start, or terminate host processes. Tests should use isolated temporary state and mocks where process or tray behavior is involved. Do not run the application against a developer's live process table as a test.

### 3. Version and changelog

The source currently declares version 0.1.0 in pyproject.toml. Routine maintenance does not itself publish a release or authorize a version change. Describe user-visible changes under Unreleased in CHANGELOG.md; release versioning is handled through the project's release process.

### 4. Review checklist

Before opening a pull request, provide the checks relevant to the change:

- Run the full test collection with `python -m pytest -ra -v .`.
- Run `python -m ruff check .` and `python -m compileall -q .`.
- Run the launcher parser check when changing the batch launcher or tray script.
- When changing packaging metadata, install the build frontend with `python -m pip install build`, then run `python -m build`; inspect the artifacts and run the applicable package checks.
- Review `git diff --check` and confirm that generated state, logs, credentials, and local machine paths are not included.
- Keep tests for process termination isolated; never use a real unrelated process as a test target.

These commands are contributor guidance. Hosted CI results are reported separately by the repository's workflow.

### 5. Security reports

For security-reporting instructions and the currently published contact routes, see [SECURITY.md](SECURITY.md). No response or triage time is promised by this guide.

### 6. License

Contributions are made under the project's [MIT License](LICENSE). The [NOTICE](NOTICE) file contains attribution information. [The direct dependency license summaries](THIRD_PARTY_LICENSES.md) describe only the listed direct dependencies and are not a complete transitive dependency inventory or a legal certification.

---

<a id="deutsch"></a>
## Deutsch

Vielen Dank für dein Interesse an **zombie-killer-tray**. Die Windows-Infobereichsanwendung prüft ausgewählte verwaiste Prozesse von Model Context Protocol (MCP)-Servern und Sprachservern. Nach den vorgesehenen Prüfungen kann sie versuchen, einen einzelnen Prozess zu beenden; ganze Prozessbäume werden nicht rekursiv beendet.

### 1. Aktuelle Schutzprüfungen und Grenzen

Das folgende Verhalten ist im aktuellen Quellcode erkennbar und durch gezielte Tests abgedeckt. Die Prüfungen schränken ein, welche Prozesse berücksichtigt werden. Sie machen das Beenden nicht risikofrei, beweisen nicht jeden Systemzustand und bilden keine Sicherheitsgrenze des Betriebssystems.

1. **Abgleich konfigurierter Einstiegspunkte:** Kandidaten müssen zu den konfigurierten MCP- oder Sprachserver-Einstiegspunkten passen.
2. **Prüfung des Elternprozesses:** Der Zustand des Elternprozesses wird erfasst und vor einem Ausführungsversuch erneut geprüft.
3. **Getrennte Beobachtungen:** Die Engine vergleicht zwei Prozessbeobachtungen statt sich auf einen einzelnen Schnappschuss zu stützen.
4. **Vergleich von Identität und CPU-Zeit:** Prozesserkennung und CPU-Zeit werden zwischen den Beobachtungen verglichen.
5. **Mindestprozessalter:** Das Mindestalter wird ab Prozesserstellung gemessen, nicht ab dem Zeitpunkt, an dem der Prozess verwaist ist.
6. **Gehaltenes Prozess-Handle:** Der Windows-Pfad hält während der Prüfungen und des Beendigungsversuchs ein Prozess-Handle, um das Risiko einer PID-Wiederverwendung zu verringern.
7. **Einzelne Aktion:** Ein Ausführungsversuch richtet sich gegen einen ausgewählten Prozess und beendet keinen Prozessbaum rekursiv.
8. **Absichtsprotokoll vor dem Beendigungsversuch:** Im Ausführungsmodus wird vor dem Beendigungsversuch ein Absichtsdatensatz angehängt.
9. **Umgang mit Schreibfehlern:** Kann dieser Absichtsdatensatz nicht angehängt werden, wird der zugehörige Beendigungsversuch übersprungen.

Die JSONL-Protokolldatei ist ein gewöhnliches lokales Append-Protokoll und nicht manipulationssicher. Das Projekt verspricht weder null Netzwerkverkehr auf Betriebssystem- oder Abhängigkeitsebene noch eine Antwortzeit-SLA, rechtliche Konformität oder fehlerfreien Betrieb.

### 2. Entwicklungsumgebung

Verwende einen aktuellen Klon dieses Repositorys und eine unterstützte Python-Version. Führe die folgenden Befehle in einem Verzeichnis aus, in dem du Quellcode-Klone ablegst:

~~~powershell
git clone https://github.com/dev-bricks/zombie-killer-tray.git
Set-Location zombie-killer-tray
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
~~~

Führe Tests und Prüfungen im Repository-Stammverzeichnis aus:

~~~powershell
python -m pytest -ra -v .
python -m ruff check .
python -m compileall -q .
git diff --check
.\start-zombie-killer-admin.bat --check
~~~

Der Launcher-Modus --check parst das PowerShell-Tray-Skript. Er startet weder das Tray noch untersucht, startet oder beendet er Prozesse des Hosts. Tests zu Prozessen oder Tray-Verhalten verwenden isolierte temporäre Zustände und Mocks. Die Anwendung wird nicht zum Testen gegen die aktive Prozesstabelle eines Entwicklerrechners ausgeführt.

### 3. Version und Änderungsprotokoll

Die Quelle deklariert derzeit Version 0.1.0 in pyproject.toml. Routinemäßige Wartung veröffentlicht keine Version und berechtigt für sich genommen nicht zu einer Versionsänderung. Dokumentiere sichtbare Änderungen unter Unreleased in CHANGELOG.md; die Versionierung einer Veröffentlichung erfolgt im Release-Prozess des Projekts.

### 4. Prüfliste für Beiträge

Führe vor einem Pull Request die für die Änderung passenden Prüfungen aus und dokumentiere sie:

- Führe die vollständige Testsammlung mit `python -m pytest -ra -v .` aus.
- Führe `python -m ruff check .` und `python -m compileall -q .` aus.
- Führe die Parserprüfung des Launchers aus, wenn du den Batch-Launcher oder das Tray-Skript änderst.
- Installiere bei Änderungen an Paketmetadaten zuerst mit `python -m pip install build` das Build-Frontend, führe dann `python -m build` aus, prüfe die Artefakte und führe die passenden Paketprüfungen aus.
- Prüfe `git diff --check` und stelle sicher, dass generierte Zustände, Protokolle, Zugangsdaten und lokale Rechnerpfade nicht enthalten sind.
- Halte Tests zu Prozessbeendigungen isoliert; verwende niemals einen echten, unbeteiligten Prozess als Testziel.

Diese Befehle sind Hinweise für Mitwirkende. Ergebnisse der gehosteten CI werden separat durch den Repository-Workflow ausgewiesen.

### 5. Sicherheitsmeldungen

Hinweise zum Melden von Sicherheitsproblemen und die aktuell veröffentlichten Kontaktwege stehen in [SECURITY.md](SECURITY.md). Diese Anleitung verspricht keine Antwort- oder Bearbeitungszeit.

### 6. Lizenz

Beiträge stehen unter der [MIT-Lizenz](LICENSE) des Projekts. Die Datei [NOTICE](NOTICE) enthält Namensnennungen. Die [Übersichten zu Abhängigkeitslizenzen](THIRD_PARTY_LICENSES.md) beschreiben nur die aufgeführten direkten Abhängigkeiten; sie sind weder ein vollständiges Verzeichnis transitiver Abhängigkeiten noch eine rechtliche Zertifizierung.
