# ASTRA v0.0.19 RC — Patch Notes

> Review candidate only. This version has **not** been pushed or released.
> Runtime version remains `0.0.18` until the review candidate is accepted.

## Headline

This RC turns the earlier learning/Eyes prototype into a safer, more coherent
local-first implementation. The focus is not adding more surface area; it is
making the existing new features trustworthy enough to test against real use.

## Learning v3

- Learning files migrate to `astra-learning-subject/v3` and evaluator version 3.
- Existing v2/13-case eval state is invalidated on migration. An old pass can
  never silently authorize a new evaluator.
- Adding or changing source material invalidates the previous eval, approval,
  promotion-ready flag, promoted revision, and compact promotion note.
- Duplicate source content is detected by SHA-256 and does **not** invalidate a
  still-current eval.
- Whole source text remains in the learning store and is retrieved in chunks;
  promotion no longer collapses the usable knowledge to a tiny prefix.
- Non-Latin subjects get stable hash-backed slugs instead of colliding on one
  generic filename; Unicode token retrieval works for non-Latin text too.
- Proficient learning requires at least two meaningful medium/high-confidence
  sources and enough source material to evaluate.

## Grounded eval redesign

The previous 13-case matrix repeated similar prompts and over-tested output
formatting. The new matrix is smaller and more evidence-oriented:

- source-grounding cases;
- practical application;
- cross-source synthesis for proficient subjects;
- unsupported-detail / unknown behavior;
- private/secret-source boundary;
- mandatory review boundary.

For factual answers the model must return structured JSON containing:

- `answer`;
- cited source IDs;
- an **exact `evidence_quote` copied from the captured source**;
- a decision: `answer`, `unknown`, `refuse`, or `review_required`.

ASTRA verifies that the quote actually exists in a cited source and that the
answer is linked to the evidence. Proficient synthesis must cite at least two
captured sources. Failed eval output now lists every failed case and its reason.

## Self-learning

- Removed implicit language/correction heuristics from ordinary chat.
- Persistent chat learning is explicit through:
  - `self learning preference <text>`
  - `self learning correction <text>`
- Preferences may auto-activate in `auto` mode.
- Corrections remain review-gated even in `auto` mode because a correction can
  contain a factual claim and must not poison global guidance from one message.
- Corrections still create local feedback traces for a possible future
  fine-tuning/LoRA dataset.
- Rejecting a candidate deactivates guidance that came from that candidate.
- Eyes observations never auto-promote into global guidance.

This is continual memory/RAG learning, **not neural-weight training**.

## Eyes

- Passive screen observation is integrated as a Brain-managed module.
- Screenshots remain in RAM and are sent only to the configured local Ollama
  model in the default offline setup.
- Ollama vision capability is checked via the authoritative `/api/show`
  metadata instead of `/api/tags`.
- Normal/cosmetic UI states such as greyed controls are deterministically
  filtered even if the vision model claims high confidence.
- Alerts are restricted to actionable categories such as errors, warnings,
  blocked workflows, security/privacy issues, deadlines, and important
  notifications.
- Repeated workflows can be queued for learning without interrupting the user.
- Sensitive foreground windows are skipped; Windows lock-state detection fails
  closed.
- Default screen capture is now **primary monitor only**. `mss` monitor 0 is the
  bounding box of all monitors and could leak unrelated secondary-monitor
  content into a screenshot.
- A successful Eyes alert is routed through Brain and recorded in structured
  Experience instead of bypassing the application via logger-only output.

## Experience / concurrency

- Experience writes are protected by an `RLock` and unique atomic temp files.
- Self-learning state uses thread-safe read/modify/write operations.
- Ollama calls are serialized when language and Eyes share one local model.
- This prevents background Eyes activity from corrupting local JSON state or
  overlapping requests through the same client.

## Model runtime

- Recommended local default: `gemma3:4b`.
- Default language context: 4096 tokens to reduce RAM pressure on modest PCs.
- One vision-capable Ollama client can be shared by normal chat and Eyes.
- Model switching is available at runtime and in the GUI.
- A failed switch rolls back to the previous model.
- Switching a shared Eyes client to a model that explicitly lacks vision
  disables Eyes rather than producing a background failure loop.
- Generation timeouts are range-validated.
- Ollama malformed/non-object generation payloads fail clearly.

## GUI

- Light/Dark theme toggle; default is Dark and the selection persists in
  `config.json`.
- Model selector with refresh/use controls.
- Existing quick actions were preserved while adding Eyes and Self-Learning
  status shortcuts.
- The GUI remains Tkinter-based with no browser engine.

## Configuration / export / diagnostics

- New model, theme, self-learning and Eyes settings are validated by `Config`.
- `export` now includes all new runtime configuration instead of silently
  omitting them.
- Export/model/theme persistence use unique atomic temp files.
- `diagnostics` / `status` now resurfaces warnings from Learning,
  Self-Learning, and Experience as well as Config and Memory.

## Context hygiene

- No hardcoded Czech/English language policy is injected into normal chat.
- No localized learning-command aliases are hardcoded into the command layer.
- Long-memory `learned` promotion summaries are no longer injected as a second
  authority. Current source-backed knowledge comes from LearningManager;
  ordinary memory context uses facts and explicit notes. This prevents an old
  promoted summary from surviving a newer invalidated learning revision.

## Learning evaluator v4 — live-model fix

A real `gemma3:4b` proficient eval exposed two evaluator-design problems after the
full audit: `ASTRA-LEARN-UNKNOWN-001` did not ask for a concrete unsupported fact,
and the decision enum used `answer`, which a small model reasonably interpreted as
"I produced an answer" even when its text correctly said that review was required.

The RC now uses evaluator/schema v4:

- decision classes are `supported`, `unsupported`, `privacy_block`, and `review_gate`;
- the decision classifies the **request/evidence state**, not whether text was returned;
- the unsupported-evidence case uses a deterministic synthetic marker guaranteed not
  to occur in captured sources;
- eval prompts no longer reveal the case's expected behavior label;
- failed cases now print the model's decision and short answer for useful live diagnosis;
- v3 learning files migrate automatically to v4, preserve captured sources, and
  invalidate only the stale eval/review state.


## RC3 — live synthesis grounding hardening

The second real `gemma3:4b` proficient run reached **6/7 (85.71%)**. Both
boundary cases passed; only `ASTRA-LEARN-SYNTHESIS-001` failed with
`needs_at_least_2_sources` and `unsupported_evidence_quote`.

The gate is intentionally **not** weakened to turn that into a pass. Instead:

- synthesis eval context now guarantees distinct-source coverage before filling the
  remaining chunk budget, so a case requiring two sources actually receives evidence
  from at least two captured sources when they exist;
- the model-facing prompt now explicitly states the per-case minimum number of distinct
  Source IDs and tells synthesis cases to combine concrete information rather than emit
  generic commentary about ASTRA or the learning process;
- `evidence_quote` is explicitly required to be a verbatim contiguous 8–120 character
  excerpt from a cited evidence chunk;
- failed cases now print `model_sources` and `evidence_quote` as well as decision/answer;
- added `learning sources <topic>` to inspect source provenance and bounded previews;
- status wording now says `source readiness issues` so a passed source pre-check is not
  confused with a failed eval gate;
- failed eval guidance now points to source inspection and explicit stronger acquisition
  (`research learn` / `teach`) instead of the vague "improve sources or model output".

A synthesis still **must fail** when the captured material itself is weak/off-topic or
when the model invents an evidence quote. RC3 fixes evaluator fairness and diagnostics;
it does not manufacture a 7/7 score.


## Live-learning acquisition hardening (need-check branch)

A real `learn deeply about python` run exposed that automatic memory acquisition
accepted long help/history entries that only mentioned the subject incidentally,
and near-identical help responses could masquerade as independent sources.

Fixed before the need-check branch snapshot:

- automatic memory sources now require topical relevance, not just one token hit;
- a single subject mention inside a long generic entry is rejected;
- near-identical memory candidates are deduplicated before capture;
- rerunning `learn about` / `learn deeply about` refreshes automatically captured
  `memory:` sources instead of keeping stale junk forever;
- explicit `user:teach` and `web:` evidence is preserved during that refresh;
- deep learning still does not silently use the network: when local evidence is
  insufficient, ASTRA stays in acquisition mode and points to `research learn` or
  `teach` rather than pretending to be proficient.
