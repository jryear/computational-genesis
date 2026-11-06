#!/usr/bin/env python3
"""Phase B P2/P3: run the run-2 engine on Codex's operations with agent declarations."""
import json, sys, statistics as st
from pathlib import Path
from multiprocessing import Pool
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
import semexec as S, codex_ops as C  # noqa: E402

T = json.load(open(HERE / "truth.json"))
OPS = {n: (getattr(C, n), T[n]["row_independent"], T[n]["order_insensitive"]) for n in T}

def decl_from(path):
    D = json.load(open(path))
    return {n: {"reads": D[n]["reads"], "row_wise": D[n]["row_independent"],
                "order_insensitive": D[n]["order_insensitive"]} for n in D}

def job(a):
    who, ex_name, seed = a
    decl = decl_from(HERE / "declarations" / f"{who}.json")
    cls = S.EXECUTORS[ex_name]
    ex = cls(OPS, decl, seed=seed) if ex_name.startswith(("semantic", "targeted")) else cls(OPS, decl)
    table, edits = S.stream(seed, "all_fields")
    rows, stale = table, {}
    for t in range(len(edits) + 1):
        if t:
            rows = S.apply_edit(rows, edits[t - 1])
        out = ex.step(rows)
        for n, (fn, _, _) in OPS.items():
            if S.h(out[n]) != S.h(fn(rows)):
                stale[n] = stale.get(n, 0) + 1
    return who, ex_name, seed, stale, getattr(ex, "events", [])

if __name__ == "__main__":
    who = [p.stem for p in sorted((HERE / "declarations").glob("*_r[0-9].json"))]
    jobs = [(w, e, s) for w in who for e in ("content_sharded", "semantic_trusted", "targeted_a25") for s in range(1, 6)]
    with Pool(4) as p:
        res = p.map(job, jobs)
    json.dump(res, open(HERE / "engine_results.json", "w"))
    agg = {}
    for w, e, s, stale, ev in res:
        agg.setdefault(e, 0); agg[e] += sum(stale.values())
    for e, v in agg.items():
        print(f"{e:17} stale op-steps across {len(who)} declaration sets x 5 seeds: {v}")
    print("events:", sorted({(e, str(ev)) for w, e, s, st_, ev in res if ev}) or "none")
