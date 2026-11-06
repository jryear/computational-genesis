# Isolation architecture — Computational Genesis Lab 001

Three independent components share only a published message/checkpoint contract.

1. **Inventor:** fresh Codex session and temporary broker home; neutral problem
   description, no architecture suggestion. Can submit arbitrary standard-library
   Python implementations and revise them using public development feedback.
2. **Conventional baseline:** separate fresh Codex session/home and submission
   namespace. Same contract, limits, model, examples, optimization opportunity and
   substrate. Asked to use established techniques, without prescribing a specific
   library, inefficient layout or fixed per-message process model.
3. **Evaluator:** trusted host supervisor and frozen deterministic reference/tests.
   Owns hidden inputs, source selection records, measurements, fault injection and
   cleanup. Neither design session has an evaluator-editing or host-reading tool.

The inventor's and baseline's generated code run in separate disposable containers
with no host bind mounts, Docker socket, external network or credentials. Only the
immutable transport runner enters the image; source is transmitted as data over
private stdio and evaluated exclusively inside the constrained container. Hidden
oracle, seeds, evaluator source and other participant submissions are not included.

The existing trusted native-sandbox Codex broker retains the approved ChatGPT sign-in
route. Authentication remains outside the repo and all generated-code containers.
Native tools/context, integrations, memories and project instructions are disabled
for design sessions. Only opaque submission IDs, source, explanations and public
test feedback cross their declared tools. Complete transcripts are local evidence.

Branch `lab001/genesis` is isolated from the historical `main` pilot. Participant
artifacts have separate directories; participants do not edit the working checkout.
The evaluator/protocol freeze precedes both design sessions. Their source hashes
are selected before hidden evaluation; final results never reenter those sessions.
All changes stay inside this lab. No remote, service, listener or external integration
is created, and no host policy/credential changes are authorized.

The supervisor's atomic persisted record is an opaque checkpoint plus an input cursor.
It can restore the acknowledged prefix on another disposable execution boundary.
This fixed transport/persistence boundary permits invention INSIDE an execution model;
it excludes arbitrary new host interfaces, hardware, network or cross-machine protocols.
That limitation is part of the result, not concealed by architecture vocabulary.
