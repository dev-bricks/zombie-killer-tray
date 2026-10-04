"""Contract and hygiene test suite for dev-bricks/zombie-killer-tray.

Validates repository metadata, CI workflows, packaging invariants, direct-license scope,
multi-host lock defense, six-language documentation structure, and Mermaid diagrams.
"""
from __future__ import annotations

import re
import subprocess
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class MetadataContractTests(unittest.TestCase):
    def test_notice_attribution_present_and_valid(self):
        notice = ROOT / "NOTICE"
        self.assertTrue(notice.is_file(), "NOTICE file must exist in repository root")
        text = notice.read_text(encoding="utf-8")
        self.assertIn("Zombie Killer Tray", text)
        self.assertIn("Lukas Geiger", text)
        self.assertIn("dev-bricks", text)
        self.assertIn("open-bricks", text)
        self.assertIn("MIT License", text)
        self.assertIn("THIRD_PARTY_LICENSES.md", text)
        self.assertIn("THIRD_PARTY_LICENSES.txt", text)

    def test_ci_workflows_present_and_hardened(self):
        workflows = ROOT / ".github" / "workflows"
        self.assertTrue(workflows.is_dir(), ".github/workflows directory must exist")

        tests_yml = workflows / "tests.yml"
        self.assertTrue(tests_yml.is_file(), "tests.yml must exist")
        tests_text = tests_yml.read_text(encoding="utf-8")
        self.assertIn("timeout-minutes: 15", tests_text)
        self.assertIn("cancel-in-progress: true", tests_text)
        self.assertIn("pytest", tests_text)

        stale_yml = workflows / "stale.yml"
        self.assertTrue(stale_yml.is_file(), "stale.yml must exist")
        stale_text = stale_yml.read_text(encoding="utf-8")
        self.assertIn("actions/stale@v9", stale_text)
        self.assertIn("timeout-minutes: 10", stale_text)
        self.assertIn("cancel-in-progress: true", stale_text)
        self.assertIn("issues: write", stale_text)
        self.assertIn("pull-requests: write", stale_text)

        welcome_yml = workflows / "welcome.yml"
        self.assertTrue(welcome_yml.is_file(), "welcome.yml must exist")
        welcome_text = welcome_yml.read_text(encoding="utf-8")
        self.assertIn("actions/first-interaction@v3", welcome_text)
        self.assertIn("timeout-minutes: 5", welcome_text)
        self.assertIn("cancel-in-progress: true", welcome_text)

        auto_assign_yml = workflows / "auto-assign.yml"
        self.assertTrue(auto_assign_yml.is_file(), "auto-assign.yml must exist")
        auto_assign_text = auto_assign_yml.read_text(encoding="utf-8")
        self.assertIn("actions/github-script@v7", auto_assign_text)
        self.assertIn("timeout-minutes: 5", auto_assign_text)
        self.assertIn("cancel-in-progress: true", auto_assign_text)
        self.assertIn("pull-requests: write", auto_assign_text)

        label_sync_yml = workflows / "label-sync.yml"
        self.assertTrue(label_sync_yml.is_file(), "label-sync.yml must exist")
        label_sync_text = label_sync_yml.read_text(encoding="utf-8")
        self.assertIn("EndBug/label-sync@v2", label_sync_text)
        self.assertIn("timeout-minutes: 5", label_sync_text)
        self.assertIn("cancel-in-progress: true", label_sync_text)
        self.assertIn("issues: write", label_sync_text)
        self.assertIn(".github/labels.yml", label_sync_text)

        labels_yml = ROOT / ".github" / "labels.yml"
        self.assertTrue(labels_yml.is_file(), ".github/labels.yml must exist")
        labels_text = labels_yml.read_text(encoding="utf-8")
        for expected_label in ["bug", "enhancement", "good first issue", "help wanted", "priority: high"]:
            self.assertIn(expected_label, labels_text)

    def test_gitignore_multihost_and_lock_defense(self):
        gitignore = ROOT / ".gitignore"
        self.assertTrue(gitignore.is_file(), ".gitignore must exist")
        content = gitignore.read_text(encoding="utf-8")

        required_patterns = [
            "*conflicted copy*",
            "* (Kopie)*",
            "* (Copy)*",
            "*.swp",
            "*.swo",
            "*~",
            "TASKPLAN_*.md",
            "*-TASKPLAN*",
            "desktop.ini",
            "ehthumbs.db",
            "*-WORKSTATION*",
            "*_WORKSTATION*",
            "*-ASUS*",
            "*-LAPTOP*",
            "*-IDEAPAD*",
            "LOCK",
            "LOCK.*",
            "LOCK.user.*",
            "LOCK.until.*",
            "LOCK.condition.*",
            "LOCK.dev.*",
            "LOCK.antigravity.*",
            "LOCK.bugsearch.*",
            "LOCK.permissions.json",
            "uv.lock",
            "!package-lock.json",
            "MARKETING-LOG.txt",
            "zombie_events.jsonl",
            "zombie_tray.log",
            ".pytest_temp/",
            ".pytest_tmp*/",
        ]
        for pattern in required_patterns:
            self.assertIn(pattern, content, f"Missing required .gitignore pattern: {pattern}")

    def test_pyproject_pep621_metadata_and_version_frozen(self):
        pyproject = ROOT / "pyproject.toml"
        self.assertTrue(pyproject.is_file(), "pyproject.toml must exist")
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

        project = data.get("project", {})
        self.assertEqual(project.get("name"), "zombie-killer-tray")
        # Rule T-20260920-167562623: Pfad A/B fasst NIE die Versionsnummer an
        self.assertEqual(project.get("version"), "0.1.0", "Version 0.1.0 must remain frozen")
        self.assertIn("psutil>=7.2,<8", project.get("dependencies", []))

        license_files = project.get("license-files", [])
        self.assertIn("LICENSE", license_files)
        self.assertIn("NOTICE", license_files)
        self.assertIn("THIRD_PARTY_LICENSES.md", license_files)
        self.assertIn("THIRD_PARTY_LICENSES.txt", license_files)
        self.assertNotIn("CONTRIBUTING.md", license_files)

        urls = project.get("urls", {})
        for required_url_key in [
            "Homepage",
            "Documentation",
            "Repository",
            "Issues",
            "Security",
            "Notice",
            "Direct Dependency License Summary",
            "Direct Dependency License Summary (Text)",
            "LLM Ready",
            "Contributing",
            "Parent Organization",
            "Umbrella Ecosystem",
        ]:
            self.assertIn(required_url_key, urls, f"Missing project URL key: {required_url_key}")

        self.assertNotIn("Marketing Log", urls)
        self.assertEqual(
            urls["Contributing"],
            "https://github.com/dev-bricks/zombie-killer-tray/blob/main/CONTRIBUTING.md",
        )
        self.assertNotIn("Level 1 SBOM", urls)
        self.assertNotIn("Plain-Text Licenses", urls)

        keywords = project.get("keywords", [])
        self.assertEqual(len(keywords), 20, "Must have exactly 20 discoverability keywords")
        self.assertNotIn("zero-egress", keywords)

        self.assertIn("tool", data)
        self.assertIn("pytest", data["tool"])
        pytest_ini = data["tool"]["pytest"].get("ini_options", {})
        self.assertIn("--basetemp=.pytest_temp", pytest_ini.get("addopts", ""))
        self.assertIn("ruff", data["tool"])

    def test_third_party_licenses_are_scoped_to_direct_dependencies(self):
        summary = ROOT / "THIRD_PARTY_LICENSES.md"
        self.assertTrue(summary.is_file(), "direct dependency license summary must exist")
        text = summary.read_text(encoding="utf-8")

        self.assertIn("pyproject.toml", text)
        self.assertIn("reviewed 2026-10-03", text)
        self.assertIn("MIT License", text)
        self.assertIn("psutil", text)
        self.assertIn(">=7.2,<8", text)
        self.assertIn("BSD-3-Clause", text)
        self.assertIn("hatchling", text)
        self.assertIn("pytest", text)
        self.assertIn("ruff", text)
        self.assertIn("| Development | `ruff` | `>=0.5.0` | MIT |", text)
        self.assertNotIn("Apache-2.0", text)
        self.assertIn("does not enumerate transitive dependencies", text)
        self.assertNotIn("SBOM", text)
        self.assertNotIn("INV-SLA-10", text)
        self.assertNotIn("Zero-Egress", text)

        companion = ROOT / "THIRD_PARTY_LICENSES.txt"
        self.assertTrue(companion.is_file(), "plain-text direct dependency summary must exist")
        companion_text = companion.read_text(encoding="utf-8")
        for expected in ["psutil", "BSD-3-Clause", "hatchling", "pytest", "ruff"]:
            self.assertIn(expected, companion_text)
        self.assertIn("ruff >=0.5.0 - MIT", companion_text)
        self.assertNotIn("Apache-2.0", companion_text)
        self.assertIn("does not enumerate transitive dependencies", companion_text)
        self.assertNotIn("SBOM", companion_text)
        self.assertNotIn("INV-SLA-10", companion_text)

    def test_security_policy_has_no_unpromised_sla_or_statutory_claim(self):
        security = ROOT / "SECURITY.md"
        self.assertTrue(security.is_file(), "SECURITY.md must exist")
        text = security.read_text(encoding="utf-8")
        self.assertIn("security@dev-bricks.org", text)
        self.assertIn("security@open-bricks.org", text)
        self.assertIn("does not promise", text)
        for withdrawn in ["48 hours", "48-hour", "5 business days", "INV-SLA-10", "521 BGB"]:
            self.assertNotIn(withdrawn, text)

    def test_contributing_guidance_is_bilingual_and_bounded(self):
        path = ROOT / "CONTRIBUTING.md"
        self.assertTrue(path.is_file(), "CONTRIBUTING.md must exist")
        source = path.read_text(encoding="utf-8")
        self.assertIn('<a id="english"></a>', source)
        self.assertIn('<a id="deutsch"></a>', source)
        self.assertIn("python -m pytest -ra -v .", source)
        self.assertIn("Führe die vollständige Testsammlung", source)
        self.assertEqual(source.count("**") % 2, 0, "Bold markers must be balanced")
        for withdrawn in ["RunAsInvoker", "§ 521 BGB", "48-hour", "5-business-day"]:
            self.assertNotIn(withdrawn, source)
        self.assertNotRegex(source, r"(?i)\b[A-Z]:\\", "Contributor instructions must not embed host paths")
        for label in [
            "Configured entrypoint matching",
            "Parent-state checks",
            "Separate observations",
            "Identity and CPU comparison",
            "Minimum process age",
            "Retained process handle",
            "Individual action",
            "Pre-termination intent record",
            "Write-failure handling",
        ]:
            self.assertIn(label, source)
        self.assertEqual(source.count("\n1. "), 2, "Each language should start its safeguards list once")

    def test_documentation_six_languages_share_structure_and_navigation(self):
        files = ["README.md", "README_de.md", "README_es.md", "README_zh.md", "README_ja.md", "README_ru.md"]
        documents = {}
        for filename in files:
            path = ROOT / filename
            self.assertTrue(path.is_file(), f"{filename} must exist")
            documents[filename] = path.read_text(encoding="utf-8")

        for filename, source in documents.items():
            self.assertIn("CONTRIBUTING.md", source, f"{filename} must link to contributor guidance")
            self.assertIn("2026-10-03", "\n".join(source.splitlines()[:25]), f"{filename} must date the source review")
            for other in files:
                if other != filename:
                    self.assertIn(other, source, f"{filename} must link to {other}")

            lines = source.splitlines()
            for number in range(1, 19):
                heading_prefix = f"## {number}. "
                headings = [line for line in lines if line.startswith(heading_prefix)]
                self.assertEqual(len(headings), 1, f"{filename} must have section {number} exactly once")
                anchor = f'id="sec-{number:02d}"'
                self.assertEqual(source.count(anchor), 1, f"{filename} must have {anchor} exactly once")

            fences = sum(line.startswith("```") for line in lines)
            self.assertEqual(fences, 18, f"{filename} must contain nine balanced code blocks")

            nav_start = next(i for i, line in enumerate(lines) if line.startswith("### "))
            nav_end = next(i for i in range(nav_start + 1, len(lines)) if lines[i].strip() == "---")
            nav_targets = []
            for line in lines[nav_start:nav_end]:
                marker = "](#"
                if marker in line:
                    nav_targets.append(line.split(marker, 1)[1].split(")", 1)[0])
            self.assertEqual(len(nav_targets), 18, f"{filename} navigation must link to all sections")
            for target in nav_targets:
                self.assertIn(f'id="{target}"', source, f"{filename} navigation target #{target} must exist")

    def test_mermaid_diagrams_syntax_and_hygiene(self):
        for filename in ["README.md", "README_de.md", "README_es.md", "README_zh.md", "README_ja.md", "README_ru.md"]:
            source = (ROOT / filename).read_text(encoding="utf-8")
            self.assertEqual(source.count("```mermaid"), 2, f"{filename} must retain two diagrams")
            self.assertIn("flowchart TD", source, f"{filename} missing flowchart TD")
            self.assertIn("sequenceDiagram", source, f"{filename} missing sequenceDiagram")
            self.assertIn("autonumber", source, f"{filename} sequenceDiagram missing autonumber")
            sequences = re.findall(r"```mermaid\s+sequenceDiagram(.*?)```", source, re.DOTALL)
            self.assertEqual(len(sequences), 1, f"{filename} must have one sequence diagram")
            self.assertNotIn(";", sequences[0], f"{filename} sequence diagram must not contain semicolons")

    def test_changelog_has_unreleased_and_frozen_version(self):
        changelog = ROOT / "CHANGELOG.md"
        self.assertTrue(changelog.is_file(), "CHANGELOG.md must exist")
        text = changelog.read_text(encoding="utf-8")

        self.assertIn("## [Unreleased]", text)
        self.assertIn("## Historical Unreleased Entry (2026-10-03; corrected above)", text)
        self.assertIn("## Historical Unreleased Entry (2026-10-01)", text)
        self.assertEqual(text.count("## [Unreleased]"), 1)
        self.assertIn("are withdrawn", text)
        self.assertIn("## 0.1.0", text)
        self.assertNotIn("## 0.2.0", text, "Version bump forbidden in Pfad A/B")

    def test_llms_txt_reflects_bounded_source_scope(self):
        path = ROOT / "llms.txt"
        self.assertTrue(path.is_file(), "llms.txt must exist")
        source = path.read_text(encoding="utf-8")
        self.assertIn("Source version declared in `pyproject.toml`: 0.1.0", source)
        for filename in ["README.md", "README_de.md", "README_es.md", "README_zh.md", "README_ja.md", "README_ru.md"]:
            self.assertIn(filename, source)
        self.assertIn("not an OS-level network block", source)
        self.assertIn("not a complete transitive dependency inventory", source)
        self.assertIn("No response-time SLA", source)
        self.assertIn("Last-checked: 2026-10-03", source)
        self.assertIn("CONTRIBUTING.md", source)
        for withdrawn in ["INV-SLA-10", "521 BGB", "Level 1 SBOM", "100% Local-First & Zero Egress"]:
            self.assertNotIn(withdrawn, source)

    def test_marketing_log_is_private_and_not_published(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("MARKETING-LOG.txt", gitignore)
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertNotIn("Marketing Log", project.get("project", {}).get("urls", {}))
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", "MARKETING-LOG.txt"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(tracked.returncode, 0, "private marketing log must not be tracked")

    def test_public_docs_do_not_restore_withdrawn_assurance_claims(self):
        public_docs = [
            "README.md", "README_de.md", "README_es.md", "README_zh.md", "README_ja.md", "README_ru.md",
            "SECURITY.md", "llms.txt", "CONTRIBUTING.md", "THIRD_PARTY_LICENSES.md", "THIRD_PARTY_LICENSES.txt",
        ]
        source = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in public_docs).casefold()
        for withdrawn in [
            "inv-sla-10",
            "100% zero-copyleft",
            "zero-egress governance",
            "level 1 sbom",
            "5-business-day triage commitment",
            "within 48 hours",
        ]:
            self.assertNotIn(withdrawn, source)

if __name__ == "__main__":
    unittest.main()
