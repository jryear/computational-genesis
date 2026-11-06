"""Trusted execution/measurement boundary; no generated source runs on the host."""
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import threading
import time
import uuid

LABEL = "research.computational-genesis"
MAX_LINE = 2097152


class ExecutionError(Exception):
    pass


def docker(*args, timeout=30):
    result = subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise ExecutionError("docker_operation_failed")
    return result.stdout.strip()


def build_image():
    runner = Path(__file__).with_name("runner.py").read_bytes()
    base = json.loads(docker("image", "inspect", "python:3.13-alpine"))[0]
    digest = next(d for d in base["RepoDigests"] if d.startswith("python@sha256:"))
    tag = "genesis-lab001:" + hashlib.sha256(runner + digest.encode()).hexdigest()[:16]
    with tempfile.TemporaryDirectory(prefix="genesis-build-") as directory:
        root = Path(directory)
        (root / "runner.py").write_bytes(runner)
        (root / "Dockerfile").write_text(
            "FROM " + digest + "\nCOPY runner.py /opt/runner.py\nUSER 65532:65532\nWORKDIR /tmp\n"
            'ENTRYPOINT ["/usr/bin/env","-i","PATH=/usr/local/bin:/usr/bin:/bin","PYTHONDONTWRITEBYTECODE=1","python","-u","/opt/runner.py"]\n')
        docker("build", "--network=none", "-t", tag, str(root), timeout=120)
    return {"tag": tag, "id": json.loads(docker("image", "inspect", tag))[0]["Id"], "base_digest": digest}


class Boundary:
    def __init__(self, image, source):
        self.name = "genesis-" + uuid.uuid4().hex[:16]
        self.proc = None
        self.buffer = b""
        self.transport_bytes = 0
        self.latencies = []
        self.stderr = bytearray()
        self.stderr_total = 0
        try:
            docker("create", "-i", "--name", self.name, "--label", LABEL + "=lab001",
                   "--network=none", "--read-only", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges:true", "--pids-limit=32",
                   "--memory=128m", "--memory-swap=128m", "--cpus=0.5",
                   "--ulimit", "fsize=2097152:2097152",
                   "--tmpfs", "/tmp:rw,noexec,nosuid,size=8m,mode=1777", image)
            self.proc = subprocess.Popen(["docker", "start", "-ai", self.name], stdin=subprocess.PIPE,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
            os.set_blocking(self.proc.stdin.fileno(), False)
            os.set_blocking(self.proc.stdout.fileno(), False)
            self.stderr_reader = threading.Thread(target=self._stderr, daemon=True)
            self.stderr_reader.start()
            self.request({"op": "install", "source": source})
        except BaseException:
            self.close()
            raise

    def _stderr(self):
        channel = self.proc.stderr
        while True:
            try:
                chunk = channel.read(4096)
            except (ValueError, OSError):
                return
            if not chunk:
                return
            self.stderr_total += len(chunk)
            if len(self.stderr) < 65536:
                self.stderr.extend(chunk[:65536-len(self.stderr)])

    def request(self, value):
        encoded = (json.dumps(value, separators=(",", ":")) + "\n").encode()
        if len(encoded) > MAX_LINE:
            raise ExecutionError("input_limit")
        start = time.perf_counter()
        deadline = time.monotonic() + 3
        offset = 0
        with selectors.DefaultSelector() as selector:
            selector.register(self.proc.stdin, selectors.EVENT_WRITE)
            while offset < len(encoded):
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise ExecutionError("request_write_timeout")
                try:
                    offset += os.write(self.proc.stdin.fileno(), encoded[offset:])
                except (BlockingIOError, InterruptedError):
                    continue
                except BrokenPipeError:
                    raise ExecutionError("execution_closed") from None
            selector.unregister(self.proc.stdin)
            selector.register(self.proc.stdout, selectors.EVENT_READ)
            while b"\n" not in self.buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise ExecutionError("response_timeout")
                try:
                    chunk = os.read(self.proc.stdout.fileno(), 65536)
                except (BlockingIOError, InterruptedError):
                    continue
                if not chunk:
                    raise ExecutionError("execution_closed")
                self.buffer += chunk
                if len(self.buffer) > MAX_LINE:
                    raise ExecutionError("response_limit")
        line, self.buffer = self.buffer.split(b"\n", 1)
        self.transport_bytes += len(encoded) + len(line) + 1
        self.latencies.append(time.perf_counter() - start)
        if self.stderr_total > 65536:
            raise ExecutionError("diagnostic_limit")
        try:
            result = json.loads(line)
        except (ValueError, UnicodeError):
            raise ExecutionError("invalid_response") from None
        if type(result) is not dict or result.get("ok") is not True or "value" not in result:
            error = result.get("error_type", "invalid_envelope") if type(result) is dict else "invalid_envelope"
            raise ExecutionError("candidate_error:" + str(error)[:64])
        return result["value"]

    def configuration(self):
        config = json.loads(docker("inspect", self.name))[0]
        h = config["HostConfig"]
        result = {"network": h["NetworkMode"], "read_only": h["ReadonlyRootfs"],
                  "user": config["Config"]["User"], "mount_types": [m["Type"] for m in config["Mounts"]],
                  "cap_drop": h["CapDrop"], "security_options": h["SecurityOpt"],
                  "memory_bytes": h["Memory"], "cpu_quota_nanos": h["NanoCpus"],
                  "pids_limit": h["PidsLimit"], "image_id": config["Image"]}
        if (result["network"] != "none" or not result["read_only"] or result["user"] != "65532:65532"
            or any(kind != "tmpfs" for kind in result["mount_types"]) or result["cap_drop"] != ["ALL"]
            or "no-new-privileges:true" not in result["security_options"]):
            raise ExecutionError("isolation_configuration_mismatch")
        return result

    def measure(self):
        raw = docker("exec", self.name, "/bin/sh", "-c",
                     "cat /sys/fs/cgroup/cpu.stat; cat /sys/fs/cgroup/memory.peak; cat /sys/fs/cgroup/pids.peak", timeout=5)
        lines = raw.splitlines()
        numbers = [int(line) for line in lines if line.isdigit()]
        if len(numbers) != 2:
            raise ExecutionError("measurement_incomplete")
        return {"cpu_usec": next(int(line.split()[1]) for line in lines if line.startswith("usage_usec ")),
                "memory_peak_bytes": numbers[0], "tasks_peak": numbers[1], "raw": raw,
                "transport_bytes": self.transport_bytes, "active_request_seconds": sum(self.latencies),
                "request_seconds": list(self.latencies), "stderr_total_bytes": self.stderr_total}

    def close(self):
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)
        if self.proc:
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait()
            for channel in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                channel.close()
            self.proc = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
