# Results, all phases

Last updated 2026-11-10. This is the single place to read what each phase tested and found. Every
number links to the file it came from, on this branch (`self`), which carries every phase.

**One-line summary:** the execution model didn't make computation cheaper or faster. Every
efficiency test failed. What held every time it was tested is **trust**:
- work survives crashes without being redone;
- agents cannot reach what they weren't granted;
- false claims about what work depends on are caught;
- agents state those dependencies accurately.

Labels used below: **Observed** = measured. **Not established** = untested, or tested too weakly
to count.

---

## Phase 1: the interface experiment (224 trials)

**Question.** Does it help an agent to work through an interface with no processes and no paths,
and if so, is that because processes are hidden, or because the runtime adds services?

**Setup.**
- A 2×2 design: processes visible or hidden, crossed with runtime services on or off (caching,
  persistent state, checkpoints, verified delivery). Four interfaces:

  | | No runtime services | With runtime services |
  |---|---|---|
  | **Processes visible** | `shell` | `shell_svc` |
  | **Processes hidden** | `cap` | `cap_svc` |

- Claude Haiku 5.5 and Sonnet 5.5, with built-in tools removed, not merely forbidden in the
  prompt.
- An independent supervisor traced every process, killed agents mid-task, and graded against a
  reference implementation.
- Task 1: a finance pipeline whose capability list fit the job. Task 2: the list didn't fit, so
  agents needed an escape hatch.

**Observed.**

| Finding | Evidence |
|---|---|
| Reliability did not separate the interfaces | 220 of 224 trials passed. Both tasks were too easy. |
| Hidden processes plus runtime-owned state stopped all redone work after a crash | 0 of 28 full redos for `cap_svc`, against 3–8 of 8 for every other interface |
| Services added next to a shell were ignored | Agents listed checkpoints but almost never used the cache before the kill |
| Shell agents wandered the machine | 6 of 32 searched the host without a sandbox. 2 found harness data and failed. |
| Capability agents never wandered | 0 of 56. No tool could express a path. |
| Shell agents read implementations, and in the pilot skipped a costly check | Source read in 49 of 56 trials. Skipping was seen in the pilot only. |
| Efficiency was mostly vocabulary | 5–12× fewer processes, mostly shell exploration. Host CPU barely moved. |
| With an incomplete catalog, the escape hatch held up; the cost advantage didn't | 55 of 56 reports delivered via the hatch, about 3× the round-trips |

**Not established.** Reliability on hard tasks. Generality beyond two task families I designed.

**Files:** [`README.md`](README.md), [`results/final/summary.md`](results/final/summary.md),
[`results/task2/summary.md`](results/task2/summary.md).

---

## Lab 001: an inventor agent vs a conventional runtime (run by a separate Codex lab)

Reported by that lab, not reproduced here. Its code is on branch `lab001/genesis` at `9ed5d0a`.
- **H1 (correctness and recovery): supported.** 4,740 response comparisons matched the
  independent evaluator.
- **H2 (efficiency): failed.** The inventor used 1.2% less CPU and 13.4% more checkpoint space.
  The preregistered bar was 20% less CPU and 25% fewer bytes.
- **No new architectural primitive appeared.** Both designs used familiar mechanisms.

---

## Lab 002, phase A: declared semantics vs content-addressed reuse

**Question.** If the actor declares what each operation depends on, can a runtime that checks
those declarations reuse more work than Bazel-style content keys, without ever serving a stale
result?

**Setup.**
- 5 operations, 2 change mixes, 5 seeds × 25 steps.
- One honest declaration scenario, plus four with a single false declaration each:
  - **W1:** omits a field.
  - **W2:** a false "row-independent" claim.
  - **W3:** a rare dependence (only when memo is "REFUND").
  - **W4:** a false "order-insensitive" claim.
- Baselines: plain content keys, and content keys with oracle row-level sharding.
- Criteria were preregistered and frozen in git before each run.

**Observed.**

| | Run 1 | Run 2 (targeted audits) | Run 3 (expensive-work measure) |
|---|---|---|---|
| Safety: stale results from detectable lies (W1, W2, W4) | **0, PASS** | **0, PASS** | **0, PASS** |
| Rare lie (W3): stale results | 16 (trusted: 93) | **1** (0 at 50% audit) | not the focus |
| Efficiency vs best baseline | 1.86× CPU, **FAIL** | 1.52× CPU, **FAIL** | 1.62× expensive evaluations, **FAIL** |

- **The reuse ceiling is low.** Even with declarations simply trusted, semantics save at most
  **20%** of expensive work over well-sharded content keys (754 vs 940 evaluations), and 0% when
  every change matters.
- **Sampling-based verification costs about one full recompute** (608 expensive evaluations) on
  first use. That is more than reuse saves.
- Two of my own bugs were caught before the first run, and are logged as amendments: a wrong
  "true" declaration, and a control that could never pass.

**Files:** [`lab002/PREREG.md`](lab002/PREREG.md),
[`lab002/results/run1/verdict.txt`](lab002/results/run1/verdict.txt),
[`lab002/RUN2.md`](lab002/RUN2.md),
[`lab002/results/run2/verdict.txt`](lab002/results/run2/verdict.txt),
[`lab002/RUN3.md`](lab002/RUN3.md) (the result is at the end).

---

## Lab 002, phase B: can agents declare semantics for code they didn't write?

**Setup.** Codex wrote 8 finance operations, and later 8 more designed to hide their
dependencies. It never saw the runtime. Haiku, Sonnet and a fresh Codex each declared the
operations' semantics 3 times, scored against a white-box reference oracle.

**Observed.**
- **144 of 144 declarations exact,** across both sets. That includes dependencies hidden behind
  field selection driven by another field, parse-failure fallbacks, a lowercase "refund", and an
  exemption that applies only above 1,000,000.
- **The runtime verifier, probed directly (exploratory, not preregistered), caught 42 of 52
  omitted fields.** It missed collision-dependent, tie-breaker and rare-value dependencies, which
  are exactly the ones the agents got right.
- **Reading:** on code this size, agents' static reading beats black-box testing. The verifier,
  not the declaration, is the weak link.

**Not established.** Long, multi-file code, where agents will eventually start to err.

**Files:** [`lab002/phaseb/RESULTS.md`](lab002/phaseb/RESULTS.md).

---

## Builds (not experiments)

- **`self`:** one memory, one voice and one set of intents above interchangeable engines (Claude,
  Codex). Proof is recorded by the runtime, not claimed by a model.
  - **Observed:** a fact told to one engine was recalled by the other in the same voice. A
    decision answered once steered the other engine's next reasoning.
  - File: [`self/README.md`](self/README.md).
- **`machine_self`:** one intelligence that knows its machine. It compares against a factory
  baseline, journals every read, and answers only from evidence.
  - **Observed on a cloud container:**
    - It separated image noise (7,098 stripped doc files) from real changes.
    - It caught a new package, a new listening server (down to its pid) and a new file in `/etc`.
    - It corrected its own earlier wrong answer, unprompted.
    - It said "unattributed" instead of guessing.
  - **Missing:** who made each change. On macOS, Endpoint Security events would supply that.
  - Files: [`self/machine_self.py`](self/machine_self.py), [`self/birth.sh`](self/birth.sh)
    (the macOS first read, not yet run on a real Mac).

---

## Where this leaves the thesis

- **Not supported:** that hiding processes or declaring semantics makes computation cheaper.
  It failed in four efficiency tests across two labs.
- **Supported, small-scale and not independently reproduced:**
  - runtime-owned state makes interruptions harmless;
  - capability boundaries prevent agents from reaching beyond their grant;
  - declared semantics can be checked;
  - agents state them accurately.
- **Context, as of 2026-11:** others are now publishing on agent authorization and delegation.
  - AuthorizationBench reports agents acting outside their authority in about 19% of runs.
  - Agent Mesh argues that no shared benchmark exists for agents' irreversible, unlisted actions.
  - That benchmark is the clearest next experiment: crashes, ambiguity and injected
    instructions, with durable execution compared against an enforced capability runtime.

## Where everything is

| Branch | Holds |
|---|---|
| `self` | **Everything:** all of the above, plus this file |
| `lab002` | Lab 002 only, plus the phase 1 files it was branched from |
| `runtime-abstraction` | Phase 1 only |
| `lab001/genesis` | The other lab's Lab 001, untouched (repo default) |
| `main` | The pre-existing history, untouched |
