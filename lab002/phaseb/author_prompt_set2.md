You are writing a benchmark workload. Output ONE Python module (stdlib only) and nothing else, inside a single ```python fenced block.

Data: a table is a list of dict rows. Every value is a string. Fields:
- txn_id: e.g. "T000123" (duplicates of a whole row can occur)
- region: one of north, south, east, west
- product: one of anvil, bolt, cable, dynamo, ember
- amount: decimal string like "412.07"
- currency: one of USD, EUR, GBP, JPY
- date: "2026-10-DD" or "2026-11-DD"
- fingerprint: 12 hex chars
- memo: free text, usually one of "", gift, net30, promo, backorder, rush, but can be anything
- channel: one of web, pos, wire

Write exactly 8 functions `op_1` ... `op_8`, each `def op_N(rows): ...`, realistic for a finance/ops team.
Contract:
- Pure and deterministic: no I/O, no randomness, no globals mutated, no time.
- Either ROW-WISE (returns a list with exactly one output per input row, in the same order) or TABLE-LEVEL (returns a single JSON-serializable value).
- Each must do real work. This set is deliberately HARD to analyze, the way real production code is: dependencies should be hidden through realistic engineering patterns, not obfuscation. Across the 8 functions use at least five of: helper functions and small classes; configuration dicts that map one field's value to another field's name or to a rule; dispatch tables keyed by a field value; try/except fallbacks where a field is only read when parsing another fails; sorting where ties are broken by an extra field; early returns or caches inside the call; dependence on a field only for rare values (e.g. one specific memo string, or amounts above a threshold that typical data never reaches). Keep each function readable to a competent engineer and under ~40 lines.
- Vary them on purpose:
  - at least 3 row-wise and at least 3 table-level;
  - at least 2 whose result depends on row ORDER, and at least 2 that do not;
  - at least 2 that read a field only under some condition (e.g. only when another field has a particular value), written naturally, not flagged;
  - at least 1 that reads several fields but ignores most of the row;
  - floating-point totals must be computed so the result is genuinely independent of row order when the function is meant to be order-independent.
- Add a one-line docstring with the business intent. Do NOT document which fields are read or whether the function is row-wise or order-dependent.

Also define `TRUTH = {"op_1": {"reads": [...], "row_wise": bool, "order_insensitive": bool}, ...}` with your own honest statement of each function's real semantics ("reads" = every field whose value can ever change the output).
