"""Lab 002 phase A: declared-semantics execution vs content-addressed baselines.

Pure stdlib. Everything an executor does (keying, hashing, verification,
audits, operation runs) is inside its measured CPU. The evaluator recomputes
each operation's TRUE function from scratch and is outside the measurement.
"""
import hashlib
import math
import json
import random

ROUNDS_USD = 2500     # fingerprint verification: the expensive work
ROUNDS_FEE = 300
RATES = {"2026-10": {"USD": 1.0, "EUR": 1.05, "GBP": 1.22, "JPY": 0.0068},
         "2026-11": {"USD": 1.0, "EUR": 1.09, "GBP": 1.27, "JPY": 0.0065}}
FIELDS = ["txn_id", "region", "product", "amount", "currency", "date", "fingerprint", "memo", "channel"]
PRODUCTS = ["anvil", "bolt", "cable", "dynamo", "ember"]
CHANNELS = {"web": 0.029, "pos": 0.015, "wire": 0.004}
MEMOS = ["", "gift", "net30", "promo", "backorder", "rush"]


def _chain(text, rounds):
    h = text.encode()
    for _ in range(rounds):
        h = hashlib.sha256(h).digest()
    return h.hex()[:12]


def sign(txn, amount):
    return _chain(f"{txn}|{amount}", ROUNDS_USD)


# ------------------------------------------------------------------ operations
# Each operation: run(rows) -> list aligned to rows (row-wise ops) or a value.

def usd_clean(rows):
    out = []
    for r in rows:
        ok = _chain(f"{r['txn_id']}|{r['amount']}", ROUNDS_USD) == r["fingerprint"]
        out.append(round(float(r["amount"]) * RATES[r["date"][:7]][r["currency"]], 2) if ok else None)
    return out


def monthly_totals(rows):
    seen, per = set(), {}
    for r in rows:
        if r["txn_id"] in seen:
            continue
        seen.add(r["txn_id"])
        m = r["date"][:7]
        per.setdefault(m, []).append(float(r["amount"]) * RATES[m][r["currency"]])
    # fsum is correctly rounded, hence order-independent. The original per-row rounding was
    # order-dependent by a cent; the verifier caught it before the first run.
    return {m: round(math.fsum(per[m]), 2) for m in sorted(per)}


def fees(rows):
    out = []
    for r in rows:
        _chain(r["txn_id"], ROUNDS_FEE)
        out.append(round(float(r["amount"]) * CHANNELS[r["channel"]], 2))
    return out


def fees_refund(rows):   # W3: reads memo, but only when it is "REFUND"
    out = []
    for r in rows:
        _chain(r["txn_id"], ROUNDS_FEE)
        f = round(float(r["amount"]) * CHANNELS[r["channel"]], 2)
        out.append(-f if r["memo"] == "REFUND" else f)
    return out


def first_seen(rows):
    seen, out = set(), []
    for r in rows:
        out.append(r["txn_id"] not in seen)
        seen.add(r["txn_id"])
    return out


def product_mix(rows):
    seen, mix = set(), {}
    for r in rows:
        if r["txn_id"] not in seen:
            seen.add(r["txn_id"])
            mix[r["product"]] = mix.get(r["product"], 0) + 1
    return dict(sorted(mix.items()))


# true structure: (function, row_wise, order_insensitive) -- the oracle
TRUE_OPS = {
    "usd_clean": (usd_clean, True, False),
    "monthly_totals": (monthly_totals, False, True),
    "fees": (fees, True, False),
    "first_seen": (first_seen, False, False),
    "product_mix": (product_mix, False, True),
}
TRUE_DECL = {
    "usd_clean": {"reads": ["txn_id", "amount", "currency", "date", "fingerprint"], "row_wise": True, "order_insensitive": False},
    "monthly_totals": {"reads": ["txn_id", "amount", "currency", "date"], "row_wise": False, "order_insensitive": True},
    "fees": {"reads": ["txn_id", "amount", "channel"], "row_wise": True, "order_insensitive": False},
    "first_seen": {"reads": ["txn_id"], "row_wise": False, "order_insensitive": False},
    "product_mix": {"reads": ["txn_id", "product"], "row_wise": False, "order_insensitive": True},
}


def scenario(name):
    """-> (ops: name -> (fn, true_row_wise, true_order_insensitive), decls)."""
    ops = dict(TRUE_OPS)
    decl = json.loads(json.dumps(TRUE_DECL))
    if name == "W1":
        decl["usd_clean"]["reads"].remove("currency")
    elif name == "W2":
        decl["first_seen"]["row_wise"] = True
    elif name == "W3":
        ops["fees"] = (fees_refund, True, False)          # truth now depends on memo; decl unchanged
    elif name == "W4":
        decl["first_seen"]["order_insensitive"] = True
    elif name != "true":
        raise ValueError(name)
    return ops, decl


# ------------------------------------------------------------------ data + streams
def make_table(rng, n, start=0):
    rows = []
    for i in range(start, start + n):
        txn, amt = f"T{i:06d}", f"{rng.uniform(5, 900):.2f}"
        rows.append({"txn_id": txn, "region": rng.choice(["north", "south", "east", "west"]),
                     "product": rng.choice(PRODUCTS), "amount": amt,
                     "currency": rng.choice(list(RATES["2026-10"])),
                     "date": f"2026-{rng.choice(['10', '11'])}-{rng.randint(1, 28):02d}",
                     "fingerprint": sign(txn, amt), "memo": rng.choice(MEMOS),
                     "channel": rng.choice(list(CHANNELS))})
    for r in rng.sample(rows, max(1, n // 50)):          # tampered after signing
        r["amount"] = f"{float(r['amount']) * 3 + 1:.2f}"
    return rows


MIXES = {
    "realistic": {"append": .25, "memo": .15, "currency": .05, "reorder": .10, "amount": .15,
                  "product": .10, "channel": .10, "refund": .10},
    "relevant_only": {"amount": .5, "append": .5},
}


def stream(seed, mix, steps=25, n=600):
    """Deterministic: the initial table plus a list of edit functions, identical for every executor."""
    rng = random.Random(seed)
    table = make_table(rng, n)
    kinds, weights = zip(*MIXES[mix].items())
    edits, next_id = [], n
    for _ in range(steps):
        k = rng.choices(kinds, weights)[0]
        s = rng.randrange(1 << 30)
        if k == "append":
            new = make_table(random.Random(s), 20, start=next_id)
            next_id += 20
            edits.append((k, s, new))
        else:
            edits.append((k, s, None))
    return table, edits


def apply_edit(rows, edit):
    k, s, payload = edit
    rng = random.Random(s)
    rows = [dict(r) for r in rows]
    if k == "append":
        dup = [dict(r) for r in rng.sample(rows, 2)]        # some duplicate transactions arrive
        rows += [dict(r) for r in payload] + dup
    elif k == "reorder":
        rng.shuffle(rows)
    else:
        idx = rng.sample(range(len(rows)), {"memo": 30, "amount": 10, "product": 20,
                                            "channel": 20, "refund": 3, "currency": 5}[k])
        for i in idx:
            r = rows[i]
            if k == "memo":
                r["memo"] = rng.choice(MEMOS)
            elif k == "amount":                               # re-signed: a legitimate correction
                r["amount"] = f"{rng.uniform(5, 900):.2f}"
                r["fingerprint"] = sign(r["txn_id"], r["amount"])
            elif k == "product":
                r["product"] = rng.choice(PRODUCTS)
            elif k == "channel":
                r["channel"] = rng.choice(list(CHANNELS))
            elif k == "refund":
                r["memo"] = "REFUND"
            elif k == "currency":                             # booking correction
                r["currency"] = rng.choice([c for c in RATES["2026-10"] if c != r["currency"]])
    return rows


# ------------------------------------------------------------------ executors
def h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Naive:
    def __init__(self, ops, decl):
        self.ops = ops

    def step(self, rows):
        return {name: fn(rows) for name, (fn, _, _) in self.ops.items()}


class Content:
    """Bazel/Nix-style: one action key per operation over its whole input."""
    def __init__(self, ops, decl):
        self.ops, self.cache = ops, {}

    def run_op(self, name, fn, rows):
        key = (name, h(rows))
        if key not in self.cache:
            self.cache[key] = fn(rows)
        return self.cache[key]

    def step(self, rows):
        return {name: self.run_op(name, fn, rows) for name, (fn, _, _) in self.ops.items()}


class ContentSharded(Content):
    """Per-row content keys where the operation is TRULY row-wise (oracle structure)."""
    def __init__(self, ops, decl):
        super().__init__(ops, decl)
        self.rowcache = {}

    def step(self, rows):
        out = {}
        for name, (fn, row_wise, _) in self.ops.items():
            if not row_wise:
                out[name] = self.run_op(name, fn, rows)
                continue
            keys = [h(r) for r in rows]
            missing = [i for i, k in enumerate(keys) if (name, k) not in self.rowcache]
            if missing:
                for i, v in zip(missing, fn([rows[i] for i in missing])):
                    self.rowcache[(name, keys[i])] = v
            out[name] = [self.rowcache[(name, k)] for k in keys]
        return out


class Semantic:
    """Keys on declared semantics: projection to declared fields, per-row reuse for
    declared row-wise operations, order-free keys for declared order-insensitive ones."""
    verify = False

    def __init__(self, ops, decl, audit_rate=0.05, seed=0):
        self.ops, self.decl = ops, decl
        self.cache, self.rowcache = {}, {}
        self.trusted = {}                 # name -> bool (declaration accepted)
        self.fallback = Content(ops, decl)
        self.rng = random.Random(seed)
        self.audit_rate = audit_rate
        self.events = []                  # (step, op, what)
        self.t = 0

    def proj(self, name, r):
        return [r[f] for f in self.decl[name]["reads"]]

    def check(self, name, rows):
        """Property tests of the declaration on a sample. True = accepted."""
        return True

    def step(self, rows):
        self.t += 1
        out = {}
        for name, (fn, _, _) in self.ops.items():
            if name not in self.trusted:
                self.trusted[name] = self.check(name, rows)
                if not self.trusted[name]:
                    self.events.append((self.t, name, "rejected_at_verification"))
            if not self.trusted[name]:
                out[name] = self.fallback.run_op(name, fn, rows)
                continue
            d = self.decl[name]
            if d["row_wise"]:
                keys = [h(self.proj(name, r)) for r in rows]
                missing = [i for i, k in enumerate(keys) if (name, k) not in self.rowcache]
                reused = [i for i in range(len(rows)) if (name, keys[i]) in self.rowcache]
                if missing:
                    for i, v in zip(missing, fn([rows[i] for i in missing])):
                        self.rowcache[(name, keys[i])] = v
                if self.verify and reused and not self.audit_rows(name, fn, rows, keys, reused):
                    out[name] = self.fallback.run_op(name, fn, rows)
                    continue
                out[name] = [self.rowcache[(name, k)] for k in keys]
            else:
                p = [self.proj(name, r) for r in rows]
                if d["order_insensitive"]:
                    p = sorted(p, key=json.dumps)
                key = (name, h(p))
                hit = key in self.cache
                if not hit:
                    self.cache[key] = fn(rows)
                elif self.verify and self.rng.random() < self.audit_rate:
                    if fn(rows) != self.cache[key]:
                        self.revoke(name)
                        out[name] = self.fallback.run_op(name, fn, rows)
                        continue
                out[name] = self.cache[key]
        return out

    def audit_rows(self, name, fn, rows, keys, reused):
        k = max(1, int(len(reused) * self.audit_rate))
        pick = self.rng.sample(reused, min(k, len(reused)))
        fresh = fn([rows[i] for i in pick])
        if any(f != self.rowcache[(name, keys[i])] for i, f in zip(pick, fresh)):
            self.revoke(name)
            return False
        return True

    def revoke(self, name):
        self.trusted[name] = False
        self.rowcache = {k: v for k, v in self.rowcache.items() if k[0] != name}
        self.cache = {k: v for k, v in self.cache.items() if k[0] != name}
        self.events.append((self.t, name, "revoked_by_audit"))


class SemanticTrusted(Semantic):
    verify = False


class SemanticVerified(Semantic):
    verify = True
    SAMPLE = 40

    def check(self, name, rows):
        fn = self.ops[name][0]
        d = self.decl[name]
        sample = [dict(r) for r in self.rng.sample(rows, min(self.SAMPLE, len(rows)))]
        base = fn(sample)
        # 1. undeclared fields must not matter: perturb each, three ways
        for f in FIELDS:
            if f in d["reads"]:
                continue
            pool = [r[f] for r in rows]
            for trial in range(3):
                pert = [dict(r) for r in sample]
                for r in pert:
                    if trial == 0:
                        r[f] = self.rng.choice(pool)
                    elif trial == 1:
                        r[f] = str(r[f]) + "~"
                    else:
                        r[f] = "" if not str(r[f]).replace(".", "").isdigit() else str(float(r[f]) + 1.0)
                try:
                    if fn(pert) != base:
                        return False
                except Exception:      # perturbation broke the op => it reads the field
                    return False
        # 2. declared order-insensitivity
        if d["order_insensitive"]:
            for batch in (sample, sample + sample[:10]):     # plain, and with duplicated rows
                shuf = list(batch)
                self.rng.shuffle(shuf)
                if fn(shuf) != fn(batch):
                    return False
        # 3. declared row-wise: output per row independent of the other rows
        if d["row_wise"]:
            if not isinstance(base, list) or len(base) != len(sample):
                return False
            if [fn([r])[0] for r in sample[:8]] != base[:8]:
                return False
            if fn(sample + sample) != base + base:
                return False
        return True


class SemanticTargeted(SemanticVerified):
    """Run 2: same first-use verification, but audits only reuse that the DECLARATION enables.

    A reused row whose full content was already computed or audited is safe by content
    hashing alone. A reused row whose full content is new, but whose declared projection
    matches a cached one, is reused only because the declaration is trusted: audit those,
    a fraction `audit_rate` per step. Unaudited ones stay candidates on later steps."""

    def __init__(self, ops, decl, audit_rate=0.25, seed=0):
        super().__init__(ops, decl, audit_rate=audit_rate, seed=seed)
        self.known = {}     # op -> set of full-content hashes computed fresh or audited OK

    def step(self, rows):
        self.t += 1
        out = {}
        for name, (fn, _, _) in self.ops.items():
            if name not in self.trusted:
                self.trusted[name] = self.check(name, rows)
                if not self.trusted[name]:
                    self.events.append((self.t, name, "rejected_at_verification"))
            if not self.trusted[name]:
                out[name] = self.fallback.run_op(name, fn, rows)
                continue
            known = self.known.setdefault(name, set())
            d = self.decl[name]
            if d["row_wise"]:
                full = [h(r) for r in rows]
                keys = [h(self.proj(name, r)) for r in rows]
                missing = [i for i, k in enumerate(keys) if (name, k) not in self.rowcache]
                decl_enabled = [i for i in range(len(rows))
                                if (name, keys[i]) in self.rowcache and full[i] not in known]
                if missing:
                    for i, v in zip(missing, fn([rows[i] for i in missing])):
                        self.rowcache[(name, keys[i])] = v
                        known.add(full[i])
                if decl_enabled:
                    k = min(len(decl_enabled), max(1, math.ceil(self.audit_rate * len(decl_enabled))))
                    pick = self.rng.sample(decl_enabled, k)
                    fresh = fn([rows[i] for i in pick])
                    if any(f != self.rowcache[(name, keys[i])] for i, f in zip(pick, fresh)):
                        self.revoke(name)
                        self.known.pop(name, None)
                        out[name] = self.fallback.run_op(name, fn, rows)
                        continue
                    known.update(full[i] for i in pick)
                out[name] = [self.rowcache[(name, k)] for k in keys]
            else:
                full = h(rows)
                p = [self.proj(name, r) for r in rows]
                if d["order_insensitive"]:
                    p = sorted(p, key=json.dumps)
                key = (name, h(p))
                if key not in self.cache:
                    self.cache[key] = fn(rows)
                    known.add(full)
                elif full not in known and self.rng.random() < self.audit_rate:
                    if fn(rows) != self.cache[key]:
                        self.revoke(name)
                        self.known.pop(name, None)
                        out[name] = self.fallback.run_op(name, fn, rows)
                        continue
                    known.add(full)
                out[name] = self.cache[key]
        return out


def _targeted(rate):
    return lambda ops, decl, seed=0: SemanticTargeted(ops, decl, audit_rate=rate, seed=seed)


EXECUTORS = {"naive": Naive, "content": Content, "content_sharded": ContentSharded,
             "semantic_trusted": SemanticTrusted, "semantic_verified": SemanticVerified,
             "targeted_a10": _targeted(0.10), "targeted_a25": _targeted(0.25),
             "targeted_a50": _targeted(0.50)}
