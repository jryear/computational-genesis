#!/usr/bin/env python3
"""run.py OUT_DIR [--seeds N] [--jobs J]  -- full Lab 002 phase A grid.

Pass 1 computes the evaluator's truth (true function, from scratch, every step) per
(mix, seed, opset). Pass 2 runs each executor in its own process and measures only
the executor's CPU. Truth computation is never inside an executor's measurement.
"""
import argparse
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import semexec as S  # noqa: E402

SCENARIOS = ["true", "W1", "W2", "W3", "W4"]
BASELINES = ["naive", "content", "content_sharded"]
SEMANTIC = ["semantic_trusted", "semantic_verified"]


def opset(scn):
    return "W3" if scn == "W3" else "true"


def steps(mix, seed):
    table, edits = S.stream(seed, mix)
    rows = table
    yield rows
    for e in edits:
        rows = S.apply_edit(rows, e)
        yield rows


def truth_job(args):
    mix, seed, ops_name = args
    ops, _ = S.scenario(ops_name)
    return (mix, seed, ops_name), [{n: S.h(fn(rows)) for n, (fn, _, _) in ops.items()}
                                   for rows in steps(mix, seed)]


def exec_job(args):
    mix, seed, scn, ex_name, truth = args
    ops, decl = S.scenario(scn)
    cls = S.EXECUTORS[ex_name]
    ex = cls(ops, decl, seed=seed) if ex_name.startswith("semantic") else cls(ops, decl)
    cpu, stale, first_stale = [], {}, {}
    for t, rows in enumerate(steps(mix, seed)):
        c0 = time.process_time()
        out = ex.step(rows)
        cpu.append(time.process_time() - c0)
        for n, v in out.items():
            if S.h(v) != truth[t][n]:
                stale[n] = stale.get(n, 0) + 1
                first_stale.setdefault(n, t)
    return {"mix": mix, "seed": seed, "scenario": scn, "executor": ex_name,
            "cpu_total": round(sum(cpu), 4), "cpu_steps": [round(c, 4) for c in cpu],
            "stale": stale, "first_stale_step": first_stale,
            "events": getattr(ex, "events", [])}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mixes, seeds = list(S.MIXES), list(range(1, a.seeds + 1))
    with Pool(a.jobs) as pool:
        truth = dict(pool.map(truth_job, [(m, s, o) for m in mixes for s in seeds for o in ("true", "W3")]))
        jobs = [(m, s, opset(sc), e, truth[(m, s, opset(sc))]) for m in mixes for s in seeds
                for sc in ("true", "W3") for e in BASELINES]
        jobs += [(m, s, sc, e, truth[(m, s, opset(sc))]) for m in mixes for s in seeds
                 for sc in SCENARIOS for e in SEMANTIC]
        results = pool.map(exec_job, jobs)
    with open(out / "results.jsonl", "w") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"{len(results)} runs -> {out / 'results.jsonl'}")
