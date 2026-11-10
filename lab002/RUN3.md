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

## Result (appended after the run; the criteria above are untouched)

Controls passed. **S1″ PASS, E3 FAIL, E4 FAIL.** The prediction recorded before the run held.
Full verdict in `results/run3/verdict.txt`.

| Realistic mix, expensive evaluations (median) | Total | Compute | Verify | Audit |
|---|---|---|---|---|
| content (Bazel-style, unsharded) | 17,536 | 17,536 | 0 | 0 |
| content_sharded (best baseline) | **940** | 940 | 0 | 0 |
| semantic_trusted (ceiling for reuse) | 754 (0.80×) | 754 | 0 | 0 |
| targeted_a25 | 1,523 (1.62×) | 754 | 608 | 162 |

- **Semantic reuse saves at most 20% over a well-sharded content-addressed baseline on the
  realistic mix, and 0% on relevant-only.** Even trusted completely, it only reaches the E3 bound.
- **Black-box first-use verification costs 608 expensive evaluations**, about one full recompute
  of the table. That is three times the total reuse saving over 25 steps.
- **Audits cost little** (113–183) when targeted to declaration-enabled reuse.

## Reading

- **The efficiency thesis is not supported in Lab 002** (three runs, three efficiency failures).
  Good content-addressed sharding already captures most of the reuse, so declared semantics add
  little on top.
- **The safety thesis is supported in all three runs:** 0 stale outputs from detectable false
  declarations, and rare ones limited by audits.
- Phase B found agents declare semantics accurately (144/144), and found static reading beats
  black-box sampling. A verifier based on review rather than sampling would cut the 608 to
  roughly one call, but that cannot rescue E3 here: the reuse ceiling itself is 0.80.
