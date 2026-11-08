"""Exercise the portable examples against the actual AIKO CLI."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "sieve"


class SieveSkillTests(unittest.TestCase):
    def run_report(self, path, today, output="json"):
        return subprocess.run([sys.executable, str(ROOT / "scripts/check_aiko.py"),
            str(path), "--mode", "gate", "--today", today, "--output", output],
            capture_output=True, text=True)

    def test_examples_have_expected_gate_results(self):
        for name, code, status in (("pending", 1, "BLOCKED"),
                ("declared-conditions-met", 0, "REPORTED_APPROVED"),
                ("expired", 1, "BLOCKED")):
            with self.subTest(name=name):
                path = SKILL / "examples" / (name + ".json")
                result = self.run_report(path, "2026-11-07")
                self.assertEqual(result.returncode, code, result.stderr)
                payload = json.loads(result.stdout)
                self.assertEqual(payload["status"], status)
                self.assertEqual(payload["release_gate_passed"], code == 0)
                rendered = self.run_report(path, "2026-11-07", "markdown")
                saved = (SKILL / "examples" / (name + ".md")).read_text()
                self.assertEqual(saved.split("\n\n", 1)[1],
                    "\n".join(line.rstrip() for line in rendered.stdout.splitlines()) + "\n")

    def test_approval_example_expires_without_new_evidence(self):
        path = SKILL / "examples" / "declared-conditions-met.json"
        result = self.run_report(path, "2026-11-18")
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["release_gate_passed"])

    def test_portable_starter_matches_canonical_template(self):
        self.assertEqual(json.loads((SKILL / "assets/aiko-report.json").read_text()),
                         json.loads((ROOT / "templates/aiko-report.json").read_text()))
