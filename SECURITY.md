# Security Policy

## Reporting a vulnerability

Please report suspected security vulnerabilities privately through GitHub Security Advisories or by using one of the project contacts listed below. Do not post sensitive command-line arguments, host details, or credentials in public issues or pull requests.

- Project contact: `security@dev-bricks.org`
- Organization contact: `security@open-bricks.org`

The project does not promise an acknowledgment, triage, or remediation timeline. Contact details do not constitute a service-level agreement.

## What the program does

The project provides a Windows tray application and Python command-line tools for inspecting selected MCP and language-server processes and, when explicitly run in apply mode, attempting to terminate an eligible individual process. The current source includes several checks, including configured entrypoint matching, parent-process checks, process identity and CPU observations, a minimum-age threshold, a retained Windows process handle, and a pre-termination audit-intent write. If that intent write fails, the corresponding termination attempt is skipped.

These checks narrow which processes the program considers. They do not make termination risk-free or guarantee that every system condition is detected. The project is not an operating-system sandbox, an OS-enforced network boundary, or a security certification.

The batch launcher's `--check` mode checks for the tray script and asks PowerShell to parse it. It does not inspect processes, validate the Python environment, or change the caller's privilege token. Normal tray launch through the provided administrator launcher requests elevation.

## Local data

The tool reads local process information. Its JSONL and diagnostic logs can include process identifiers, executable names, command-line arguments, timestamps, and local paths. The tray's settings file stores local UI and automatic-mode choices. Protect and remove these files according to your own retention needs; they are ordinary local files and are not tamper-evident records.

## Reporting details

When reporting a problem, include the relevant version, operating system, exact command, and a redacted error message. Remove personal paths, process arguments, identifiers, and secrets unless they are essential and you are sending them through a private channel.