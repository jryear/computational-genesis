"""Slow independent specification model. Not shipped to execution boundaries."""
import copy
import json


def same(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(right, sort_keys=True, separators=(",", ":"))


class Oracle:
    def __init__(self):
        self.credits = []
        self.definitions = []
        self.completed = {}

    def step(self, message):
        op = message["op"]
        if op == "credit":
            for old, receipt in self.credits:
                if old["id"] == message["id"]:
                    return copy.deepcopy(receipt if old["key"] == message["key"] and old["delta"] == message["delta"] else {"ok": False, "error": "conflict"})
            total = message["delta"] + sum(m["delta"] for m, _ in self.credits if m["key"] == message["key"])
            receipt = {"ok": True, "total": total}
            self.credits.append((copy.deepcopy(message), receipt))
            return dict(receipt)
        if op == "balance":
            return {"total": sum(m["delta"] for m, _ in self.credits if m["key"] == message["key"])}
        if op == "define":
            for old in self.definitions:
                if old["id"] == message["id"]:
                    return {"ok": True} if old["parents"] == message["parents"] and old["weight"] == message["weight"] else {"ok": False, "error": "conflict"}
            self.definitions.append(copy.deepcopy(message))
            return {"ok": True}
        if op == "run":
            while True:
                ready = [m for m in self.definitions if m["id"] not in self.completed and all(p in self.completed for p in m["parents"])]
                if not ready:
                    break
                for job in ready:
                    self.completed[job["id"]] = job["weight"] + sum(self.completed[p] for p in job["parents"])
            return {"done": dict(self.completed)}
        if op == "result":
            key = message["id"]
            return {"ready": key in self.completed, "value": self.completed.get(key)}
        raise ValueError("invalid evaluator input")
