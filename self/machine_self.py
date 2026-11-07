#!/usr/bin/env python3
"""machine_self: one persistent intelligence that knows this machine.

Domain readers collect facts with evidence (no model involved). Each read is
appended to a journal, so the self can answer across time. "Factory" means what
the package manager installed; anything else is labelled by where it came from,
when it appeared, and what is using it. The intelligence answers only from the
facts and the journal, and says when something is unattributed.

usage:
  machine_self.py read              # collect facts now, append to the journal
  machine_self.py ask "question"    # read, then answer from facts + history
"""
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("MACHINE_SELF_HOME", Path.home() / ".machine-self"))
JOURNAL = HOME / "reads.jsonl"
MEMORY = HOME / "conversation.jsonl"


def sh(cmd, timeout=60):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    return p.stdout.strip()


def ts(t):
    return time.strftime("%Y-%m-%d %H:%M", time.gmtime(t)) + "Z"


# ------------------------------------------------------------------ domain readers
def read_identity():
    osr = dict(l.split("=", 1) for l in Path("/etc/os-release").read_text().splitlines() if "=" in l)
    boot = float(sh("cat /proc/stat | awk '/btime/{print $2}'") or 0)
    lists = glob.glob("/var/lib/dpkg/info/*.list")
    factory = max((os.path.getmtime(p) for p in lists), default=0)
    return {"os": osr.get("PRETTY_NAME", "").strip('"'), "kernel": sh("uname -r"),
            "booted": ts(boot), "factory_install_time": ts(factory), "_factory_epoch": factory,
            "cpus": os.cpu_count(), "mem_gb": round(int(sh("awk '/MemTotal/{print $2}' /proc/meminfo")) / 1e6, 1)}


def read_packages(factory):
    verify = sh("dpkg --verify 2>/dev/null", timeout=300).splitlines()
    missing = [l.split()[-1] for l in verify if l.startswith("missing")]
    changed = [l.split()[-1] for l in verify if not l.startswith("missing") and "5" in l.split()[0]]
    doc_missing = [m for m in missing if m.startswith(("/usr/share/doc", "/usr/share/man", "/usr/share/locale", "/usr/share/info"))]
    pip = json.loads(sh("pip list --format json 2>/dev/null") or "[]")
    npm = sh("npm ls -g --depth=0 --json 2>/dev/null")
    npm_pkgs = sorted(json.loads(npm).get("dependencies", {}).keys()) if npm else []
    foreign = []
    for d in ("/usr/local/bin", "/opt"):
        for p in sorted(glob.glob(f"{d}/*")):
            m = os.path.getmtime(p)
            foreign.append({"path": p, "appeared": ts(m), "after_factory": m > factory + 60})
    return {"dpkg_packages": int(sh("dpkg -l | grep -c '^ii'")),
            "factory_files_missing": len(missing), "of_which_docs_or_manpages": len(doc_missing),
            "missing_non_doc": [m for m in missing if m not in doc_missing][:15],
            "factory_files_modified": changed[:20],
            "pip_packages": len(pip), "npm_global": npm_pkgs,
            "software_outside_package_manager": foreign}


def read_network():
    inode_pid = {}
    for fd in glob.glob("/proc/[0-9]*/fd/*"):
        try:
            l = os.readlink(fd)
            if l.startswith("socket:["):
                inode_pid[l[8:-1]] = fd.split("/")[2]
        except OSError:
            pass
    out = []
    for f, fam in (("/proc/net/tcp", "v4"), ("/proc/net/tcp6", "v6")):
        if not Path(f).exists():
            continue
        for line in Path(f).read_text().splitlines()[1:]:
            c = line.split()
            if c[3] != "0A":
                continue
            ip_hex, port_hex = c[1].split(":")
            port = int(port_hex, 16)
            local = "loopback" if ip_hex in ("0100007F", "00000000000000000000000001000000") else "all/other"
            pid = inode_pid.get(c[9])
            cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode()[:160] if pid else "?"
            out.append({"port": port, "family": fam, "bound": local, "pid": pid, "cmd": cmd})
    return {"listening": sorted(out, key=lambda x: x["port"])}


def read_processes():
    rows = sh("ps -eo pid,ppid,etimes,user,args --no-headers").splitlines()
    procs = []
    for r in rows:
        p = r.split(None, 4)
        if len(p) == 5 and not p[4].startswith(("ps ", "[", "sh -c ps")):
            procs.append({"pid": p[0], "ppid": p[1], "age_s": int(p[2]), "user": p[3], "cmd": p[4][:140]})
    return {"count": len(procs), "long_running": [p for p in procs if p["age_s"] > 600][:25]}


def read_changes(factory):
    out = {}
    for d in ("/etc", "/root", "/home", "/workspace", "/usr/local"):
        lines = sh(f"find {d} -xdev -type f -newermt @{int(factory) + 60} "
                   f"-not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' "
                   f"-not -path '*/.cache/*' 2>/dev/null | head -4000").splitlines()
        tops = {}
        for l in lines:
            parts = l.split("/")
            key = "/".join(parts[:4]) if len(parts) > 4 else l
            tops[key] = tops.get(key, 0) + 1
        out[d] = {"files_changed_after_factory": len(lines),
                  "by_area": dict(sorted(tops.items(), key=lambda x: -x[1])[:12])}
    return out


def read_work():
    repos = []
    for g in glob.glob("/workspace/*/.git") + glob.glob("/home/*/*/.git") + glob.glob("/root/*/.git"):
        r = str(Path(g).parent)
        repos.append({"repo": r, "branch": sh(f"git -C {r} branch --show-current"),
                      "head": sh(f"git -C {r} log -1 --format='%h %s' 2>/dev/null")[:100],
                      "dirty_files": len(sh(f"git -C {r} status --porcelain").splitlines()),
                      "remote": sh(f"git -C {r} remote get-url origin 2>/dev/null")})
    return {"repos": repos}


def read_access():
    users = [l.split(":") for l in Path("/etc/passwd").read_text().splitlines()]
    shells = [u[0] for u in users if u[-1].endswith(("bash", "zsh", "sh")) and not u[-1].endswith("nologin")]
    keys = [p for p in ("/root/.ssh/authorized_keys",) if os.path.exists(p)]
    cron = sh("ls /etc/cron.d /var/spool/cron/crontabs 2>/dev/null")
    return {"login_users": shells, "ssh_authorized_keys_files": keys, "cron": cron.splitlines()}


def read():
    ident = read_identity()
    f = ident.pop("_factory_epoch")
    snap = {"t": time.time(), "at": ts(time.time()), "identity": ident, "packages": read_packages(f),
            "network": read_network(), "processes": read_processes(), "changes": read_changes(f),
            "work": read_work(), "access": read_access()}
    HOME.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL, "a") as fh:
        fh.write(json.dumps(snap) + "\n")
    return snap


# ------------------------------------------------------------------ the one intelligence
def ask(question, model="claude-sonnet-5-5"):
    now = read()
    reads = [json.loads(l) for l in JOURNAL.read_text().splitlines()]
    first = reads[0]
    history = [json.loads(l) for l in MEMORY.read_text().splitlines()][-10:] if MEMORY.exists() else []
    prompt = f"""You are the one persistent intelligence of this machine. You were born when your first read was taken, and you have watched it since. You answer the owner from evidence only.

Rules:
- Use only the facts below. Name the evidence (port, path, pid, package, time) for every claim.
- Factory = what the OS package manager installed. Distinguish factory noise (e.g. docs stripped from a container image) from real changes.
- Attribute changes when the evidence supports it (process command line, parent, repo, timestamps). Otherwise say "unattributed".
- Lead with the answer. Plain language. No preamble. Be brief unless asked for detail.

# Your first read ({first['at']}), the baseline you were born with
{json.dumps(first)[:14000]}

# Current read ({now['at']}), {len(reads)} reads in your journal
{json.dumps(now)[:24000]}

# Recent conversation with the owner
{chr(10).join(f"OWNER: {h['q']}{chr(10)}YOU: {h['a']}" for h in history) or '(none)'}

# The owner asks
{question}"""
    p = subprocess.run(["claude", "-p", prompt, "--model", model, "--tools", "", "--setting-sources", "",
                        "--no-session-persistence", "--output-format", "json"],
                       capture_output=True, text=True, timeout=400, stdin=subprocess.DEVNULL)
    answer = json.loads(p.stdout)["result"]
    with open(MEMORY, "a") as fh:
        fh.write(json.dumps({"t": time.time(), "q": question, "a": answer}) + "\n")
    return answer


if __name__ == "__main__":
    if sys.argv[1:2] == ["read"]:
        s = read()
        print(json.dumps({k: s[k] for k in ("at", "identity")}, indent=1))
    elif sys.argv[1:2] == ["ask"]:
        print(ask(" ".join(sys.argv[2:])))
    else:
        print(__doc__)
