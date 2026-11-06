#!/usr/bin/env python3
"""run3.py OUT_DIR -- Lab 002 run 3: count expensive evaluations (rows through usd_clean).

The engine is unchanged. The expensive operation is wrapped with a counter that
attributes each evaluated row to where the call came from (first-use verification,
an audit, or ordinary computation), read from the caller's source line, so
semexec.py needs no changes.
"""
import json
import sys
import traceback
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import semexec as S  # noqa: E402
import run as R      # noqa: E402

EXECS = ["content", "content_sharded", "semantic_trusted", "semantic_verified",
         "targeted_a10", "targeted_a25", "targeted_a50"]


def counted(fn, tally):
    def wrapper(rows):
        frames = traceback.extract_stack(limit=6)[:-1]
        where = "compute"
        for f in reversed(frames):
            if f.name == "check":
                where = "verify"
                break
            if f.name == "audit_rows" or (f.line or "").startswith(("fresh = fn(", "if fn(rows) != self.cache")):
                where = "audit"
                break
        tally[where] = tally.get(where, 0) + len(rows)
        return fn(rows)
    return wrapper


def job(args):
    mix, seed, scn, ex_name, truth = args
    ops, decl = S.scenario(scn)
    fn, rw, oi = ops["usd_clean"]
    tally = {}
    ops = dict(ops, usd_clean=(counted(fn, tally), rw, oi))
    cls = S.EXECUTORS[ex_name]
    ex = cls(ops, decl, seed=seed) if ex_name.startswith(("semantic", "targeted")) else cls(ops, decl)
    stale, per_step = {}, []
    for t, rows in enumerate(R.steps(mix, seed)):
        before = sum(tally.values())
        out = ex.step(rows)
        per_step.append(sum(tally.values()) - before)
        for n, v in out.items():
            if S.h(v) != truth[t][n]:
                stale[n] = stale.get(n, 0) + 1
    return {"mix": mix, "seed": seed, "scenario": scn, "executor": ex_name,
            "evals_total": sum(tally.values()), "evals_by_source": tally, "evals_step0": per_step[0],
            "evals_per_step": per_step, "stale": stale, "events": getattr(ex, "events", [])}


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    mixes, seeds = list(S.MIXES)[:2], range(1, 6)        # realistic, relevant_only (as runs 1-2)
    with Pool(4) as pool:
        truth = dict(pool.map(R.truth_job, [(m, s, o) for m in mixes for s in seeds for o in ("true", "W3")]))
        jobs = [(m, s, sc, e, truth[(m, s, R.opset(sc))]) for m in mixes for s in seeds
                for sc in R.SCENARIOS for e in EXECS
                if not (e in ("content", "content_sharded") and sc not in ("true", "W3"))]
        res = pool.map(job, jobs)
    with open(out / "results.jsonl", "w") as f:
        for r in res:
            f.write(json.dumps(r) + "\n")
    print(f"{len(res)} runs -> {out / 'results.jsonl'}")
