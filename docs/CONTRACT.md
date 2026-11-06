# Runtime and isolation contract

## Authority

The human supervisor creates trial environments, supplies synthetic fixtures,
selects the model and arm, and owns start, stop, pause, restart, inspection and
cleanup. Only explicitly supplied dynamic tools reach the experimental model.

The abstract agent can observe its one objective and request allowed transitions.
It cannot create objectives, expand permissions, select arbitrary host resources,
pause the supervisor, export private state, invoke an OS operation, or change its
own budget. The prototype has one objective per environment; multi-objective
scheduling is not implemented.

The supervisor methods `export` and `pause` exist only on private container stdio.
The model tool allowlist does not route them. Supervisor metadata, process/container
identifiers, volume names, filesystem paths and cgroup counters are retained only
in local human evidence. Tool responses are constructed from a narrow public
projection. Invalid inputs return a fixed refusal without a traceback or path.

## Canonical state

SQLite is canonical for the abstract runtime. The resource is immutable synthetic
input. State advances `raw → normalized → aggregated → verified`. Every request
supplies an expected revision and an immutable request identity. A transaction
contains validation, work, result checks, budget debit, checkpoint and receipt.

An exact retry returns the original receipt before checking current revision or
budget. Reusing an identity with different intent is rejected. A stale revision,
failed dependency, mismatched target, exhausted budget or paused supervisor cannot
partially change state. Concurrent writes serialize. Already-satisfied targets
avoid repeated computation but consume a new transition allowance and revision;
exact receipt replay consumes neither.

Each environment has 12 transition allowances. The broker separately bounds model
tool calls and turn duration. Containers have a 128 MiB memory limit, 0.5 CPU quota,
32-task limit, file-size ulimit and a small temporary filesystem. A named volume
persists checkpoint state through container restart and is removed with the trial.
The volume has no aggregate disk quota: the shell baseline remains bounded by
time and per-file limits, not a proved total storage bound.

Runtime routes implemented here are pure computation, receipt reuse, and no work
when a target is already satisfied. Inference and existing-service routing are
future adapters; this prototype does not simulate them as real executions.

## Isolation

The new Git repository contains only authored source, public model policy,
synthetic fixtures, tests, documentation and selected evidence. Runtime data and
temporary protocol/source inspection are ignored. No credential is tracked.

The trusted host broker creates a private temporary HOME and CODEX_HOME outside
the repo, with a generated configuration and a host-only symlink to the existing
Codex auth file. Codex manages authentication; Python never reads or extracts its
tokens. The broker does not copy user configuration, plugins, skills, memories,
MCP integrations, session history or other projects. Managed machine policy still
applies. Ordinary Codex preferences are not imported as experiment instructions.

The broker is enclosed in a native macOS sandbox: filesystem data reads are
limited to system runtime locations, its own private directory, the installed
Codex package, the auth file and the exact Codex preferences/encoding files.
Writes are confined to the broker's temporary directory and `/dev/null`.
Metadata reads, system IPC and outbound network are permitted for Codex's runtime,
managed-policy lookup and authentication. The broker is trusted and networked;
it is not a container for untrusted model code. Codex may refresh authentication
in its private home. That home is removed at normal close.

Native environment access is disabled; filesystem/environment/permission context
injection and project instructions are disabled. A pinned public model catalog
removes patch tools and model-advertised native utilities; shell, browser, apps,
plugins, skills, memories, multi-agent tools and other optional facilities are
disabled. Unexpected server requests and native execution items fail the trial.
The declared tool policy is an enforceable client configuration, not a packet-level
attestation of the provider's received prompt. Actual provider tool-schema capture
is not implemented.

Workload containers run as an unprivileged user with no network, no capabilities,
no new privileges, a read-only root, and no host bind mounts or Docker socket.
Their only writable persistent resource is a fresh, uniquely named Docker volume.
No credentials or host environment are forwarded. The baseline's terminal runs
inside this container, never in the host shell. The independent oracle is not
included in the image. Container isolation is a practical boundary, not a proof
against Docker, kernel, Codex or broker vulnerabilities.

Cloud inference necessarily receives the deliberately supplied synthetic objective,
tool schemas, calls and results. “Clean” does not mean no experiment data reaches
the selected cloud model.

## Recovery and cleanup

`check` exercises a real container stop/restart after a committed transition and
an exact lost-response replay. Supervisor pause rejects new mutations while
allowing prior receipts to be recovered. The supervisor can interrupt the owned
container independently of the model or abstraction.

Normal context-manager exit stops/removes the trial container, removes its volume,
terminates the Codex broker and deletes its private temporary directory. A host
crash or forced kill can leave owned resources behind. Inspect only objects with
label `research.objective-lab=true`; confirm no active trial owns an object before
manual removal. No sweeping cleanup of other Docker resources is permitted.

The source is trusted. Generated primitives are interpreted data in a finite
grammar: no eval, dynamic imports, loops, subprocesses or native code. The host
supervisor can inspect container configuration and cgroup counters throughout.
