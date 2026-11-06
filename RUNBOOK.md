# Reproducible runbook — Lab 001

Use this local lab branch. Keep all input synthetic. Existing Codex ChatGPT sign-in,
Python 3, Docker and the native macOS broker sandbox are required for live development.
There is no API key, package installation, published endpoint or provider fallback.

## Ordered execution

1. Inspect Git state and Docker availability. Preserve the historical pilot.
2. Read the five root protocol documents. Implement and validate the trusted
   transport/evaluator and controls, then freeze their hashes and Git checkpoint.
3. Build a minimal image from a recorded local Python image digest with only the
   transport runner. Verify restrictions and that oracle/corpus/auth are absent.
4. Run independent conventional and inventor design sessions with equal budgets,
   preserving every submission and development result. No hidden feedback is allowed.
5. Freeze selected source hashes. Execute three counterbalanced paired repetitions
   on the reserved corpus. Preserve complete messages, responses, errors and cgroups.
6. Apply the already-frozen H1/H2 rules; characterize source mechanisms without
   inferring novelty from names. Write the result and limitations, even for failures.

The supervisor CLI enforces a fresh run directory. Run these stages in order:

```sh
python3 -m genesis.lab prepare --run evidence/lab001/run-001
python3 -m genesis.lab develop --run evidence/lab001/run-001
python3 -m genesis.lab evaluate --run evidence/lab001/run-001
```

`prepare` builds the restricted image, records immutable source/protocol hashes,
and runs positive, negative and hostile-code controls. `develop` uses the existing
approved Codex sign-in and subscription capacity for two independent sessions.
`evaluate` accepts only the frozen selections and unchanged evaluator. It creates
a new evaluation subdirectory, preserving incomplete and earlier evaluations.
Use a new run directory for a new design attempt. Never execute submitted source
directly on the host. Inspect `progress.jsonl`, participant source/development
artifacts, and `evaluations/*/report.json` for the actual result.

## Recovery and evidence

Persist every submitted source before testing it. Persist each development result
before returning feedback. Preserve exceptions, timeouts and final selections in
append-only run directories; do not overwrite prior runs. The evaluator writes a
progress journal and final report so host interruption leaves inspectable evidence.
On resume, do not revise candidates using hidden results: rerun a complete final
evaluation with frozen hashes and a new report directory, documenting the interruption.

The host supervisor may stop/remove only its uniquely named labeled containers.
No host volume or personal directory enters execution. Normal cleanup removes owned
containers and temporary broker homes, preserving source/checkpoints/results as lab
evidence. A forced host kill may leave labeled resources: inspect ownership before
manual cleanup. Never sweep other Docker resources.

Required regression checks after material changes:

```sh
python3 -m unittest discover -s tests -v
python3 -m src.lab check
```

All integration beyond this lab requires explicit approval. The completed hidden
corpus becomes historical evidence; a later generalization study needs new holdouts.
