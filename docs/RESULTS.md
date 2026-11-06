# Local results — 2026-11-06

The final capability-matched, lost-reply recovery pilot passed the independent
result oracle in all three arms. It used the existing Codex ChatGPT sign-in,
`gpt-6.1-sol`, low effort, no model/provider fallback, synthetic records, and a
fresh isolated container per arm. Each trial comprised an interrupted session
and a fresh recovery session against durable state.

| Arm | Independent grade after restart | Model tool calls, both sessions | Model-turn seconds, both sessions | Reported total tokens | Workload CPU ms across restart | Workload peak MiB |
|---|---|---:|---:|---:|---:|---:|
| Conventional, same capabilities through shell | Pass | 5 | 18.63 | 3,634 | 771.96 | 24.09 |
| Abstract transitions | Pass | 5 | 15.19 | 2,639 | 174.76 | 16.56 |
| Discovery with finite composition | Pass | 5 | 22.59 | 2,971 | 177.80 | 16.51 |

These are individual pilot observations, not estimates of reliability or a
performance win. CPU counters cover actual container work, including adapter,
qualification and measurement overhead, across both cgroup segments. They exclude
the host broker and cloud inference. Latency sums the two model turns, excludes
broker initialization and container provisioning, and includes tool execution.
End-to-end time including broker initialization is also retained in the JSON.
Peak tasks were 11 for the shell adapter and 7 for each other arm; these are
concurrent-task peaks, not lifetime process counts. Dollar cost is unknown.

The discovery agent proposed `p_reconcile = [normalize, aggregate, verify]`.
The runtime qualified it on eight additional synthetic inputs and retained it
under the declared criterion: equal output with one transition request instead
of three. The primitive and its qualification receipt survived restart. Total
model tool calls remained five because observation, proposal and recovery also
consume calls. This does not demonstrate invention of a novel algorithm.

## Verification

- 15 unit/policy tests pass, including concurrent claims, replay, request and
  primitive identity conflicts, stale state, dependency denial, budget exhaustion,
  pause, process death before commit, partial compositions and multiple inputs.
- Container integration checks pass, including a real stop/restart after commit,
  exact replay, denied networking/root writes, unprivileged execution, no host
  mounts, no Docker socket, no auth environment and no supervisor oracle in image.
- Native broker canary probes deny reads/writes outside its allowed data boundary,
  allow its own private data, retain ChatGPT authentication and remove its private
  temporary home on close. Its directory mode is 0700.
- Effective model/provider and zero imported instruction sources are recorded.
  No unexpected native execution items or server requests occurred in the final
  live trials. Packet-level provider tool-manifest attestation is not implemented.

The final reports carry SHA-256 manifests of the actual source and model policy:

- [Final live recovery trace](../evidence/live-matched-recovery-final.json)
- [Container and recovery integration evidence](../evidence/local-check.json)
- [Native broker isolation probe](../evidence/broker-isolation.json)

## Preserved exploratory evidence and corrected issues

`live-pilot.json` was an initial, capability-unmatched smoke test. It has no source
manifest and supports no interface-specific comparison. `live-matched-recovery.json`
is an intermediate recovery test with an ambiguous target schema; the model
recovered from rejected requests. It also predates source manifests.
`live-matched-recovery-exploratory.json` has a source manifest but its resource
counters covered only the post-restart cgroup. Do not treat those counters as total
trial resource usage. The final report fixes this by retaining both segments.

During setup, the initial broker sandbox blocked a root-directory read needed
for executable startup and IPC needed for managed-preference synchronization.
The broker failed closed until those narrow runtime allowances were established.
No auth keys were created, no user/global configuration was edited and no alternate
provider was used. A public Python image environment key initially tripped an
overbroad environment check; workload entrypoints and shell executions now receive
an explicit clean environment, and actual runtime environment absence is checked.

## Next experimental boundary

The working substrate is one synthetic objective per isolated trial, with finite
compositions and durable state across restarts. A general discovery claim requires
more task families, held-out evaluation, counterbalanced repetitions, fuller host
instrumentation, and a predefined implementation-knowledge rubric. See the
[experiment design](EXPERIMENT.md). Trials remove their state volumes at normal
completion; long-lived multi-objective environments are not implemented.
