# Computational Genesis — Lab 001 result

**The joint improvement claim was falsified for this implementation pair.** Both
implementations passed every specified response and recovery check. The inventor
did not achieve the preregistered CPU/checkpoint improvement.

The five protocol documents were first committed at `63c9ccc`. The completed
evaluator, clarified fault schedule, transport, model-tool boundary and passing
controls were frozen at `325d5e3`, before either participant session began. Both
selected source hashes were fixed before hidden evaluation; frozen files remained
unchanged throughout development and evaluation. The earlier pilot is separate.

## Preregistered decisions

H1: supported **for the inventor submission on these tests**, with no population
reliability estimate. The conventional baseline also passed. Six hidden synthetic
cases per suite, three paired repetitions, and two real container-death recovery
faults per suite produced 4,740 exact response comparisons across both arms; all
matched the independent specification. Restore-after-snapshot checks also passed.

H2: **falsified for this pair**. Eligibility required complete correctness for
both implementations, then at least 20% less median workload CPU AND 25% fewer
checkpoint bytes, with no more than 10% active-request latency regression.

| Metric, median of three complete suites | Conventional | Inventor | Inventor relative change |
|---|---:|---:|---:|
| Whole-suite workload CPU | 273.820 ms | 270.442 ms | 1.23% lower |
| Raw checkpoint bytes, summed over fixed schedule | 5,838 | 6,619 | 13.38% larger |
| Summed active request duration | 680.988 ms | 655.548 ms | 3.74% lower |

The CPU difference is small compared with the variation between repetitions.
The checkpoint-size threshold clearly fails regardless of how that timing noise
is interpreted. These are bounded observations, not evidence of general superiority
or inferiority of alternative computational architectures.

## What the participants implemented

Both independently chose existing techniques: hash maps for balances and immutable
receipts, dependency indexes and ready queues, and pickle/zlib snapshots. Renaming
those structures would not make them new abstractions. No new architectural
primitive was demonstrated.

The conventional implementation snapshots canonical data, then reconstructs its
derived dependency indexes on restore; it uses zlib compression level 6. The inventor
keeps incremental partial sums, dependency indexes and its queue in the checkpoint
and uses compression level 1. That is an ordinary space/reconstruction/compression
tradeoff. The design differs in several dimensions, so this run cannot isolate
which choice caused each measurement difference.

The source implementations contain 3,295 and 3,089 UTF-8 bytes respectively, with
749 and 696 AST nodes. Those are size proxies, not measurements of how much a human
or model must understand. Both have one class, three functions and three imports.
Pickle checkpoints remain untrusted bytes and are restored only inside the container.

## Development and independence

Each fresh design session used `gpt-6.1-sol`, low effort, existing Codex ChatGPT
authentication, and exactly the tools `develop` and `select`. Each was granted
240 seconds, eight calls and three submissions. Each chose to submit once and select
that submission after passing public tests: two calls, approximately 24.52 seconds
for the conventional builder and 24.81 seconds for the inventor. Optimization
opportunity was equal; multiple design/revision rounds were not exercised.

Both sessions completed with no unexpected tool/server capabilities. Reported token
totals were 8,801 and 8,705; marginal subscription dollar cost is unknown. Native
host tools, project context, integrations and memories were excluded. Neither
participant could read the other design, hidden corpus, evaluator, or results.
Final evaluation began only after both sessions closed and selections were frozen.

The evaluator is independently owned/frozen relative to the two participant
implementations. It has not had an external human or separate-model audit. Its
positive control passed; wrong-result, broken-restore and duplicate-effect controls
were rejected. A hostile-code control could not read a synthetic host canary,
write the immutable root, connect outward, or find credentials/a Docker socket.

## Execution and evidence

Order was AB / BA / AB. Every arm/repetition began in a fresh constrained execution
boundary. Six cases tested ledger streams, evolving dependency graphs and unseen
cross-domain interleavings. One fault killed execution after a fresh mutation
without checkpointing; the other killed it after persisting the mutation but before
acknowledging it. Restoring and retrying produced one correct logical effect.

CPU counters were collected outside participant code, preserved before each kill,
and summed over three cgroup segments per suite. Raw counters, memory/tasks, active
durations, transport bytes, every response/expected answer, checkpoint bytes and
source hashes are retained. CPU includes workload startup/load/recovery and sampling
work up to each reading; host Docker/broker, cloud inference and probe tail costs
are excluded. Whole-suite elapsed time is separately retained.

- [Frozen protocol/source hashes](evidence/lab001/run-001/freeze.json)
- [Controls and full control traces](evidence/lab001/run-001/controls.json)
- [Conventional source](evidence/lab001/run-001/participants/baseline/baseline-1.py)
- [Inventor source](evidence/lab001/run-001/participants/inventor/inventor-1.py)
- [Machine-readable decision](evidence/lab001/run-001/evaluations/20261106T154150Z-9be0384c/report.json)
- [Completed held-out corpus](evidence/lab001/run-001/evaluations/20261106T154150Z-9be0384c/completed-corpus.json)
- [Progress journal](evidence/lab001/run-001/progress.jsonl)

Each participant directory also contains its complete captured session tool calls,
submission explanation, public development trace and frozen selection. Each final
trial has its own complete JSON trace. The report's broad `trial_files` glob also
lists `completed-corpus.json`; the six actual trial records have `role`, `repetition`
and `result` fields. This indexing imperfection does not change the decision.

The first setup control run is preserved under `setup-001` and marked superseded.
Before participant development, inspection found its committed fault point landed
on an existing zero-delta retry; the final protocol instead selects a fresh nonzero
mutation. No participant saw hidden feedback or received a post-evaluation repair.

## Assumptions worth testing next

1. Derived-state checkpointing may pay off when restore/rebuild cost is material.
   These small workloads do not establish that tradeoff. Separate this from
   compression-level effects in a new preregistered ablation.
2. A Python class/message/snapshot boundary may constrain the architecture search.
   This experiment permits arbitrary code inside that boundary but does not test
   multi-host networks, distributed consensus, autonomous inference routing or new
   persistence interfaces.
3. One design session per role is not a distribution of designs. New studies need
   additional independent design pairs, genuinely new holdouts and, if desired,
   equal mandatory optimization rounds defined in advance.

No source, architecture, service or host integration was promoted outside the lab.
Normal execution removed all owned containers; source, checkpoints and evidence
remain in this isolated branch. A future study must reserve a new hidden corpus.
