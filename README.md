# Objective Lab

A local, isolated experiment in computation through verified state transitions.
See [the executed results](docs/RESULTS.md) for the current evidence and its limits.

The abstract model sees objectives, capabilities, synthetic resources, revisions,
budgets, checkpoints, receipts, and results. Its interface has no shell, filesystem,
process, or application tools. An independent supervisor owns the operating-system
boundary and grades actual outputs.

The current vertical reconciles synthetic records: retain active records, deduplicate
by identity, sum integer minor units by team, and verify the result. No personal or
project data is imported.

## Run

Requirements: Docker, Python 3, and the installed Codex CLI with an existing ChatGPT
sign-in. The native auth broker currently requires macOS `sandbox-exec`.

```sh
python3 -m unittest discover -s tests -v
python3 -m src.lab check --output evidence/local-check.json
python3 -m src.lab live --output evidence/live-pilot.json
python3 -m src.lab live --interrupt --output evidence/live-matched-recovery-final.json
```

`live` uses existing Codex authentication and subscription capacity. There is no
API-key setup, token extraction, alternate provider, or paid API fallback. Model
and effort are recorded. The default is `gpt-6.1-sol`, low effort. An unavailable
model fails rather than silently switching. The current tool policy is pinned to
that model; changing models requires a corresponding reviewed catalog entry.

The repository is local. No remote, published service, or listening port is created.
Each trial removes its own container and named state volume on normal exit. Docker
retains the locally built image. See [the contract](docs/CONTRACT.md) for authority,
recovery and isolation limits, and [the experiment](docs/EXPERIMENT.md) for what the
comparison can establish.

## Three environments

| Arm | Model interface | Execution |
|---|---|---|
| Conventional | Terminal inside a container | Agent invokes the same domain capabilities through commands and JSON arguments |
| Abstract | `observe`, `transition` | Runtime checks revision, dependencies, budget and result, then commits atomically |
| Discovery | Abstract interface plus `propose` | Agent supplies a finite composition; runtime qualifies and retains it against a declared criterion |

The discovery arm implements compositions of trusted primitives, not arbitrary
native code. Request-count improvement is distinct from latency, CPU or cost
improvement. This is a constrained research substrate, not an autonomous operating
system or an unrestricted access service for the host.
