# Pending CHANGELOG entry — v0.0.19

> **Not released.** This file is the reviewable changelog entry for the current
> RC. If the RC is accepted, merge this entry into `docs/CHANGELOG.md` when the
> actual version bump is performed.

# v0.0.19 - PENDING REVIEW

## Added

### Token-free Slack changelog automation

- Added a repository-root GitHub workflow that summarizes every push from GitHub
  event metadata and posts it through a secret-backed Slack Incoming Webhook.
- The formatter lists commits, changed files, and affected components without an
  AI/model call, so routine team changelogs consume no model tokens.
- Added secret redaction, Slack-host URL validation, bounded messages, tests, and
  one-time setup documentation.

### Integrated local Eyes

- Added a Brain-managed passive `ScreenObserverModule` with local in-memory
  screenshot capture, visual-change gating, foreground-window privacy checks,
  actionable-event filtering, and explicit `eyes status/on/off/once` commands.
- Added Brain event delivery for Eyes alerts so visual notifications are stored
  in structured Experience rather than existing only as logger output.
- Added primary-monitor-only capture as the privacy-first default.
- Eyes on/off state now persists through restart.
- Stale Eyes configuration degrades safely when its model is missing/text-only,
  and slow in-flight requests cannot create duplicate workers on quick re-enable.

### Explicit continual self-learning

- Added `SelfLearningManager` with persistent candidates, approved guidance,
  feedback traces, review workflow, thread-safe writes, and Eyes observation
  intake.
- Added explicit `self learning preference/correction/status/review/mode/
  approve/reject` commands.
- Added `self learning guidance` so approved rules and their revocable candidate
  IDs remain visible.
- Correction traces now retain the immediately preceding ASTRA response.
- Self-learning mode changes persist through restart using the shared atomic
  config writer.

### Runtime model + GUI controls

- Added Ollama model enumeration and immediate validated runtime switching.
- Added model selection controls to the Tkinter GUI.
- Added persistent Dark/Light GUI themes.
- Added in-memory image-byte generation to the local Ollama client so Eyes does
  not need to write screenshots to disk.

## Changed

### Learning evaluator upgraded to v4

- Replaced the repetitive 13-case proficient prototype with a compact grounded
  matrix that tests source grounding, application, cross-source synthesis,
  unsupported-details behavior, private-source refusal, and review gating.
- Grounded answers now require source IDs plus an exact evidence quote verified
  against captured source material.
- Proficient synthesis requires at least two cited sources.
- Eval output now exposes individual failed cases and reasons.
- Proficient readiness now requires at least two medium/high-confidence sources
  and sufficient source material.

### Learning persistence and retrieval

- Full source material remains authoritative in the learning store and is
  chunk-retrieved at answer/eval time.
- Every learning payload has a content revision hash. New/changed sources or
  target settings invalidate stale eval/approval/promotion state.
- Existing v2/v3 and 13-case files migrate automatically and invalidate old validation.
- Duplicate source content is deduplicated without unnecessarily invalidating a
  current evaluation.
- Unicode retrieval and non-Latin-safe subject slugs replace ASCII-only
  assumptions.
- Promoted knowledge is retrieved from the current LearningManager revision;
  stale compact `learned` long-memory summaries are no longer injected into
  model context as a competing source.

### Safety / observability

- Removed implicit chat heuristics that tried to infer durable language/style
  preferences from normal messages.
- Explicit corrections remain review-gated even in auto mode.
- Sensitive Windows screen-capture checks fail closed.
- Vision capability uses `POST /api/show`; unavailable metadata falls back to a
  real image request instead of false-negative rejection.
- Normal UI visual false positives are deterministically suppressed.
- Learning, Self-Learning, and Experience warnings are included in diagnostics.
- Experience and Self-Learning file updates are thread safe and atomic.

### Low-resource defaults

- Local default model changed to `gemma3:4b` for one-model text+vision use.
- Language context defaults to 4096 tokens and Eyes semantic analysis is
  throttled.
- Added runtime dependencies: `mss`, `Pillow`, and `psutil`.

## Fixed

- Fixed the learning evaluator validating `evidence_quote` while failing to ask
  the model to return one.
- Fixed new learning sources retaining stale passing eval/review/promotion state.
- Fixed old 13-case eval reports surviving evaluator migration.
- Fixed source-ID collisions in migrated learning files.
- Fixed source citations being accepted without evidence actually present in
  the cited source.
- Fixed factual corrections being eligible for immediate global guidance.
- Fixed rejecting a self-learning candidate while leaving its active guidance
  enabled.
- Fixed Eyes treating cosmetic greyed UI as a high-confidence actionable alert.
- Fixed Eyes capability checks incorrectly claiming `gemma3:4b` had no vision.
- Fixed Eyes samples during model-busy/cooldown paths consuming the last
  successfully analyzed visual baseline.
- Fixed Eyes alerts bypassing structured Experience.
- Fixed all-monitor capture potentially including unrelated secondary displays.
- Fixed new config fields being omitted from `export`.
- Fixed GUI quick-action regression that removed existing Ollama controls.
- Fixed ASCII-only context tokenization for non-Latin notes/queries.
- Fixed fixed-name model config temp files and bounded invalid generation
  timeouts.

## Tests

- The RC contains 73 audit/regression test functions in the overlay, including
  replacements for learning/model/GUI/export tests whose expected behavior
  intentionally changed.
- Shipping compatibility/regression harness: superseded by RC3 **79/79 PASS**.
- Additional adversarial audit harness: **46/46 PASS**.
- Full upstream DEV suite must still be run on the user's local checkout before
  release; this environment cannot bulk-clone the connected repository.

### Learning evaluator v4 live validation fix

- Reworked eval decisions from ambiguous `answer/unknown/refuse/review_required` to
  `supported/unsupported/privacy_block/review_gate` after a real Gemma 3 4B run
  classified correct boundary explanations as ordinary answers.
- Replaced the vague unsupported-detail test with a synthetic per-subject probe marker
  that is verified absent from captured source text.
- Removed expected-behavior labels from the model-facing eval prompt so passing a case
  reflects the question/evidence rather than copying the expected result.
- Failed eval output now includes `model_decision` and a bounded `model_answer` preview.
- Bumped learning/eval schema to v4. Existing v3 subject files migrate in place;
  source material is retained while stale eval/review/promotion authorization is reset.


### RC3 live synthesis grounding hardening

- Fixed proficient synthesis evaluation being able to require two cited sources while
  the evidence window contained chunks from only one source.
- Added source-diverse evidence selection for multi-source eval cases.
- Added explicit multi-source and verbatim-quote instructions to grounded eval prompts.
- Added `learning sources <topic>` for source provenance and preview inspection.
- Failed eval diagnostics now include model-selected sources and the returned evidence quote.
- Renamed status `readiness issues` to `source readiness issues` to distinguish source
  preflight readiness from the actual eval gate.
- Replaced vague failed-eval guidance with source inspection / stronger-source commands.


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
