# Security Policy & Governance

## Reporting Security Vulnerabilities

If you discover a security vulnerability in `zombie-killer-tray`, please report it privately through **GitHub Security Advisories** or directly via email:

- **Primary Security Contact:** `security@dev-bricks.org`
- **Umbrella Security Team:** `security@open-bricks.org`

Please **do not** report security vulnerabilities via public GitHub issues, discussions, or pull requests. Do not include private command-line arguments, hostnames, or system credentials in report descriptions.

### Security Response SLA (INV-SLA-10)

We operate under an explicit, standardized dual-tier Security Response Service Level Agreement:
- **Initial Acknowledgment:** Within **48 hours** of report receipt.
- **Triage & Remediation Plan:** Within **5 business days** of confirmation.

---

## Security Model & Architectural Invariants

`zombie-killer-tray` is built with a defense-in-depth, fail-closed architecture to prevent accidental termination of legitimate user or system processes:

1. **Local-First & Zero-Egress (INV-LOCAL-01):** The utility performs 100% offline local operations. It initiates no outbound network connections and emits zero telemetry.
2. **Unprivileged Mode for Inspection (`RunAsInvoker` / INV-SEC-02):** Read-only verification (`--check`) runs in unprivileged user mode. Elevated privileges are only requested when launching the tray to enable termination of orphaned system/service processes.
3. **Dead-Parent Verification (INV-PARENT-03):** Reaping occurs only if the parent process PID is verified dead in multiple sampling rounds and immediately prior to termination.
4. **Two-Sample Stability (INV-STABLE-04):** Requires two consecutive snapshots with zero CPU delta and identical creation timestamps to avoid interfering with active tasks.
5. **Retained Kernel Handle (INV-HANDLE-05):** Holds a Win32 process handle to prevent PID-reuse race conditions.
6. **Strict Allowlist (INV-ALLOW-06):** Only exact, verified MCP servers and language server executables/modules are eligible for termination.
7. **No Blanket Process Tree Termination (INV-NOTREE-07):** Does not execute blanket recursive process tree kills (`taskkill /T`).
8. **Pre-Termination Audit Logging (INV-AUDIT-08):** Every candidate termination is logged to `zombie_events.jsonl` prior to invoking the termination API. If audit logging fails, the process is not terminated.
9. **Minimum Process Age Gate (INV-AGE-09):** Processes must exceed a minimum runtime threshold (default: 30 minutes) before being considered for termination.

---

## Legal & Statutory Notice (§ 521 BGB)

This software is provided free of charge as open-source software under the MIT License. In accordance with statutory German law (§ 521 BGB - Gefälligkeitsrecht / liability for gratuitous services), liability for defects in quality and title is limited to cases of fraudulent concealment of defects, gross negligence, or intentional misconduct.
