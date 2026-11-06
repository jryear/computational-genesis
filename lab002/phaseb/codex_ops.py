# Authored by Codex (codex-cli 0.167.0, default model) from phaseb/author_prompt.md.
# Verbatim; not edited. The author never saw semexec.py or the verifier.
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


TRUTH = {
    "op_1": {
        "reads": ["channel", "currency", "amount"],
        "row_wise": True,
        "order_insensitive": True,
    },
    "op_2": {
        "reads": ["region", "amount", "currency"],
        "row_wise": True,
        "order_insensitive": True,
    },
    "op_3": {
        "reads": ["channel", "memo", "date"],
        "row_wise": True,
        "order_insensitive": True,
    },
    "op_4": {
        "reads": ["currency", "amount"],
        "row_wise": True,
        "order_insensitive": False,
    },
    "op_5": {
        "reads": ["region", "product", "currency", "amount"],
        "row_wise": False,
        "order_insensitive": True,
    },
    "op_6": {
        "reads": ["txn_id", "fingerprint"],
        "row_wise": False,
        "order_insensitive": True,
    },
    "op_7": {
        "reads": ["txn_id", "amount", "currency", "date"],
        "row_wise": False,
        "order_insensitive": False,
    },
    "op_8": {
        "reads": ["memo", "currency", "amount"],
        "row_wise": False,
        "order_insensitive": True,
    },
}
