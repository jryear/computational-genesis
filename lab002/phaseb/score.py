#!/usr/bin/env python3
"""Score declarations against the oracle (PHASEB.md P1)."""
import glob, json
T = json.load(open("truth.json"))
rows = []
for f in sorted(glob.glob("declarations/*_r[0-9].json")):
    who = f.split("/")[-1][:-5]
    D = json.load(open(f))
    exact, omit, extra, rowerr, ordererr = 0, [], [], [], []
    for op, t in T.items():
        d = D[op]
        dr, tr = set(d["reads"]), set(t["reads"])
        om, ex = sorted(tr - dr), sorted(dr - tr)
        ri_ok = d["row_independent"] == t["row_independent"]
        oi_ok = t["row_independent"] or d["order_insensitive"] == t["order_insensitive"]
        if om: omit.append(f"{op}:-{','.join(om)}")
        if ex: extra.append(f"{op}:+{','.join(ex)}")
        if not ri_ok: rowerr.append(f"{op}(said {d['row_independent']})")
        if not oi_ok: ordererr.append(f"{op}(said {d['order_insensitive']})")
        exact += (not om and not ex and ri_ok and oi_ok)
    rows.append((who, exact, omit, extra, rowerr, ordererr))
    print(f"{who:10} exact {exact}/8  omitted={omit or '-'}  extra={extra or '-'}  row_err={rowerr or '-'}  order_err={ordererr or '-'}")
