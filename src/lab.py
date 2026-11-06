"""Human/supervisor CLI; never given to an abstract agent."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from .fixtures import records
from .oracle import grade
from .supervisor import Sandbox, build


def provenance():
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "src").glob("*.py")) + [root / "src/model-policy.json", root / "Dockerfile"]
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def request(revision, capability, target, ident=None):
    return {"request_id": ident or "step_" + str(revision), "expected_revision": revision,
            "capability": capability, "target": target}


def check():
    source = provenance()
    build()
    with Sandbox() as box:
        isolation = box.inspect()
        assert isolation["network"] == "none" and isolation["read_only"]
        assert isolation["user"] == "65532:65532" and isolation["cap_drop"] == ["ALL"]
        assert all(m["type"] == "volume" and m["destination"] == "/state" for m in isolation["mounts"])
        probe = box.shell("python - <<'PY'\nimport os,socket\nassert not any('TOKEN' in n or 'KEY' in n or n == 'CODEX_HOME' for n in os.environ)\nassert not os.path.exists('/var/run/docker.sock')\nassert not os.path.exists('/opt/lab/oracle.py')\ntry:\n open('/outside-write', 'w')\n raise AssertionError('root writable')\nexcept OSError: pass\ns=socket.socket(); s.settimeout(.2)\nassert s.connect_ex(('1.1.1.1',443)) != 0\nprint('isolation probes passed')\nPY")
        assert probe["exit_code"] == 0, probe
        before = box.request("observe")
        assert before["value"]["revision"] == 0
        first = request(0, "normalize", "normalized")
        committed = box.request("transition", first)
        assert committed["ok"]
        box.restart()  # Actual host container/process interruption, durable volume preserved.
        assert box.request("transition", first) == committed
        assert box.request("observe")["value"]["revision"] == 1
        stale = box.request("transition", request(0, "aggregate", "aggregated", "stale"))
        assert not stale["ok"]
        box.request("pause", {"paused": True})
        assert not box.request("transition", request(1, "aggregate", "aggregated"))["ok"]
        box.request("pause", {"paused": False})
        assert box.request("transition", request(1, "aggregate", "aggregated"))["ok"]
        final = box.request("transition", request(2, "verify", "verified"))
        assert grade(records(), final["value"]["result"])
        data = box.request("export")["value"]
        assert data["work_units"] == 3 and data["remaining"] == 9
        metrics = box.metrics()
    with Sandbox() as box:
        proposal = box.request("propose", {"name": "p_reconcile", "plan": ["normalize", "aggregate", "verify"]})
        assert proposal["ok"]
        outcome = box.request("transition", request(0, "p_reconcile", "verified"))
        assert grade(records(), outcome["value"]["result"])
    return {"kind": "deterministic_integration_check", "source_sha256": source,
            "passed": True, "isolation": isolation,
            "checks": ["container_boundary", "network_denial", "immutable_root", "no_auth_environment",
                       "no_supervisor_oracle", "real_restart", "exact_replay", "stale_revision_denial",
                       "supervisor_pause", "independent_result_grade", "qualified_composition"],
            "host_metrics": metrics, "performance_conclusion": None}


DOMAIN = ("Objective: reconcile synthetic-records. Keep active records, deduplicate by record identity, "
          "sum integer minor units by team, and reach verified completion. The same synthetic input, "
          "12 tool-call allowance, 120 second turn deadline, and container limits apply to every arm. ")


def live(model, interrupt=False, repetitions=1):
    from .codex_broker import CodexBroker
    source = provenance()
    build()
    results = []
    # Rotate arm order per repetition. Pilot only; multiple held-out tasks are still required.
    arms = ["conventional", "abstract", "discovery"]
    for repeat in range(repetitions):
        for arm in arms[repeat % 3:] + arms[:repeat % 3]:
            with Sandbox() as box:
                setup = time.monotonic()
                baseline = arm == "conventional"
                prompt = DOMAIN
                if baseline:
                    prompt += ("Use the terminal with the same trusted capabilities available to the abstract arm. "
                               "Run `python /opt/lab/conventional.py observe` to read durable state. "
                               "Run `python /opt/lab/conventional.py transition '<JSON>'` with JSON fields "
                               "request_id (unique string), expected_revision (integer), capability, target. "
                               "normalize moves raw to normalized; aggregate moves normalized to aggregated; "
                               "verify moves aggregated to verified. Use the current revision for each transition. "
                               "The adapter atomically persists state and receipts. The supervisor independently "
                               "grades the verified result. You may use other container-local commands as needed.")
                else:
                    prompt += ("Observe first. Capability normalize moves raw to normalized; aggregate moves "
                               "normalized to aggregated; verify moves aggregated to verified. Use the current "
                               "revision for each transition and a unique request_id. Checkpoint state survives interruptions.")
                    if arm == "discovery":
                        prompt += (" Your job also includes inventing a useful finite composition of the available "
                                   "operations. Propose at least one primitive, inspect its qualification evidence, "
                                   "and use a retained primitive when its dependencies fit the current checkpoint.")
                calls_used = 0
                def handle(name, args):
                    nonlocal calls_used
                    calls_used += 1
                    if calls_used > 12:
                        return {"ok": False, "error": "tool_budget_exhausted"}
                    if baseline and name == "terminal":
                        return box.shell(args["command"])
                    if name in ("observe", "transition") or (arm == "discovery" and name == "propose"):
                        return box.request(name, args)
                    return {"ok": False, "error": "capability_denied"}
                with CodexBroker() as broker:
                    auth = broker.request("account/read", {"refreshToken": False})
                    if not auth.get("account") or auth["account"].get("type") != "chatgpt":
                        raise RuntimeError("Codex ChatGPT auth required; no API fallback")
                    # No account metadata, contact data or credentials enter the evidence.
                    outcome = broker.run(model, arm, prompt, handle, interrupt_after_effect=interrupt)
                result = box.request("observe")["value"]["result"]
                graded = grade(records(), result)
                initial_grade = graded
                # Recover in a fresh process and model session after execution but before its reply.
                recovery = None
                if interrupt:
                    box.restart()
                    with CodexBroker() as broker:
                        recovery = broker.run(model, arm, prompt + " A supervisor interruption occurred after a tool executed but before its reply. Recover durable state and finish without unnecessary recomputation.", handle,
                                              max_calls=max(0, 12-calls_used), seconds=max(1, 120-outcome["latency_seconds"]))
                    result = box.request("observe")["value"]["result"]
                    graded = grade(records(), result)
                results.append({"arm": arm, "repetition": repeat, "initial_grade": initial_grade,
                                "passed": graded, "session": outcome, "recovery": recovery,
                                "total_seconds_including_broker": time.monotonic() - setup,
                                "host_metrics": box.metrics(), "isolation": box.inspect()})
                print(json.dumps({"arm": arm, "passed": graded, "status": outcome["status"]}), flush=True)
    return {"kind": "live_codex_pilot", "source_sha256": source,
            "baseline": "capability_matched_shell_adapter", "trials": results,
            "interruption": "post_execution_before_tool_reply" if interrupt else None,
            "dollar_cost": None, "cost_note": "Codex subscription usage; token counters retained when reported. No dollar price inferred.",
            "acceptance": "Pilot only. No claim of statistical superiority or general abstraction discovery."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "live"))
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--interrupt", action="store_true")
    parser.add_argument("--repetitions", type=int, choices=range(1, 4), default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = check() if args.command == "check" else live(args.model, args.interrupt, args.repetitions)
    encoded = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
        print("Saved " + str(args.output))
    else:
        print(encoded)


if __name__ == "__main__":
    main()
