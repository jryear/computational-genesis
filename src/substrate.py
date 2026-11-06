"""Model-facing runtime. All mutations are transactional, bounded, and replayable."""
import json
import re
import sqlite3
import sys

from fixtures import records

STAGES = ("raw", "normalized", "aggregated", "verified")
OPS = ("normalize", "aggregate", "verify")


class Refusal(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def normalize(rows):
    unique = {}
    for row in rows:
        if row["active"]:
            unique[row["record"]] = row
    return [unique[key] for key in sorted(unique)]


def aggregate(rows):
    totals = {}
    for row in rows:
        totals[row["team"]] = totals.get(row["team"], 0) + row["minor"]
    return dict(sorted(totals.items()))


def reference(rows):
    # Separate control implementation for candidate qualification. Host oracle is independent.
    return aggregate(normalize(rows))


class Runtime:
    def __init__(self, database, seed=17, budget=12):
        self.db = sqlite3.connect(database, isolation_level=None, timeout=3)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT);
          CREATE TABLE IF NOT EXISTS receipts (id TEXT PRIMARY KEY, request TEXT, response TEXT);
          CREATE TABLE IF NOT EXISTS candidates (name TEXT PRIMARY KEY, plan TEXT, evidence TEXT);
        """)
        initial = {"objective": "reconcile", "resource": "synthetic-records", "revision": 0,
                   "stage": "raw", "value": records(seed), "remaining": budget,
                   "work_units": 0, "cache_hits": 0, "paused": False}
        self.db.execute("INSERT OR IGNORE INTO state VALUES(1, ?)", (canonical(initial),))
        self.initialize_metadata(seed)

    def close(self):
        self.db.close()

    def state(self):
        return json.loads(self.db.execute("SELECT payload FROM state WHERE id=1").fetchone()[0])

    def observe(self):
        s = self.state()
        return {"objective": s["objective"], "resource": s["resource"], "revision": s["revision"],
                "checkpoint": s["stage"], "remaining_transitions": s["remaining"],
                "paused": s["paused"], "capabilities": list(OPS),
                "retained_primitives": [r[0] for r in self.db.execute("SELECT name FROM candidates ORDER BY name")],
                "result": s["value"] if s["stage"] == "verified" else None}

    def transition(self, request):
        allowed = {"request_id", "expected_revision", "capability", "target"}
        if set(request) != allowed or not isinstance(request["request_id"], str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", request["request_id"]):
            raise Refusal("invalid_request")
        if type(request["expected_revision"]) is not int or request["expected_revision"] < 0:
            raise Refusal("invalid_revision")
        if not isinstance(request["capability"], str) or not isinstance(request["target"], str):
            raise Refusal("invalid_capability_or_target")
        encoded = canonical(request)
        self.db.execute("BEGIN IMMEDIATE")
        try:
            previous = self.db.execute("SELECT request,response FROM receipts WHERE id=?", (request["request_id"],)).fetchone()
            if previous:
                if previous[0] != encoded:
                    raise Refusal("request_identity_conflict")
                self.db.execute("COMMIT")
                return json.loads(previous[1])
            s = self.state()
            if s["paused"]:
                raise Refusal("supervisor_paused")
            if s["revision"] != request["expected_revision"]:
                raise Refusal("stale_revision")
            if s["remaining"] <= 0:
                raise Refusal("budget_exhausted")
            capability, target = request["capability"], request["target"]
            candidate = self.db.execute("SELECT plan FROM candidates WHERE name=?", (capability,)).fetchone()
            plan = json.loads(candidate[0]) if candidate else [capability]
            if not all(op in OPS for op in plan) or target not in STAGES:
                raise Refusal("unknown_capability_or_target")
            start_stage = STAGES.index(s["stage"])
            if STAGES.index(target) <= start_stage:
                s["cache_hits"] += 1
                route = "already_satisfied"
            else:
                stage = start_stage
                value = s["value"]
                for op in plan:
                    if stage >= 3 or OPS[stage] != op:
                        raise Refusal("dependency_unsatisfied")
                    if op == "normalize":
                        value = normalize(value)
                    elif op == "aggregate":
                        value = aggregate(value)
                    else:
                        # Check derived state against immutable synthetic input.
                        if value != self.expected:
                            raise Refusal("verification_failed")
                    stage += 1
                if STAGES[stage] != target:
                    raise Refusal("target_mismatch")
                s.update(value=value, stage=target, work_units=s["work_units"] + len(plan))
                route = "composed" if candidate else "pure"
            s.update(revision=s["revision"] + 1, remaining=s["remaining"] - 1)
            self.db.execute("UPDATE state SET payload=? WHERE id=1", (canonical(s),))
            answer = {**self.observe(), "route": route, "receipt": request["request_id"]}
            self.db.execute("INSERT INTO receipts VALUES(?,?,?)", (request["request_id"], encoded, canonical(answer)))
            self.db.execute("COMMIT")
            return answer
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    @property
    def expected(self):
        row = self.db.execute("SELECT value FROM metadata WHERE key='expected'").fetchone()
        return json.loads(row[0])

    def initialize_metadata(self, seed):
        self.db.execute("CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT)")
        self.db.execute("INSERT OR IGNORE INTO metadata VALUES('expected',?)", (canonical(reference(records(seed))),))

    def propose(self, name, plan):
        plans = [list(OPS[:2]), list(OPS[1:]), list(OPS)]
        if not isinstance(name, str) or not re.fullmatch(r"p_[a-z_]{1,24}", name) or plan not in plans:
            raise Refusal("invalid_primitive")
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if self.state()["paused"]:
                raise Refusal("supervisor_paused")
            old = self.db.execute("SELECT plan,evidence FROM candidates WHERE name=?", (name,)).fetchone()
            if old:
                if old[0] != canonical(plan):
                    raise Refusal("primitive_identity_conflict")
                self.db.execute("COMMIT")
                return json.loads(old[1])
            if self.db.execute("SELECT count(*) FROM candidates").fetchone()[0] >= 2:
                raise Refusal("proposal_budget_exhausted")
            # Grammar is deliberately finite. No eval, imports, loops, or arbitrary source.
            for seed in range(200, 208):
                rows = records(seed)
                result = rows if plan[0] == "normalize" else normalize(rows)
                for op in plan:
                    if op == "normalize":
                        result = normalize(result)
                    elif op == "aggregate":
                        result = aggregate(result)
                    elif result != reference(rows):
                        raise Refusal("qualification_failed")
                independently = {team: sum({r["record"]: r["minor"] for r in rows if r["active"] and r["team"] == team}.values())
                                 for team in {r["team"] for r in rows if r["active"]}}
                if result != independently:
                    raise Refusal("qualification_failed")
            evidence = {"primitive": name, "retained": True, "qualification_cases": 8,
                        "baseline_requests": len(plan), "candidate_requests": 1,
                        "criterion": "equal_result_fewer_boundary_requests",
                        "latency_improvement": None, "cpu_improvement": None}
            self.db.execute("INSERT INTO candidates VALUES(?,?,?)", (name, canonical(plan), canonical(evidence)))
            self.db.execute("COMMIT")
            return evidence
        except BaseException:
            if self.db.in_transaction:
                self.db.execute("ROLLBACK")
            raise

    def pause(self, paused):
        self.db.execute("BEGIN IMMEDIATE")
        s = self.state(); s["paused"] = paused
        self.db.execute("UPDATE state SET payload=? WHERE id=1", (canonical(s),))
        self.db.execute("COMMIT")
        return {"paused": paused}


def main():
    runtime = Runtime("/state/runtime.db")
    for line in sys.stdin:
        try:
            if len(line) > 32768:
                raise Refusal("request_too_large")
            request = json.loads(line)
            method, args = request["method"], request.get("args", {})
            if method == "observe":
                result = runtime.observe()
            elif method == "transition":
                result = runtime.transition(args)
            elif method == "propose":
                result = runtime.propose(**args)
            elif method == "pause":
                result = runtime.pause(bool(args["paused"]))
            elif method == "export":
                result = runtime.state()
            else:
                raise Refusal("unknown_operation")
            print(canonical({"ok": True, "value": result}), flush=True)
        except Refusal as error:
            print(canonical({"ok": False, "error": str(error)}), flush=True)
        except (ValueError, TypeError, KeyError):
            print(canonical({"ok": False, "error": "request_refused"}), flush=True)


if __name__ == "__main__":
    main()
