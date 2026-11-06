"""Reference oracle for the true semantics of an operation.

Distinct from the runtime verifier: the oracle knows each field's full value domain,
including values the data rarely contains (huge amounts that cross wire limits,
case/space variants of memo keywords), and runs hundreds of trials. It is the
answer key; the runtime verifier is the thing under test and gets none of this.

Definitions (the same text the declarers receive):
- reads: every field whose value can ever change the output.
- row_independent: the output is a list with one element per input row, and each
  element depends only on that row (not on other rows or their order).
- order_insensitive: permuting the input rows never changes the output.
"""
import random

FIELDS = ["txn_id", "region", "product", "amount", "currency", "date", "fingerprint", "memo", "channel"]
MEMOS = ["", "gift", "net30", "promo", "backorder", "rush", "Backorder", " BACKORDER ", "REFUND",
         "back order", "x" * 40]


def domain(f, rng):
    if f == "txn_id":
        return f"T{rng.randrange(12):06d}"                  # small pool -> duplicates
    if f == "region":
        return rng.choice(["north", "south", "east", "west"])
    if f == "product":
        return rng.choice(["anvil", "bolt", "cable", "dynamo", "ember"])
    if f == "amount":
        return rng.choice([f"{rng.uniform(1, 900):.2f}", f"{rng.uniform(9000, 2_000_000):.2f}",
                           "10000.00", "1000000.00"])
    if f == "currency":
        return rng.choice(["USD", "EUR", "GBP", "JPY"])
    if f == "date":
        return f"2026-{rng.choice(['10', '11'])}-{rng.randint(1, 28):02d}"
    if f == "fingerprint":
        return rng.choice(["a1b2c3d4e5f6", "0f0f0f0f0f0f", "ffffeeeedddd"])
    if f == "memo":
        return rng.choice(MEMOS)
    if f == "channel":
        return rng.choice(["web", "pos", "wire"])
    raise KeyError(f)


def table(rng, n):
    rows = [{f: domain(f, rng) for f in FIELDS} for _ in range(n)]
    for _ in range(rng.randrange(3)):
        rows.append(dict(rng.choice(rows)))                 # exact duplicates
    return rows


def truth(fn, trials=400, seed=0):
    rng = random.Random(seed)
    reads = set()
    for f in FIELDS:
        for _ in range(trials):
            t = table(rng, rng.randint(1, 12))
            u = [dict(r) for r in t]
            for r in rng.sample(u, rng.randint(1, len(u))):
                r[f] = domain(f, rng)
            if fn(t) != fn(u):
                reads.add(f)
                break
    row_ind, order_ins = True, True
    for _ in range(trials):
        t = table(rng, rng.randint(2, 12))
        out = fn(t)
        if row_ind and not (isinstance(out, list) and len(out) == len(t)
                            and all(fn([r])[0] == o for r, o in zip(t, out))):
            row_ind = False
        p = list(t)
        rng.shuffle(p)
        if order_ins and fn(p) != out:
            order_ins = False
    return {"reads": sorted(reads, key=FIELDS.index), "row_independent": row_ind,
            "order_insensitive": order_ins}
