#!/usr/bin/env python3
"""verdict2.py RESULTS.jsonl -- evaluates RUN2.md criteria mechanically."""
import json, statistics as st, sys
R = [json.loads(x) for x in open(sys.argv[1])]
def runs(**kw): return [r for r in R if all(r[k] == v for k, v in kw.items())]
def stale(r): return sum(r["stale"].values())
def med(**kw):
    xs = [r["cpu_total"] for r in runs(**kw)]; return st.median(xs) if xs else float("nan")
P = "targeted_a25"
ok = {}
ok["C1"] = sum(stale(r) for r in runs(executor="semantic_trusted", scenario="W1")) > 0
ok["C2"] = sum(stale(r) for r in R if r["executor"] in ("naive", "content", "content_sharded")) == 0
s1 = {s: sum(stale(r) for r in runs(executor=P, scenario=s)) for s in ("true", "W1", "W2", "W4")}
ok["S1'"] = all(v == 0 for v in s1.values())
print(f"C1 {'PASS' if ok['C1'] else 'FAIL'}   C2 {'PASS' if ok['C2'] else 'FAIL'}")
print(f"S1' {P} stale (true/W1/W2/W4) {s1} -> {'PASS' if ok[chr(83)+'1'+chr(39)] else 'FAIL'}")
for c, mix, b in (("E1'", "realistic", 0.80), ("E2'", "relevant_only", 1.10)):
    base = {e: med(executor=e, scenario="true", mix=mix) for e in ("content", "content_sharded")}
    best = min(base.values())
    for ex in ("semantic_trusted", "semantic_verified", "targeted_a10", "targeted_a25", "targeted_a50"):
        v = med(executor=ex, scenario="true", mix=mix)
        tag = ""
        if ex == P:
            ok[c] = v <= b * best; tag = f"  <- {c} bound {b}: {'PASS' if ok[c] else 'FAIL'}"
        print(f"{mix:13} {ex:18} {v:6.2f}s  ratio {v/best:.3f} vs best baseline {best:.2f}s{tag}")
print("\nS2' W3 rare dependence (realistic mix): stale op-steps / revocation step per seed")
for ex in ("semantic_trusted", "semantic_verified", "targeted_a10", "targeted_a25", "targeted_a50"):
    rs = sorted(runs(executor=ex, scenario="W3", mix="realistic"), key=lambda r: r["seed"])
    det = [next((e[0] for e in r["events"] if e[2] == "revoked_by_audit"), None) for r in rs]
    print(f"  {ex:18} stale={[stale(r) for r in rs]} total={sum(stale(r) for r in rs)} revoked_at={det}")
print("\nstale op-steps, all mixes, by scenario:")
for ex in ("semantic_trusted", "semantic_verified", "targeted_a10", "targeted_a25", "targeted_a50"):
    print(f"  {ex:18} " + "  ".join(f"{s}={sum(stale(r) for r in runs(executor=ex, scenario=s))}" for s in ("true","W1","W2","W3","W4")))
ctl = ok["C1"] and ok["C2"]
print(f"\nControls {'passed' if ctl else 'FAILED: nothing counts'}. S1'={'PASS' if ok[chr(83)+'1'+chr(39)] else 'FAIL'} E1'={'PASS' if ok[chr(69)+'1'+chr(39)] else 'FAIL'} E2'={'PASS' if ok[chr(69)+'2'+chr(39)] else 'FAIL'}")
