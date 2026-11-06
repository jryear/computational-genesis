"""Positive/negative controls; evaluator-owned and never sent to design agents."""
POSITIVE = '''
import json
class Engine:
    def __init__(self, snapshot):
        self.s = json.loads(snapshot) if snapshot else {"balances":{},"receipts":{},"jobs":{},"done":{}}
    def snapshot(self):
        return json.dumps(self.s,sort_keys=True,separators=(",",":")).encode()
    def handle(self,m):
        s=self.s; op=m["op"]
        if op=="credit":
            k=m["id"]; intent=[m["key"],m["delta"]]
            if k in s["receipts"]:
                old=s["receipts"][k]
                return old[1].copy() if old[0]==intent else {"ok":False,"error":"conflict"}
            total=s["balances"].get(m["key"],0)+m["delta"]
            s["balances"][m["key"]]=total
            reply={"ok":True,"total":total}; s["receipts"][k]=[intent,reply.copy()]
            return reply
        if op=="balance": return {"total":s["balances"].get(m["key"],0)}
        if op=="define":
            k=m["id"]; spec=[m["parents"],m["weight"]]
            if k in s["jobs"] and s["jobs"][k]!=spec: return {"ok":False,"error":"conflict"}
            s["jobs"][k]=spec; return {"ok":True}
        if op=="run":
            while True:
                progress=False
                for k,(parents,weight) in s["jobs"].items():
                    if k not in s["done"] and all(p in s["done"] for p in parents):
                        s["done"][k]=weight+sum(s["done"][p] for p in parents); progress=True
                if not progress: break
            return {"done":s["done"].copy()}
        if op=="result": return {"ready":m["id"] in s["done"],"value":s["done"].get(m["id"])}
'''

WRONG = 'class Engine:\n def __init__(self,s): pass\n def handle(self,m): return {}\n def snapshot(self): return b"{}"\n'
BROKEN_RESTORE = POSITIVE.replace('self.s = json.loads(snapshot) if snapshot else', 'self.s =')
DUPLICATE_EFFECT = POSITIVE.replace('if k in s["receipts"]:', 'if False:')
HOSTILE = '''
import os,socket
class Engine:
 def __init__(self,s): pass
 def snapshot(self): return b"probe"
 def handle(self,m):
  try:
   open(m["host_canary"]).read(); host_read=True
  except OSError: host_read=False
  try:
   open("/outside-write","w").write("test"); root_write=True
  except OSError: root_write=False
  sock=socket.socket(); sock.settimeout(.2)
  network=sock.connect_ex(("1.1.1.1",443))==0; sock.close()
  return {"host_read":host_read,"root_write":root_write,"network":network,
   "docker_socket":os.path.exists("/var/run/docker.sock"),
   "credential_environment":any("TOKEN" in k or "KEY" in k or k=="CODEX_HOME" for k in os.environ)}
'''
