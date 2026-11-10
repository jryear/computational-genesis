#!/usr/bin/env python3
"""verdict3.py RESULTS.jsonl -- evaluates RUN3.md criteria mechanically."""
import json, statistics as st, sys
R = [json.loads(x) for x in open(sys.argv[1])]
def runs(**kw): return [r for r in R if all(r[k] == v for k, v in kw.items())]
def stale(r): return sum(r["stale"].values())
def med(key, **kw):
    xs = [r[key] for r in runs(**kw)]; return st.median(xs) if xs else float("nan")
P = "targeted_a25"; ok = {}
ok["C1"] = sum(stale(r) for r in runs(executor="semantic_trusted", scenario="W1")) > 0
ok["C2"] = sum(stale(r) for r in R if r["executor"] in ("content", "content_sharded")) == 0
s1 = {s: sum(stale(r) for r in runs(executor=P, scenario=s)) for s in ("true", "W1", "W2", "W4")}
ok["S1"] = all(v == 0 for v in s1.values())
print(f"C1 {'PASS' if ok['C1'] else 'FAIL'}  C2 {'PASS' if ok['C2'] else 'FAIL'}  S1'' {s1} -> {'PASS' if ok['S1'] else 'FAIL'}")
for c, mix, b in (("E3", "realistic", 0.80), ("E4", "relevant_only", 1.10)):
    base = {e: med("evals_total", executor=e, scenario="true", mix=mix) for e in ("content", "content_sharded")}
    best = min(base.values())
    print(f"\n{mix} (expensive evaluations, median of 5 seeds; best baseline {best:.0f} = {min(base, key=base.get)})")
    for ex in ("content", "content_sharded", "semantic_trusted", "semantic_verified", "targeted_a10", "targeted_a25", "targeted_a50"):
        rs = runs(executor=ex, scenario="true", mix=mix)
        tot = st.median(r["evals_total"] for r in rs)
        src = {k: st.median(r["evals_by_source"].get(k, 0) for r in rs) for k in ("compute", "verify", "audit")}
        tag = ""
        if ex == P:
            ok[c] = tot <= b * best; tag = f"  <- {c} bound {b}: {'PASS' if ok[c] else 'FAIL'}"
        print(f"  {ex:17} {tot:6.0f}  ratio {tot/best:.2f}  compute={src['compute']:.0f} verify={src['verify']:.0f} audit={src['audit']:.0f}{tag}")
ctl = ok["C1"] and ok["C2"]
print(f"\nControls {'passed' if ctl else 'FAILED: nothing counts'}. S1''={'PASS' if ok['S1'] else 'FAIL'} E3={'PASS' if ok['E3'] else 'FAIL'} E4={'PASS' if ok['E4'] else 'FAIL'}")
