# Third-Party Licenses & Transparency Notice

> **Project:** `dev-bricks/zombie-killer-tray`<br>
> **Audited:** 2026-10-03<br>
> **Repository License:** [MIT License](LICENSE)<br>
> **Attribution Notice:** [NOTICE](NOTICE)<br>
> **Plain-Text Companion:** [THIRD_PARTY_LICENSES.txt](THIRD_PARTY_LICENSES.txt)<br>
> **Architecture & Privacy:** 100% Local-First, Zero-Egress, Unprivileged User-Mode Inspection (`RunAsInvoker`), Win32 Retained Handle Process Termination

---

## Executive Summary & Compliance Assurance

`zombie-killer-tray` is engineered under strict architectural and governance invariants: **100% Local-First, Zero-Egress by default, unprivileged user-mode inspection (`RunAsInvoker`), and conservative orphan reaping**. The process table scanner, parent-child validator, Win32 process handle pin, CPU stability sampler, and termination engine operate completely within local system boundaries without any unsolicited external network communication, telemetry, or cloud dependencies.

All direct runtime, development, and quality assurance dependencies utilized across `zombie-killer-tray` are distributed under strictly **permissive and free open-source licenses** (MIT, Apache-2.0, PSFL, BSD-3-Clause). There are **zero AGPL or proprietary restrictive copyleft constraints**, ensuring maximum safety and portability for local developer desktop environments, automated test runners, and multi-agent workstations.

Furthermore, `zombie-killer-tray` guarantees:
1. **100% Local-First & Zero Egress (INV-LOCAL-01):** Core orphan scanning, inspection, and termination execute completely offline with zero telemetry and zero external network calls.
2. **Unprivileged Inspection & Verification (INV-SEC-02):** Read-only inspection (`--check`, `--list`, unit tests) runs strictly in unprivileged user mode (`RunAsInvoker`) without requiring administrator elevation.
3. **Dead-Parent Verification (INV-PARENT-03):** Stale processes are only classified as eligible orphans if their parent PID is confirmed dead in both sampling cycles and immediately before termination.
4. **Two-Sample CPU & Identity Stability (INV-STABLE-04):** Requires two consecutive snapshots separated by an observation interval with zero CPU delta and identical process creation timestamps.
5. **PID-Reuse Protection via Pinned Handle (INV-HANDLE-05):** Obtains and retains an explicit Win32 process handle (`OpenProcess`) to lock the kernel object and prevent PID-reuse race conditions.
6. **Strict Allowlist of Entrypoints (INV-ALLOW-06):** Target processes are strictly restricted to verified MCP and language server executables, modules, and scripts. Arbitrary processes or unknown executables are never matched.
7. **No Blanket Process Tree Termination (INV-NOTREE-07):** Never performs blanket `taskkill /T` operations. Every process is verified and terminated individually.
8. **Pre-Termination Audit Logging (INV-AUDIT-08):** Writes an immutable event record to local audit logs (`zombie_events.jsonl`) before any termination syscall is issued; audit failures abort termination.
9. **Minimum Process Age Gate (INV-AGE-09):** Enforces a conservative minimum process age threshold (default 30 minutes) to avoid interfering with newly spawned processes.
10. **Dual Security Response & Triage SLA (INV-SLA-10):** Strict 48-hour acknowledgment and 5-business-day triage commitment via canonical security reporting channels (`security@open-bricks.org`, `security@dev-bricks.org`).

---

## Invariant Cross-Reference Matrix

The 10 architectural and governance invariants are enforced across the codebase and validated by automated test suites:

| Invariant Code | Guarantee Name | Category | Primary Code Enforcing Invariant | Test Suite Verification |
|:---|:---|:---|:---|:---|
| **INV-LOCAL-01** | Local-First & Zero Egress | Network Privacy | Pure standard library + `psutil`; no networking calls; local audit logs | `test_zombie_killer.py::SafetyTests::test_non_targets` |
| **INV-SEC-02** | Unprivileged Inspection | Security Privilege | `start-zombie-killer-admin.bat --check` and Python CLI inspect without elevation | `tests/test_metadata.py::test_launcher_check_clean` |
| **INV-PARENT-03** | Dead-Parent Verification | Process Safety | `Win32.parent_dead(ppid)` in `zombie_killer.py` | `test_zombie_killer.py::SafetyTests::test_live_parent_second_sample_blocks` |
| **INV-STABLE-04** | Two-Sample CPU & Identity Stability | Mutation Safety | `cycle()` two-sample verification in `zombie_killer.py` | `test_zombie_killer.py::SafetyTests::test_cycle_requires_two_samples` |
| **INV-HANDLE-05** | PID-Reuse Protection via Pinned Handle | Kernel Safety | `Win32.open(pid, terminate=True)` held during checks | `test_zombie_killer.py::SafetyTests::test_stable_orphan_uses_same_handle` |
| **INV-ALLOW-06** | Strict Allowlist of Entrypoints | Scope Boundary | `classify()` matching `LSP`, `NODE_ENTRIES`, `MCP_PACKAGES`, `PYTHON_MODULES` | `test_zombie_killer.py::SafetyTests::test_real_entrypoint` |
| **INV-NOTREE-07** | No Blanket Tree Kills | Safety Isolation | Individual process handle termination; no recursive child kill | `test_zombie_killer.py::SafetyTests::test_owned_process_handle_smoke_and_live_parent` |
| **INV-AUDIT-08** | Pre-Termination Audit Logging | Auditability | `audit()` called prior to `api.terminate()` in `safe_terminate()` | `test_zombie_killer.py::SafetyTests::test_failed_audit_prevents_kill` |
| **INV-AGE-09** | Minimum Process Age Gate | Timing Safety | Minimum 30m (`min_age_s`) validation against creation timestamp | `test_zombie_killer.py::SafetyTests::test_young_orphan_blocks` |
| **INV-SLA-10** | Dual Security Response SLA | Governance & Triage | 48-hour response, 5-business-day triage codified in `SECURITY.md` | `tests/test_metadata.py::test_security_sla_and_contacts` |

---

## Runtime Dependency Matrix

The runtime dependency of `zombie-killer-tray` is limited to `psutil` for platform process table inspection.

| Package | Constraint | Role / Functional Scope | License | Project Repository / Upstream |
|:---|:---:|:---|:---|:---|
| **psutil** | `>=7.2,<8` | Process table enumeration, command-line arguments inspection, memory/CPU statistics | [BSD-3-Clause](https://github.com/giampaolo/psutil/blob/master/LICENSE) | [giampaolo/psutil](https://github.com/giampaolo/psutil) |
| **Python Standard Library** | Built-in | Core CLI, Win32 ctypes bindings, dataclasses, JSON logging, threading | [PSFL-2.0](https://docs.python.org/3/license.html) | [python/cpython](https://github.com/python/cpython) |

---

## Direct Development, Build & Quality Assurance Tooling

| Package | Constraint | Usage & Purpose | License | Source / Upstream |
|:---|:---:|:---|:---|:---|
| **hatchling** | `>=1.24` | Modern PEP 517/621 build backend and wheel packaging | [MIT](https://github.com/pypa/hatch/blob/master/LICENSE.txt) | [pypa/hatch](https://github.com/pypa/hatch) |
| **pytest** | `>=9.1.1` | Automated contract test runner, unit tests and regression assertions | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) | [pytest-dev/pytest](https://github.com/pytest-dev/pytest) |
| **ruff** | `>=0.5.0` | Fast Python linter, style enforcement and import hygiene | [MIT / Apache-2.0](https://github.com/astral-sh/ruff/blob/main/LICENSE-MIT) | [astral-sh/ruff](https://github.com/astral-sh/ruff) |

---

## Distribution Notes & Compliance Verification

- Installing the package via `pip install -r requirements.txt` installs solely `psutil` (BSD-3-Clause permissive).
- Win32 API interactions utilize Python's built-in `ctypes` bindings without additional external DLL or C-extension requirements.
- The tray wrapper `zombie_tray.ps1` runs purely using standard Windows built-in PowerShell and Windows Forms notify icon APIs (`System.Windows.Forms.NotifyIcon`).
- All software artifacts comply fully with open-source licensing guidelines under the MIT License and the canonical [NOTICE](NOTICE) attribution file.
