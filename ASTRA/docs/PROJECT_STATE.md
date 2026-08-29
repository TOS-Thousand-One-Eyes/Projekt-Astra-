# ASTRA project state

Version: 0.0.22

Branch under review: `DEV-need-check`

Remote base commit: `8ad04cd`

Status: `DEV-need-check` review candidate; not released

## Product direction

ASTRA is a local-first, desktop-first personal assistant. The current build keeps
runtime memory and screenshots local, uses Ollama for optional language/vision
generation, avoids external AI frameworks, and keeps risky actions behind explicit
commands or approval gates.

## Current runtime

- `main.py` and `gui/app.py` build the same Brain-managed runtime.
- CLI and lightweight Tkinter GUI are available.
- Persistent stores cover long memory, facts, structured experience, learning,
  self-learning candidates/guidance, reflections, reminders, and actions.
- Ollama language fallback is optional and model calls are serialized so a shared
  text/vision model is never called concurrently by chat and Eyes.
- Runtime/package/config version values are synchronized at `0.0.22`.
- Local profiles `Erik` and `Petr` authenticate with separately salted PIN
  hashes and use isolated persistent runtime directories.

## Learning layers

### Source-backed learning

`LearningManager` owns subject sources, chunk retrieval, distillation, evaluator
state, approval, and promotion. The v4 evaluator uses a compact 6/7-case grounded
matrix instead of the retired repetitive 13-case prototype. Content revision hashes
invalidate stale eval/approval/promotion state whenever evidence changes.

Proficient promotion requires meaningful source coverage, a passing grounded eval,
and explicit approval. Exact evidence quotes and source IDs are verified before an
answer can pass. Old compact `learned` long-memory entries are not injected into
normal prompts; current promoted LearningManager content is authoritative.

### Continual self-learning

`SelfLearningManager` supports modes `off`, `review`, and `auto`.

- Explicit preferences can become active guidance in `auto` mode.
- Corrections remain review-gated even in `auto` mode.
- A correction trace stores both the user feedback and the immediately preceding
  ASTRA response.
- Repeated Eyes observations become candidates but never global guidance without
  approval.
- Active guidance is inspectable with `self learning guidance` and can be revoked
  by rejecting its candidate ID.
- Mode changes persist atomically to `config.json`.
- `self learning scan` uses the active local model to propose review-gated
  preferences, corrections, and personal memory notes from recent conversation.
- `self learning health` audits candidate, guidance, and correction-trace
  integrity without modifying data. Inconsistent active guidance is blocked
  before model-prompt injection.

This is continual memory/RAG learning, not autonomous neural-weight training.
Training JSONL is preparation for a later reviewed fine-tune/LoRA workflow.

## Vision / Eyes

- Explicit local files: `image inspect` and model-backed `image describe`.
- Passive/local screen observation: `eyes status/on/off/once`.
- Screenshots are JPEG-compressed in memory and are not persisted by Eyes.
- Capture defaults to the primary monitor, skips sensitive foreground windows,
  and fails closed when Windows lock-state detection fails.
- Semantic analysis is throttled by visual change, minimum analysis interval,
  model busy state, notification confidence, and notification cooldown.
- Deterministic actionability filters suppress ordinary/cosmetic UI false positives.
- Eyes events are routed through Brain into structured Experience.
- `eyes on/off` persists to config. A stale enabled setting with a missing or
  text-only model degrades to Eyes-off without preventing ASTRA startup.
- A slow in-flight model request cannot create a duplicate worker during a quick
  off/on cycle.

Recommended single low-footprint text+vision model: `gemma3:4b`. Actual quality is
probabilistic; run `vision check`, `image describe`, and `eyes once` on the target
Windows machine before enabling continuous Eyes.

## Configuration writes

`Config.persist()` is the shared atomic settings writer. It validates known keys,
uses a process/thread/UUID-unique temporary file, serializes writes across Config
instances, preserves unrelated settings, and refuses to overwrite malformed JSON.
Model, GUI theme, self-learning mode, and Eyes state use this path.

Long memory and facts now use locked read/modify/write operations plus
process/thread/UUID-unique temporary paths. Concurrent GUI/background writes no
longer collide on the same temporary file.

## Profile backups

- `backup create [label]` creates a ZIP from the active profile's persistent
  memory, learning, experience, action, and reminder data.
- Each archive has a versioned manifest, per-file size/SHA-256 records, a 128 MiB
  safety limit, and immediate post-create verification.
- `backup list` and `backup verify <file|latest>` are read-only.
- Backups and legacy JSON exports live inside the active profile directory, so
  Erik and Petr do not share personal export artifacts.
- Restore remains manual to prevent accidental live-memory replacement from chat.

## Identity and privacy

- Profile selection is explicit; ASTRA never guesses identity from IP, webcam,
  network, or device metadata.
- PINs are PBKDF2-SHA256 hashed with independent random salts and never enter chat.
- Corrupt PIN metadata fails closed, including an excessive work factor that
  could otherwise stall authentication.
- Personal stores live under the stable OS user-data root (`%LOCALAPPDATA%\Astra`
  on Windows), outside replaceable source/ZIP directories.
- Checkout-local identity, profile, and pre-profile data is copied forward once
  without deleting the recoverable originals.
- Erik and Petr track update briefings independently; a version is recorded only
  after its message is displayed.
- The GUI hides chat and stops Brain/Eyes when locked or switching users.
- Automatic lock defaults to 15 minutes and waits for an active model/command worker
  to finish before stopping the runtime.
- The PIN prevents accidental profile mixing; local files are not encrypted from an
  operating-system administrator.

## Repository automation

- Repository-root `.github/workflows/tests.yml` runs the full suite on Python
  3.10–3.14 for pushes and pull requests.
- Repository-root `.github/workflows/slack-changelog.yml` posts a deterministic
  `ASTRA v<version>` summary after every push when the `SLACK_WEBHOOK_URL`
  Actions secret is configured.
- Concrete features/fixes come from `docs/CHANGELOG_PENDING_<version>.md`; commit,
  Git-diff file metadata, and the comparison link remain attached.
- Slack changelog generation uses only repository/GitHub event data and Python
  stdlib; it consumes no AI tokens and redacts common secret-like strings.
- Setup: `docs/SLACK_CHANGELOG_SETUP.md`.

## Verification state

- Full local suite: **529 passed** with warnings treated as errors; repeated with
  a fixed hash seed for the same **529 passed** result.
- Python compilation: PASS.
- `git diff --check`: PASS.
- GitHub confirmed the v0.0.21 review push and token-free Slack changelog.
- No v0.0.22 GitHub push or release performed.

## Manual Windows review gates

1. Install/update the environment with `python -m pip install -e ".[dev]"`.
2. Run `python -m pytest -q` and confirm the same green suite.
3. Start Ollama with the intended model and run `model check` and `vision check`.
4. Run `image describe <path> -- <question>` against a known local image.
5. Run `eyes once`; inspect whether the result is accurate and private.
6. Optionally run `eyes on`, exercise real workflows, then confirm `eyes off` stops
   passive observation cleanly.
7. Set separate PINs for Erik and Petr; verify `who am i`, Lock/switch, chat hiding,
   and that each profile has separate facts/preferences.
8. Test `self learning preference`, `correction`, `scan`, `review`, `guidance`,
   `health`, approval, rejection, and restart persistence.
9. Run `backup create before-review`, `backup list`, and `backup verify latest`;
   keep the generated personal ZIP private.
10. Configure the Slack webhook secret, push a small review commit, and verify
   the chosen channel receives one versioned changelog with concrete bullets.
11. Review the diff before any commit, push, or merge.

## Main source areas

- `src/core`: Brain lifecycle and event integration.
- `src/commands`: command routing and user-facing workflows.
- `src/memory`: short/long memory, facts, and prompt context.
- `src/learning`: source-backed and continual self-learning managers.
- `src/vision`: image inspection, local vision description, passive Eyes.
- `src/utils`: Ollama client, logging, update checks, and time helpers.
- `src/gui`: lightweight Tkinter runtime and presenter.
- `src/identity`: local profile authentication, private data roots, and safe legacy migration.
- `tests`: deterministic unit/integration regressions; no real Slack/Ollama calls.

## Design rules still in force

- Offline first and user-owned data.
- Pure Python unless explicitly approved.
- No LangChain/LangGraph before the planned architecture needs them.
- Preserve backward compatibility where it does not conflict with corrected safety
  or grounding behavior.
- Every behavior change gets a regression test.
- One commit should represent one reviewable capability.
