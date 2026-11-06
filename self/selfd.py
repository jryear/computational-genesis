#!/usr/bin/env python3
"""self: one memory, one voice, one set of intents, above any engine.

The journal (DATA/journal.jsonl) is the self. Engines (Claude, Codex) are stateless
and interchangeable: every turn, the runtime hands the current engine the voice spec,
memory, intents, open decisions and recent conversation, and the engine answers in
JSON. Capabilities are executed by the runtime, never by the engine, and each run is
recorded as Proof (command, exit code, output hash), so "done" is never a model's claim.

usage: selfd.py [--port 8787] [--data DIR]     stdlib only
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / "lab002"
CODEX = os.environ.get("CODEX_BIN", "codex")
CODEX_HOME = os.environ.get("CODEX_HOME_FOR_SELF", "")
LOCK = threading.Lock()

VOICE = (HERE / "voice.md").read_text()


# ------------------------------------------------------------------ the self (journal)
class Self:
    def __init__(self, data: Path):
        self.path = data / "journal.jsonl"
        data.mkdir(parents=True, exist_ok=True)
        self.path.touch()

    def append(self, kind, **body):
        rec = {"t": round(time.time(), 3), "kind": kind, **body}
        with LOCK, open(self.path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        return rec

    def events(self):
        with LOCK:
            return [json.loads(x) for x in self.path.read_text().splitlines() if x.strip()]

    def state(self):
        mem, intents, decisions, proof, turns = [], {}, {}, [], []
        for e in self.events():
            k = e["kind"]
            if k == "memory":
                mem.append(e["text"])
            elif k == "intent":
                intents[e["title"].strip().lower()] = {"title": e["title"], "status": e["status"], "t": e["t"]}
            elif k == "decision":
                decisions[e["id"]] = {**e, "answer": None}
            elif k == "answer" and e["id"] in decisions:
                decisions[e["id"]]["answer"] = e["choice"]
            elif k == "proof":
                proof.append(e)
            elif k in ("you", "self"):
                turns.append(e)
        return {"memory": mem, "intents": sorted(intents.values(), key=lambda i: -i["t"]),
                "decisions": list(decisions.values()), "proof": proof, "turns": turns}


# ------------------------------------------------------------------ capabilities
def _run(cmd, cwd=None, timeout=240):
    t0 = time.time()
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout + p.stderr)
    return {"cmd": " ".join(cmd), "exit": p.returncode, "secs": round(time.time() - t0, 1),
            "sha256": hashlib.sha256(out.encode()).hexdigest()[:16], "out": out[-3000:]}


def cap_lab_status(_):
    repo = str(LAB.parent)
    log = _run(["git", "log", "--oneline", "-8"], cwd=repo)
    br = _run(["git", "branch", "-a", "--no-color"], cwd=repo)
    log["out"] = "branches:\n" + br["out"] + "\nrecent commits:\n" + log["out"]
    return log


def cap_lab_results(args):
    which = {"run1": "results/run1/verdict.txt", "run2": "results/run2/verdict.txt",
             "phaseb": "phaseb/RESULTS.md", "prereg": "PREREG.md", "run2_prereg": "RUN2.md"}
    name = args.get("which", "phaseb")
    rel = which.get(name)
    if not rel:
        return {"cmd": f"read {name}", "exit": 2, "secs": 0, "sha256": "-", "out": f"unknown; options: {sorted(which)}"}
    r = _run(["git", "show", f"lab002:lab002/{rel}"], cwd=str(LAB.parent))
    r["cmd"] = f"read lab002:{rel}"
    return r


def cap_lab_tests(_):
    path = tempfile.mkdtemp(prefix="selftest-") + "/wt"
    _run(["git", "worktree", "add", "--detach", path, "lab002"], cwd=str(LAB.parent))
    try:
        res = _run(["python3", "-m", "unittest", "test_semexec"], cwd=f"{path}/lab002", timeout=600)
    finally:
        _run(["git", "worktree", "remove", "--force", path], cwd=str(LAB.parent))
    res["cmd"] = "python3 -m unittest test_semexec  (lab002, clean worktree)"
    return res


CAPS = {
    "lab_status": (cap_lab_status, "Branches and recent commits of the computational-genesis lab repo."),
    "lab_results": (cap_lab_results, "Read a lab document. args: {which: run1|run2|phaseb|prereg|run2_prereg}."),
    "lab_tests": (cap_lab_tests, "Run the Lab 002 test suite on a clean checkout. ~20 s. Returns pass/fail."),
}


# ------------------------------------------------------------------ engines
def build_prompt(st, message, cap_results=None):
    open_dec = [d for d in st["decisions"] if d["answer"] is None]
    answered = [d for d in st["decisions"] if d["answer"] is not None][-8:]
    turns = st["turns"][-12:]
    convo = "\n".join(f"{'YOU' if t['kind'] == 'you' else 'SELF'}: {t['text']}" for t in turns)
    parts = [
        "You are the user's one persistent agent. Different language models take turns being you; "
        "the user must never be able to tell which. Everything you know about the user is below. "
        "It is the only memory that exists.",
        "# Voice (follow exactly)\n" + VOICE,
        "# Memory\n" + ("\n".join(f"- {m}" for m in st["memory"]) or "(empty)"),
        "# Intents (what the user is pursuing)\n" + ("\n".join(f"- {i['title']}: {i['status']}" for i in st["intents"]) or "(none yet)"),
        "# Open decisions awaiting the user\n" + ("\n".join(f"- [{d['id']}] {d['question']}" for d in open_dec) or "(none)"),
        "# How the user decided before (learn their judgment)\n" + ("\n".join(f"- {d['question']} -> {d['answer']}" for d in answered) or "(nothing yet)"),
        "# Capabilities (the runtime executes these; you never claim results you did not get)\n"
        + "\n".join(f"- {k}: {v[1]}" for k, v in CAPS.items()),
        "# Recent conversation\n" + (convo or "(first message)"),
        "# The user just said\n" + message,
    ]
    if cap_results is not None:
        parts.append("# Capability results (verified by the runtime)\n" + json.dumps(cap_results)[:12000]
                     + "\nNow answer. Do not request capabilities again.")
    parts.append(
        "# Reply with ONLY one JSON object, no prose outside it:\n"
        '{"use": [{"capability": "<name>", "args": {}}],   // ONLY if you need data before answering; otherwise []\n'
        ' "say": "<what you say to the user, in the voice>",\n'
        ' "remember": ["<durable facts about the user, their preferences or judgment worth keeping; [] if none>"],\n'
        ' "intents": [{"title": "<short>", "status": "<one line, current>"}],   // create/update; [] if none\n'
        ' "decisions": [{"question": "<a real judgment call only the user should make>", '
        '"options": ["<a>", "<b>"], "recommend": "<one of options>", "why": "<one line>"}]}   // usually []'
    )
    return "\n\n".join(parts)


def engine_claude(prompt, model="claude-sonnet-5-5"):
    p = subprocess.run(["claude", "-p", prompt, "--model", model, "--tools", "", "--setting-sources", "",
                        "--disable-slash-commands", "--no-session-persistence", "--output-format", "json",
                        "--system-prompt", "You produce exactly the JSON object requested."],
                       capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
    return json.loads(p.stdout)["result"]


def engine_codex(prompt):
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "last.txt"
        env = dict(os.environ, **({"CODEX_HOME": CODEX_HOME} if CODEX_HOME else {}))
        subprocess.run([CODEX, "exec", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check",
                        "-s", "read-only", "--disable", "shell_tool", "--disable", "unified_exec",
                        "-o", str(out), prompt], cwd=d, env=env, capture_output=True, text=True,
                       timeout=400, stdin=subprocess.DEVNULL)
        return out.read_text()


ENGINES = {"claude": engine_claude, "codex": engine_codex}


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    d = json.loads(m.group(0))
    for k, v in (("use", []), ("say", ""), ("remember", []), ("intents", []), ("decisions", [])):
        d.setdefault(k, v)
    return d


# ------------------------------------------------------------------ a turn
def turn(me: Self, message, engine):
    if engine == "auto":   # alternate, so continuity across engines is the default, not a trick
        n = sum(1 for e in me.events() if e["kind"] == "self")
        engine = ["claude", "codex"][n % 2]
    me.append("you", text=message)
    t0 = time.time()
    reply = parse(ENGINES[engine](build_prompt(me.state(), message)))
    used = []
    if reply["use"]:
        for u in reply["use"][:3]:
            name = u.get("capability")
            if name not in CAPS:
                continue
            r = CAPS[name][0](u.get("args") or {})
            me.append("proof", capability=name, cmd=r["cmd"], exit=r["exit"], secs=r["secs"],
                      sha256=r["sha256"], excerpt=r["out"][-600:])
            used.append({"capability": name, "exit": r["exit"], "output": r["out"]})
        reply = parse(ENGINES[engine](build_prompt(me.state(), message, used)))
    for m in reply["remember"][:5]:
        if m and m not in me.state()["memory"]:
            me.append("memory", text=m, by=engine)
    for i in reply["intents"][:5]:
        if i.get("title"):
            me.append("intent", title=i["title"], status=i.get("status", ""), by=engine)
    for d in reply["decisions"][:2]:
        if d.get("question") and d.get("options"):
            me.append("decision", id=hashlib.sha256(d["question"].encode()).hexdigest()[:8],
                      question=d["question"], options=d["options"][:4], recommend=d.get("recommend"),
                      why=d.get("why", ""), by=engine)
    return me.append("self", text=reply["say"], engine=engine, secs=round(time.time() - t0, 1),
                     used=[u["capability"] for u in used])


# ------------------------------------------------------------------ the surface
class H(BaseHTTPRequestHandler):
    me: Self = None

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/api/state":
            return self._json(self.me.state())
        b = (HERE / "surface.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        try:
            if self.path == "/api/say":
                return self._json(turn(self.me, body["text"], body.get("engine", "auto")))
            if self.path == "/api/answer":
                self.me.append("answer", id=body["id"], choice=body["choice"])
                return self._json({"ok": True})
        except Exception as e:  # noqa: BLE001 -- surface every failure verbatim
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        self._json({"error": "not found"}, 404)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--data", default=str(Path.home() / ".self"))
    a = ap.parse_args()
    H.me = Self(Path(a.data))
    print(f"self on http://127.0.0.1:{a.port}  journal={H.me.path}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
