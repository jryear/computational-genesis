# Lab 002, run 3: preregistration

Frozen before run 3. The criteria are proposed by Claude; the operator owns acceptance.

## Question

When the expensive operation costs as much as an AI call, so that CPU and hashing overhead stop
mattering, does verified semantic reuse spend fewer expensive evaluations than the best
content-addressed baseline, **counting every evaluation the verifier and the audits make**?

## Change from run 2

- **The measure is expensive evaluations, not CPU.** Each row that `usd_clean` (the
  fingerprint-verifying operation) processes counts as one unit. That includes rows evaluated
  during first-use verification and audits. All other operations are treated as free, since they
  are cheap in any realistic setting.
- Everything else is unchanged from run 2: data, streams, seeds, mixes, scenarios, executors
  (`content`, `content_sharded`, `semantic_trusted`, `semantic_verified`, `targeted_a10/a25/a50`)
  and the evaluator.

## Prediction recorded before running

`targeted_a25` may lose. First-use verification evaluates about 18 × 40 = 720 sample rows, more
than the 600-row table, and audits recompute reused rows.

## Criteria (judged on `targeted_a25`)

- **S1″:** 0 stale outputs in scenarios `true`, W1, W2 and W4 (a regression check; nothing
  changed that affects it).
- **E3:** realistic mix, scenario `true`: median expensive evaluations ≤ **0.80** × the better
  of `content` and `content_sharded`.
- **E4:** relevant-only mix, scenario `true`: ≤ **1.10** × the better baseline.
- **Descriptive:** an evaluation breakdown (cold start, verification, audits, steady-state
  recompute), plus `semantic_trusted`'s count as the ceiling for what reuse alone can save.
- **Controls C1 and C2, as before.**
