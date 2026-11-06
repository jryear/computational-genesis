# Phase B results (first operation set)

- **P1, declaration accuracy:** **72 of 72 exact**. That is 8 operations × 3 repetitions × 3
  declarers (claude-haiku-5-5, claude-sonnet-5-5, Codex in a fresh session), with no omitted
  reads, no extra reads and no structural errors. All 9 declaration sets were identical.
  Details are in `p1_scores.txt`.
  - This includes the conditional reads: `op_1` (amount and currency only for wire), `op_3`
    (memo only for wire, date only for pos) and `op_8` (case-insensitive backorder filter).
- **P2, safety:** `targeted_a25` served 0 stale outputs across 9 declaration sets × 5 seeds on
  the `all_fields` mix. **PASS, but uninformative.** No declaration was wrong, so the control
  could not apply and the verifier was never challenged.
  - The one thing this does show: the verifier, built before this code existed, falsely
    rejected **none** of the 8 correct declarations.
- **P3:** `semantic_trusted` also served 0 stale outputs, as expected with correct declarations.

## Reading

- Declaring semantics for short, readable functions is easy for current models. On this set
  it matched the oracle every time.
- This repeats the ceiling problem from the interface experiment. The informative regime is
  code where the dependencies are hidden: helper indirection, data-driven field access,
  dispatch tables, behaviour on exceptions.
- That is the next operation set (B2), again authored by Codex, independently of the verifier.
