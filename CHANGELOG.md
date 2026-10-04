# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Replaced overstated process-safety, network, audit, support, and license claims with descriptions scoped to source behavior and the listed direct dependencies.
- Added six-language tray documentation and a bilingual contributor guide with reproducible local checks.
- Removed the internal marketing log from tracked package and repository metadata while retaining it locally as an ignored file.
- Kept the declared source version at 0.1.0; no package release or version change is recorded here.

### Correction (2026-10-03)
- The historical entry's machine-specific local clone path is redacted in this public copy.
- The current README badges label the date as a source review; they do not imply security certification or a complete audit.
- The dated historical entry below is retained for traceability. Its statements about zero-egress guarantees, RunAsInvoker, Plan D host paths, § 521 BGB, response-time commitments, and complete SBOM or invariant compliance were not supported as written and are withdrawn. The current public documents state observed behavior and its limits; they make no compliance certification, response-time SLA, or complete transitive dependency claim.

## Historical Unreleased Entry (2026-10-03; corrected above)

> The following entry is retained as the original dated record. Its inaccurate assurances are superseded by the correction above.

### Added
- Repository Hygiene & Contributing Guidelines: Canonical bilingual `CONTRIBUTING.md` guidelines (English / Deutsch) detailing the 10 governance and runtime invariants (`INV-LOCAL-01` through `INV-SLA-10`), unprivileged `RunAsInvoker` mode (`INV-SEC-02`), Plan D local development workflow (`[host-specific local clone path omitted]` as Source of Truth), § 521 BGB Gefälligkeitsrecht statutory disclaimer, and 48-hour security response SLA.
- PEP 621 Metadata Alignment: Registered the `Contributing` URL under `[project.urls]` in `pyproject.toml`. `CONTRIBUTING.md` is contributor documentation, not a license file.
- Multi-Host Lock & OS Defense: Hardened `.gitignore` with Windows system files (`desktop.ini`, `ehthumbs.db`), editor backup patterns (`*.swp`, `*.swo`, `*~`), transient agent tasks (`TASKPLAN_*.md`, `*-TASKPLAN*`), host-neutral multi-host sync-conflict filename patterns, and canonical lock prefixes (`LOCK.dev.*`, `LOCK.antigravity.*`, `LOCK.bugsearch.*`).
- Direct-Dependency License Summary (2026-10-03): Updated `THIRD_PARTY_LICENSES.md` and `THIRD_PARTY_LICENSES.txt` to document the listed direct dependencies and their recorded license identifiers and notices. These summaries do not inventory transitive dependencies or certify project invariants.
- Badges & Documentation Synchronization: Updated `Verified: 2026-10-03` / `Geprüft: 2026-10-03` and `Last Checked: 2026-10-03` / `Stand: 2026-10-03` status badges across `README.md` and `README_de.md`; synchronized `llms.txt` RAG context (Last-checked: 2026-10-03).
- Automated Contract Tests: Expanded `tests/test_metadata.py` with checks for bilingual `CONTRIBUTING.md` guidance, the PEP 621 Contributing URL, `.gitignore` patterns, and the dated documentation review.

## Historical Unreleased Entry (2026-10-01)

### Added
- Visual Architecture: ASCII Four-View Architectural Topology projection in Section 2 of `README.md` and `README_de.md` (Views 1-4 / Sichten 1-4: Entrypoints & Tray Runtimes, Zombie Reaper Sovereign Core Engine, Runtime Persistence & Kernel Locks, Air-Gap Defense Perimeter & Zero-Egress Governance).
- Direct-dependency license summaries (Stand 2026-10-01): Reviewed `THIRD_PARTY_LICENSES.md` and `THIRD_PARTY_LICENSES.txt` to document the listed direct dependencies and their recorded license identifiers and notices; they do not inventory transitive dependencies or certify project invariants.
- Project metadata enrichment: Added `"Level 1 SBOM"` URL under `[project.urls]` in `pyproject.toml`.
- Status and audit badges synchronized across `README.md` and `README_de.md` to `2026-10-01`.
- Expanded automated contract tests in `tests/test_metadata.py` validating ASCII Four-View Architectural Topology projection, bilingual view parity, Level 1 SBOM recency, and 2026-10-01 badge synchronization.

### Added (Previous)
- CI/CD Lifecycle Workflows: `.github/workflows/auto-assign.yml` (automated PR assignment using `actions/github-script@v7`, `timeout-minutes: 5`, least-privilege `issues: write`, `pull-requests: write`, and concurrency `cancel-in-progress: true`), `.github/workflows/label-sync.yml` (automated label synchronization using `EndBug/label-sync@v2`, `timeout-minutes: 5`, least-privilege `issues: write`, and concurrency `cancel-in-progress: true`), and canonical `.github/labels.yml` with 11 standard triage labels per `GOVERNANCE.md §4.2`.
- Plain-Text Direct-Dependency License Summary: Added `THIRD_PARTY_LICENSES.txt` as a plaintext companion to the listed direct-dependency license information, cross-referenced from canonical root `NOTICE` and `THIRD_PARTY_LICENSES.md`; it does not inventory transitive dependencies or certify project invariants.
- PEP 621 metadata enhancement in `pyproject.toml`: Added `"THIRD_PARTY_LICENSES.txt"` to `license-files` whitelist and registered `"Third-Party Licenses (Text)"` and `"Plain-Text Licenses"` URLs under `[project.urls]`.
- Pytest runtime isolation & temporary directory defense: Added `addopts = "-ra -v --basetemp=.pytest_temp"` to `pyproject.toml` and broadened `norecursedirs` to ignore `.pytest_temp`, `.pytest_tmp*`, `.tox`, `.hypothesis`, and `.turbo`.
- Multi-host sync and canonical lock protection in `.gitignore`: Hardened with generic workstation, laptop, and device-family sync-conflict filename patterns and test cache directories (`.pytest_temp/`, `.pytest_tmp*/`).
- Automated contract tests: Expanded `tests/test_metadata.py` with validations for the new CI lifecycle workflows (`auto-assign.yml`, `label-sync.yml`), standard labels manifest (`labels.yml`), Level 1 SBOM text companion (`THIRD_PARTY_LICENSES.txt`), PEP 621 URL/license-file entries, and hardened multi-host `.gitignore` patterns.
- Installable `src/zombie_killer_tray/` package (T-20260926-212716751), distribution name `zombie-killer-tray` (unchanged), enabling `python -m zombie_killer_tray <action>` — for CareCenter-for-Codex and safe-start-for-codex to eventually depend on and launch as their own subprocess, the same pattern CareCenter already uses for safe-start-for-codex. `zombie_killer.py`/`zombie_settings.py` at the repository root are now thin backward-compatible wrapper scripts (used unchanged by `zombie_tray.ps1`/`start-zombie-killer-admin.bat`); local runtime state (`zombie_events.jsonl`, `zombie_worker_errors.log`) now follows the process's current working directory rather than the script's own location, matching how the tray already launches it and letting a future embedding consumer choose its own state location via its subprocess `cwd`.
- Bilingual tray UI (English / German, T-20260926-368033290): menu, tooltip, and toggle labels follow the Windows UI language at startup and switch instantly via a new **Language / Sprache** submenu, persisted in `zombie_state.json`. The audit trail and diagnostic log stay English (technical event data, not UI prose).
- Read-only `broker-report` action and background detection (in `watch`/`scan`/`reap`) for superseded, idle `codex@openai-codex` app-server-broker processes (T-20260924-303164669): the plugin's own `ensureBrokerSession` never kills an old broker when it spawns a replacement, only its session files, so these can accumulate. Detection is scoped per workspace cwd and CPU-gated so an older broker still legitimately blocked on a model response is never flagged; `track_broker_idle_streaks()` additionally requires the same idle reading to hold across several separately-sampled cycles (a real, cumulative multi-minute span) before marking a finding `confirmed`. Display/audit only — the existing "parent dead" kill criterion (T-20260816-50) is untouched and this detection never terminates anything.

### Fixed
- `cycle()`'s broker before/after CPU sample is now taken across the same real `interval` gap the reap loop already sleeps for, instead of back-to-back with ~0 elapsed time (which made the CPU delta ~0 and most brokers look idle regardless of actual activity).
- Tray "Automatik" toggle (checkbox) with an "Intervall" submenu (5/10/20/30/60 min, 3/5/10/15/20 h, 24 h daily; default 30 min) to turn continuous background reaping on/off and pick its cadence, plus a second "Mindestwartezeit" submenu (5/10/15/30/60 min, 2/6/12/24 h; default 30 min, matching the prior hardcoded value) controlling `zombie_killer.py`'s `--min-age`. New `zombie_settings.py` module is the single source of truth for both allowed-value lists and their fail-safe persistence to the already-reserved, gitignored `zombie_state.json` slot; PowerShell reads both lists from it once at startup instead of duplicating the tables. Automatik off means no background worker runs at all — the manual "Jetzt prüfen..." menu item stays available regardless. Safety gates (parent-dead check, allowlist classification, retained-handle termination, and the hard `min_age >= 30s` / `interval >= 3s` floor in `zombie_killer.py`'s own argument parser) are unchanged — this feature only narrows the offered range within that floor. 20 unit tests in `test_zombie_settings.py`.
- Visual Architecture & Dual Mermaid diagrams in `README.md` and `README_de.md` (5-layer system topology `flowchart TD` and process termination lifecycle `sequenceDiagram` with `autonumber` and zero semicolons).
- 18-point bilingual navigation architecture across `README.md` and `README_de.md` with reciprocal dual HTML anchor aliases (`<a id="..."></a>`).
- Target Personas specification ([PERSONA-01] to [PERSONA-04]) and high-intent bilingual search queries (EN/DE).
- 10-dimension 5-way comparative matrix benchmarking `zombie-killer-tray` against Windows Task Manager, ad-hoc taskkill scripts, generic cleaners, and cloud APM tools mapped to invariants INV-LOCAL-01 through INV-SLA-10.
- Full 20/20 GitHub topics saturation and canonical homepage URL set to `https://github.com/dev-bricks/zombie-killer-tray#readme`.
- Canonical Open-Source `NOTICE` attribution file attributing copyright to Lukas Geiger, dev-bricks, and open-bricks umbrella.
- PEP 621 metadata standardization in `pyproject.toml` with license-files, classifiers, synchronized 20 keywords, URLs, and pytest/ruff tool configurations (version 0.1.0 frozen).
- Comprehensive Level 1 SBOM in `THIRD_PARTY_LICENSES.md` auditing `psutil` (BSD-3-Clause), standard library (PSFL-2.0), and test tooling (`pytest`, `ruff`), establishing 100% Zero-Copyleft assurance.
- 10 codified architectural and governance invariants (INV-LOCAL-01 through INV-SLA-10) with complete cross-reference matrix.
- CI/CD lifecycle workflows `.github/workflows/stale.yml` (`actions/stale@v9`, timeout 10m) and `welcome.yml` (`actions/first-interaction@v3`, timeout 5m).
- Full bilingual documentation parity in `README_de.md` alongside expanded `README.md` with Shields.io status badges and § 521 BGB statutory disclaimer.
- Governance register `MARKETING-LOG.txt` tracking repository hygiene and target personas.
- Automated contract test suite in `tests/test_metadata.py` validating file invariants, CI workflows, and packaging discipline.

### Changed
- Hardened `.github/workflows/tests.yml` with concurrency `cancel-in-progress: true`, `timeout-minutes: 15`, and integrated pytest/ruff checks.
- Hardened `.gitignore` against multi-host synchronization conflict copies, canonical lock files (`LOCK`, `LOCK.*`), and test caches.
- Updated `SECURITY.md` with dual-tier Security Response SLA (48h response, 5 business days triage) and canonical contacts.
- Updated `llms.txt` with current architectural context, 18-point navigation index, and test baselines.
- Cleaned Win32 helper methods and code formatting in `zombie_killer.py` and `test_zombie_killer.py`.

### Corrected (2026-10-03)

- Earlier text in this Unreleased record and associated project documents overstated offline and zero-egress boundaries, air-gap protection, universal safety guarantees, security response timing, license completeness, and a legal outcome under § 521 BGB. Those assertions are withdrawn. Current documents describe observed source behavior with explicit limits; no response-time SLA, compliance certification, or complete transitive dependency inventory is claimed.
- The tray menu, tooltip, and language selector support English, German, Spanish, Simplified Chinese, Japanese, and Russian. The six README files describe the corresponding user-facing languages.
- The default pytest collection includes the repository-root tests and metadata tests together. License notes and package links are scoped to directly declared dependencies; Ruff's recorded license reference now points to its upstream MIT license. The internal marketing log is no longer tracked and is ignored locally.


## 0.1.0 - 2026-09-21

- Add conservative Windows zombie killer tray for orphaned MCP and language
  server processes.
- Add safety gates for parent death, CPU stability, allowlisted entry points,
  and retained process handles.
- Add unit tests, local audit logging, and admin launcher.
