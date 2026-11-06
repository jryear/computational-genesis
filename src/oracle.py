"""Supervisor-only grade: independently expressed and never shipped to the model."""
from collections import defaultdict


def expected(rows):
    buckets = defaultdict(list)
    for row in rows:
        if row["active"]:
            buckets[row["team"]].append((row["record"], row["minor"]))
    return {team: sum(dict(values).values()) for team, values in sorted(buckets.items())}


def grade(rows, result):
    return type(result) is dict and all(type(v) is int for v in result.values()) and result == expected(rows)
