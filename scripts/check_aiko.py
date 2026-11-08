#!/usr/bin/env python3
"""AIKO report validator and hold-only release gate.

No external dependencies. This tool checks declared metadata, not the authenticity
of human identities, approvals, test logs or referenced URLs. External review
protection must enforce those independently.

Exit codes:
  0: schema/semantic lint passed (--mode lint), or gate conditions met (--mode gate)
  1: valid report but release held by missing/failed/expired checks (--mode gate)
  2: invalid report or input
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

SCHEMA_VERSION = "0.1.0"
REVIEW_CLASSES = {
    "reversible_private",
    "reversible_public",
    "irreversible_or_load_bearing",
    "legally_or_contractually_operative",
}
ESCALATION_FLAGS = {"authentication", "payments", "personal_data"}
HIGH_CLASSES = {"irreversible_or_load_bearing", "legally_or_contractually_operative"}
RISK_FLAGS = ESCALATION_FLAGS | {"other"}


def require_obj(value, label, errors):
    if not isinstance(value, dict):
        errors.append(f"{label}: expected object")
        return {}
    return value


def require_list(value, label, errors):
    if not isinstance(value, list):
        errors.append(f"{label}: expected list")
        return []
    return value


def only_keys(obj, allowed, label, errors):
    for key in obj.keys() - set(allowed):
        errors.append(f"{label}: unknown field {key!r}")


def required_str(obj, key, label, errors):
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}.{key}: required nonempty string")
        return ""
    return value.strip()


def date_str(obj, key, label, errors, required=True):
    value = obj.get(key)
    if (value is None or value == "") and not required:
        return None
    value = required_str(obj, key, label, errors)
    if not value:
        return None
    try:
        if len(value) != 10:
            raise ValueError("not canonical")
        parsed = dt.date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError("not canonical")
        return parsed
    except ValueError:
        errors.append(f"{label}.{key}: expected YYYY-MM-DD")
        return None


def choice(obj, key, allowed, label, errors):
    value = required_str(obj, key, label, errors)
    if value and value not in allowed:
        errors.append(f"{label}.{key}: expected one of {', '.join(sorted(allowed))}")
    return value


def unique_id(item, seen, label, errors):
    ident = required_str(item, "id", label, errors)
    if ident in seen and ident:
        errors.append(f"{label}.id: duplicate id {ident!r}")
    seen.add(ident)
    return ident


def evaluate(report, today):
    """Return (invalid_fields, holds, stage). Stage is computed, never supplied."""
    errors = []
    holds = []
    root = require_obj(report, "report", errors)
    only_keys(root, {"schema_version", "report_id", "created_on", "artefact", "assess", "inspect", "keep_accountable", "observe"}, "report", errors)
    if root.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version: expected {SCHEMA_VERSION}")
    required_str(root, "report_id", "report", errors)
    created = date_str(root, "created_on", "report", errors)
    if created and created > today:
        holds.append("report created_on is in the future")
    artefact = require_obj(root.get("artefact"), "artefact", errors)
    only_keys(artefact, {"id", "revision", "location", "type", "diff_ref", "use_on"}, "artefact", errors)
    for key in ("id", "revision", "location", "type", "diff_ref"):
        required_str(artefact, key, "artefact", errors)
    use_on = date_str(artefact, "use_on", "artefact", errors, required=False)
    if use_on and use_on < today:
        holds.append("planned use date is in the past; refresh the report before a new use")
    assess = require_obj(root.get("assess"), "assess", errors)
    only_keys(assess, {"context_ref", "source_of_truth", "data_classification", "trust_boundaries", "review_class", "risk_flags", "review_budget_minutes"}, "assess", errors)
    for key in ("context_ref", "trust_boundaries"):
        required_str(assess, key, "assess", errors)
    anchors = require_list(assess.get("source_of_truth"), "assess.source_of_truth", errors)
    if not anchors:
        errors.append("assess.source_of_truth: at least one source required")
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, str) or not anchor.strip():
            errors.append(f"assess.source_of_truth[{index}]: expected nonempty string")
    choice(assess, "data_classification", {"public", "internal", "confidential"}, "assess", errors)
    review_class = choice(assess, "review_class", REVIEW_CLASSES, "assess", errors)
    risk_flags = require_list(assess.get("risk_flags"), "assess.risk_flags", errors)
    if len(risk_flags) != len(set(str(f) for f in risk_flags)):
        errors.append("assess.risk_flags: duplicate entries")
    for flag in risk_flags:
        if not isinstance(flag, str) or flag not in RISK_FLAGS:
            errors.append(f"assess.risk_flags: unsupported flag {flag!r}")
    budget = assess.get("review_budget_minutes")
    if type(budget) is not int or budget <= 0:
        errors.append("assess.review_budget_minutes: expected positive integer")

    inspect = require_obj(root.get("inspect"), "inspect", errors)
    only_keys(inspect, {"automated_checks", "claims", "verification_surface_ref"}, "inspect", errors)
    checks = require_list(inspect.get("automated_checks"), "inspect.automated_checks", errors)
    if not checks:
        holds.append("no scripted check supplied")
    ids = set()
    for index, value in enumerate(checks):
        label = f"inspect.automated_checks[{index}]"
        item = require_obj(value, label, errors)
        only_keys(item, {"id", "tool", "status", "evidence_ref", "checked_on"}, label, errors)
        unique_id(item, ids, label, errors)
        required_str(item, "tool", label, errors)
        state = choice(item, "status", {"passed", "failed", "not_run"}, label, errors)
        if state != "passed":
            holds.append(f"{label}: scripted check did not pass")
        if state == "passed":
            required_str(item, "evidence_ref", label, errors)
            checked = date_str(item, "checked_on", label, errors)
            if checked and checked > today:
                holds.append(f"{label}: check date is in the future")
        else:
            date_str(item, "checked_on", label, errors, required=False)
    claims = require_list(inspect.get("claims"), "inspect.claims", errors)
    if not claims:
        holds.append("no claims instrumented")
    ids = set()
    for index, value in enumerate(claims):
        label = f"inspect.claims[{index}]"
        item = require_obj(value, label, errors)
        only_keys(item, {"id", "statement", "source_ref", "status", "evidence_ref", "checked_on"}, label, errors)
        unique_id(item, ids, label, errors)
        required_str(item, "statement", label, errors)
        required_str(item, "source_ref", label, errors)
        state = choice(item, "status", {"verified", "unverified"}, label, errors)
        if state == "unverified":
            holds.append(f"{label}: claim unverified")
        elif state == "verified":
            required_str(item, "evidence_ref", label, errors)
            checked = date_str(item, "checked_on", label, errors)
            if checked and checked > today:
                holds.append(f"{label}: verification date is in the future")
    required_str(inspect, "verification_surface_ref", "inspect", errors)

    keep = require_obj(root.get("keep_accountable"), "keep_accountable", errors)
    only_keys(keep, {"owner", "human_reviews", "open_items"}, "keep_accountable", errors)
    required_str(keep, "owner", "keep_accountable", errors)
    reviews = require_list(keep.get("human_reviews"), "keep_accountable.human_reviews", errors)
    required_roles = {"primary"}
    if review_class in HIGH_CLASSES or any(isinstance(f, str) and f in ESCALATION_FLAGS for f in risk_flags):
        required_roles.add("independent")
    seen_roles = set()
    people = {}
    for index, value in enumerate(reviews):
        label = f"keep_accountable.human_reviews[{index}]"
        item = require_obj(value, label, errors)
        only_keys(item, {"role", "reviewer", "decision", "reviewed_on", "evidence_ref"}, label, errors)
        role = choice(item, "role", {"primary", "independent"}, label, errors)
        if role in seen_roles:
            errors.append(f"{label}.role: duplicate {role!r} review role")
        seen_roles.add(role)
        people[role] = required_str(item, "reviewer", label, errors)
        decision = choice(item, "decision", {"pending", "approved", "rejected"}, label, errors)
        if decision == "approved":
            required_str(item, "evidence_ref", label, errors)
            checked = date_str(item, "reviewed_on", label, errors)
            if checked and checked > today:
                holds.append(f"{label}: review is dated in the future")
        elif decision == "rejected":
            holds.append(f"{label}: review rejected")
        else:
            holds.append(f"{label}: human review pending")
            date_str(item, "reviewed_on", label, errors, required=False)
    for role in required_roles - seen_roles:
        holds.append(f"missing {role} human review")
    if (people.get("primary") and people.get("independent")
            and people["primary"].casefold() == people["independent"].casefold()):
        errors.append("independent reviewer must differ from primary reviewer")
    debts = require_list(keep.get("open_items"), "keep_accountable.open_items", errors)
    ids = set()
    for index, value in enumerate(debts):
        label = f"keep_accountable.open_items[{index}]"
        item = require_obj(value, label, errors)
        only_keys(item, {"id", "description", "owner", "status", "expiry_on", "decision_ref", "accepted_by"}, label, errors)
        unique_id(item, ids, label, errors)
        required_str(item, "description", label, errors)
        required_str(item, "owner", label, errors)
        state = choice(item, "status", {"open", "accepted", "resolved"}, label, errors)
        expiry = date_str(item, "expiry_on", label, errors, required=state != "resolved")
        if state == "open":
            holds.append(f"{label}: unresolved open item")
        if state == "accepted":
            required_str(item, "decision_ref", label, errors)
            required_str(item, "accepted_by", label, errors)
        if state != "resolved" and expiry and expiry <= today:
            holds.append(f"{label}: debt expired")

    observe = require_obj(root.get("observe"), "observe", errors)
    only_keys(observe, {"verifications"}, "observe", errors)
    observations = require_list(observe.get("verifications"), "observe.verifications", errors)
    ids = set()
    for index, value in enumerate(observations):
        label = f"observe.verifications[{index}]"
        item = require_obj(value, label, errors)
        only_keys(item, {"id", "claim_ref", "checked_on", "recheck_by", "owner", "status", "schedule_ref"}, label, errors)
        unique_id(item, ids, label, errors)
        required_str(item, "claim_ref", label, errors)
        required_str(item, "owner", label, errors)
        required_str(item, "schedule_ref", label, errors)
        state = choice(item, "status", {"current", "changed", "withdrawn"}, label, errors)
        checked = date_str(item, "checked_on", label, errors)
        due = date_str(item, "recheck_by", label, errors)
        if checked and checked > today:
            holds.append(f"{label}: observation checked in the future")
        if checked and due and due <= checked:
            errors.append(f"{label}: recheck_by must be after checked_on")
        if state == "changed":
            holds.append(f"{label}: observation changed")
        if state == "withdrawn":
            holds.append(f"{label}: observation withdrawn")
        if due and due <= today:
            holds.append(f"{label}: verification expired or due today")
        if use_on and due and due >= use_on:
            holds.append(f"{label}: re-check not before planned use date")

    stage = "INVALID" if errors else ("BLOCKED" if holds else "REPORTED_APPROVED")
    return errors, holds, stage


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="AIKO JSON report")
    parser.add_argument("--mode", choices=("lint", "gate"), default="gate")
    parser.add_argument("--today", help="UTC date override, YYYY-MM-DD; for repeatable testing")
    parser.add_argument("--output", choices=("text", "json", "markdown"), default="text")
    args = parser.parse_args(argv)
    try:
        today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    errors, holds, stage = evaluate(report, today)
    code = 2 if errors else (1 if args.mode == "gate" and holds else 0)
    if args.output == "markdown":
        # Do not attempt to render nested sections of a malformed report.
        if errors:
            print("# SIEVE Report — AIKO\n\n**Status:** INVALID\n")
            print("## Invalid report\n")
            for reason in errors:
                print(f"- {reason}")
            return code
        a, assessed = report["artefact"], report["assess"]
        inspected, kept, observed = report["inspect"], report["keep_accountable"], report["observe"]
        def fmt(value):
            return str(value if value is not None else "—").replace("\n", " ").replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")
        print("# SIEVE Report — AIKO")
        print(f"\n**Status:** {stage}  ")
        print(f"**Report:** {fmt(report['report_id'])}  ")
        print(f"**Artefact:** {fmt(a['id'])} @ {fmt(a['revision'])}  ")
        print(f"**Location:** {fmt(a['location'])}  ")
        print(f"**Diff:** {fmt(a['diff_ref'])}  ")
        print(f"**As of:** {today.isoformat()}\n")
        print("## A · Assess\n")
        print(f"- Context: {fmt(assessed['context_ref'])}")
        for source in assessed["source_of_truth"]:
            print(f"- Source of truth: {fmt(source)}")
        print(f"- Data classification: {fmt(assessed['data_classification'])}")
        print(f"- Trust boundaries: {fmt(assessed['trust_boundaries'])}")
        print(f"- Review class: {fmt(assessed['review_class'])}")
        print(f"- Risk flags: {fmt(', '.join(assessed['risk_flags']) or 'none')}")
        print(f"- Review budget (minutes): {fmt(assessed['review_budget_minutes'])}")
        print("\n## I · Inspect\n")
        if not inspected["automated_checks"]:
            print("- No automated checks recorded")
        for c in inspected["automated_checks"]:
            print(f"- Check {fmt(c['id'])}: **{fmt(c['status'])}**, tool: {fmt(c['tool'])}, checked: {fmt(c.get('checked_on'))}, evidence: {fmt(c.get('evidence_ref'))}")
        for c in inspected["claims"]:
            print(f"- Claim {fmt(c['id'])}: {fmt(c['statement'])} — **{fmt(c['status'])}**; source: {fmt(c['source_ref'])}; checked: {fmt(c.get('checked_on'))}; evidence: {fmt(c.get('evidence_ref'))}")
        print(f"- Verification surface: {fmt(inspected['verification_surface_ref'])}")
        print("\n## K · Keep accountable\n")
        print(f"- Accountable owner: {fmt(kept['owner'])}")
        for r in kept["human_reviews"]:
            print(f"- {fmt(r['role'])} reviewer: {fmt(r['reviewer'])}, **{fmt(r['decision'])}**; reviewed: {fmt(r.get('reviewed_on'))}; evidence: {fmt(r.get('evidence_ref'))}")
        if not kept['open_items']:
            print("- No tracked open items")
        for d in kept['open_items']:
            print(f"- Debt {fmt(d['id'])}: {fmt(d['description'])}; **{fmt(d['status'])}**; owner: {fmt(d['owner'])}; expiry: {fmt(d.get('expiry_on'))}; decision: {fmt(d.get('decision_ref'))}")
        print("\n## O · Observe\n")
        if not observed['verifications']:
            print("- No perishable observations recorded")
        for v in observed['verifications']:
            print(f"- {fmt(v['id'])}: claim {fmt(v['claim_ref'])}; **{fmt(v['status'])}**; checked {fmt(v['checked_on'])}; recheck by {fmt(v['recheck_by'])}; owner {fmt(v['owner'])}; schedule {fmt(v['schedule_ref'])}")
        print("\n## Release holds\n")
        for h in holds:
            print(f"- {fmt(h)}")
        if not holds:
            print("- No metadata holds detected; authenticate each approval and underlying evidence independently.")
        print("\n> AIKO metadata and human identities are not independently authenticated. This report is not approval or compliance attestation.")
    elif args.output == "json":
        print(json.dumps({"status": stage, "mode": args.mode, "invalid": errors,
                          "holds": holds, "release_gate_passed": code == 0 and args.mode == "gate"}, indent=2))
    else:
        print(f"AIKO {stage} | mode={args.mode} | invalid={len(errors)} | holds={len(holds)}")
        for reason in errors:
            print(f"INVALID {reason}")
        for reason in holds:
            print(f"HOLD {reason}")
        if stage == "REPORTED_APPROVED":
            print("NOTE: reviewer identity, referenced evidence and approvals are NOT independently authenticated.")
        if args.mode == "lint" and holds:
            print("NOTE: lint success is NOT release approval; run --mode gate before release.")
    return code


if __name__ == "__main__":
    sys.exit(main())
