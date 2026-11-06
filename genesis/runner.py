"""Trusted stdio transport, shipped alone into a constrained execution image."""
import base64
import contextlib
import io
import json
import sys

CHANNEL = sys.stdout
MAX_SNAPSHOT = 1048576


def reply(value):
    CHANNEL.write(json.dumps(value, separators=(",", ":")) + "\n")
    CHANNEL.flush()


def main():
    engine = None
    namespace = {}
    for line in sys.stdin:
        try:
            if len(line) > 2097152:
                raise ValueError("input_limit")
            request = json.loads(line)
            # Candidate diagnostics never become protocol results.
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                if request["op"] == "install":
                    source = request["source"]
                    if len(source.encode()) > 65536:
                        raise ValueError("source_limit")
                    exec(compile(source, "<submitted-design>", "exec"), namespace)
                    value = {"installed": True}
                elif request["op"] == "load":
                    snapshot = request.get("snapshot")
                    engine = namespace["Engine"](base64.b64decode(snapshot, validate=True) if snapshot is not None else None)
                    value = {"loaded": True}
                elif request["op"] == "handle":
                    value = engine.handle(request["message"])
                    if not isinstance(value, dict):
                        raise ValueError("response_type")
                elif request["op"] == "snapshot":
                    snapshot = engine.snapshot()
                    if not isinstance(snapshot, bytes) or len(snapshot) > MAX_SNAPSHOT:
                        raise ValueError("snapshot_limit_or_type")
                    value = {"data": base64.b64encode(snapshot).decode(), "bytes": len(snapshot)}
                else:
                    raise ValueError("unknown_operation")
            reply({"ok": True, "value": value})
        except BaseException as error:
            # Exclude traceback, arbitrary messages and paths from design-agent feedback.
            reply({"ok": False, "error_type": type(error).__name__})


if __name__ == "__main__":
    main()
