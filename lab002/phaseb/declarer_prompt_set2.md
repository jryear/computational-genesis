Below are 8 Python functions. Each takes `rows`: a list of dict rows whose values are all strings, with fields: txn_id, region, product, amount, currency, date, fingerprint, memo, channel.

For each function, declare its semantics using these exact definitions:
- reads: every field whose value can ever change the output (including fields used only under some condition).
- row_independent: the output is a list with one element per input row, and each element depends only on that row (not on other rows or their order).
- order_insensitive: permuting the input rows never changes the output (compare the outputs exactly as returned).

A runtime will reuse cached results based on your declaration. An omitted field can make it serve stale results; an extra field only costs performance.

Reply with ONLY a JSON object, no prose, no code fences:
{"op_1": {"reads": [...], "row_independent": true|false, "order_insensitive": true|false}, ... "op_8": {...}}

```python
from datetime import date, timedelta
from fractions import Fraction


def op_1(rows):
    """Prepare rounded payment amounts and operational routing labels."""
    route_fields = {"web": "region", "pos": "product", "wire": "currency"}
    rounding = {
        "JPY": lambda amount: round(amount) * 100,
        "USD": lambda amount: round(amount * 100),
        "EUR": lambda amount: round(amount * 100),
        "GBP": lambda amount: round(amount * 100),
    }
    result = []
    for row in rows:
        currency = row["currency"]
        channel = row["channel"]
        cents = rounding[currency](Fraction(row["amount"]))
        route = row[route_fields[channel]]
        result.append({"route": f"{channel}:{route}", "cents": cents})
    return result


def op_2(rows):
    """Calculate invoice due dates from payment terms and channel defaults."""
    defaults = {"web": 7, "pos": 0, "wire": 30}
    result = []
    for row in rows:
        memo = row["memo"]
        try:
            if not memo.startswith("net"):
                raise ValueError("No explicit payment term")
            days = int(memo[3:])
            if not 0 <= days <= 365:
                raise ValueError("Payment term outside supported range")
        except ValueError:
            days = defaults[row["channel"]]
        issued = date.fromisoformat(row["date"])
        result.append((issued + timedelta(days=days)).isoformat())
    return result


def op_3(rows):
    """Track the running posted balance in each transaction currency."""
    balances = {}
    result = []
    for row in rows:
        currency = row["currency"]
        amount = Fraction(row["amount"])
        if row["memo"] == "refund":
            amount = -amount
        balances[currency] = balances.get(currency, Fraction(0)) + amount
        result.append({
            "currency": currency,
            "balance": float(balances[currency]),
        })
    return result


def op_4(rows):
    """Summarize payment totals after collapsing repeated posting identities."""
    postings = {
        (row["txn_id"], row["fingerprint"], row["currency"], row["amount"])
        for row in rows
    }
    totals = {}
    counts = {}
    for _, _, currency, amount in postings:
        totals[currency] = totals.get(currency, Fraction(0)) + Fraction(amount)
        counts[currency] = counts.get(currency, 0) + 1
    return {
        currency: {"count": counts[currency], "total": float(totals[currency])}
        for currency in sorted(totals)
    }


def op_5(rows):
    """Select the highest-value transactions for the daily review queue."""
    if not rows:
        return []
    ranked = sorted(
        rows,
        key=lambda row: (
            -Fraction(row["amount"]),
            row["date"],
            row["fingerprint"],
            row["txn_id"],
        ),
    )
    return [row["txn_id"] for row in ranked[:10]]


def op_6(rows):
    """Aggregate regional exposure while honoring approved large-value waivers."""
    exposure = {}
    for row in rows:
        amount = Fraction(row["amount"])
        if abs(amount) > 1_000_000:
            if row["memo"] == "treasury:waived":
                continue
        key = (row["region"], row["currency"])
        exposure[key] = exposure.get(key, Fraction(0)) + amount
    return [
        {"region": region, "currency": currency, "exposure": float(exposure[key])}
        for key in sorted(exposure)
        for region, currency in [key]
    ]


def op_7(rows):
    """Identify transaction identifiers associated with conflicting fingerprints."""
    fingerprints = {}
    for row in rows:
        txn_id = row["txn_id"]
        fingerprints.setdefault(txn_id, set()).add(row["fingerprint"])
    return {
        txn_id: sorted(values)
        for txn_id, values in sorted(fingerprints.items())
        if len(values) > 1
    }


def op_8(rows):
    """Build contiguous settlement batches from the incoming posting stream."""
    batches = []
    current_key = None
    count = 0
    total = Fraction(0)
    for row in rows:
        key = (row["channel"], row["currency"])
        if key != current_key:
            if current_key is not None:
                batches.append({
                    "channel": current_key[0],
                    "currency": current_key[1],
                    "count": count,
                    "total": float(total),
                })
            current_key, count, total = key, 0, Fraction(0)
        count += 1
        total += Fraction(row["amount"])
    if current_key is not None:
        batches.append({
            "channel": current_key[0],
            "currency": current_key[1],
            "count": count,
            "total": float(total),
        })
    return batches
```