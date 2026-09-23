"""Contract and hygiene test suite for dev-bricks/zombie-killer-tray.

Validates repository metadata, CI workflows, packaging invariants,
multi-host lock defense, SBOM recency, 18-point bilingual documentation parity,
dual Mermaid diagrams, target personas, and comparative matrix.
"""
from __future__ import annotations

from pathlib import Path
import re
import tomllib
import unittest

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

    def test_gitignore_multihost_and_lock_defense(self):
        gitignore = ROOT / ".gitignore"
        self.assertTrue(gitignore.is_file(), ".gitignore must exist")
        content = gitignore.read_text(encoding="utf-8")

        required_patterns = [
            "*conflicted copy*",
            "* (Kopie)*",
            "* (Copy)*",
            "*-WORKSTATION*",
            "*-ASUS*",
            "*-LAPTOP*",
            "LOCK",
            "LOCK.*",
            "LOCK.user.*",
            "LOCK.until.*",
            "LOCK.condition.*",
            "LOCK.permissions.json",
            "uv.lock",
            "!package-lock.json",
            "zombie_events.jsonl",
            "zombie_tray.log",
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

        urls = project.get("urls", {})
        for required_url_key in [
            "Homepage",
            "Documentation",
            "Repository",
            "Issues",
            "Security",
            "Notice",
            "Third-Party Licenses",
            "Marketing Log",
            "LLM Ready",
            "Parent Organization",
            "Umbrella Ecosystem",
        ]:
            self.assertIn(required_url_key, urls, f"Missing project URL key: {required_url_key}")

        keywords = project.get("keywords", [])
        self.assertEqual(len(keywords), 20, "Must have exactly 20 discoverability keywords")

        self.assertIn("tool", data)
        self.assertIn("pytest", data["tool"])
        self.assertIn("ruff", data["tool"])

    def test_third_party_licenses_audit_recency_and_invariants(self):
        sbom = ROOT / "THIRD_PARTY_LICENSES.md"
        self.assertTrue(sbom.is_file(), "THIRD_PARTY_LICENSES.md must exist")
        text = sbom.read_text(encoding="utf-8")

        self.assertTrue(
            "Audited:** 2026-09-23" in text or "Audited:** 2026-09-22" in text,
            "THIRD_PARTY_LICENSES.md audit date must be recent",
        )
        self.assertIn("[NOTICE](NOTICE)", text)
        self.assertIn("psutil", text)
        self.assertIn("BSD-3-Clause", text)
        self.assertIn("Zero-Egress", text)
        self.assertIn("RunAsInvoker", text)

        expected_invariants = [
            "INV-LOCAL-01",
            "INV-SEC-02",
            "INV-PARENT-03",
            "INV-STABLE-04",
            "INV-HANDLE-05",
            "INV-ALLOW-06",
            "INV-NOTREE-07",
            "INV-AUDIT-08",
            "INV-AGE-09",
            "INV-SLA-10",
        ]
        for inv_code in expected_invariants:
            self.assertIn(inv_code, text, f"Missing invariant code: {inv_code}")

    def test_security_sla_and_statutory_disclaimer(self):
        security = ROOT / "SECURITY.md"
        self.assertTrue(security.is_file(), "SECURITY.md must exist")
        text = security.read_text(encoding="utf-8")

        self.assertTrue(
            "48 hours" in text or "48-hour" in text, "Missing 48h response SLA in SECURITY.md"
        )
        self.assertIn("5 business days", text)
        self.assertIn("security@dev-bricks.org", text)
        self.assertIn("security@open-bricks.org", text)
        self.assertIn("521 BGB", text)

    def test_documentation_18_point_bilingual_parity(self):
        readme_en = ROOT / "README.md"
        readme_de = ROOT / "README_de.md"
        self.assertTrue(readme_en.is_file(), "README.md must exist")
        self.assertTrue(readme_de.is_file(), "README_de.md must exist")

        en_text = readme_en.read_text(encoding="utf-8")
        de_text = readme_de.read_text(encoding="utf-8")

        # Cross-linking between languages
        self.assertIn("README_de.md", en_text)
        self.assertIn("README.md", de_text)

        # 18-Point section number check in both documents
        for i in range(1, 19):
            prefix = f"## {i}. "
            self.assertIn(prefix, en_text, f"README.md missing section header prefix '{prefix}'")
            self.assertIn(prefix, de_text, f"README_de.md missing section header prefix '{prefix}'")

        # Reciprocal anchor aliases (sec-01 to sec-18)
        for i in range(1, 19):
            anchor = f'id="sec-{i:02d}"'
            self.assertIn(anchor, en_text, f"README.md missing anchor {anchor}")
            self.assertIn(anchor, de_text, f"README_de.md missing anchor {anchor}")

        # Governance & Statutory checks
        self.assertIn("521 BGB", en_text)
        self.assertIn("521 BGB", de_text)
        self.assertIn("Attribution-NOTICE-blue.svg", en_text)
        self.assertIn("Attribution-NOTICE-blue.svg", de_text)

        # Invariants INV-LOCAL-01 through INV-SLA-10 in both
        for inv_code in [
            "INV-LOCAL-01",
            "INV-SEC-02",
            "INV-PARENT-03",
            "INV-STABLE-04",
            "INV-HANDLE-05",
            "INV-ALLOW-06",
            "INV-NOTREE-07",
            "INV-AUDIT-08",
            "INV-AGE-09",
            "INV-SLA-10",
        ]:
            self.assertIn(inv_code, en_text, f"README.md missing {inv_code}")
            self.assertIn(inv_code, de_text, f"README_de.md missing {inv_code}")

        # Target Personas
        for persona in ["[PERSONA-01]", "[PERSONA-02]", "[PERSONA-03]", "[PERSONA-04]"]:
            self.assertIn(persona, en_text, f"README.md missing {persona}")
            self.assertIn(persona, de_text, f"README_de.md missing {persona}")

    def test_mermaid_diagrams_syntax_and_hygiene(self):
        readme_en = ROOT / "README.md"
        readme_de = ROOT / "README_de.md"

        for doc_path in [readme_en, readme_de]:
            text = doc_path.read_text(encoding="utf-8")
            self.assertIn("flowchart TD", text, f"{doc_path.name} missing flowchart TD")
            self.assertIn("sequenceDiagram", text, f"{doc_path.name} missing sequenceDiagram")
            self.assertIn("autonumber", text, f"{doc_path.name} sequenceDiagram missing autonumber")

            # Extract sequenceDiagram blocks and assert 0 semicolons
            seq_matches = re.findall(r"```mermaid\s+sequenceDiagram(.*?)```", text, re.DOTALL)
            self.assertTrue(len(seq_matches) >= 1, f"{doc_path.name} missing sequenceDiagram block")
            for block in seq_matches:
                self.assertNotIn(";", block, f"{doc_path.name} sequence diagram must not contain semicolons")

    def test_changelog_has_unreleased_and_frozen_version(self):
        changelog = ROOT / "CHANGELOG.md"
        self.assertTrue(changelog.is_file(), "CHANGELOG.md must exist")
        text = changelog.read_text(encoding="utf-8")

        self.assertIn("## [Unreleased]", text)
        self.assertIn("## 0.1.0", text)
        self.assertNotIn("## 0.2.0", text, "Version bump forbidden in Pfad A/B")

    def test_llms_txt_up_to_date(self):
        llms = ROOT / "llms.txt"
        self.assertTrue(llms.is_file(), "llms.txt must exist")
        text = llms.read_text(encoding="utf-8")

        self.assertIn("Last-checked: 2026-09-23", text)
        self.assertIn("0.1.0", text)
        self.assertIn("521 BGB", text)
        self.assertIn("INV-LOCAL-01", text)
        self.assertIn("INV-SLA-10", text)
        self.assertIn("[PERSONA-01]", text)

    def test_marketing_log_present_and_valid(self):
        mkt = ROOT / "MARKETING-LOG.txt"
        self.assertTrue(mkt.is_file(), "MARKETING-LOG.txt must exist")
        text = mkt.read_text(encoding="utf-8")

        self.assertIn("Target Repo: dev-bricks/zombie-killer-tray", text)
        self.assertIn("ACTION: PFAD_B_MARKETING", text)
        self.assertIn("Version: 0.1.0", text)
        self.assertIn("[PERSONA-01]", text)
        self.assertIn("INV-LOCAL-01", text)


if __name__ == "__main__":
    unittest.main()
