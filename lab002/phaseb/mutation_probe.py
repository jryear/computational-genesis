#!/usr/bin/env python3
"""Exploratory (not preregistered): does the runtime verifier, which is black-box and built
before this code existed, catch declarations that omit exactly one true read?
For each op and each true read f: declaration = truth minus f. Verified at first use on the
all_fields stream's initial table (600 rows), as the engine would. 5 verifier seeds."""
import json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import semexec as S  # noqa: E402

for label, mod, tfile in (("set1", "codex_ops", "truth.json"), ("set2", "codex_ops_set2", "truth_set2.json")):
    C = __import__(mod)
    T = json.load(open(HERE / tfile))
    ops = {n: (getattr(C, n), T[n]["row_independent"], T[n]["order_insensitive"]) for n in T}
    table, _ = S.stream(1, "all_fields")
    caught = total = 0
    misses = []
    for n, t in T.items():
        for f in t["reads"]:
            decl = {m: {"reads": [x for x in T[m]["reads"] if not (m == n and x == f)],
                        "row_wise": T[m]["row_independent"], "order_insensitive": T[m]["order_insensitive"]}
                    for m in T}
            hits = sum(not S.SemanticVerified(ops, decl, seed=s).check(n, table) for s in range(5))
            total += 1
            caught += hits == 5
            if hits < 5:
                misses.append(f"{n} omits {f}: caught {hits}/5 seeds")
    print(f"{label}: single-field omissions caught in all 5 seeds: {caught}/{total}")
    for m in misses:
        print("   MISSED", m)
