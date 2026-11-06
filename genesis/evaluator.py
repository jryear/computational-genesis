"""Frozen deterministic grading and OS measurements. No model-auth dependencies."""
import ast
import base64
import hashlib
import json
from pathlib import Path
import statistics
import tempfile
import time

from .controls import POSITIVE, WRONG, BROKEN_RESTORE, DUPLICATE_EFFECT, HOSTILE
from .corpus import public_cases, hidden_cases
from .isolation import Boundary, ExecutionError
from .oracle import Oracle, same

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ("HYPOTHESIS.md", "SUBSTRATE.md", "EVALUATION.md", "ARCHITECTURE.md", "RUNBOOK.md")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def freeze_manifest():
    files = [ROOT / name for name in PROTOCOL] + sorted((ROOT / "genesis").glob("*.py"))
    files += [ROOT / "src/codex_broker.py", ROOT / "src/model-policy.json"]
    files += sorted((ROOT / "tests").glob("test_genesis*.py"))
    return {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in files}


def verify_freeze(manifest):
    if freeze_manifest() != manifest:
        raise RuntimeError("Frozen protocol/evaluator/broker changed; new experiment required")


def source_complexity(source):
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {"source_bytes": len(source.encode()), "syntax_valid": False}
    nodes = list(ast.walk(tree))
    return {"source_bytes": len(source.encode()), "syntax_valid": True, "ast_nodes": len(nodes),
            "functions": sum(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in nodes),
            "classes": sum(isinstance(n, ast.ClassDef) for n in nodes),
            "imports": sum(isinstance(n, (ast.Import, ast.ImportFrom)) for n in nodes)}


def run_suite(image, source, cases, *, faults=False):
    started = time.perf_counter()
    trace, segments, failures, snapshots = [], [], [], []
    boundary = None
    configuration = None

    def open_boundary(snapshot=None):
        nonlocal boundary, configuration
        boundary = Boundary(image, source)
        configuration = boundary.configuration()
        boundary.request({"op": "load", "snapshot": snapshot})

    def close_segment():
        nonlocal boundary
        if boundary is not None:
            try:
                segments.append(boundary.measure())
            except Exception:
                failures.append({"error": "resource_measurement_failed"})
            finally:
                boundary.close(); boundary = None

    def checkpoint(case, reason):
        value = boundary.request({"op": "snapshot"})
        data = base64.b64decode(value["data"], validate=True)
        if len(data) > 1048576 or len(data) != value["bytes"]:
            raise ExecutionError("invalid_checkpoint")
        snapshots.append({"case": case, "reason": reason, "bytes": len(data),
                          "sha256": digest(data), "base64": value["data"]})
        return value["data"]

    try:
        for case_index, case in enumerate(cases):
            oracle = Oracle()
            try:
                if boundary is None:
                    open_boundary()
                else:
                    boundary.request({"op": "load", "snapshot": None})
                seen_credit_ids = set()
                fault_index = None
                if faults and case_index in (0, 4):
                    for i, item in enumerate(case["messages"]):
                        if item["op"] == "credit":
                            if i >= 16 and item["delta"] != 0 and item["id"] not in seen_credit_ids:
                                fault_index = i
                                break
                            seen_credit_ids.add(item["id"])
                for index, message in enumerate(case["messages"]):
                    expected = oracle.step(message)
                    fault = index == fault_index
                    prefix = checkpoint(case["name"], "pre_fault") if fault else None
                    response = boundary.request({"op": "handle", "message": message})
                    row = {"case": case["name"], "index": index, "input": message,
                           "expected": expected, "actual": response, "correct": same(expected, response)}
                    trace.append(row)
                    if not row["correct"]:
                        failures.append({"case": case["name"], "index": index, "error": "wrong_response"})
                    if fault:
                        mode = "uncommitted_rollback" if case_index == 0 else "committed_lost_reply"
                        saved = checkpoint(case["name"], "committed_reply_lost") if case_index == 4 else prefix
                        close_segment()  # Forced container death: independent of candidate behavior.
                        open_boundary(saved)
                        retry = boundary.request({"op": "handle", "message": message})
                        correct = same(expected, retry)
                        trace.append({"case": case["name"], "index": index, "fault": mode,
                                      "input": message, "expected": expected, "actual": retry, "correct": correct})
                        if not correct:
                            failures.append({"case": case["name"], "index": index, "error": "recovery_failed"})
                saved = checkpoint(case["name"], "case_end")
                boundary.request({"op": "load", "snapshot": saved})
                replay = case["messages"][-1]
                expected = oracle.step(replay)
                actual = boundary.request({"op": "handle", "message": replay})
                correct = same(actual, expected)
                trace.append({"case": case["name"], "fault": "snapshot_reload", "input": replay,
                              "expected": expected, "actual": actual, "correct": correct})
                if not correct:
                    failures.append({"case": case["name"], "error": "restore_failed"})
            except Exception as error:
                failures.append({"case": case["name"], "error": str(error)[:128] if isinstance(error, ExecutionError) else type(error).__name__})
                close_segment()
    finally:
        close_segment()
    return {"passed": not failures, "source_sha256": digest(source.encode()), "failures": failures,
            "trace": trace, "checkpoints": snapshots, "segments": segments, "configuration": configuration,
            "metrics": {"elapsed_seconds": time.perf_counter()-started,
                        "cpu_usec": sum(s["cpu_usec"] for s in segments),
                        "active_request_seconds": sum(s["active_request_seconds"] for s in segments),
                        "memory_peak_bytes": max((s["memory_peak_bytes"] for s in segments), default=0),
                        "tasks_peak": max((s["tasks_peak"] for s in segments), default=0),
                        "checkpoint_bytes": sum(s["bytes"] for s in snapshots),
                        "transport_bytes": sum(s["transport_bytes"] for s in segments)},
            "complexity": source_complexity(source)}


def controls(image):
    outcomes = {}
    for name, source in (("positive", POSITIVE), ("wrong_result", WRONG),
                         ("broken_restore", BROKEN_RESTORE), ("duplicate_effect", DUPLICATE_EFFECT)):
        outcomes[name] = run_suite(image, source, hidden_cases(), faults=True)
    with tempfile.TemporaryDirectory(prefix="genesis-host-canary-") as directory:
        marker = Path(directory) / "marker"
        marker.write_text("synthetic canary; not a credential")
        with Boundary(image, HOSTILE) as boundary:
            config = boundary.configuration()
            boundary.request({"op": "load", "snapshot": None})
            response = boundary.request({"op": "handle", "message": {"host_canary": str(marker)}})
            resource = boundary.measure()
        outcomes["hostile"] = {"observed": response, "configuration": config, "resources": resource,
                               "host_canary_unchanged": marker.read_text() == "synthetic canary; not a credential"}
    admitted = (outcomes["positive"]["passed"] and all(not outcomes[name]["passed"] for name in
                ("wrong_result", "broken_restore", "duplicate_effect"))
                and all(value is False for value in response.values()) and outcomes["hostile"]["host_canary_unchanged"])
    return {"admitted": admitted, "outcomes": outcomes}


def adjudicate(trials):
    groups = {role: [t for t in trials if t["role"] == role] for role in ("baseline", "inventor")}
    correct = {role: len(items) == 3 and all(t["result"]["passed"] for t in items) for role, items in groups.items()}
    medians = {role: {metric: statistics.median(t["result"]["metrics"][metric] for t in items)
                     for metric in ("cpu_usec", "checkpoint_bytes", "active_request_seconds")}
               for role, items in groups.items() if items}
    eligible = all(correct.values())
    ratios = {key: medians["inventor"][key] / medians["baseline"][key] if medians["baseline"][key] else None
              for key in medians.get("baseline", {})} if eligible else None
    h2 = ("supported_for_pair" if ratios["cpu_usec"] <= .8 and ratios["checkpoint_bytes"] <= .75 and
          ratios["active_request_seconds"] <= 1.10 else "falsified_for_pair") if eligible else "ineligible_correctness_gate"
    return {"H1_inventor": "supported_for_submission" if correct["inventor"] else "falsified_for_submission",
            "baseline_correct": correct["baseline"], "H2": h2, "median_metrics": medians,
            "inventor_over_baseline": ratios, "population_claim": None, "dollar_cost": None}
