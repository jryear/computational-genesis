"""Public synthetic workload. No access to host data or environment variables."""
import random


def records(seed=17):
    rng = random.Random(seed)
    rows = []
    for i in range(96):
        row = {"record": f"r{i}", "team": rng.choice(["cedar", "birch", "elm"]),
               "minor": rng.randrange(-300, 1800), "active": rng.random() > .18}
        rows.append(row)
        if i % 7 == 0:
            rows.append(dict(row))
    rng.shuffle(rows)
    return rows
