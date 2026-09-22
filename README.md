# Zombie Killer Tray

[![Attribution: NOTICE](https://img.shields.io/badge/Attribution-NOTICE-blue.svg)](NOTICE)
[![Version: 0.1.0](https://img.shields.io/badge/version-0.1.0-blue.svg)](CHANGELOG.md)
[![Tests: Passed](https://img.shields.io/badge/tests-passed%20%7C%20100%25-brightgreen.svg)](tests/test_metadata.py)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](#)
[![Zero-Egress: 100% Local](https://img.shields.io/badge/Zero--Egress-100%25%20Local-success.svg)](#privacy--security-governance)
[![Security SLA: 48h / 5d](https://img.shields.io/badge/Security%20SLA-48h%20%2F%205d-blue.svg)](SECURITY.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> **Deutsche Version:** Eine vollständige deutsche Dokumentation befindet sich in [README_de.md](README_de.md).

Conservative Windows system tray utility for cleaning up orphaned Model Context Protocol (MCP) and language server processes. It validates process incarnation, parent dead state, CPU stability, and minimum process age before termination. It never performs blanket `taskkill /T` process-tree operations.

---

## Navigation & Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Start on Windows](#start-on-windows)
- [Safety Model & Governance Invariants](#safety-model--governance-invariants)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Privacy & Security Governance](#privacy--security-governance)
- [Third-Party Transparency & SBOM](#third-party-transparency--sbom)
- [Legal & Statutory Notice (§ 521 BGB)](#legal--statutory-notice--521-bgb)
- [License](#license)

---

## Overview & Architecture

When local AI agent frameworks (Claude Code, Codex CLI, Antigravity, Kimi) or IDEs crash or disconnect, backend MCP servers (`node.exe`, `python.exe`) and language servers (`rust-analyzer.exe`, `clangd.exe`, `gopls.exe`, `pylsp`) can linger indefinitely. These orphaned processes accumulate in the background, consume gigabytes of memory, and retain filesystem locks.

`zombie-killer-tray` solves this without risking active developer processes. Instead of naive heuristics or recursive process tree killing:
1. It queries the Win32 process snapshot table.
2. Filters exclusively for an exact allowlist of MCP packages and language server binaries.
3. Takes two distinct samples separated by an observation interval to verify zero CPU activity.
4. Validates that the process parent PID is verified dead in both samples and immediately before termination.
5. Pins a retained Win32 process handle (`OpenProcess`) to eliminate PID-reuse race conditions.
6. Writes an audit record to `zombie_events.jsonl` before calling `TerminateProcess`.

---

## Start on Windows

### Prerequisites

Install Python 3.12+ and dependencies:

```powershell
python -m pip install -r requirements.txt
```

### 1. Launch the System Tray (Elevated)

Double-click `start-zombie-killer-admin.bat`. Windows requests elevation (UAC) and starts the tray minimized with administrator rights so it can terminate orphaned processes across sessions:

```bat
start-zombie-killer-admin.bat
```

The batch launcher resolves `zombie_tray.ps1` relative to its own directory, making the repository fully self-contained and portable.

### 2. Validate Without Elevation (RunAsInvoker)

To run a read-only syntax and environment pre-flight check without requesting administrator rights:

```bat
start-zombie-killer-admin.bat --check
```

### 3. Tray Context Menu Actions

- **Double-Click or "Jetzt prüfen und veraltete MCPs bereinigen":** Triggers an immediate inspection cycle.
- Local audit logs are recorded in `zombie_events.jsonl` and `zombie_tray.log` (both untracked and gitignored).

---

## Safety Model & Governance Invariants

The utility enforces 10 strict architectural and governance invariants:

| Invariant Code | Guarantee Name | Category | Enforcement Mechanism |
|:---|:---|:---|:---|
| **INV-LOCAL-01** | Local-First & Zero Egress | Network Privacy | Pure standard library + `psutil`; zero network sockets; zero telemetry |
| **INV-SEC-02** | Unprivileged Inspection | Security Privilege | `start-zombie-killer-admin.bat --check` and unit tests require zero elevation |
| **INV-PARENT-03** | Dead-Parent Verification | Process Safety | Parent PID confirmed dead across multiple samples and prior to kill |
| **INV-STABLE-04** | Two-Sample CPU & Identity Stability | Mutation Safety | Two consecutive snapshots require 0 CPU delta and identical creation time |
| **INV-HANDLE-05** | PID-Reuse Protection via Pinned Handle | Kernel Safety | Retains explicit Win32 `OpenProcess` handle to lock kernel object |
| **INV-ALLOW-06** | Strict Allowlist of Entrypoints | Scope Boundary | Only exact allowlisted MCP servers and language servers can match |
| **INV-NOTREE-07** | No Blanket Tree Kills | Safety Isolation | Individual process handle termination only; no recursive tree kills |
| **INV-AUDIT-08** | Pre-Termination Audit Logging | Auditability | Pre-write event record to `zombie_events.jsonl`; failure aborts termination |
| **INV-AGE-09** | Minimum Process Age Gate | Timing Safety | Conservative minimum age threshold (30 minutes default) |
| **INV-SLA-10** | Dual Security Response SLA | Governance & Triage | 48h initial response, 5 business days triage codified in `SECURITY.md` |

---

## Testing & Quality Assurance

Run the test suites:

```powershell
# Run the contract test suite and unit tests via pytest
python -m pytest -ra -v

# Or run unit tests directly via unittest
python -m unittest -v test_zombie_killer
```

The Windows smoke test validates process handle lifecycle and termination safety strictly against a subprocess spawned by that test itself.

---

## Privacy & Security Governance

The utility is strictly local-only and performs no network requests or telemetry. Audit logs can include local command-line arguments and therefore remain untracked and excluded from version control.

Vulnerability reporting guidelines and our 48-hour Security SLA are detailed in [SECURITY.md](SECURITY.md).

---

## Third-Party Transparency & SBOM

All runtime and development dependencies are 100% permissive open-source software (MIT, Apache-2.0, PSFL, BSD-3-Clause) with zero copyleft. For the complete Level 1 SBOM and compliance verification, see [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md).

Attribution notices for Lukas Geiger, `dev-bricks`, and `open-bricks` are codified in [NOTICE](NOTICE).

---

## Legal & Statutory Notice (§ 521 BGB)

This software is provided free of charge under the MIT License. Under statutory German law (§ 521 BGB - Gefälligkeitsrecht), liability for defects in quality and title is strictly limited to cases of fraudulent concealment, gross negligence, or intentional misconduct.

---

## License

MIT — see [LICENSE](LICENSE).
