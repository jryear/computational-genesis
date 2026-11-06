"""Local Codex app-server client. Existing auth stays outside repo and workloads."""
import json
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import tempfile
import threading
import time


FEATURES_OFF = ["apps", "plugins", "remote_plugin", "memories", "hooks", "shell_tool",
                "unified_exec", "view_image", "browser_use", "computer_use", "image_generation",
                "in_app_browser", "multi_agent", "multi_agent_v2", "goals", "sleep_tool",
                "tool_suggest", "skill_search", "code_mode", "code_mode_host", "shell_snapshot",
                "plugin_discovery_prefetch", "prevent_idle_sleep", "request_permissions_tool",
                "token_budget", "current_time_reminder", "deferred_executor", "code_mode_only",
                "multi_agent_v2_dynamic_tools", "send_async_message", "runtime_agent_instances"]


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def tool(name, description, properties):
    return {"type": "function", "name": name, "description": description, "inputSchema": object_schema(properties)}


TEXT = {"type": "string"}
TOOLS = [tool("observe", "Read the objective, capabilities, remaining budget and durable checkpoint.", {}),
         tool("transition", "Request an atomic verified transition. On interruption, observe and retry the exact request identity.",
              {"request_id": {"type": "string", "description": "Immutable identity for this exact request."},
               "expected_revision": {"type": "integer", "minimum": 0},
               "capability": {"type": "string", "description": "An available capability or retained primitive."},
               "target": {"type": "string", "enum": ["raw", "normalized", "aggregated", "verified"],
                          "description": "Desired checkpoint after the capability, not the resource identifier."}})]
PROPOSE = tool("propose", "Implement a named primitive as a finite composition; qualify on held-out inputs and retain only if equal results use fewer requests. Available operations in order: normalize, aggregate, verify. Name must start p_ and contain lowercase letters.",
               {"name": TEXT, "plan": {"type": "array", "items": TEXT}})
SHELL = tool("terminal", "Execute a shell command in the isolated synthetic workload environment. No network or host access.", {"command": TEXT})


class CodexBroker:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory(prefix="objective-broker-")
        self.root = Path(self.temp.name).resolve()
        self.home = self.root / "codex"
        self.home.mkdir(mode=0o700)
        auth = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "auth.json"
        if not auth.is_file():
            self.temp.cleanup()
            raise RuntimeError("Existing Codex file authentication unavailable; no API fallback")
        # A private host-only reference, never a credential copy, mount, or model input.
        (self.home / "auth.json").symlink_to(auth.resolve())
        # Public model metadata with native tool capabilities removed. Backend model is unchanged.
        policy = Path(__file__).with_name("model-policy.json")
        (self.home / "models.json").write_bytes(policy.read_bytes())
        config = {"model_catalog_json": str(self.home / "models.json"),
                  "include_environment_context": False, "include_environment_context_time": False,
                  "include_permissions_instructions": False, "include_apps_instructions": False,
                  "include_collaboration_mode_instructions": False, "project_doc_max_bytes": 0,
                  "web_search": "disabled", "cli_auth_credentials_store": "file",
                  "skills": {"bundled": {"enabled": False}, "include_instructions": False},
                  "agents": {"enabled": False}, "tools": {"update_plan": {"enabled": False},
                  "experimental_request_user_input": {"enabled": False}},
                  "analytics": {"enabled": False}, "feedback": {"enabled": False},
                  "model_reasoning_effort": "low", "features": {x: False for x in FEATURES_OFF}}
        # Isolated CODEX_HOME loads only this generated configuration; no user config or MCPs.
        def toml_value(v):
            if isinstance(v, dict):
                return "{ " + ", ".join(k + " = " + toml_value(a) for k, a in v.items()) + " }"
            return json.dumps(v)
        (self.home / "config.toml").write_text("\n".join(k + " = " + toml_value(v) for k, v in config.items()))
        executable = Path(shutil.which("codex")).resolve()
        package = executable.parent.parent
        # Native sandbox encloses the trusted auth broker as defense in depth. Models have
        # no native environment or command tools, and workloads never run in this process.
        quote = json.dumps
        profile = "\n".join([
            "(version 1)", "(deny default)", "(allow process* sysctl-read mach-lookup mach-register ipc* network-outbound file-read-metadata user-preference-read)",
            "(allow file-read* (literal \"/\") (subpath \"/System\") (subpath \"/usr\") (subpath \"/Library\")",
            " (subpath \"/private/etc\") (subpath \"/dev\") (subpath \"/private/var/db/timezone\")",
            f" (subpath {quote(str(self.root))}) (subpath {quote(str(package))}) (literal {quote(str(auth.resolve()))}))",
            f"(allow file-read* (literal {quote(str(Path.home() / 'Library/Preferences/com.openai.codex.plist'))}) (literal {quote(str(Path.home() / '.CFUserTextEncoding'))}))",
            f"(allow file-write* (subpath {quote(str(self.root))}) (literal \"/dev/null\"))"])
        env = {"HOME": str(self.root), "CODEX_HOME": str(self.home), "TMPDIR": str(self.root),
               "PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "en_US.UTF-8"}
        self.errors = tempfile.TemporaryFile(mode="w+t")
        self.proc = subprocess.Popen(["/usr/bin/sandbox-exec", "-p", profile, str(executable), "app-server", "--stdio"],
                                     cwd=self.root, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=self.errors, text=True, bufsize=1)
        self.events = queue.Queue()
        self.reader = threading.Thread(target=self._read, daemon=True); self.reader.start()
        self.seq = 0
        self.pending = []
        try:
            self.request("initialize", {"clientInfo": {"name": "objective_lab", "version": "0.1.0"},
                                        "capabilities": {"experimentalApi": True}})
            self.send({"method": "initialized", "params": {}})
        except BaseException:
            self.errors.seek(0)
            error = self.errors.read(4096)
            error = error.replace(str(self.root), "<private-broker>").replace(str(auth), "<codex-auth>")
            error = re.sub(r"[A-Za-z0-9_./+@=-]{30,}", "<redacted>", error)
            code = self.proc.poll()
            self.close()
            raise RuntimeError("Codex startup failed (" + str(code) + "): " + error) from None

    def _read(self):
        for line in self.proc.stdout:
            try:
                self.events.put(json.loads(line))
            except ValueError:
                self.events.put({"broker_error": "invalid_protocol"})
        self.events.put({"broker_error": "connection_closed"})

    def send(self, value):
        self.proc.stdin.write(json.dumps(value) + "\n"); self.proc.stdin.flush()

    def request(self, method, params):
        self.seq += 1; ident = self.seq
        self.send({"id": ident, "method": method, "params": params})
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            event = self.events.get(timeout=max(.01, deadline - time.monotonic()))
            if "broker_error" in event:
                raise RuntimeError(event["broker_error"])
            if event.get("id") == ident:
                if "error" in event:
                    # Errors may contain host metadata. Never forward to the model or evidence.
                    diagnostic = str(event["error"].get("message", ""))
                    diagnostic = diagnostic.replace(str(self.root), "<private-broker>")
                    diagnostic = re.sub(r"[A-Za-z0-9_./+@=-]{30,}", "<redacted>", diagnostic)
                    raise RuntimeError("Codex rejected " + method + "; code=" + str(event["error"].get("code")) + "; " + diagnostic)
                return event["result"]
            self.pending.append(event)
        raise TimeoutError("Codex protocol deadline")

    def run(self, model, arm, prompt, handle, max_calls=12, seconds=120, interrupt_after_effect=False, tool_specs=None):
        tools = tool_specs if tool_specs is not None else ([SHELL] if arm == "conventional" else TOOLS + ([PROPOSE] if arm == "discovery" else []))
        started = self.request("thread/start", {"model": model, "modelProvider": "openai",
            "allowProviderModelFallback": False, "ephemeral": True, "environments": [],
            "runtimeWorkspaceRoots": [], "selectedCapabilityRoots": [], "approvalPolicy": "never",
            "sandbox": "read-only", "baseInstructions": "You are an experimental computational agent. Complete the supplied objective using the provided tools. Return a brief result after verified completion.",
            "dynamicTools": tools})
        if started["model"] != model or started["modelProvider"] != "openai" or started.get("instructionSources"):
            raise RuntimeError("Effective model or context isolation mismatch")
        thread = started["thread"]["id"]
        self.request("turn/start", {"threadId": thread, "environments": [], "effort": "low",
                                    "input": [{"type": "text", "text": prompt}]})
        begin = time.monotonic(); calls = []; usage = None; messages = []; status = "timeout"
        deadline = begin + seconds
        unexpected = []
        while time.monotonic() < deadline:
            if self.pending:
                event = self.pending.pop(0)
            else:
                try:
                    event = self.events.get(timeout=min(1, max(.01, deadline - time.monotonic())))
                except queue.Empty:
                    continue
            if "broker_error" in event:
                raise RuntimeError(event["broker_error"])
            method, params = event.get("method"), event.get("params", {})
            if method == "item/tool/call":
                name = params["tool"]
                if name not in [t["name"] for t in tools] or len(calls) >= max_calls:
                    result = {"ok": False, "error": "capability_or_budget_denied"}
                else:
                    result = handle(name, params["arguments"])
                calls.append({"tool": name, "arguments": params["arguments"], "result": result})
                if interrupt_after_effect and ((name == "terminal") or (name == "transition" and result.get("ok"))):
                    # Deliberately drop the tool reply after execution; caller kills broker and workload.
                    status = "injected_lost_reply"
                    break
                self.send({"id": event["id"], "result": {"contentItems": [{"type": "inputText", "text": json.dumps(result)}], "success": True}})
                if len(calls) > max_calls:
                    status = "tool_budget_exhausted"; break
            elif "id" in event and "method" in event:
                unexpected.append(method)
                self.send({"id": event["id"], "error": {"code": -32601, "message": "Unsupported capability"}})
                status = "unexpected_capability"; break
            elif method == "item/started":
                item_type = params.get("item", {}).get("type")
                if item_type in ("commandExecution", "fileChange", "mcpToolCall", "webSearch", "imageGeneration"):
                    unexpected.append(item_type); status = "unexpected_native_tool"; break
            elif method == "thread/tokenUsage/updated":
                usage = params.get("tokenUsage")
            elif method == "item/completed" and params.get("item", {}).get("type") == "agentMessage":
                messages.append(params["item"].get("text", ""))
            elif method == "turn/completed":
                status = params["turn"]["status"]; break
            elif method == "error":
                status = "provider_error"; break
        # Closing the enclosing broker terminates timed out inference without any fallback.
        return {"requested_model": model, "effective_model": started["model"],
                "provider": started["modelProvider"], "effort": "low", "auth": "existing_codex_chatgpt",
                "declared_tools": [t["name"] for t in tools], "environment_access": False,
                "instruction_sources": len(started.get("instructionSources", [])),
                "status": status, "latency_seconds": time.monotonic() - begin,
                "prompt_bytes": len(prompt.encode()), "tool_schema_bytes": len(json.dumps(tools).encode()),
                "usage": usage, "cost_usd": None, "unexpected_capabilities": unexpected,
                "calls": calls, "messages": messages}

    def close(self):
        if getattr(self, "proc", None):
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait()
            self.proc.stdin.close(); self.proc.stdout.close()
        self.temp.cleanup()
        if getattr(self, "errors", None):
            self.errors.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
