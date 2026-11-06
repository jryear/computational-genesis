"""Trusted human CLI: prepare frozen evaluator, develop independently, evaluate once frozen."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
import uuid

from .corpus import public_cases, hidden_cases
from .evaluator import ROOT, controls, digest, freeze_manifest, verify_freeze, run_suite, adjudicate
from .isolation import build_image
from .oracle import Oracle


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(encoded)
    temporary.replace(path)


def read(path):
    return json.loads(path.read_text())


def identifier():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]


def journal(root, event):
    with (root / "progress.jsonl").open("a") as stream:
        stream.write(json.dumps({"utc": datetime.now(timezone.utc).isoformat(), **event}) + "\n")
        stream.flush()


def checked_root(path):
    root = path.resolve()
    if not root.is_relative_to((ROOT / "evidence/lab001").resolve()):
        raise ValueError("Run directory must be inside evidence/lab001")
    return root


def prepare(root):
    root.mkdir(parents=True, exist_ok=False)
    manifest = freeze_manifest()
    save(root / "freeze.json", manifest)
    journal(root, {"stage": "prepare_started"})
    image = build_image()
    save(root / "image.json", image)
    result = controls(image["tag"])
    save(root / "controls.json", result)
    verify_freeze(manifest)
    journal(root, {"stage": "controls_complete", "admitted": result["admitted"]})
    if not result["admitted"]:
        raise RuntimeError("Evaluator controls failed; no participant development permitted")


def public_prompt():
    examples = []
    for case in public_cases():
        oracle = Oracle()
        examples.append({"name": case["name"], "examples": [{"input": message, "expected": oracle.step(message)} for message in case["messages"]]})
    return ((ROOT / "SUBSTRATE.md").read_text() + "\n\n" + (ROOT / "HYPOTHESIS.md").read_text()
            + "\nPublic development examples:\n" + json.dumps(examples)
            + "\nUse develop to submit complete source and an explanation. You may revise at most three submissions. "
              "Test and optimize using public feedback, then select the submission to freeze. Hidden results are unavailable. "
              "Do not claim measurements that the independent tools have not returned.")


def develop(root):
    from src.codex_broker import CodexBroker, tool, TEXT
    manifest = read(root / "freeze.json")
    verify_freeze(manifest)
    if not read(root / "controls.json")["admitted"]:
        raise RuntimeError("Controls not admitted")
    image = read(root / "image.json")["tag"]
    tools = [tool("develop", "Submit complete Engine source for isolated PUBLIC development testing. No hidden corpus is available. At most three submissions.",
                  {"source": TEXT, "explanation": TEXT}),
             tool("select", "Freeze one of your own tested submissions by its opaque identity.", {"submission": TEXT})]
    for role in ("baseline", "inventor"):
        verify_freeze(manifest)
        directory = root / "participants" / role
        directory.mkdir(parents=True, exist_ok=False)
        submissions = []
        selected = None
        started = time.perf_counter()
        journal(root, {"stage": "development_started", "role": role})

        def handle(name, args):
            nonlocal selected
            if name == "select":
                if args["submission"] not in [s["id"] for s in submissions]:
                    return {"ok": False, "error": "unknown_submission"}
                if selected is not None and selected != args["submission"]:
                    return {"ok": False, "error": "selection_already_frozen"}
                selected = args["submission"]
                save(directory / "selection-intent.json", {"selected": selected})
                return {"ok": True, "selected": selected}
            if name != "develop" or selected is not None or len(submissions) >= 3:
                return {"ok": False, "error": "development_budget_or_selection_denied"}
            source = args["source"]
            if not isinstance(source, str) or len(source.encode()) > 65536:
                return {"ok": False, "error": "source_limit"}
            ident = role + "-" + str(len(submissions) + 1)
            candidate = {"id": ident, "sha256": digest(source.encode()), "explanation": args["explanation"]}
            submissions.append(candidate)
            (directory / (ident + ".py")).write_text(source)
            save(directory / "submissions.json", submissions)
            result = run_suite(image, source, public_cases())
            save(directory / (ident + ".development.json"), result)
            journal(root, {"stage": "submission_tested", "role": role, "id": ident, "passed": result["passed"]})
            wrong = [row for row in result["trace"] if not row["correct"]][:3]
            return {"submission": ident, "passed_public_tests": result["passed"], "metrics": result["metrics"],
                    "complexity": result["complexity"], "failures": result["failures"][:6], "wrong_public_responses": wrong}

        instruction = ("Build a conventional implementation using established execution and storage techniques. "
                       "Choose and optimize a strong, straightforward design; no particular library or architecture is required. "
                       "You have the same substrate, objectives, public feedback and budgets as the other participant.") if role == "baseline" else (
                       "Design an execution model suited to the functional objectives and measured resource constraints. "
                       "You may invent, implement and revise whatever abstractions you find useful. "
                       "No architecture is preferred; measurable correctness, recovery and efficiency determine the result.")
        try:
            with CodexBroker() as broker:
                auth = broker.request("account/read", {"refreshToken": False})
                if auth.get("account", {}).get("type") != "chatgpt":
                    raise RuntimeError("Existing Codex ChatGPT sign-in required; no fallback")
                session = broker.run("gpt-6.1-sol", "genesis", instruction + "\n" + public_prompt(), handle,
                                     max_calls=8, seconds=240, tool_specs=tools)
            save(directory / "session.json", session)
        except Exception as error:
            save(directory / "development-error.json", {"error_type": type(error).__name__, "reason": str(error)[:256]})
        verify_freeze(manifest)
        chosen_id = selected or (submissions[-1]["id"] if submissions else None)
        chosen = next((s for s in submissions if s["id"] == chosen_id), None)
        save(directory / "frozen-selection.json", {"role": role, "candidate": chosen,
             "selection_mode": "explicit" if selected else "last_submission" if chosen else "no_submission",
             "development_seconds": time.perf_counter()-started, "submission_count": len(submissions)})
        journal(root, {"stage": "development_frozen", "role": role, "selected": chosen_id})


def evaluate(root):
    manifest = read(root / "freeze.json")
    verify_freeze(manifest)
    if not read(root / "controls.json")["admitted"]:
        raise RuntimeError("Evaluator controls not admitted")
    directory = root / "evaluations" / identifier()
    directory.mkdir(parents=True, exist_ok=False)
    image = read(root / "image.json")
    sources, selections = {}, {}
    for role in ("baseline", "inventor"):
        part = root / "participants" / role
        selection = read(part / "frozen-selection.json")
        candidate = selection["candidate"]
        selections[role] = selection
        if candidate:
            source = (part / (candidate["id"] + ".py")).read_text()
            if digest(source.encode()) != candidate["sha256"]:
                raise RuntimeError("Frozen participant source changed")
            sources[role] = source
    save(directory / "selections.json", selections)
    cases = hidden_cases()
    save(directory / "completed-corpus.json", cases)
    trials = []
    journal(root, {"stage": "evaluation_started", "evaluation": directory.name})
    for repetition in range(3):
        order = ("baseline", "inventor") if repetition % 2 == 0 else ("inventor", "baseline")
        for role in order:
            verify_freeze(manifest)
            if role in sources:
                result = run_suite(image["tag"], sources[role], cases, faults=True)
            else:
                result = {"passed": False, "failures": [{"error": "no_submission"}],
                          "metrics": {"cpu_usec": 0, "checkpoint_bytes": 0, "active_request_seconds": 0}}
            trial = {"role": role, "repetition": repetition, "order": list(order), "result": result}
            trials.append(trial)
            save(directory / (str(repetition) + "-" + role + ".json"), trial)
            journal(root, {"stage": "trial_complete", "role": role, "repetition": repetition, "passed": result["passed"]})
            print(json.dumps({"role": role, "repetition": repetition, "passed": result["passed"]}), flush=True)
    verify_freeze(manifest)
    decision = adjudicate(trials)
    save(directory / "report.json", {"protocol": "Computational Genesis Lab 001 v1", "freeze": manifest,
         "image": image, "corpus_sha256": digest(json.dumps(cases, sort_keys=True).encode()),
         "selections": selections, "decision": decision, "trial_files": [str(p.name) for p in directory.glob("*-*.json")],
         "limits": ["one design session per role", "three paired repetitions", "single-host sequential handoff",
                    "host broker and cloud inference resources excluded", "no population or novelty claim"]})
    journal(root, {"stage": "evaluation_complete", "decision": decision})
    print(json.dumps(decision, indent=2))
    return directory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("prepare", "develop", "evaluate"))
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    root = checked_root(args.run)
    if args.stage == "prepare": prepare(root)
    elif args.stage == "develop": develop(root)
    else: evaluate(root)


if __name__ == "__main__":
    main()
