# Minimal substrate — Lab 001, version 1

The agent receives a functional contract, limits and synthetic public examples.
Its only tools submit a design for a development test or select a prior submission.
There is no host execution, filesystem, process, application or network tool.

The submitted Python source defines `Engine`:

```python
class Engine:
    def __init__(self, snapshot: bytes | None): ...
    def handle(self, message: dict) -> dict: ...
    def snapshot(self) -> bytes: ...
```

The supervisor delivers messages, observes responses and holds opaque snapshot
bytes. Restore must recreate the same logical state. No storage representation,
domain algorithm, concurrency model, deduplication scheme or checkpoint encoding
is supplied. Python and this transport are experimental constraints, not claims
about ideal computational primitives. Engines can implement arbitrary computation
inside their constrained execution boundary. The earlier fixed capability grammar
is not used.

## Functional objectives

All input identifiers are nonempty strings of at most 64 characters. Integer
arithmetic is exact. Only specified well-formed messages are graded. Extra response
fields are incorrect; dictionary member order is irrelevant.

**Ledger:** `{"op":"credit","id":I,"key":K,"delta":D}` accepts one integer
delta per immutable request identity. First acceptance changes that key's balance
and returns `{"ok":true,"total":T}`. An exact retry returns its ORIGINAL receipt,
even if later credits changed the balance. Reusing the identity with different
key/delta returns `{"ok":false,"error":"conflict"}` and changes nothing.
`{"op":"balance","key":K}` returns `{"total":T}`; an absent key has balance zero.

**Dependencies:** `{"op":"define","id":J,"parents":[P...],"weight":W}` accepts
a job and returns `{"ok":true}`. Exact redefinition returns the same response;
a changed parents list or weight returns the conflict response without mutation.
Parents are unique, ordered strings; forward references and cycles are valid.
`{"op":"run"}` completes every transitively ready job, computing
`value = weight + sum(parent values)`, and returns `{"done":{J:value,...}}`
for ALL completed jobs. Missing/cyclic dependencies stay pending. Later definitions
can unblock pending jobs. `{"op":"result","id":J}` returns
`{"ready":true,"value":V}` when complete, otherwise `{"ready":false,"value":null}`.
Ledger and dependency state must coexist without identity collisions.

## Limits and permissions

Each participant: the same `gpt-6.1-sol` model, low effort, eight tool calls,
240 seconds active model-turn time including development-tool execution, at most
three source submissions of 65,536 UTF-8 bytes each. A final selection can refer
only to its own previously tested source. No final selection means the last
submission is frozen, including failures. No silent model/provider fallback.

Each execution: unprivileged Linux container, 128 MiB RAM, 0.5 CPU quota, 32 tasks,
no network/capabilities/host mounts/authentication, read-only root, 8 MiB temporary
memory-backed storage. The Python standard library is available; installing packages
is not. Every supervisor request has a three-second deadline and 2 MiB response cap;
snapshot bytes are capped at 1 MiB. Stderr and unsolicited output are bounded.
The supervisor may kill the entire execution boundary independently.

The source and its imports execute only in the container. The host treats source,
responses and checkpoints as untrusted data. No generated source is imported or
executed by the host. Checkpoints do not confer host access.
