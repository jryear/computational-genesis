"""Capability-matched conventional command adapter, available only inside workloads."""
import argparse
import json
from substrate import Runtime, Refusal

parser = argparse.ArgumentParser()
parser.add_argument("operation", choices=("observe", "transition"))
parser.add_argument("request", nargs="?", default="{}")
args = parser.parse_args()
runtime = Runtime("/state/runtime.db")
try:
    value = runtime.observe() if args.operation == "observe" else runtime.transition(json.loads(args.request))
    print(json.dumps({"ok": True, "value": value}))
except Refusal as error:
    print(json.dumps({"ok": False, "error": str(error)}))
except (ValueError, TypeError, KeyError):
    print(json.dumps({"ok": False, "error": "request_refused"}))
finally:
    runtime.close()
