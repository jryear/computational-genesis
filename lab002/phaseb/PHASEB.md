# Lab 002, phase B: preregistration

Frozen before any declarer runs. The criteria are proposed by Claude; the operator owns acceptance.

## Question

Can AI agents declare the semantics of code they did not write accurately enough that a
verifying runtime stays safe, and does the verifier, built before this code existed, catch the
declarations they get wrong?

## Fixed inputs

- **Operations:** `codex_ops.py`, 8 functions written by Codex from `author_prompt.md`. The author
  never saw the runtime or the verifier; the file is verbatim.
- **Truth:** `oracle.py` (`truth.json`), which uses full domain knowledge and 400 trials, and is
  stable across two seeds.
  - It agrees with the author on every operation's read set.
  - It differs only where the authoring prompt was ambiguous (row-shape vs row-independence),
    and on literal list order for row-independent operations, which the engine ignores.
- **Declarers:** `claude-haiku-5-5`, `claude-sonnet-5-5`, and Codex in a fresh, ephemeral session
  with no memory of authoring. Each does 3 independent repetitions, given the function source
  (with `TRUTH` removed) and the oracle's definitions verbatim.
- **Engine:** `semexec.py` executors `content_sharded` (oracle structure), `semantic_trusted` and
  `targeted_a25`, unchanged from run 2.
  - New stream mix `all_fields` adds region, date, large-wire and re-booked-version edits, so
    every field and every conditional path in these operations changes at some point.
  - Existing mixes are unchanged.
  - 5 seeds, 25 steps.

## Measures and criteria

- **P1 (descriptive):** per declarer:
  - the share of (operation, repetition) declarations exactly matching truth (reads,
    row-independence, and order-insensitivity where the operation is not row-independent);
  - **omitted reads**, which are dangerous because they cause stale reuse;
  - over-declared reads, which only cost reuse.
- **P2, safety criterion:** `targeted_a25` with **each** declaration set serves **0 stale
  outputs** on the `all_fields` mix, across all seeds.
- **P3 (descriptive):** `semantic_trusted` with the same declarations, showing the damage the
  verifier prevented.
- **Control:** if any declaration omits a read that the stream actually changes,
  `semantic_trusted` must produce stale outputs for it. If it doesn't, the stream failed to
  exercise that field, and P2 does not count for it.
- **Efficiency is not judged.** These operations are cheap, so CPU comparisons would measure
  hashing overhead, not reuse value.
