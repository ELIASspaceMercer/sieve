"""Tests for AIKO metadata validation and hold-only semantics."""

from __future__ import annotations

import copy
import datetime as dt
import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_aiko.py"
spec = importlib.util.spec_from_file_location("check_aiko", SCRIPT)
aiko = importlib.util.module_from_spec(spec)
spec.loader.exec_module(aiko)
TODAY = dt.date(2026, 11, 7)


def approved_fixture():
    return {
        "schema_version": "0.1.0", "report_id": "synthetic-fixture", "created_on": "2026-11-06",
        "artefact": {"id": "example", "revision": "test-sha", "location": "examples/example.md",
                     "type": "document", "diff_ref": "synthetic://diff", "use_on": "2026-11-20"},
        "assess": {"context_ref": "examples/context.md", "source_of_truth": ["examples/spec.md"],
                   "data_classification": "public", "trust_boundaries": "Synthetic fixture only",
                   "review_class": "reversible_private", "risk_flags": [], "review_budget_minutes": 15},
        "inspect": {"automated_checks": [
            {"id": "unit-tests", "tool": "unittest", "status": "passed",
             "checked_on": "2026-11-06", "evidence_ref": "synthetic://unit-test-log"}],
            "claims": [{"id": "claim-1", "statement": "Fixture result", "source_ref": "synthetic://spec",
                        "status": "verified", "checked_on": "2026-11-06", "evidence_ref": "synthetic://evidence"}],
            "verification_surface_ref": "synthetic://contact-sheet"},
        "keep_accountable": {"owner": "synthetic-owner", "human_reviews": [
            {"role": "primary", "reviewer": "synthetic-reviewer-1", "decision": "approved",
             "reviewed_on": "2026-11-06", "evidence_ref": "synthetic://human-review"}],
             "open_items": []},
        "observe": {"verifications": [
            {"id": "check-1", "claim_ref": "claim-1", "checked_on": "2026-11-06",
             "recheck_by": "2026-11-18", "owner": "synthetic-owner", "status": "current",
             "schedule_ref": "synthetic://scheduled-job"}]},
    }


class AikoTests(unittest.TestCase):
    def check(self, report):
        return aiko.evaluate(copy.deepcopy(report), TODAY)

    def test_synthetic_approved_report_meets_declared_conditions(self):
        errors, holds, state = self.check(approved_fixture())
        self.assertEqual((errors, holds, state), ([], [], "REPORTED_APPROVED"))

    def test_human_pending_holds(self):
        report = approved_fixture()
        report["keep_accountable"]["human_reviews"][0]["decision"] = "pending"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_missing_scripted_evidence_invalid(self):
        report = approved_fixture()
        del report["inspect"]["automated_checks"][0]["evidence_ref"]
        self.assertEqual(self.check(report)[2], "INVALID")

    def test_missing_scripted_check_holds(self):
        report = approved_fixture()
        report["inspect"]["automated_checks"] = []
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_failed_scripted_check_holds(self):
        report = approved_fixture()
        report["inspect"]["automated_checks"][0]["status"] = "failed"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_high_risk_needs_independent_reviewer(self):
        report = approved_fixture()
        report["assess"]["risk_flags"] = ["authentication"]
        self.assertIn("missing independent human review", self.check(report)[1])

    def test_non_string_risk_flags_are_invalid(self):
        for flag in ({}, [], None, 1):
            with self.subTest(flag=flag):
                report = approved_fixture()
                report["assess"]["risk_flags"] = [flag]
                errors, _, state = self.check(report)
                self.assertEqual(state, "INVALID")
                self.assertTrue(any("unsupported flag" in error for error in errors))

    def test_high_class_needs_independent_reviewer(self):
        report = approved_fixture()
        report["assess"]["review_class"] = "irreversible_or_load_bearing"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_independent_must_be_distinct(self):
        report = approved_fixture()
        report["assess"]["risk_flags"] = ["payments"]
        extra = copy.deepcopy(report["keep_accountable"]["human_reviews"][0])
        extra["role"] = "independent"
        report["keep_accountable"]["human_reviews"].append(extra)
        self.assertEqual(self.check(report)[2], "INVALID")

    def test_distinct_independent_satisfies_high_risk(self):
        report = approved_fixture()
        report["assess"]["review_class"] = "legally_or_contractually_operative"
        extra = copy.deepcopy(report["keep_accountable"]["human_reviews"][0])
        extra.update({"role": "independent", "reviewer": "synthetic-reviewer-2"})
        report["keep_accountable"]["human_reviews"].append(extra)
        self.assertEqual(self.check(report)[2], "REPORTED_APPROVED")

    def test_recheck_due_today_holds(self):
        report = approved_fixture()
        report["observe"]["verifications"][0]["recheck_by"] = "2026-11-07"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_recheck_after_use_holds(self):
        report = approved_fixture()
        report["observe"]["verifications"][0]["recheck_by"] = "2026-11-20"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_observation_changed_holds(self):
        report = approved_fixture()
        report["observe"]["verifications"][0]["status"] = "changed"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_open_debt_holds(self):
        report = approved_fixture()
        report["keep_accountable"]["open_items"] = [{"id": "debt-1", "description": "Mocked login",
            "owner": "synthetic-owner", "status": "open", "expiry_on": "2026-12-01"}]
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_accepted_debt_needs_decision_and_expiry(self):
        report = approved_fixture()
        report["keep_accountable"]["open_items"] = [{"id": "debt-1", "description": "Temporary waiver",
            "owner": "synthetic-owner", "status": "accepted", "expiry_on": "2026-12-01"}]
        self.assertEqual(self.check(report)[2], "INVALID")
        report["keep_accountable"]["open_items"][0].update(
            {"accepted_by": "synthetic-human", "decision_ref": "synthetic://waiver"})
        self.assertEqual(self.check(report)[2], "REPORTED_APPROVED")
        report["keep_accountable"]["open_items"][0]["expiry_on"] = "2026-11-01"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_invalid_date(self):
        report = approved_fixture()
        report["created_on"] = "not-a-date"
        self.assertEqual(self.check(report)[2], "INVALID")

    def test_duplicate_claim_id(self):
        report = approved_fixture()
        report["inspect"]["claims"].append(copy.deepcopy(report["inspect"]["claims"][0]))
        self.assertEqual(self.check(report)[2], "INVALID")

    def test_unknown_root_field_invalid(self):
        report = approved_fixture()
        report["self_approved"] = True
        self.assertEqual(self.check(report)[2], "INVALID")

    def test_date_in_past_holds_for_new_use(self):
        report = approved_fixture()
        report["artefact"]["use_on"] = "2026-11-06"
        self.assertEqual(self.check(report)[2], "BLOCKED")

    def test_json_output_does_not_approve_pending(self):
        template = ROOT / "templates" / "aiko-report.json"
        result = subprocess.run([sys.executable, str(SCRIPT), str(template), "--mode", "gate",
                                 "--output", "json", "--today", "2026-11-07"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["release_gate_passed"])

    def test_markdown_report_reports_holds(self):
        template = ROOT / "templates" / "aiko-report.json"
        result = subprocess.run([sys.executable, str(SCRIPT), str(template), "--mode", "gate",
                                 "--output", "markdown", "--today", "2026-11-07"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("## Release holds", result.stdout)
        self.assertIn("human review pending", result.stdout)

    def test_template_lints_but_gate_holds(self):
        template = ROOT / "templates" / "aiko-report.json"
        lint = subprocess.run([sys.executable, str(SCRIPT), str(template), "--mode", "lint",
                               "--today", "2026-11-07"], capture_output=True, text=True)
        gate = subprocess.run([sys.executable, str(SCRIPT), str(template), "--mode", "gate",
                               "--today", "2026-11-07"], capture_output=True, text=True)
        self.assertEqual(lint.returncode, 0, lint.stdout + lint.stderr)
        self.assertEqual(gate.returncode, 1, gate.stdout + gate.stderr)
        self.assertIn("BLOCKED", gate.stdout)

    def test_optional_fields_validate_when_present(self):
        cases = [
            (("artefact",), "use_on", ""),
            (("artefact",), "use_on", None),
            (("artefact",), "use_on", " 2026-11-20 "),
            (("inspect", "claims", 0), "checked_on", "not-a-date"),
            (("inspect", "claims", 0), "evidence_ref", {}),
            (("inspect", "automated_checks", 0), "evidence_ref", ""),
            (("keep_accountable", "human_reviews", 0), "reviewed_on", "not-a-date"),
            (("keep_accountable", "human_reviews", 0), "evidence_ref", None),
            (("keep_accountable", "open_items", 0), "decision_ref", []),
            (("keep_accountable", "open_items", 0), "accepted_by", 42),
        ]
        for path, key, value in cases:
            with self.subTest(path=path, key=key, value=value):
                report = approved_fixture()
                report["inspect"]["claims"][0]["status"] = "unverified"
                report["inspect"]["automated_checks"][0]["status"] = "not_run"
                report["keep_accountable"]["human_reviews"][0]["decision"] = "rejected"
                report["keep_accountable"]["open_items"] = [{
                    "id": "resolved", "description": "Fixed", "owner": "owner", "status": "resolved"}]
                item = report
                for segment in path:
                    item = item[segment]
                item[key] = value
                self.assertEqual(self.check(report)[2], "INVALID")

    def test_optional_fields_can_be_omitted(self):
        report = approved_fixture()
        del report["artefact"]["use_on"]
        report["keep_accountable"]["open_items"] = [{
            "id": "resolved", "description": "Fixed", "owner": "owner", "status": "resolved"}]
        self.assertEqual(self.check(report)[2], "REPORTED_APPROVED")

    def test_enum_whitespace_is_invalid(self):
        report = approved_fixture()
        report["keep_accountable"]["human_reviews"][0]["decision"] = " approved "
        self.assertEqual(self.check(report)[2], "INVALID")

    def test_observation_must_reference_a_report_claim(self):
        report = approved_fixture()
        report["observe"]["verifications"][0]["claim_ref"] = "missing-claim"
        errors, _, state = self.check(report)
        self.assertEqual(state, "INVALID")
        self.assertTrue(any("unknown claim id" in error for error in errors))

    def test_invalid_reference_cannot_pass_cli_gate(self):
        import tempfile
        report = approved_fixture()
        report["observe"]["verifications"][0]["claim_ref"] = "missing-claim"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(report))
            result = subprocess.run([sys.executable, str(SCRIPT), str(path),
                "--today", "2026-11-07", "--output", "json"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["release_gate_passed"])

    def test_schema_json_parses(self):
        schema = json.loads((ROOT / "schemas" / "aiko-report.schema.json").read_text())
        self.assertEqual(schema["properties"]["schema_version"]["const"], "0.1.0")


if __name__ == "__main__":
    unittest.main()
