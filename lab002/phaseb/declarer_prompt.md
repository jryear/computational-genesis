Below are 8 Python functions. Each takes `rows`: a list of dict rows whose values are all strings, with fields: txn_id, region, product, amount, currency, date, fingerprint, memo, channel.

For each function, declare its semantics using these exact definitions:
- reads: every field whose value can ever change the output (including fields used only under some condition).
- row_independent: the output is a list with one element per input row, and each element depends only on that row (not on other rows or their order).
- order_insensitive: permuting the input rows never changes the output (compare the outputs exactly as returned).

A runtime will reuse cached results based on your declaration. An omitted field can make it serve stale results; an extra field only costs performance.

Reply with ONLY a JSON object, no prose, no code fences:
{"op_1": {"reads": [...], "row_independent": true|false, "order_insensitive": true|false}, ... "op_8": {...}}

```python
from fractions import Fraction


def op_1(rows):
    """Assign payment approval queues using channel and currency-specific limits."""
    result = []
    for row in rows:
        if row["channel"] == "wire":
            limit = 1_000_000 if row["currency"] == "JPY" else 10_000
            queue = (
                "treasury_review"
                if Fraction(row["amount"]) >= limit
                else "wire_operations"
            )
        else:
            queue = "standard_processing"
        result.append(queue)
    return result


def op_2(rows):
    """Estimate regional USD exposure using fixed planning exchange rates."""
    rates = {
        "USD": Fraction(1),
        "EUR": Fraction("1.08"),
        "GBP": Fraction("1.27"),
        "JPY": Fraction("0.0067"),
    }
    return [
        {
            "region": row["region"],
            "usd_exposure": float(
                Fraction(row["amount"]) * rates[row["currency"]]
            ),
        }
        for row in rows
    ]


def op_3(rows):
    """Prepare channel-specific settlement instructions for operations staff."""
    result = []
    for row in rows:
        channel = row["channel"]
        if channel == "wire":
            memo = row["memo"].strip()
            instruction = {
                "desk": "treasury",
                "reference": memo if memo else "reference_required",
            }
        elif channel == "pos":
            instruction = {
                "desk": "merchant_settlement",
                "batch_date": row["date"],
            }
        else:
            instruction = {"desk": "online_settlement"}
        result.append(instruction)
    return result


def op_4(rows):
    """Track cumulative booked amounts within each currency as transactions arrive."""
    balances = {}
    result = []
    for row in rows:
        currency = row["currency"]
        balances[currency] = (
            balances.get(currency, Fraction(0)) + Fraction(row["amount"])
        )
        result.append({
            "currency": currency,
            "running_amount": float(balances[currency]),
        })
    return result


def op_5(rows):
    """Summarize booked revenue by region, product, and currency."""
    totals = {}
    counts = {}
    for row in rows:
        key = (row["region"], row["product"], row["currency"])
        totals[key] = totals.get(key, Fraction(0)) + Fraction(row["amount"])
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "region": region,
            "product": product,
            "currency": currency,
            "transaction_count": counts[(region, product, currency)],
            "total_amount": float(totals[(region, product, currency)]),
        }
        for region, product, currency in sorted(totals)
    ]


def op_6(rows):
    """Identify repeated transaction identities for duplicate-booking review."""
    counts = {}
    for row in rows:
        key = (row["txn_id"], row["fingerprint"])
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "txn_id": txn_id,
            "fingerprint": fingerprint,
            "occurrences": counts[(txn_id, fingerprint)],
            "excess_bookings": counts[(txn_id, fingerprint)] - 1,
        }
        for txn_id, fingerprint in sorted(counts)
        if counts[(txn_id, fingerprint)] > 1
    ]


def op_7(rows):
    """Build a transaction register using the last received version of each booking."""
    latest = {}
    for row in rows:
        latest[row["txn_id"]] = {
            "amount": row["amount"],
            "currency": row["currency"],
            "date": row["date"],
        }
    return [
        {"txn_id": txn_id, **latest[txn_id]}
        for txn_id in sorted(latest)
    ]


def op_8(rows):
    """Measure booked amounts awaiting fulfillment because of backorders."""
    totals = {}
    counts = {}
    for row in rows:
        if row["memo"].strip().casefold() == "backorder":
            currency = row["currency"]
            totals[currency] = (
                totals.get(currency, Fraction(0)) + Fraction(row["amount"])
            )
            counts[currency] = counts.get(currency, 0) + 1
    return [
        {
            "currency": currency,
            "backorder_count": counts[currency],
            "booked_amount": float(totals[currency]),
        }
        for currency in sorted(totals)
    ]
```