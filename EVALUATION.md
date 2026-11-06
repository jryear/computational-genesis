# Independent evaluation — Lab 001, version 1

Freeze this contract and the deterministic evaluator before either AI participant
starts. The evaluator is a separate trusted component, not participant-authored code.
Its independence is a trust/source boundary, not a claim of external human review.

## Workloads

Public development: small ledger receipt/retry/conflict cases and dependency
forward-reference/unblocking cases. Both participants receive exactly the same
public contract and development tests. Development feedback includes deterministic
correctness, bounded diagnostic errors, source size and execution measurements.

Hidden evaluation: six synthetic cases, two per family: ledger streams, evolving
dependency graphs, and previously unseen interleavings of both domains. Include
negative/zero deltas, original-receipt retries after later changes, identity conflicts,
forward references, cycles, and identities shared across domains. Hidden generator,
seeds, messages and expected answers never enter either design agent's context or
development execution image. Generated implementations necessarily receive individual
test messages during final execution, after the design sessions are closed/frozen.
No hidden feedback may be used for revision in this experiment.

Three paired repetitions, alternating arm order AB / BA / AB, with a fresh execution
boundary per arm. Every case begins with a fresh engine. Checkpoints after each case
are included in the byte metric. Two cases per suite inject a lost reply: snapshot
the acknowledged prefix; execute the next message and discard its reply; kill the
whole container; restore the prefix into a new container; redeliver and compare.
Other cases test in-boundary snapshot restoration. This is sequential handoff and
message replay; it is not multi-host parallelism, consensus or network partition proof.

## External measurements and fixed decisions

Exact canonical JSON equality grades EVERY response against an independent reference
model. Correctness and recovery are absolute gates. The evaluator checks source and
protocol hashes before/after development and evaluation, and freezes submitted hashes
before generating final reports. No self-reported completion or performance counts.

Collect wall-clock active request durations, whole-suite elapsed time, raw and summed
cgroup CPU across killed/recreated boundaries, maximum cgroup memory/tasks, total
raw checkpoint bytes, transport bytes, source bytes, AST node/function/class counts,
all responses, faults, errors, source hashes and order. Record Codex effective model,
provider, effort, calls, observed token counters and development duration. Dollar
cost and host-broker/cloud-inference CPU are unknown; do not substitute API prices.
Code size and prompt bytes are complexity proxies, not a complete knowledge metric.

H2 uses median complete-suite workload CPU and summed raw checkpoint sizes (same
messages/checkpoint schedule), with median summed active request duration as a
non-regression guard. Charge load, execution, snapshot, recovery and resource-probe
overhead. Report measurement overhead and setup separately where possible. Retain
failures and missing observations; do not discard slow or incorrect trials.

## Evaluator controls and security

Before participant evaluation: a trusted positive-control engine must pass public
and hidden semantics; wrong-result, broken-restore and duplicate-effect mutants must
be rejected. A hostile-code control must fail to read a synthetic host-only canary,
modify the immutable root, connect outward, or find a Docker socket/credentials.
The evaluator and expected answers are absent from execution images. Verify actual
container configuration; do not rely on participant claims.

Security probes establish the tested boundary, not immunity from kernel/Docker/broker
vulnerabilities. Hidden test integrity depends on no evaluator edits or corpus feedback
after design freeze. Preserve evaluator source, protocol, all source submissions,
development transcripts, complete final inputs/outputs, controls and raw measurements.
Final evidence can disclose the completed corpus to humans; subsequent studies must
reserve a NEW hidden corpus and must not call this one unseen again.
