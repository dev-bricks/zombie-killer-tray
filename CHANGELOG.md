# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Canonical Open-Source `NOTICE` attribution file attributing copyright to Lukas Geiger, dev-bricks, and open-bricks umbrella.
- PEP 621 metadata standardization in `pyproject.toml` with license-files, classifiers, keywords, URLs, and pytest/ruff tool configurations (version 0.1.0 frozen).
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
- Updated `llms.txt` with current architectural context and test baselines.
- Cleaned Win32 helper methods and code formatting in `zombie_killer.py` and `test_zombie_killer.py`.

## 0.1.0 - 2026-09-21

- Add conservative Windows zombie killer tray for orphaned MCP and language
  server processes.
- Add safety gates for parent death, CPU stability, allowlisted entry points,
  and retained process handles.
- Add unit tests, local audit logging, and admin launcher.
