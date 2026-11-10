# Synthetic AIKO examples

These are teaching fixtures, not evidence that any person reviewed real work.
All `synthetic://` references and people are deliberately fictitious. The dates
are fixed to **2026-11-07** for repeatable demonstration, not current validity.

| Scenario | JSON input | Readable report | Gate result at the fixed date |
|---|---|---|---|
| Human review pending | [pending.json](pending.json) | [pending.md](pending.md) | BLOCKED, exit 1 |
| Declared conditions met | [declared-conditions-met.json](declared-conditions-met.json) | [declared-conditions-met.md](declared-conditions-met.md) | REPORTED_APPROVED, exit 0; not authenticated approval |
| Observation due today | [expired.json](expired.json) | [expired.md](expired.md) | BLOCKED, exit 1 |

The same declared-conditions-met input becomes blocked when its observation
expires. Do not remove an observation or backdate the evaluation to obtain a
pass for current work. Obtain fresh evidence and the necessary human review.

With a local SIEVE checkout, reproduce a report from the repository root:

```sh
python3 scripts/check_aiko.py skills/sieve/examples/pending.json --mode gate --today 2026-11-07 --output markdown
```

The Markdown files add a synthetic-example notice above the validator output.
