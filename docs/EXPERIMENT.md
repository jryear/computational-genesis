# First experiment

## Question

Does changing the agent's execution interface improve verified completion and
recovery without hiding real resource consumption or transferring unmeasured
engineering work into the runtime?

The three arms use the same selected model and effort, synthetic input, independent
output oracle, container privileges and resource ceilings. Their interfaces differ.
The conventional arm has a container terminal; the abstract arm receives only
state-transition tools; the discovery arm can additionally propose finite
compositions.

## Current measurement

Record per trial: requested/effective model and provider; auth mode; declared tools;
instruction-source count; allowed environment access; actual tool calls/results;
completion status; independent grade; inference token usage when Codex reports it;
turn and end-to-end latency; cgroup CPU usage, peak memory and peak tasks; runtime
request counts and shell execution counts. Measurement itself runs a shell probe,
and this overhead is explicitly included in the host counters.

Dollar cost is unknown. A Codex subscription run is not a zero-cost inference run,
and API token prices do not establish marginal subscription cost. No cost estimate
is invented.

Implementation knowledge is not directly quantified yet. Prompt and tool descriptions
are visible in source; the conventional arm is told Python import and artifact
locations, while the abstract arm is told capabilities, stage order and revision
semantics. A human-rated implementation-knowledge rubric and schema/prompt byte
counts should accompany the larger experiment. Token count alone is not that rubric.

## Limits and confounders

The first exploratory shell baseline implemented the transformation while the
abstract runtime already contained those capabilities. Its evidence is retained
as `live-pilot.json`, without an interface-specific performance conclusion. The
current conventional adapter gives the shell agent the same preimplemented domain
capabilities and atomic state engine as the abstract arm. The shell additionally
has arbitrary computation inside its container; its interface is intentionally
more expressive. This is capability-matched for the supplied task, not an assertion
that the tool permissions or implementation knowledge are identical. No agent is
merely prompted to deny the existence of processes.

The primitive grammar is finite composition of trusted operations. Qualification
checks additional synthetic inputs and accepts equal results with fewer boundary
requests. It does not demonstrate discovery of novel algorithms, arbitrary safe
code synthesis, lower CPU usage, or lower latency. Qualification seeds are fixed
in trusted source; they are not a secure secret or a statistical evaluation set.

One synthetic task and one trial per arm are a live smoke test. They do not estimate
completion reliability, tail latency, repeatability or generalization. Container
warmup, model/cache warmup, arm ordering and provider variability can dominate.

## Larger comparison before adoption

Freeze task fixtures, permissions, graders, runtime version, model and budgets.
Include multiple unseen task families and seeds, repeated counterbalanced arm
orders, identical available domain capabilities and complete failed/timeout trials.
Include no-op, cold/warm cache and reused-service cases as separate conditions.

Inject both post-commit/lost-reply interruptions and failures during computation,
inference, and service dependency recovery. Give each arm the same recovery budget;
measure duplicate effects and durable checkpoint loss. Record all OS execution,
including the broker, workload and qualification overhead, separately from
inference. Current cgroup measurements cover workloads only.

Keep the supervisor and output oracle outside the candidate's writable boundary.
For discovery, separate search inputs, qualification inputs and final evaluation;
charge proposal implementation, qualification and storage costs; retain candidates
only against a preregistered performance criterion after correctness. Report
negative results, rejected proposals and setup failures alongside retained ones.
