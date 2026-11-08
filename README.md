# SIEVE

**A framework for work where a machine makes the artefacts and a person is answerable for them.**

Generative tools made producing things almost free. They did nothing to the cost of checking them. So the limit on any operation that uses them is no longer how much it can make, but how much one answerable person can stand behind.

SIEVE is built on that one observation. It works at two scales, under the same three laws:

| Scale | Letters | Governs |
|---|---|---|
| **The loop** | **D**ocument · **A**nchor · **H**old · **N**arrow · **I**nspect · **N**ame | One change, one context document, one diff, two pairs of eyes |
| **The portfolio** | **S**ize · **I**nstrument · **E**scalate · **V**erify · **E**xpire | Everything one person is answerable for, and how long each check stays true |

The six loop rules (DAHNIN) make a single artefact safe to stand behind, with a security layer woven into each rule. The five portfolio practices decide which of forty artefacts a week one person can actually stand behind, and keep that true over time. The join is *inspect twice*: a step inside one loop, the constraint on the whole operation across forty.

Read the full framework in **[FRAMEWORK.md](FRAMEWORK.md)**.

## The three laws

1. **Throughput is review-bound.** `shipped = (R / r) × a`. Generation speed is not in the equation. Commission to your reviewing capacity, not your producing capacity.
2. **Iterations are free to make and expensive to accept.** Put a cheap filter between generation and the human. Generate many, show few.
3. **A verification is perishable.** Every check carries a date, and anything observational gets a scheduled re-check before it is used.

And the corollary that costs the most to learn: **a low acceptance rate is a defect in the generator, not a workload for the reviewer.**

## Adopting it in a week

| Day | Do this | Uses |
|---|---|---|
| 1 | Measure r for your two most common artefact classes, and R for the week. Write the commission number down. | [`templates/review-budget.md`](templates/review-budget.md) |
| 2 | Start every new loop from a context document with a security header. No classification, no loop. | [`templates/context-document.md`](templates/context-document.md) |
| 3 | Move your guardrails into the repo as hooks and scanners. | `H · Hold` |
| 4 | Add a debt register and an artefact header to everything that leaves a loop. | [`templates/debt-register.md`](templates/debt-register.md), [`templates/artefact-header.md`](templates/artefact-header.md) |
| 5 | Book re-checks for anything observational: copy the schedule template to the repo root as `recheck-schedule.yml`, then make the `sieve-recheck` workflow a required check so it can hold a publish. | [`templates/recheck-schedule.yml`](templates/recheck-schedule.yml), [`scripts/check_rechecks.py`](scripts/check_rechecks.py) |

Then use the one-page [`CHECKLIST.md`](CHECKLIST.md) on every loop and every week.

## AIKO — SIEVE Report (experimental)

**A**ssess · **I**nspect · **K**eep accountable · **O**bserve turns the
DAHNIN loop's evidence into one human-reviewable SIEVE report. It is a
reporting and hold-only extension, **not** a third set of SIEVE laws.

```sh
cp templates/aiko-report.json aiko-report.json
# Complete the report using real evidence and human review records.
python3 scripts/check_aiko.py aiko-report.json --mode lint
python3 scripts/check_aiko.py aiko-report.json --mode gate
python3 scripts/check_aiko.py aiko-report.json --mode gate --output markdown > AIKO-REPORT.md
```

- [`docs/AIKO.md`](docs/AIKO.md): process, mapping to SIEVE, limitations, and adoption.
- [`schemas/aiko-report.schema.json`](schemas/aiko-report.schema.json): machine-readable report shape.
- [`scripts/check_aiko.py`](scripts/check_aiko.py): standard-library validator; nonzero on missing, failed, or expired gates.
- [`templates/aiko-report.json`](templates/aiko-report.json): explicit pending-review starter template.

An AI-generated report **cannot authenticate its own evidence or human approval**.
Use protected branches, identity-backed review and trusted CI to enforce that
separately. Passing `--mode lint` is never release permission.

## Use SIEVE with your AI assistant

The portable [SIEVE skill](skills/sieve/SKILL.md) guides an assistant through a
bounded DAHNIN loop and an AIKO evidence report, with human approval kept separate.
It includes a Markdown report template, the JSON starter and three complete
synthetic examples (pending review, declared conditions met and expired evidence).

- **Skill-capable assistants:** copy the complete `skills/sieve/` folder into the
  skill location supported by your assistant. Preserve its subfolders.
- **Plain chat:** paste `skills/sieve/SKILL.md`, attach the relevant template and
  reference guide, and describe your task. If attachments are unavailable, paste
  their text. No provider-specific API or automatic tool access is required.
- **Optional validation:** use this repository's Python validator when your
  environment can execute it. The portable skill itself contains instructions
  and examples, not a bundled runtime. Without tools, it reports checks as not run.

Example request: “Use SIEVE to review this draft. Prepare an AIKO report, identify
unsupported claims and keep human approval pending. Do not publish it.”

Native skill discovery and installation differ by assistant; compatibility with
all products or model behavior is not guaranteed. The instructions and Markdown
workflow can be used independently of native skill support.

## What is in this repository

```
FRAMEWORK.md                     The full framework
CHECKLIST.md                     One-page checklist for the loop and the week
templates/
  context-document.md            D · Document, with the security header
  debt-register.md               N · Name, owners and expiry dates
  review-budget.md               S · Size, the commission number
  artefact-header.md             I · Instrument, claims, sources, gaps, dates
  recheck-schedule.yml           E · Expire, the schedule a job reads
  aiko-report.json               AIKO starter report (pending, not approved)
scripts/
  check_rechecks.py              Fails when a re-check is due, so it can hold a publish
  check_aiko.py                  Validates SIEVE Report metadata and holds by default
.github/workflows/
  recheck.yml                    Runs the check daily and before publishing
  aiko.yml                       Runs AIKO lint and unit tests (not a publish gate)
docs/AIKO.md                      AIKO protocol and adoption guide
schemas/aiko-report.schema.json  Report JSON Schema v0.1.0
tests/test_aiko.py               AIKO hold/expiry/escalation tests
CHANGELOG.md
LICENSE
```

## What it is not

SIEVE does not make output correct. It makes the rate at which incorrect output reaches the world a number you have chosen and can see. It is not a compliance framework and no supervisor has endorsed it; where a regime requires human oversight of generated output, running it is evidence you can point at, not the answer to the question.

## Contributing

Critique is welcome, especially evidence from your own operation that confirms or breaks one of the laws. Open an issue with the numbers: what g, r, R and a looked like before and after.

## Licence and citation

Text and templates: [CC BY 4.0](LICENSE). The script and workflow: MIT. You may adapt and reuse with attribution.

> Dahnin, U. (2026). *SIEVE: a framework for work where a machine makes the artefacts and a person is answerable for them.* Version 1.0.
