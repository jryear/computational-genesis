# Lab 002, run 2: preregistration

Status: **frozen before run 2.** The criteria are proposed by Claude; the operator owns
acceptance. **Disclosure:** the E1 threshold below was chosen *after* run 1. Run 1 showed that,
against oracle-sharded content keys, trusted semantics save about 25% of total CPU on this
workload. A 50% bar is therefore unreachable here. The new bar sits just below that measured
ceiling.

Run 1's verdict (S1 pass, E1 fail, E2 fail) stands and is not revisited.

## Change from run 1

New executors `targeted_aNN` keep run 1's first-use verification, but audit only **reuse that
the declaration enables**:
- A reused row whose full content was already computed or audited is safe by content hashing,
  so it is not audited.
- A reused row with new full content but a matching declared projection is audited at rate `a`
  per step. Unaudited rows remain candidates on later steps.
- For table-level operations, the same rule applies, as a coin flip at rate `a`.

Three rates: a = 0.10, 0.25 and 0.50. **The primary executor is `targeted_a25`.** Everything
else (data, streams, seeds, operations, scenarios, evaluator, controls) is unchanged from
run 1 as amended.

## Criteria (judged on `targeted_a25`)

- **S1′:** 0 stale outputs in scenarios `true`, W1, W2 and W4, across both mixes and all seeds.
- **E1′:** realistic mix, scenario `true`: median total CPU ≤ **0.80** × the better of
  `content` and `content_sharded`.
- **E2′:** relevant-only mix, scenario `true`: median total CPU ≤ **1.10** × the better
  baseline.
- **S2′ (exploratory):** for W3, stale outputs and detection step at every audit rate, against
  run 1's `semantic_verified`. This maps the cost-of-checking against speed-of-catching-lies
  tradeoff.
- **Controls C1 and C2, as in run 1.** If either fails, nothing counts.
