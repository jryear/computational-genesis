# Protocol and public model policy sources

The implementation uses the installed Codex CLI 0.167.0 and its locally generated
experimental app-server JSON schemas. The schema inspection was temporary and
is not part of the agent-visible environment.

- [Official Codex app-server documentation](https://learn.chatgpt.com/docs/app-server):
  local ChatGPT sign-in, ephemeral threads, dynamic tool requests and turn events.
- [Official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference):
  isolated configuration, tool/context controls and model catalog settings.
- [OpenAI Codex public model catalog](https://github.com/openai/codex/blob/main/codex-rs/models-manager/models.json):
  source of the metadata for the single `gpt-6.1-sol` entry. The retrieved catalog
  file had Git blob SHA `489ebe3f2483348641a16160ce8491dd077eabca`.

The local model policy removes native patch and model-advertised utility tools,
selects direct tool mode, replaces model message templates with a short experiment
instruction, and disables search/skills/apps/plugin instruction flags. It does
not replace the backend model or reuse authentication outside Codex. Optional
features are independently disabled in the generated broker configuration.

The Python base-image digest, local workload image ID, versions and authored
source hashes are retained in [build metadata](../evidence/build-metadata.json).
The Dockerfile currently selects a locally available image tag; the recorded
digest documents this run rather than guaranteeing future tag resolution.
