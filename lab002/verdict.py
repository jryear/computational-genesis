#!/usr/bin/env python3
"""verdict.py RESULTS.jsonl -- evaluates PREREG.md criteria mechanically."""
import json
import statistics as st
import sys
from collections import defaultdict

R = [json.loads(x) for x in open(sys.argv[1])]


def runs(**kw):
    return [r for r in R if all(r[k] == v for k, v in kw.items())]


def stale(r):
    return sum(r["stale"].values())


def med_cpu(**kw):
    xs = [r["cpu_total"] for r in runs(**kw)]
    return st.median(xs) if xs else float("nan")


out = []
ok = {}

# controls
c1 = sum(stale(r) for r in runs(executor="semantic_trusted", scenario="W1"))
ok["C1"] = c1 > 0
out.append(f"C1 trusted+W1 produces stale outputs the evaluator flags: {c1} stale op-steps -> {'PASS' if ok['C1'] else 'FAIL'}")
c2 = sum(stale(r) for r in R if r["executor"] in ("naive", "content", "content_sharded"))
ok["C2"] = c2 == 0
out.append(f"C2 baselines never stale: {c2} -> {'PASS' if ok['C2'] else 'FAIL'}")

# S1
s1 = {scn: sum(stale(r) for r in runs(executor="semantic_verified", scenario=scn)) for scn in ("true", "W1", "W2", "W4")}
ok["S1"] = all(v == 0 for v in s1.values())
out.append(f"S1 semantic_verified stale outputs (true/W1/W2/W4): {s1} -> {'PASS' if ok['S1'] else 'FAIL'}")

# S2 exploratory
w3 = runs(executor="semantic_verified", scenario="W3")
w3t = runs(executor="semantic_trusted", scenario="W3")
out.append("S2 (exploratory) W3 rare dependence:")
for r in sorted(w3, key=lambda r: (r["mix"], r["seed"])):
    out.append(f"   verified {r['mix']:13} seed{r['seed']}: stale={r['stale']} first_stale={r['first_stale_step']} events={r['events']}")
out.append(f"   trusted total stale op-steps: {sum(stale(r) for r in w3t)}; verified: {sum(stale(r) for r in w3)}")

# efficiency
for crit, mix, bound in (("E1", "realistic", 0.50), ("E2", "relevant_only", 1.10)):
    sv = med_cpu(executor="semantic_verified", scenario="true", mix=mix)
    base = {e: med_cpu(executor=e, scenario="true", mix=mix) for e in ("content", "content_sharded")}
    best = min(base.values())
    ok[crit] = sv <= bound * best
    out.append(f"{crit} {mix}: semantic_verified {sv:.2f}s vs best baseline {best:.2f}s "
               f"({min(base, key=base.get)}) ratio {sv / best:.3f} (bound {bound}) -> {'PASS' if ok[crit] else 'FAIL'}")

# descriptive table
out.append("\nmedian total CPU s (scenario true) / stale op-steps summed over seeds:")
tab = defaultdict(dict)
for r in R:
    if r["scenario"] in ("true",):
        tab[r["mix"]].setdefault(r["executor"], []).append(r["cpu_total"])
for mix, d in tab.items():
    out.append(f"  {mix}: " + ", ".join(f"{e}={st.median(v):.2f}" for e, v in sorted(d.items(), key=lambda x: st.median(x[1]))))
out.append("\nstale op-steps by scenario x executor (all mixes, seeds):")
agg = defaultdict(int)
for r in R:
    agg[(r["scenario"], r["executor"])] += stale(r)
for scn in ("true", "W1", "W2", "W3", "W4"):
    out.append(f"  {scn}: " + ", ".join(f"{e}={agg[(scn, e)]}" for e in ("naive", "content", "content_sharded", "semantic_trusted", "semantic_verified") if (scn, e) in agg))
out.append("\nverification/audit events (semantic_verified):")
for r in sorted(runs(executor="semantic_verified"), key=lambda r: (r["scenario"], r["mix"], r["seed"])):
    if r["events"]:
        out.append(f"  {r['scenario']:4} {r['mix']:13} seed{r['seed']}: {r['events']}")
controls = ok["C1"] and ok["C2"]
out.append(f"\nControls {'passed' if controls else 'FAILED: no criterion result counts'}. "
           f"S1={'PASS' if ok['S1'] else 'FAIL'} E1={'PASS' if ok['E1'] else 'FAIL'} E2={'PASS' if ok['E2'] else 'FAIL'}")
print("\n".join(out))
