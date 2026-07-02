# Suggestions

Ideas for what to tackle next, roughly in order of impact vs. effort.

Done items are kept at the bottom for history.

---

## 1. Module lifecycle needs error handling before a real module exists

`Modules.start_all()`/`stop_all()` (`src/modules/modules.py`) call each
module's `start()`/`stop()` with no try/except, and `Brain.start()`/`stop()`
call them mid-lifecycle, after the state has already moved to `STARTING`/
`STOPPING`. If a module's `start()` raises, the exception aborts `start()`
*before* `_set_state(RUNNING)` runs — the Brain is left stuck in `STARTING`
forever, since the `TRANSITIONS` state machine has no `STARTING -> STARTING`
retry path and no `STARTING -> STOPPING` escape either. Same problem
symmetrically in `stop()` (a failing module strands the Brain in `STOPPING`).
Harmless today only because the real `Modules()` starts empty — but this is
the exact landmine waiting for suggestion #2 below, since a `LanguageModule`
talking to Ollama is precisely the kind of subsystem that fails (model not
pulled, server not running, network hiccup). `UpdateChecker.check()` already
established the right pattern in this codebase (`ASTRA/src/utils/
update_checker.py`): wrap the risky call, log the failure via `logger`, never
let it propagate and take down the Brain. `Modules` needs the same treatment
— likely means giving `Modules` a `logger` (injected the same way
`UpdateChecker` is), so a broken module degrades to "logged and skipped"
instead of bricking the assistant.

## 2. Local LLM as a fallback brain

Per the "Offline First" principle: instead of `I heard: ...` for unknown
input, a `LanguageModule` could pass the message to a local model (e.g. via
Ollama). Rule-based commands stay instant and free; only unmatched input
goes to the model. This is the bridge from "chatbot with if-statements" to
"actual AI assistant" — the Modules system it depends on now exists
(`src/modules/module.py`), so a `LanguageModule` just needs to be written.
Note: per the permanent development rules, no external AI frameworks
(LangChain, LangGraph, etc.) before v0.1 — a direct Ollama HTTP call is fine,
a framework wrapper is not. Do suggestion #1 first, or a flaky local model
server will brick the Brain the first time it hiccups.

## 3. Notes-only recall/search

`LongMemory` entries are now tagged `"chat"` or `"note"` (v0.0.9), but
`recall`/`search` still show both mixed together — asking to `search milk`
after `remember buy milk` returns the note *and* the raw `remember buy milk`
command text *and* the bot's "Got it, I'll remember..." confirmation, three
near-duplicate hits for one real memory. Worth adding a notes-only view (e.g.
a `notes` trigger, or filtering `recall`/`search` to `type == "note"` by
default with an explicit way to see full chat history) now that the tagging
exists to make it possible.

## 4. Sync the version number from one place

`0.0.9` currently has to be hand-edited in three files kept in sync
manually: `pyproject.toml`, `config.json`, and `Config.DEFAULTS` in
`src/config/config.py`. Worth having `Config` (or `main.py`) read the
version from `pyproject.toml` (or `importlib.metadata.version("astra")`
once installed) instead of duplicating the literal string three times —
low urgency, but it's exactly the kind of thing that quietly drifts.

## 5. CI only tests one Python version

`pyproject.toml` declares `requires-python = ">=3.10"`, but
`.github/workflows/tests.yml` only runs on `3.14`. A 3.10/3.11/3.12/3.13-only
breakage would pass CI and ship undetected — worth a small version matrix
(`3.10`, `3.14`) if the >=3.10 claim is meant to be real, or narrowing
`requires-python` if 3.14+ is the actual intent.

---

## Done

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
