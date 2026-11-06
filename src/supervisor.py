"""Trusted OS adapter. Nothing in this module is exposed as a model tool."""
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time
import uuid

IMAGE = "objective-lab:local"
ROOT = Path(__file__).resolve().parent.parent
LABEL = "research.objective-lab"


def docker(*args, timeout=30):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Docker operation failed; inspect the local supervisor")
    return result.stdout.strip()


def build():
    docker("build", "--network=none", "-t", IMAGE, str(ROOT), timeout=120)


class Sandbox:
    def __init__(self):
        token = uuid.uuid4().hex[:12]
        self.name = "objective-lab-" + token
        self.volume = self.name + "-state"
        self.proc = None
        self.requests = 0
        self.shell_executions = 0
        self.samples = []
        self.cgroup_segments = []
        docker("volume", "create", "--label", LABEL + "=true", self.volume)
        try:
            docker("create", "-i", "--name", self.name, "--label", LABEL + "=true",
                   "--network=none", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges:true", "--pids-limit=32",
                   "--memory=128m", "--memory-swap=128m", "--cpus=0.5",
                   "--ulimit", "fsize=4194304:4194304",
                   "--tmpfs", "/tmp:rw,noexec,nosuid,size=8m,mode=1777",
                   "--mount", "type=volume,src=" + self.volume + ",dst=/state",
                   IMAGE)
            self.start()
        except BaseException:
            self.close()
            raise

    def start(self):
        self.proc = subprocess.Popen(["docker", "start", "-ai", self.name], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def request(self, method, args=None):
        self.requests += 1
        self.proc.stdin.write((json.dumps({"method": method, "args": args or {}}) + "\n").encode())
        self.proc.stdin.flush()
        with selectors.DefaultSelector() as selector:
            selector.register(self.proc.stdout, selectors.EVENT_READ)
            if not selector.select(5):
                self.stop()
                raise RuntimeError("Workload deadline exceeded")
        line = self.proc.stdout.readline(65537)
        if not line or len(line) > 65536:
            raise RuntimeError("Workload returned an invalid response")
        return json.loads(line)

    def stop(self):
        docker("stop", "-t", "1", self.name)
        if self.proc:
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait()
            self.proc.stdin.close(); self.proc.stdout.close()
            self.proc = None

    def restart(self):
        # Container cgroups are recreated on restart. Preserve pre-interruption counters.
        self.cgroup_segments.append(self.cgroup_snapshot())
        self.stop()
        self.start()

    def shell(self, command):
        self.shell_executions += 1
        if not isinstance(command, str) or len(command) > 8192:
            return {"ok": False, "error": "invalid_command"}
        # All text is passed as one argv element to the container's shell, never a host shell.
        with tempfile.TemporaryFile() as output:
            proc = subprocess.Popen(["docker", "exec", self.name, "env", "-i", "PATH=/usr/local/bin:/usr/bin:/bin", "timeout", "5", "/bin/sh", "-c", command],
                                    stdout=output, stderr=subprocess.STDOUT)
            try:
                proc.wait(timeout=7)
            except subprocess.TimeoutExpired:
                proc.kill(); proc.wait(); self.stop()
                return {"ok": False, "error": "deadline_exceeded"}
            output.seek(0)
            text = output.read(8193).decode("utf-8", errors="replace")
        return {"exit_code": proc.returncode, "output": text[:8192], "truncated": len(text) > 8192}

    def inspect(self):
        config = json.loads(docker("inspect", self.name))[0]
        host = config["HostConfig"]
        return {"network": host["NetworkMode"], "read_only": host["ReadonlyRootfs"],
                "cap_drop": host["CapDrop"], "security_options": host["SecurityOpt"],
                "memory_bytes": host["Memory"], "pids_limit": host["PidsLimit"],
                "user": config["Config"]["User"],
                "mounts": [{"type": m["Type"], "destination": m["Destination"]} for m in config["Mounts"]],
                "environment_names": sorted(v.split("=", 1)[0] for v in config["Config"]["Env"])}

    def cgroup_snapshot(self):
        probe = self.shell("cat /sys/fs/cgroup/cpu.stat; cat /sys/fs/cgroup/memory.peak; cat /sys/fs/cgroup/pids.peak")
        lines = probe["output"].splitlines()
        cpu = next(int(line.split()[1]) for line in lines if line.startswith("usage_usec "))
        scalars = [int(line) for line in lines if line.isdigit()]
        if len(scalars) != 2:
            raise RuntimeError("Incomplete workload resource measurement")
        return {"cpu_usage_usec": cpu, "memory_peak_bytes": scalars[0], "tasks_peak": scalars[1], "raw": probe["output"]}

    def metrics(self):
        # Counters cover workload execution across restarts, including measurement overhead.
        segments = self.cgroup_segments + [self.cgroup_snapshot()]
        return {"cgroup_segments": segments,
                "cpu_usage_usec": sum(s["cpu_usage_usec"] for s in segments),
                "memory_peak_bytes": max(s["memory_peak_bytes"] for s in segments),
                "tasks_peak": max(s["tasks_peak"] for s in segments),
                "includes_measurement_overhead": True, "stdio_requests": self.requests,
                "shell_executions_including_measurement": self.shell_executions,
                "container": self.name, "volume": self.volume}

    def baseline_result(self):
        answer = self.shell("cat /state/result.json")
        try:
            return json.loads(answer["output"])
        except (ValueError, KeyError):
            return None

    def close(self):
        if self.proc:
            try:
                self.stop()
            except Exception:
                self.proc.kill(); self.proc.wait()
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        subprocess.run(["docker", "volume", "rm", self.volume], capture_output=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
