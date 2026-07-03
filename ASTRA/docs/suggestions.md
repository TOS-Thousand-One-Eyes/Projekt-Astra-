# Suggestions

Ideas for what to tackle next, roughly in order of impact vs. effort.

`docs/ROADMAP.md` has the longer-term version-gated milestone sequence
(v0.1.1 onward) — items here are that roadmap's nearest milestones scoped
down to a concrete, small, single-commit-sized first step, the same way
every item in this file has been scoped so far. Reconciled against the
roadmap on 2026-07-03.

Done items are kept at the bottom for history.

---

## 0. Findings from the 2026-07-03 six-agent full-codebase bug audit, not fixed yet

Six parallel agents audited `core/config`, `utils`, `memory`, `commands`,
`modules`, and `main`/integration end to end (not diff-only) after this
session's failure-flagging work landed. Three confirmed bugs were fixed
immediately (see Done below: dispatch crashing on a non-string message,
`Logger.log()` crashing on a bad `level` or an unprintable character, and
`forget` deleting entries of the wrong type). The rest are real but
deliberately deferred — small individually, but bundling six unrelated
fixes into one commit would violate the single-capability-commit rule, so
each needs its own pass next time this area is touched:

- **`Facts`/`LongMemory`'s atomic-write tmp path isn't unique across
  concurrent instances** (`memory/facts.py`, `memory/long_memory.py`
  `save()`): both use a fixed `path.tmp` name with no PID/UUID component.
  Two ASTRA processes writing at overlapping times could interleave writes
  to the same tmp file before either `os.replace()` runs, corrupting or
  losing data. Low likelihood for a single-user CLI, but a real gap if
  ASTRA ever runs as more than one process.

A same-day recheck round (6 fresh agents verifying the fixes above) found
one more concrete bug in the same area, since fixed: `MemoryManager.forget()`
called `self.short_memory.forget(entry)` unconditionally, even when
`long_memory.forget()` removed nothing — so `forget test` after only a chat
message "test" (no note) would tell the user "I couldn't find anything
matching: test" while silently deleting that chat turn from short-term
`recall`/`history`, contradicting the bot's own response. Now only calls
`short_memory.forget()` when a note was actually removed. Covered by
`tests/test_memory.py::test_memory_manager_forget_with_no_matching_note_leaves_short_memory_untouched`
and `tests/test_brain.py::TestNotes::test_forget_with_no_matching_note_does_not_touch_short_term_recall`.

Still not filed as a bug, since it's a bigger restructuring than a
same-day fix warrants: `ShortMemory` itself has no type concept at all
(it's an in-memory rolling buffer of raw strings, no persisted type
field), so it still can't distinguish "note" from "chat" the way
`LongMemory` now can — the fix above only stopped `forget` from touching
`short_memory` on a no-op, it didn't make `short_memory` type-aware.

## 1. A `diagnostics`/`status` command to see warnings after startup scrolls by (preview of roadmap v0.1.8 "Observability")

Config/memory load warnings (see `docs/CHANGELOG.md`'s latest entry) are
only visible in the startup log stream — if the console scrolls, or
`log_to_file` is off, there's no way to ask "did anything go wrong?"
later in a long-running session. `Config.load_warnings`,
`MemoryManager.load_warnings()`, and whether `Logger` had to disable
`log_to_file` after a write failure are all already tracked in memory
right now — a `diagnostics`/`status` chat trigger just needs to read
and report them on demand, the same way `memory stats` already reports
`LongMemory`'s shape. No new tracking, just a new way to ask for what's
already being tracked. Small, reuses what exists, and is the obvious
first step toward roadmap v0.1.8's "internal health report."

## 2. `MemoryCommand`'s non-string `response length` fact silently falls back, unlike everything else fixed this session

`_entry_limit()` guards against a non-string `response length` fact
value (a hand-edited `facts.json`) with `isinstance(preference, str)`,
falling back to the default limit — safely, but silently, the exact
pattern just fixed everywhere else this session (see MANIFEST.md's
"OBSERVABLE FALLBACKS"). Deliberately not fixed today: `Command`
subclasses don't currently take a `logger` (only `MemoryCommand`/
`GreetingCommand`'s `config`/`memory`), so warning here would mean
giving every command a logger dependency — a real DI change, not a
one-line fix, and out of scope for a single edge case reachable only
by manually corrupting `facts.json`. Worth deciding deliberately (give
`Command` a logger now, generalizing the pattern) rather than
one-off-ing a workaround, next time this file is touched.

## 3. TFT coaching via screen access (correctly placed: far out, two dependencies)

Erik's real near-term want, raised this session: Astra watching the screen
during a TFT match and coaching live. Honest scope check before this goes
anywhere: it needs **both** the local LLM fallback (now shipped, see Done
below) **and** Vision (roadmap v0.2.2 — "OCR, screenshots, basic 'what's on
screen'"), which doesn't exist yet. It's also not really an LLM-reasoning problem underneath
— TFT patches every ~2 weeks and rotates trait/item sets every ~4 months,
so a generic local model's training data goes stale fast regardless of
which one is running; real coaching value needs live/curated current-meta
data as grounding context fed into the model, not just a bigger model.
Correctly sequenced this stays a v0.2.2+ idea, not something to reach for
early — flagging it here so it's on record and roadmap-placed rather than
forgotten, not because it's next.

---

## Done

- ~~**`update_checker` version comparison breaking on differing segment
  counts**~~ — Done (this session, deferred item 0 from the 2026-07-03
  audit): Python tuple comparison makes `(1, 2) < (1, 2, 0)`, so `"1.2"`
  vs `"1.2.0"` spuriously compared as an available update. `check()` now
  zero-pads the shorter parsed tuple to the longer one's length
  (`_pad_to_same_length()`) before comparing. Covered by new cases in
  `tests/test_update_checker.py`.
- ~~**Ollama `<think>` stripping eating literal text that isn't reasoning
  markup**~~ — Done (this session, deferred item 0 from the 2026-07-03
  audit): the audit said "no clean fix without structure", but there *is*
  structure to use — reasoning models emit their `<think>` block at the
  *start* of the response, never after real content. All three stripping
  patterns in `utils/ollama_client.py` are now anchored to the leading
  position (`\A`), so a literal `<think>`/`</think>` later in a real
  answer (e.g. an answer *about* prompt formats) is kept as content
  instead of truncating everything after/before it. The
  template-swallowed-opener case (bare reasoning ending in a lone
  `</think>`) is still stripped, but only when no `<think>` opener
  appeared anywhere in the raw response — if it did, a remaining
  `</think>` is literal content. One old test asserting the buggy
  truncation (`preamble<think>cut off` → `preamble`) was updated: a
  mid-text `<think>` is now a literal mention, not markup. Known residual
  (inherent, documented in the code comment): an answer that *opens* with
  prose ending in a literal `</think>` and never mentions `<think>` is
  indistinguishable from the swallowed-opener case and still loses its
  prefix. Covered by new cases in `tests/test_ollama_client.py`.
- ~~**`Config` not validating types from `config.json`**~~ — Done (this
  session, deferred item 0 from the 2026-07-03 audit): a hand-edited
  `"use_language_fallback": "false"` (string, not JSON `false`) was
  truthy in Python, silently flipping the flag on against the user's
  intent. `Config` now type-checks every loaded key against its
  `DEFAULTS` entry (`_validated()`/`_same_type()`): booleans must be
  real booleans, numbers must be numeric (a JSON `true` doesn't count as
  a number even though Python's `bool` is an `int` subclass), strings
  must be strings — anything else keeps the default and records a
  `load_warnings` entry that `Brain.start()` surfaces at `WARNING`, per
  MANIFEST.md's observable-fallbacks rule. Unknown keys (like `version`,
  which isn't in `DEFAULTS`) pass through untouched. Covered by new
  cases in `tests/test_config.py`.
- ~~**`Modules.start_all()`/`stop_all()`'s error handler crashing on a
  module without `.name`**~~ — Done (this session, deferred item 0 from
  the 2026-07-03 audit): the `except` blocks' f-string did `module.name`
  directly — a malformed (non-`Module`-derived) object that both lacks
  `.name` and raises would crash the handler itself with an
  `AttributeError`. Both handlers now use a `_module_name()` helper
  (`getattr(module, "name", type(module).__name__)`). Covered by new
  nameless-module cases in `tests/test_modules.py`.
- ~~**`Brain` stuck-state on a mid-transition crash**~~ — Done (this
  session, deferred item 0 from the 2026-07-03 audit): `start()`/`stop()`
  now wrap their bodies in try/except — on any failure between
  `STARTING`→`RUNNING` or `STOPPING`→`OFFLINE`, the error is logged at
  `ERROR` (observable, per MANIFEST.md), the state escapes back to
  `OFFLINE` (new `STARTING → OFFLINE` transition in `TRANSITIONS`), and
  the original exception re-raises — so a retried `start()` reports the
  real problem (e.g. a corrupt timestamp) instead of a confusing
  `Invalid state transition`. Covered by
  `tests/test_brain.py::TestLifecycleRecovery`.
- ~~**Automatic failure flagging instead of crashing or silently
  continuing**~~ — Done (this session): `CommandRegistry.dispatch()` now
  wraps message normalization and every `command.handle()` call in
  try/except, logs the failure via `logger.error()` (command name,
  message, exception type/text) instead of crashing the whole REPL, and
  returns a graceful "I've logged it" response; `Brain` now wires its own
  logger into `build_default_registry(...)` so this is on by default, not
  opt-in. Found and fixed by a 6-agent audit in the same pass (see item 0
  above for what else the audit found but deferred): `normalize(message)`
  was running *before* the try block and could still crash `dispatch()` on
  a non-`str` message; `Logger.log()` could itself crash on an invalid
  `level` string or an unprintable character reaching `print()`, which
  would have defeated the whole point of the new error logging. Both
  fixed. Covered by `tests/test_brain.py::TestFailureFlagging` and new
  cases in `tests/test_logger.py`.
- ~~**`forget` deleting entries of the wrong type**~~ — Done (this
  session, found by the same audit): `LongMemory.forget()` matched by text
  only, ignoring `type`, so `forget test` after both `test` (a chat
  message) and `remember test` (a note) existed would silently delete
  both, not just the note — the exact asymmetry the earlier "Notes-only
  recall/search" fix (below) was supposed to establish everywhere.
  `LongMemory.forget()` now takes an optional `entry_type` filter, and
  `MemoryManager.forget()` passes `entry_type="note"` to match `forget`'s
  actual UX (removing notes, same as `recall`/`search`). Covered by new
  cases in `tests/test_memory.py` and `tests/test_brain.py::TestNotes`.
- ~~**Local LLM as a fallback brain**~~ — Done in v0.0.15 (merged in from
  a parallel `copilot/analyze-project-changes` branch, PR #6, rather than
  built fresh this session): added `OllamaClient`, `LanguageModule`,
  config gating (`use_language_fallback`, `language_base_url`,
  `language_model`), and `CommandRegistry` fallback wiring for unmatched
  messages; covered by `tests/test_ollama_client.py`,
  `tests/test_modules.py`, and `tests/test_brain.py`.
- ~~**Deduplicate the `StubModule` test double**~~ — Done in v0.0.15
  (same merged branch): moved the shared `StubModule` into
  `tests/conftest.py`, removing the duplicate definitions from
  `tests/test_modules.py` and `tests/test_brain.py`.
- ~~**A preference fact that actually changes behavior**~~ — Done in
  v0.0.12: teaching `my response length is short` now shortens
  `MemoryCommand`'s `recall`/`history` triggers from the last-5 default
  to the last 2 (`_entry_limit()`); proves the `GreetingCommand`-style
  "facts change behavior" pattern generalizes; covered by
  `tests/test_brain.py::TestPreferences`. (The merged-in v0.0.15 branch
  had independently built the same behavior with a last-3 cutoff under
  different constant names — dropped in favor of this already-shipped
  version rather than keeping two competing implementations.)
- ~~**Memory visibility**~~ — Done in v0.0.11: `memory stats` chat
  trigger reports total/note/chat entry counts and oldest/newest
  timestamps, reusing `LongMemory.recall()`; covered by
  `tests/test_brain.py::TestMemoryStats`.
- ~~**Memory export**~~ — Done in v0.0.11: `export` chat trigger bundles
  `Config` settings, all facts, and the full long-term memory into a
  timestamped JSON file under `data/exports/`; covered by
  `tests/test_export_command.py`.
- ~~**A permission convention**~~ — Done in v0.0.11: "PERMISSION
  CONVENTION" section added to `docs/MANIFEST.md`, docs-only.
- ~~**Module lifecycle needs error handling**~~ — Done in v0.0.10:
  `Modules` now takes a required `logger` (injected the same way
  `UpdateChecker` is) and `start_all()`/`stop_all()` catch a failing
  module's exception, log it by name via `logger.error()`, and keep
  going instead of stranding `Brain.start()`/`stop()` mid-transition;
  covered by `tests/test_modules.py` and
  `tests/test_brain.py::TestModulesLifecycle`.
- ~~**Notes-only recall/search**~~ — Done in v0.0.10: `recall`,
  `what do you remember`, and `search <text>` now filter to
  `type == "note"` entries only, so `search milk` no longer surfaces the
  raw `remember buy milk` command echo or the bot's own confirmation as
  false hits; a new `history` trigger shows the last 5 entries
  unfiltered (notes and chat both) for anyone who wants the old mixed
  view; covered by `tests/test_brain.py::TestNotes`.
- ~~**Sync the version number from one place**~~ — Done in v0.0.10:
  `Config.DEFAULTS` no longer carries a hardcoded version literal —
  `config.json` is the sole runtime source of truth, falling back to an
  honest `"0.0.0-unknown"` sentinel (instead of a silently-stale
  duplicate) if the file is missing the key; `pyproject.toml`'s version
  stays the hand-maintained packaging/release-tag source (neither
  `importlib.metadata` nor stdlib TOML parsing are safe zero-dependency
  options here — confirmed `importlib.metadata.version("astra")`
  returns a stale value on an editable install lagging behind
  `pyproject.toml`, and `tomllib` needs 3.11+ while this project
  supports 3.10+); the remaining two-literal sync is now a reminder in
  the release checklist in `docs/MANIFEST.md`; covered by
  `tests/test_config.py`.
- ~~**CI only tests one Python version**~~ — Done in v0.0.10:
  `.github/workflows/tests.yml` now runs the suite across
  `python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]` with
  `fail-fast: false`, actually exercising the `requires-python = ">=3.10"`
  claim in `pyproject.toml` instead of testing 3.14 alone.
- ~~**Startup briefing steps**~~ — Done in v0.0.9: `Brain.start()` logs
  the current date/time and how long ago the previous session's last
  memory entry was (or "This is our first session!"); covered by
  `tests/test_brain.py::TestStartupBriefing`.
- ~~**Session summary on shutdown**~~ — Done in v0.0.9: `Brain.stop()`
  logs messages exchanged, new facts learned, and session duration, via
  a new `utils/time_format.format_duration()` helper; covered by
  `tests/test_time_format.py` and `tests/test_brain.py::TestSessionSummary`.
- ~~**Real Modules system**~~ — Done in v0.0.9: base `Module` class
  (`name`, `start()`, `stop()`), `Modules.start_all()`/`stop_all()`, and
  `Brain.start()`/`stop()` now actually drive module lifecycle instead of
  holding an inert placeholder list; covered by `tests/test_modules.py`
  and `tests/test_brain.py::TestModulesLifecycle`.
- ~~**Use facts to personalize Astra**~~ — Done in v0.0.9: `GreetingCommand`
  and `Brain.start()`'s greeting now use the known `name` fact for
  `hi`/`hello`/`hey` (e.g. "Hello, Erik!"); scoped to greeting only.
- ~~**Continuous Integration (GitHub Actions)**~~ — Done in v0.0.9:
  `.github/workflows/tests.yml` runs `python -m pytest` on every push and
  pull request.
- ~~**Memory: forget/search, not just append**~~ — Done in v0.0.9:
  `LongMemory.search()`/`forget()`, `remember <note>` now tagged `"note"`
  separately from ordinary chat (`"chat"`), and `search`/`forget` chat
  commands; covered by `tests/test_memory.py` and `tests/test_brain.py`.
- ~~**Packaging / entry point**~~ — Done in v0.0.8: added `pyproject.toml`
  (setuptools) with an `astra` console-script entry point (`main:main`)
  and `pytest` as a `[dev]` extra; `pip install -e ".[dev]"` sets up a
  fresh machine in one command; `src/` subpackages gained `__init__.py`
  for clean packaging; verified `astra` runs correctly from an unrelated
  working directory.
- ~~**Logger: file output + levels**~~ — Done in v0.0.8: `Logger` now
  filters by level (`DEBUG < INFO < WARNING < ERROR`), gained
  `debug()/info()/warning()/error()` convenience methods, and supports
  optional file output to `data/astra.log`, controlled by the new
  `log_level`/`log_to_file` keys in `config.json`; covered by
  `tests/test_logger.py`.
- ~~**Input handling hardening**~~ — Done in v0.0.7: Ctrl+C is caught and
  routed through `brain.stop()` for a clean lifecycle shutdown instead of a
  raw traceback; blank/whitespace-only input is skipped before it reaches
  `brain.receive()`; covered by `tests/test_main.py`.
- ~~**Command registry instead of if/elif chains**~~ — Done in v0.0.7:
  `src/commands/` now holds one class per command (`GreetingCommand`,
  `FactCommand`, `MemoryCommand`, `HelpCommand`, `ExitCommand`) behind a
  `CommandRegistry`; `Brain` only dispatches and no longer knows individual
  commands or trigger words.
- ~~**Permanent development rules**~~ — Done in v0.0.7: recorded in
  `docs/MANIFEST.md` (pure Python, no AI frameworks before v0.1, small
  single-capability commits, never break tests).
- ~~**Tests**~~ — Done in v0.0.6: 29 pytest tests covering Brain, memory,
  and config, with injectable paths so tests never touch real data.
- ~~**Config from file, not hardcoded**~~ — Done in v0.0.6: `Config` loads
  `config.json` with defaults fallback.
- ~~**Brain Lifecycle (roadmap v0.0.6)**~~ — Done in v0.0.6: validated
  `OFFLINE → STARTING → RUNNING → STOPPING → OFFLINE` transitions, `is_running`,
  farewell-driven shutdown.
- ~~**Packaging cleanup (stale `.pyc`)**~~ — Superseded by #2; the namespace
  packages work, the remaining task is a real `pyproject.toml`.
