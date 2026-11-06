# Lab 002, phase A: preregistration

Status: **proposed criteria, frozen in git before any run. The operator owns acceptance.** If the
operator replaces a criterion, the replacement is a new commit, and results are judged against
whichever version the operator approves, with both versions kept.

## Question

When the actor declares the semantics of its operations, can a runtime that *verifies* those
declarations reuse more work than a strong content-addressed baseline (Bazel/Nix-style action
keys) **without ever serving a stale result**, including when a declaration is false?

## Prior art (why this is not "just build fuzzing")

- Checking declared dependencies by perturbing inputs is established in build systems: Licker &
  Rice's build fuzzing, and later work on missing and redundant dependencies. The verifier here
  borrows that technique.
- Bazel and Nix key reuse on hashes of the command and its whole inputs.
- What is being tested: declarations finer than files (fields read, row-independence,
  order-insensitivity), verified when first used and audited continuously at runtime. No LLM in
  phase A; phase B asks whether agents write accurate declarations.

## Setup (fixed)

- **Data:** a synthetic ledger table of 600 rows with fields txn_id, region, product, amount,
  currency, date, fingerprint, memo and channel. Fingerprints are signed; some rows are
  tampered; some are duplicates.
- **Operations:** five, with known true semantics.
  - `usd_clean`: row-wise. Verifies the fingerprint (expensive) and converts at the month's rate.
  - `monthly_totals`: table-level, order-insensitive.
  - `fees`: row-wise, moderate cost.
  - `first_seen`: table-level, order-sensitive.
  - `product_mix`: table-level, order-insensitive.
- **Change streams:** 25 steps each, 5 seeds per mix. Two mixes:
  - *realistic*: append 25%, memo edit 15%, currency correction 5%, reorder 10%, amount edit
    15%, product edit 10%, channel edit 10%, refund-memo edit 10%. (Amended before any run; see
    the amendments section.)
  - *relevant-only*: amount edit 50%, append 50%.
- **Executors:**
  - `naive`: recompute everything every step.
  - `content`: whole-input content hash per operation, i.e. a Bazel action key.
  - `content_sharded`: per-row content keys for operations that are *truly* row-wise (oracle
    structure, the best a skilled build author could do), and whole-input keys otherwise.
  - `semantic_trusted`: uses the declarations without checking them.
  - `semantic_verified`: property-tests each declaration on first use against a 40-row sample,
    by perturbing undeclared fields, shuffling, singleton/batch equality, and duplicated batches.
    A rejected declaration falls back to `content`. Reuse is then audited at runtime: 5% of
    reused rows are recomputed fresh, and table-level cache hits are recomputed with
    probability 5%. A mismatch revokes the declaration.
- **Declaration scenarios:** `true` (all correct), plus four with one false declaration each:
  - **W1:** `usd_clean` omits `currency`.
  - **W2:** `first_seen` is declared row-wise.
  - **W3:** `fees` reads `memo` only when it equals "REFUND", but the declaration omits `memo`
    (a rare dependence).
  - **W4:** `first_seen` is declared order-insensitive.
- **Measurement:**
  - Each executor's CPU per step, `time.process_time` inside a dedicated process, including
    keying, hashing and verification.
  - Stale outputs: steps where an operation's output differs from the true function recomputed
    from scratch by the independent evaluator.

## Proposed criteria

- **S1, safety:** `semantic_verified` serves **0 stale outputs** in scenarios `true`, W1, W2 and
  W4, across all seeds and both mixes.
- **S2, rare dependence (exploratory, no threshold):** for W3, report stale outputs and detection
  latency for `semantic_verified`. This is the known hole: sampling cannot prove the absence of a
  rare dependence.
- **E1, efficiency:** in scenario `true` on the realistic mix, median total CPU of
  `semantic_verified` ≤ 0.50 × the better of `content` and `content_sharded`.
- **E2, no regression:** in scenario `true` on the relevant-only mix, median total CPU of
  `semantic_verified` ≤ 1.10 × the better baseline.

## Required controls (the evaluator must demonstrate it catches errors)

- **C1:** `semantic_trusted` under W1 must produce stale outputs, and the evaluator must flag
  them. If it doesn't, the evaluator is blind and no result counts.
- **C2:** `naive`, `content` and `content_sharded` must have 0 stale outputs in every scenario
  (declarations never affect them).

## What would make this result not count

- Any failed control.
- Changes to the operations, streams, verifier sampling or audit rate after the first full run,
  unless they are reported as a new, separately labelled run.

## Amendments before the first run

1. **The realistic mix gains currency corrections at 5%, taken from memo edits (20% → 15%).**
   - Found by control C1's unit test. No stream ever edited `currency`, so W1 (a declaration that
     omits `currency`) could never produce a stale result, and control C1 could not pass.
   - A false declaration is only dangerous when the omitted field changes. That is a property
     the workloads have to exercise, not one the executor can assume.
2. **`monthly_totals` now sums each month with `math.fsum` and rounds once.**
   - Found by the verifier's own test against the *true* declarations. Per-row rounding made the
     result depend on row order by a cent, so the declared order-insensitivity was false.
   - The intended semantics never depended on order; the implementation did.
