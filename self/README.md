# self

One memory, one voice, one set of intents, above any engine.

- **The self is a journal** (`~/.self/journal.jsonl`) that you own. Engines are stateless and
  interchangeable: each turn, whichever engine is up gets the voice (`voice.md`), your memory,
  intents, open decisions, your past decisions, and the recent conversation.
- **Engines:** Claude (`claude -p`) and Codex (`codex exec`). `auto` alternates on purpose, so
  continuity across engines is the default, not a trick.
- **Capabilities run in the runtime, never in the model.** Every run is recorded as **Proof**:
  command, exit code, time and output hash. "Done" is never a model's claim.
- **Surface** (`surface.html`) has four sections:
  - **Needs you:** judgment calls, answered with one tap.
  - **Intents.**
  - **Conversation.**
  - **Proof.**

Your answers become "how the user decided before", which every engine sees on every turn.

```
python3 self/selfd.py --port 8787            # journal defaults to ~/.self
```

## Verified in the test session (`evidence/test-session-journal.jsonl`, test data, not the user's)

1. **A fact told to Claude was recalled by Codex** in the same voice.
2. **"Is the lab healthy? Don't guess."** Codex ran `lab_status` and `lab_tests` (7 tests green
   on a clean worktree). It reported that green tests don't prove the research claims.
3. **Claude read three lab documents** (each recorded as Proof), summarized Lab 002 accurately,
   said it had only read excerpts, and raised one real decision.
4. **That decision was answered** ("leave Lab 002 as is"). Codex then argued against a week on the
   verifier, citing that answer.
5. **Claude volunteered that it had no calendar access** instead of pretending.

## Not built yet

- More engines (Grok, a local model).
- Bodies beyond the web surface (Telegram, voice).
- Real-world capabilities beyond the lab repo.
- Exactly-once effect receipts for irreversible actions.
