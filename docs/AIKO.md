# AIKO — SIEVE Report Protocol

**Status:** experimental extension · **Version:** 0.1.0

AIKO is a reporting process for SIEVE, not a new law or a replacement for DAHNIN.
It turns the DAHNIN loop outputs into one checkable surface for the SIEVE
portfolio and records why a human may or may not stand behind the artefact.

**AIKO = Assess · Inspect · Keep accountable · Observe.**

| Step | Question | Source in SIEVE | Report section |
|---|---|---|---|
| **A — Assess** | What are we making, with what authority and consequence? | D · Document, A · Anchor, S · Size, E · Escalate | `assess` |
| **I — Inspect** | Which claims and scripted checks have actual evidence? | H · Hold, N · Narrow, I · Inspect, I · Instrument, V · Verify | `inspect` |
| **K — Keep accountable** | Who owns the decision, and who separately reviewed it? | I · Inspect twice, N · Name, E · Escalate | `keep_accountable` |
| **O — Observe** | Which checks can expire, change or require renewed review? | E · Expire | `observe` |

## Operating sequence

1. **Before generation (Assess):** cite a context document, authoritative source(s),
   classification and trust boundaries. Choose the SIEVE consequence-based review
   class *before* production. Record a measured or allocated review budget.
2. **Before human review (Inspect):** attach a scripted-check result, a stable
   reference to every material claim, and one untruncated review surface.
   `passed` and `verified` require dates and references to actual evidence.
   Do not create fictitious tests, citations, logs or evidence paths.
3. **Before use (Keep accountable):** record a named primary human reviewer.
   For high consequence classes or authentication/payment/personal-data changes,
   record a second, different independent human reviewer. A missing, pending
   or rejected review holds the artefact. Record any accepted security debt
   with a named approver, decision reference and future expiry.
4. **Through use (Observe):** for every perishable observation, store checked
   date, re-check date, named owner and a reference to an actionable schedule.
   Re-checking must be wired into a job that can hold a release, not just written
   in a document. Align entries with `templates/recheck-schedule.yml` and
   `scripts/check_rechecks.py` (the existing schedule gate).

## Report format

- Template: [`../templates/aiko-report.json`](../templates/aiko-report.json)
- Machine-readable schema: [`../schemas/aiko-report.schema.json`](../schemas/aiko-report.schema.json)
- Standard library validator: [`../scripts/check_aiko.py`](../scripts/check_aiko.py)

All dates use ISO 8601 calendar dates (`YYYY-MM-DD`). `created_on` is the
report creation date; `checked_on` and `reviewed_on` are dates of actual actions,
not dates predicted by an AI. `artefact.revision` should pin the reviewed
revision; a changed revision requires renewed review. `evidence_ref` should
point to a durable, retrievable record (e.g., CI run, review URL, test log).
Do not place credentials, personal data or private logs into public reports.

`artefact.diff_ref` points to the bounded, reviewable change or diff. For
non-code artefacts it may identify a document revision comparison.

The four `review_class` values correspond to the review classes in SIEVE Part 2:
`reversible_private`, `reversible_public`, `irreversible_or_load_bearing`,
`legally_or_contractually_operative`. Additional `risk_flags` are
`authentication`, `payments`, `personal_data`, `other`.

## Use

```sh
# Start a new report by copying the template, then replace placeholders.
cp templates/aiko-report.json aiko-report.json

# Check form/semantic consistency without approving a release.
python3 scripts/check_aiko.py aiko-report.json --mode lint

# Hold on any missing, rejected, or expired check/approval.
python3 scripts/check_aiko.py aiko-report.json --mode gate

# Machine-readable result for a CI pipeline.
python3 scripts/check_aiko.py aiko-report.json --mode gate --output json

# Render a single human-readable verification surface.
python3 scripts/check_aiko.py aiko-report.json --mode gate --output markdown > AIKO-REPORT.md

# Deterministic verification for tests or an audit of a historic report.
python3 scripts/check_aiko.py aiko-report.json --mode gate --today 2026-11-07
```

**Exit codes:** `0` = lint success or (in gate mode) all declared conditions
met; `1` = gate held; `2` = invalid report/input. `lint` passing is never
permission to release. `REPORTED_APPROVED` means only that the *report says*
approvals and checks were completed. It is not a security attestation.

## Required external enforcement

The validator can validate structure, dates, explicit attestations, reviewer
separation and expiry. It **cannot prove** that an apparent human approval is
human, that a referenced test actually ran, that a URL is truthful, or that
an unchanged `artefact.revision` still describes the code under release.

For a meaningful hold, configure external controls on the protected branch or
release environment: required reviews/independent CODEOWNERS where relevant,
identity-backed approvals, immutable CI evidence, revision binding and
required gate checks. Use those native controls to verify the human decision.
**Never** give an AI the permission to write its own accepted review record
and interpret that record as independently authenticated.

AIKO only **holds**; it does not deploy, approve, publish or assert compliance.
This protocol is a practical evidence format, not a certification.

## Scope in version 0.1

The shipped workflow runs report lint and unit tests on a PR. It does not yet
bind GitHub's authenticated review API to the report or block a release without
that external binding. Projects can add `--mode gate` as a release check once
they have defined how approval evidence is verified independently.

## Relationship to other SIEVE artefacts

- `context_ref` links to `templates/context-document.md` style context.
- Claims and their sources extend `templates/artefact-header.md`.
- `open_items` extends `templates/debt-register.md`.
- The observational `verifications` section links to the existing
  `recheck-schedule.yml`; AIKO does not replace that scheduled mechanism.
- Reports are one review surface, not a substitute for examining the actual
  artefact and the trust boundary.
