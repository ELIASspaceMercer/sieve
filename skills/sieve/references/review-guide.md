# Review and reporting guide

## Consequence before volume

| AIKO review class | Human review to arrange |
|---|---|
| `reversible_private` | Proportionate spot check by a named primary reviewer |
| `reversible_public` | One competent read by a named primary reviewer |
| `irreversible_or_load_bearing` | Full read plus a distinct independent reviewer |
| `legally_or_contractually_operative` | Full read, named accountable owner, dated review and a distinct independent reviewer |

Authentication, payments or personal-data changes also require independent
review. Apply the strongest relevant class; document ambiguity. These are
review requirements, not permission to make the consequential change.

SIEVE's two eyes are a scripted check and a human look. For non-code artefacts,
use checks appropriate to the medium (for example calculations, link validation
or completeness checks), and state what still requires visual or factual review.

## Portfolio work

Use `shipped = (R / r) × a`: R is available human-review time, r is measured time
per artefact and a is the acceptance fraction. Keep units consistent. If inputs
are missing, ask or show a labeled estimate, never invented measurements.
Commission within review capacity. Prioritize by consequence and freshness;
reduce loop size or improve the generator if rejection is high.

Build a complete review surface (table, contact sheet, diff or report) showing
the property actually under review. Show omitted/unavailable items explicitly.
Do not schedule ongoing work or send reminders without the user's authorization.

## JSON and optional execution

The JSON asset follows AIKO 0.1.0. It is a pending starter, not a completed report.
Use canonical YYYY-MM-DD dates and the documented enum values without padding.
Give claims unique IDs and set each observation's `claim_ref` to an ID in the
same report. Put external sources in `source_ref`, not in `claim_ref`.

- `passed` checks and `verified` claims require actual dates and evidence refs.
- `approved` human reviews require actual reviewer, date and evidence refs.
- `accepted` debt requires an approver, decision reference and future expiry.
- Observations need a checked date, later recheck date, owner and schedule ref;
  the recheck must be before planned use and not already due.
- A changed artefact requires renewed checks and review for its revision.

When a local SIEVE checkout is available, run from that checkout's root, replacing
`REPORT.json` with the actual report path (quote paths containing spaces):

```sh
python3 scripts/check_aiko.py REPORT.json --mode lint
python3 scripts/check_aiko.py REPORT.json --mode gate --output json
python3 scripts/check_aiko.py REPORT.json --mode gate --output markdown
```

Report the actual exit codes: 0 means lint success or declared gate conditions
met, 1 means gate held, and 2 means invalid input. Never interpret lint success
as approval. Preserve failure output. Use the current date for current work;
`--today` is only for explicit historical evaluation or deterministic examples,
not for making expired evidence appear current.

Even a gate pass cannot establish that URLs, identities or approvals are genuine,
that omitted claims are covered, or that a schedule will actually run. These are
external checks. Do not describe SIEVE as a compliance attestation.

## Working without tools

Read the supplied sources, prepare the artefact and a concise Markdown report.
Mark inaccessible sources unverified, checks not run, reviews pending and
uncreated schedules proposed. Do not substitute a manual impression for a
validator result. State what a human or tool-enabled environment must do next.
The reporting process remains useful even when validation cannot run.
