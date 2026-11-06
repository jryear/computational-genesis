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

# Set 2: dependencies hidden on purpose

- Codex authored 8 operations designed to hide dependencies realistically (`codex_ops_set2.py`,
  verbatim). The patterns include field choice driven by channel, a fallback when memo parsing
  fails, a lowercase `"refund"` sign flip, a memo exemption only above 1,000,000, dedup by
  identity tuple, tie-breaker sort keys, and order-dependent batching.
- **Oracle:** now also white-box: it adds each function's own string and number literals to its
  value pools. Set-1 truth is unchanged under the extended oracle (re-checked). It agrees with
  the author's answer key on every read set; the only difference is `op_3` again, the
  row-shape vs row-independence ambiguity in my prompt.
- **Declarations: 72 of 72 exact again**, across Haiku, Sonnet and Codex × 3 repetitions
  (`p1_scores_set2.txt`). Across both sets that is **144 of 144**.

## Exploratory, not preregistered: can the runtime verifier catch an omitted field?

Agents never erred, so the verifier was probed directly. Each true declaration had exactly one
true read removed, and each mutation was verified at first use on the `all_fields` initial
table with 5 verifier seeds (`mutation_probe.py`, `mutation_probe.txt`).

- **Caught: 42 of 52 omissions** (set 1: 21/24; set 2: 21/28). The 10 misses fall into three
  classes:
  1. **Collision-dependent reads:** dedup or conflict detection on txn_id or fingerprint. The
     sample has no collisions, so perturbing the field changes nothing.
  2. **Tie-breaker reads:** a secondary sort key matters only when the primary keys tie, which
     random data never does.
  3. **Rare-literal reads:** `"refund"`, `"treasury:waived"` above 1,000,000, and a JPY limit of
     1,000,000. Black-box sampling cannot find values it never generates.

## Reading

- On functions of this size, agents' static reading beat the runtime's black-box sampling. The
  verifier missed exactly the dependencies the agents got right.
- Taken alone, the declaration side is not the weak link here; the verifier is. Two of the miss
  classes look fixable generically:
  - collisions: a constant-fill perturbation that sets every sampled row's field to the same
    value;
  - rare literals: grey-box verification that analyzes the code the runtime is about to execute.
- Tie-breakers need joint perturbation (make the primary keys equal, then vary the secondary).
- That is a verifier v2. It should be preregistered as its own run, not tuned against these 10
  misses.
- Set-2 engine runs were not part of the preregistration and were not run. With all
  declarations exact, `targeted_a25` would only repeat set 1's trivially safe result.
