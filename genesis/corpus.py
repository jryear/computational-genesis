"""Evaluator-owned deterministic corpus. NEVER provided through design tools/images."""
import random


def public_cases():
    return [
        {"name": "public-ledger", "messages": [
            {"op": "balance", "key": "x"},
            {"op": "credit", "id": "a", "key": "x", "delta": 5},
            {"op": "credit", "id": "b", "key": "x", "delta": -2},
            {"op": "credit", "id": "a", "key": "x", "delta": 5},
            {"op": "credit", "id": "a", "key": "y", "delta": 5},
            {"op": "balance", "key": "x"}]},
        {"name": "public-dependencies", "messages": [
            {"op": "define", "id": "child", "parents": ["parent"], "weight": 3},
            {"op": "run"}, {"op": "result", "id": "child"},
            {"op": "define", "id": "parent", "parents": [], "weight": 2},
            {"op": "run"},
            {"op": "define", "id": "parent", "parents": [], "weight": 99},
            {"op": "result", "id": "child"}]}
    ]


def ledger(seed):
    rng = random.Random(seed)
    accepted = []
    messages = [{"op": "balance", "key": "absent"}]
    for i in range(64):
        message = {"op": "credit", "id": "id" + str(i), "key": "k" + str(rng.randrange(7)), "delta": rng.randrange(-10**8, 10**8)}
        if i % 5 == 0:
            message["delta"] = 0
        messages.append(message); accepted.append(message)
        if i % 3 == 0:
            messages.append(dict(rng.choice(accepted)))
        if i % 7 == 0:
            conflict = dict(rng.choice(accepted)); conflict["delta"] += 1
            messages.append(conflict)
        if i % 4 == 0:
            messages.append({"op": "balance", "key": message["key"]})
    messages += [{"op": "balance", "key": "k" + str(i)} for i in range(7)]
    return messages


def dependencies(seed):
    rng = random.Random(seed)
    jobs = []
    for i in range(32):
        parents = rng.sample(["j" + str(n) for n in range(i)], min(i, rng.randrange(4)))
        jobs.append({"op": "define", "id": "j" + str(i), "parents": parents, "weight": rng.randrange(-99, 100)})
    rng.shuffle(jobs)
    messages = []
    for i, job in enumerate(jobs):
        messages.append(job)
        if i % 3 == 0:
            messages.extend([{"op": "run"}, {"op": "result", "id": job["id"]}])
        if i % 5 == 0:
            messages.append(dict(job))
            conflict = dict(job); conflict["weight"] += 1; messages.append(conflict)
    messages.extend([
        {"op": "define", "id": "cycle_a", "parents": ["cycle_b"], "weight": 3},
        {"op": "define", "id": "cycle_b", "parents": ["cycle_a"], "weight": 7},
        {"op": "define", "id": "missing", "parents": ["absent"], "weight": 5},
        {"op": "run"}, {"op": "result", "id": "cycle_a"}, {"op": "result", "id": "missing"}])
    return messages


def hidden_cases():
    cases = []
    for seed in (97131, 118903):
        cases.append({"name": "ledger-" + str(seed), "messages": ledger(seed)})
    for seed in (73193, 88129):
        cases.append({"name": "dependencies-" + str(seed), "messages": dependencies(seed)})
    for seed in (192811, 293729):
        left, right = ledger(seed), dependencies(seed)
        messages = []
        for i in range(max(len(left), len(right))):
            if i < len(left): messages.append(left[i])
            if i < len(right): messages.append(right[i])
        messages += [{"op": "credit", "id": "j0", "key": "j0", "delta": 4},
                     {"op": "result", "id": "j0"}, {"op": "balance", "key": "j0"}]
        cases.append({"name": "mixed-" + str(seed), "messages": messages})
    return cases
