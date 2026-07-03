# CHANGELOG

All notable changes to this project will be documented here.

The format is inspired by "Keep a Changelog".

---

# v0.0.12 - 03.07.2026

## Added

### A preference fact that actually changes behavior

**Why:** `docs/suggestions.md`'s top open item was to prove the existing
facts system changes more than greeting copy before a bigger v0.1.1
preferences subsystem exists.

- `MemoryCommand` now consults the existing `response length` fact for
  `recall` and `history`
- `my response length is short` lowers those two summaries from the
  default last-5 entries to last-3 entries; any other/missing value keeps
  today's baseline behavior
- Added regression coverage in `tests/test_brain.py` so both notes-only
  recall and mixed history summaries are proven to respect the preference

### Local Ollama fallback for unmatched chat

**Why:** `docs/suggestions.md`'s next open item was to make unmatched input
use a local model instead of the hardcoded `I heard: ...` echo, while still
preserving Offline First and the already-documented permission convention.

- Added `src/utils/ollama_client.py`: stdlib-only Ollama client
  (`urllib.request` + `json`), with `GET /api/tags` preflight and
  `POST /api/generate` inference
- Added `src/modules/language_module.py`: `LanguageModule(Module)` wraps
  `OllamaClient`, tracks `available`, raises a clear startup error when
  Ollama is unreachable, and disables itself if generation later fails
- `CommandRegistry` now accepts an optional `language_module` and consults
  it only after normal command matching and the stray-shell-command guard,
  falling back to the existing echo when the module is absent,
  unavailable, or returns nothing
- `Brain` now auto-wires the first module named `language` into the default
  registry, keeping the coupling one-way (`Brain` still does not know
  command trigger words)
- `main.py` now gates the feature behind new `config.json` settings:
  `use_language_fallback` (default `false` per the permission convention),
  `language_base_url`, and `language_model`
- `<think>...</think>` blocks are stripped from local-model output before it
  is shown, so reasoning-trace models like DeepSeek-R1 degrade cleanly too
- Added tests in `tests/test_ollama_client.py`, `tests/test_modules.py`,
  `tests/test_brain.py`, and `tests/test_config.py`

## Changed

### Test hygiene and docs sync

- Deduplicated the shared `StubModule` test double into
  `tests/conftest.py`, closing the last easy cleanup item from
  `docs/suggestions.md`
- Bumped version to `0.0.12` in `pyproject.toml` and `config.json`
- Updated `docs/PROJECT_STATE.md` and `docs/suggestions.md` to reflect the
  shipped language fallback, preference-backed memory output, and current
  next-step list

## Notes

Run the tests with: `python -m pytest` (143 tests)

This version closes the remaining near-term implementation items that were
listed in `docs/suggestions.md`: the preference-backed behavior proof, the
local-Ollama fallback brain, and the `StubModule` deduplication cleanup.

---

# v0.0.1 - 01.07.2026

## Added

### Project

- Initial project created
- Git repository initialized
- Project documentation created
- Development workflow established

### Documentation

- README
- MANIFEST
- PROJECT_STATE
- ROADMAP
- CHANGELog

### Architecture

Initial project structure:

src/
├── config/
├── core/
├── memory/
├── modules/
└── utils/

docs/
├── architecture/
├── journal/
├── research/

### Core

- Created first `Brain` class
- Implemented object initialization (`__init__`)
- Added project metadata
  - name
  - version
  - running state
- Added first `greet()` method
- Created first executable `main.py`

### Development

- Installed Git
- Configured VS Code
- Configured Python environment
- Configured Git identity
- First successful commit
- First successful project execution

---

## Notes

This version focuses entirely on establishing the project's foundation.
No AI functionality has been implemented yet.

The primary goal of v0.0.1 is to create a clean architecture and development workflow for future development.

---

# v0.0.2 - 02.07.2026

### Added
- Logger class
- Dependency Injection (Logger -> Brain)
- Brain startup lifecycle
- start() now controls startup flow

### Changed
- Removed direct print() calls from Brain
- main.py now only creates objects and starts Brain

---

# v0.0.3 - 0.0.4 - 02.07.2026

### #&@&#&$ß$÷¤ß
- F#*k if I know.. go look at Commit Graph lol..

---

# v0.0.5 - 02.07.2026

## Added

- Introduced MemoryManager
- Added ShortMemory architecture
- Added LongMemory placeholder
- Established memory flow:
  User → Brain → MemoryManager → ShortMemory
- Prepared foundation for persistent memory

## Notes

This version introduces the memory architecture only.
Long-term persistence will be implemented in future versions.

---

# v0.0.6 - 02.07.2026

## Added

### Memory (earlier v0.0.6 commits)

- Persistent LongMemory saved to `data/long_memory.json` with timestamps
- Facts store (`my <thing> is <value>` / `what is my <thing>`) saved to `data/facts.json`
- Basic commands: greetings, `remember`, `recall`, `facts`, `help`, farewells
- Fixed the main loop so the conversation actually keeps running

### Brain Lifecycle

- Formal lifecycle states: `OFFLINE → STARTING → RUNNING → STOPPING → OFFLINE`
- State transitions are validated — an invalid transition (e.g. starting twice)
  raises an error instead of silently corrupting state
- Every transition is logged (`State: OFFLINE -> STARTING`)
- `is_running` property; the main loop now runs on `while brain.is_running`
- `receive()` refuses messages when the Brain is not running
- Farewells (`bye` / `exit` / `quit`) now stop the Brain through the lifecycle
  itself — `main.py` no longer manages shutdown manually
- Startup now reports config source and how many memories/facts were loaded

### Config System

- `Config` now loads from `config.json` in the project root instead of
  hardcoding values in code
- Missing file or missing keys fall back to safe defaults in `DEFAULTS`
- Config file path is injectable for testing

### Testing System

- Introduced `pytest` with `pytest.ini` (`pythonpath = src`, `testpaths = tests`)
- 29 tests across `tests/test_brain.py`, `tests/test_memory.py`,
  `tests/test_config.py` covering lifecycle transitions, commands, facts,
  notes, memory persistence, and config loading
- Shared fixtures in `tests/conftest.py`
- Memory classes (`LongMemory`, `Facts`, `MemoryManager`) accept injectable
  file paths so tests never touch real `data/` files

## Changed

- `main.py` simplified: creates objects, starts the Brain, and loops while it
  is running — all shutdown logic lives in the Brain now

## Notes

Run the tests with: `python -m pytest`

This version completes the v0.0.6 "Brain Lifecycle" roadmap item and pulls
the v0.0.7 "Config System" item forward.

---

# v0.0.7 - 02.07.2026

## Added

### Development Rules

**Why:** Erik set a list of permanent constraints (pure Python, no
LangChain/LangGraph/external AI frameworks before v0.1, no overengineering,
small single-capability commits, preserve backwards compatibility, never
break tests) in conversation, on top of the existing README principles
(Offline First / Desktop First / Modular Architecture / User Ownership).
Rules that only live in chat history get forgotten or silently violated
later — writing them into the repo makes them binding for every future
change, including ones made in a different session.

- Added a `DEVELOPMENT RULES` section to `docs/MANIFEST.md` listing all of
  the above

### Command Registry

**Why:** `Brain.process()` had grown into an if/elif chain, and `Brain`
itself owned every command's data directly as class attributes
(`GREETINGS`, `FAREWELLS`, `LEARN_PATTERN`, `QUERY_PATTERN`). Every new
command meant editing `Brain` again, which contradicts "Brain should only
dispatch commands" and would only get worse — help, facts, notes, and exit
had already made the method long, and voice/vision/plugins from the roadmap
would make it much longer. The fix needed to add zero new dependencies
(pure Python `re`/`dict`, per the development rules above) and change zero
observable behavior, so the 29 existing tests could stay untouched as proof
nothing broke.

- Replaced the if/elif chain with a `CommandRegistry` (`src/commands/`)
- Every command is now its own class: `GreetingCommand`, `FactCommand`,
  `MemoryCommand`, `HelpCommand`, `ExitCommand`, all implementing a shared
  `Command.handle(message, normalized) -> str | None` contract
- `Brain` no longer knows about individual commands or trigger words — it
  only dispatches and reacts to `DispatchResult.stops_brain` (a small result
  object, not just a string, so `Brain` can tell whether to call `self.stop()`
  without hardcoding which words mean "exit" and without re-dispatching the
  message a second time, which would have double-run side effects like
  `memory.learn()`)
- `build_default_registry(config, memory)` is the single place that wires
  commands together; `Brain` imports only that factory function
- No behavior changed: all 29 existing tests pass unmodified

### Input Handling

**Why:** `main.py`'s input loop had two rough edges: Ctrl+C crashed with a
raw `KeyboardInterrupt` traceback instead of shutting down, and an empty
Enter press was sent all the way to `Brain.receive()`, producing a useless
"I heard: " reply and a blank entry saved to memory. Both were flagged in
`docs/suggestions.md` as easy wins covered by the test suite.

- Ctrl+C is now caught and routed through `brain.stop()`, so shutdown goes
  through the normal lifecycle (logged, clean) instead of crashing
- Blank/whitespace-only input is skipped before it reaches `brain.receive()`
- Added `tests/test_main.py` covering both cases

## Notes

Run the tests with: `python -m pytest`

This version records the project's permanent development rules and closes
out the "Command registry instead of if/elif chains" and "Input handling
hardening" items from `docs/suggestions.md`.

---

# v0.0.8 - 02.07.2026

## Added

### Logger

**Why:** `Logger` only printed and kept an in-memory list, with no way to
tell routine startup noise apart from real problems, and no persistent
record once the console scrolled away. `docs/PROJECT_STATE.md` and
`docs/ROADMAP.md` both named levels + file output as the next planned
Logger capability.

- `Logger.log(message, level="INFO")` now filters by level
  (`DEBUG < INFO < WARNING < ERROR`); messages below the configured level
  are neither printed, stored, nor written to file
- Added `debug()`, `info()`, `warning()`, `error()` convenience methods
- Optional file output to `data/astra.log` (path is injectable, same
  pattern as `LongMemory`/`Facts`), controlled by the new `log_to_file`
  config key
- `config.json` gains `log_level` (default `"INFO"`) and `log_to_file`
  (default `false`); `main.py` now builds `Config` before `Logger` so the
  logger can read both settings
- All existing unlabeled `self.logger.log(message)` calls in `Brain`
  keep working unchanged (level defaults to `"INFO"`)
- Added `tests/test_logger.py` and extended `tests/test_config.py` to
  cover the new behavior

### Update Checker

**Why:** ASTRA had no way to tell you it was out of date; the only option
was checking GitHub by hand. This is ASTRA's first internet-touching code,
so it had to hold to "Offline First": never block or crash startup when
there's no network.

- `UpdateChecker` (`src/utils/update_checker.py`) fetches `version` from
  `config.json` on the GitHub repo's `main` branch over plain HTTPS (the
  repo is public — no credentials involved) and compares it to the local
  version
- On `Brain.start()`, if a newer version exists, logs one sentence with a
  link to the repo (`https://github.com/TOS-Thousand-One-Eyes/Projekt-Astra-`);
  if up to date, stays silent
- Any network error, timeout, or malformed response is caught and treated
  as "skip the check" — no exception ever reaches `Brain`
- New `config.json` key `check_for_updates` (default `true`); when `false`,
  `main.py` never constructs an `UpdateChecker`, so no network call happens
- Injected into `Brain` the same way as Logger/Config/MemoryManager;
  `fetch` is injectable so `tests/test_update_checker.py` never touches
  the real network — verified manually instead (real GitHub check, a
  simulated outdated version, and a real unreachable-host timeout)
- Redo: `check()` now catches any exception while fetching/parsing (not
  just network/JSON errors), so a malformed or unexpected fetch result
  (e.g. `None`, wrong type) can never leak through as a false "update
  available" message — the link is shown only when a newer version is
  genuinely confirmed
- Redo: silence wasn't good enough — `UpdateChecker` no longer returns a
  message for `Brain` to interpret; it now gets `logger` injected and logs
  its own outcome directly. `"Astra is up to date."` and the newer-version
  sentence go through `logger.info()`; any failure (network error,
  timeout, malformed/unexpected fetch result) goes through `logger.debug()`
  instead of being discarded in a bare `except`. Logger's own level
  filtering — not application code — decides whether a failure is shown,
  so it's quiet by default (`log_level: INFO`) but real and visible with
  `log_level: DEBUG`

### Packaging

**Why:** Running Astra meant `python src/main.py` from the exact right
directory, and there was no declared way to install `pytest` for a fresh
machine — both flagged in `docs/suggestions.md`.

- Added `pyproject.toml` (setuptools backend) with a `[project]` section
  and an `astra` console-script entry point (`main:main`)
- `pip install -e ".[dev]"` installs Astra editable plus `pytest` as a dev
  dependency in one command
- Added `__init__.py` to every `src/` subpackage so setuptools can find
  them as regular packages
- Verified: `astra`, run from an unrelated working directory, correctly
  read/wrote the real project's `config.json` and `data/` (path resolution
  is `__file__`-relative, not cwd-relative, so this was already safe)
- `*.egg-info/`, `build/`, `dist/` added to `.gitignore`

## Notes

Run the tests with: `python -m pytest`

This version closes out the "Logger: file output + levels" item from
`docs/suggestions.md` and the v0.0.8 roadmap milestone, and adds the
Update Checker and the packaging/entry-point setup on top.

---

# v0.0.9 - 03.07.2026

## Added

### Memory: search, forget, and note/transcript separation

**Why:** `LongMemory` only ever grew, with no way to search it or prune a
wrong/old entry, and every `remember <note>` was stored as an
indistinguishable plain string alongside routine chat — flagged as the
top item in `docs/suggestions.md`.

- `LongMemory.remember(entry, entry_type="chat")` now tags every entry with
  a `"type"` (defaults to `"chat"`, so existing callers/tests are
  unaffected); `remember <note>` is tagged `"note"` instead
- `LongMemory.search(query)` — case-insensitive substring search,
  uncapped (searching is for finding one specific thing, not a recent
  digest, unlike `recall`'s existing last-5 cap)
- `LongMemory.forget(entry_text)` — removes entries with an exact text
  match, persists only if something was actually removed, returns the
  count removed
- `MemoryManager.search_long()` / `MemoryManager.forget()` delegate through
- `MemoryCommand` gained two new chat triggers: `search <text>` and
  `forget <text>`, with "couldn't find anything matching" replies when
  nothing matches
- Fixed a real bug these tests surfaced: `Brain.receive()` used to store
  the raw incoming message *before* dispatching it to commands, so e.g.
  `search bicycle` would find its own just-stored input text as a false
  match. `receive()` now dispatches first and logs the turn to memory
  afterward, so a command only ever searches memory as it existed before
  the current turn
- Extended `tests/test_memory.py` and `tests/test_brain.py::TestNotes`

### Continuous Integration

**Why:** There was a real test suite but nothing running it automatically —
a broken commit would only be caught by remembering to run `pytest` by
hand.

- Added `.github/workflows/tests.yml`: checks out the repo, sets up Python
  3.14, runs `pip install -e ".[dev]"`, then `python -m pytest`, on every
  push and pull request

### Personalization

**Why:** Astra could already learn `my name is Erik` via `FactCommand`, but
nothing ever read it back — the whole point of memory feeding into
behavior, per `docs/suggestions.md`.

- `GreetingCommand` now takes `memory` and, when a `name` fact is known,
  personalizes the three short greetings: `hi` → `"Hello, {name}!"`,
  `hello` → `"Hi there, {name}!"`, `hey` → `"Hey, {name}!"`. `how are you`
  and `what's up` are left generic — they don't read naturally with a name
  inserted
- `Brain.start()`'s own greeting log line does the same:
  `"Hello, {name}! I am Astra."` when known, otherwise unchanged
- Scoped to greeting only for now (not farewell, not every response) —
  smaller and matches the suggestion's own example
- Extended `tests/test_brain.py` with `TestPersonalization`

### Real Modules system

**Why:** `Modules` was a placeholder holding the strings `"Module1"` and
`"Module2"`, injected into `Brain` but never actually read anywhere —
zero behavior. Voice, vision, and internet from the roadmap all need a
real subsystem contract to plug into.

- Added `src/modules/module.py`: base `Module` class with a `name`
  attribute and `start()`/`stop()` (raise `NotImplementedError` in the
  base, same convention as `Command.handle()`)
- `Modules` now starts empty (`self.modules = []`, dropping the dead
  placeholder strings) and gained `start_all()`/`stop_all()`
- `Brain.start()`/`stop()` now actually call
  `self.modules.start_all()`/`stop_all()` as part of the lifecycle, and
  log how many modules ran (even `0`) — no more inert dependency
- Added `tests/test_modules.py`; extended `tests/test_brain.py` with
  `TestModulesLifecycle`

### Session summary on shutdown

**Why:** `Brain`'s `STOPPING` phase existed but did nothing beyond logging
"Stopping..." — a real chance to make the lifecycle feel alive, cheap to
build since `ShortMemory` already holds the whole session.

- Added `src/utils/time_format.py`: `format_duration(delta)` renders a
  `timedelta` as a short human string (`"5s"`, `"2m 5s"`, `"1h 3m"`,
  `"2d 4h"`)
- `Brain.start()` now records the session start time and the fact count
  at that moment
- `Brain.stop()` logs one line before shutting down:
  `"Session summary: {n} messages exchanged, {n} new facts learned,
  session lasted {duration}."`
- Added `tests/test_time_format.py`; extended `tests/test_brain.py` with
  `TestSessionSummary`

### Startup briefing

**Why:** `docs/suggestions.md` named the current date/time and time since
the last session as the easiest first steps of the planned startup
briefing sequence, and `LongMemory`'s timestamps already made "time since
last session" possible with no new state.

- `Brain.start()` now logs the current date/time
  (`"Current time: 2026-07-03 21:04:11."`)
- Also logs how long ago the previous session's last memory entry was
  (`"Last seen 2m 5s ago."`, reusing `format_duration` from the session
  summary work above), or `"This is our first session!"` when LongMemory
  is empty
- Reads `LongMemory` once at the very top of `start()`, before this
  session's own turns are recorded, so it only ever reflects prior
  sessions
- Extended `tests/test_brain.py` with `TestStartupBriefing`

### Bug fixes found in a review pass

**Why:** Before pushing v0.0.9, ran a multi-angle review over the six
commits above and found four real bugs, all now fixed and covered by new
tests:

- `MemoryManager.forget()` only ever pruned `LongMemory`, never
  `ShortMemory`, so a forgotten note's raw text could still linger in the
  current session's short-term memory (used for the session-summary
  message count) even though the user was told it was forgotten.
  `ShortMemory` gained its own `forget(entry_text)` and `forget()` now
  clears both stores.
- `LongMemory.forget()`/`ShortMemory.forget()` required a byte-exact
  match, while `search()` was already case-insensitive — `remember Buy
  Milk` followed by `forget buy milk` silently failed to match. Both
  `forget()` methods are now case-insensitive, matching `search()`.
- `Brain._log_session_summary()`'s message count read
  `len(self.memory.recall())` directly instead of diffing against a
  session-start snapshot (unlike the already-correct `new_facts`
  calculation) — restarting the same `Brain` instance without recreating
  `MemoryManager` made the message count silently accumulate across
  sessions instead of resetting. Added `self._messages_at_start`,
  captured in `start()` alongside `_facts_at_start`.
- `format_duration()` had no floor on negative durations, so a backward
  clock adjustment (e.g. DST fall-back, manual/NTP correction) between
  sessions could produce a nonsensical `"Last seen -900s ago."` log line.
  Negative deltas now clamp to `0s`.
- Also extracted two small duplicated helpers while in there:
  `MemoryCommand._argument()` (was `message.split(" ", 1)[1].strip()`
  repeated three times) and `_format_entries()` (shared by
  `_recall_summary()`/`_search_summary()`), and `Brain.start()` no longer
  calls `self.memory.all_facts()` twice.

## Changed

- Bumped version to `0.0.9` in `pyproject.toml`, `config.json`, and
  `Config.DEFAULTS`

## Notes

Run the tests with: `python -m pytest` (97 tests)

This version closes out all six items that were pending in
`docs/suggestions.md`: memory search/forget with note/transcript
separation, CI, personalization, a real Modules system, session summary,
and startup briefing.

---

# v0.0.10 - 03.07.2026

## Added

### Module lifecycle error handling

**Why:** `Modules.start_all()`/`stop_all()` called each module's
`start()`/`stop()` with no try/except, and `Brain.start()`/`stop()` call
them after the state machine has already committed to `STARTING`/
`STOPPING`. A failing module's exception used to abort the method before
the terminal `_set_state()` call ran, permanently stranding the Brain —
no `STARTING -> STARTING` retry or `STARTING -> STOPPING` escape exists
in `TRANSITIONS`. Harmless while `Modules()` started empty, but exactly
the landmine a flaky local-LLM module (see suggestions.md) would hit
first.

- `Modules.__init__` now takes a required `logger` param (mirrors
  `UpdateChecker`'s constructor-injection style)
- `start_all()`/`stop_all()` wrap each module's call in try/except; a
  failing module is logged via `logger.error()` (includes the module's
  `name`) and skipped, never propagated — the rest of the modules still
  run and the Brain still reaches `RUNNING`/`OFFLINE`
- Updated all 10 existing bare `Modules()` call sites across `src/main.py`,
  `tests/conftest.py`, `tests/test_brain.py`, and `tests/test_modules.py`
- Added a local `FailingModule(Module)` test double (mirrors the existing
  `StubModule` convention) in both `tests/test_modules.py` and
  `tests/test_brain.py::TestModulesLifecycle`, plus new tests proving the
  Brain still reaches `RUNNING`/`OFFLINE` and remaining modules still run
  when one fails

### Notes-only recall/search

**Why:** With `LongMemory` entries tagged `"chat"`/`"note"` (v0.0.9),
`recall`/`search` still showed both mixed together — `search milk` after
`remember buy milk` returned the note *and* the raw `remember buy milk`
command echo *and* the bot's confirmation, three near-duplicate hits for
one real memory.

- `recall`/`what do you remember` and `search <text>` now filter to
  `type == "note"` entries only — filtering lives in `MemoryCommand`
  (presentation layer), matching the existing convention that the
  last-5 cap and entry formatting already live there, not in
  `LongMemory`/`MemoryManager`
- New `history` trigger shows the last 5 entries unfiltered (notes and
  chat both) for anyone who wants the old mixed view back
- `forget <text>` is intentionally left unscoped (can still remove chat
  entries too) — only `recall`/`search` were noisy
- `help_text` updated to match the new behavior
- Extended `tests/test_brain.py::TestNotes`

### Single source of truth for the version number

**Why:** `0.0.9` was hand-edited in three places kept in sync manually:
`pyproject.toml`, `config.json`, and `Config.DEFAULTS`. Considered
`importlib.metadata.version("astra")` as an automatic fix, but it
empirically returns a **stale** value on this very checkout (an editable
install can lag behind `pyproject.toml`) and raises `PackageNotFoundError`
for anyone running straight from `src/` without installing first, which
is exactly how this project's own test suite runs (`pytest.ini`'s
`pythonpath = src`). Considered reading `pyproject.toml` directly via
`tomllib`, but that needs Python 3.11+ while the project declares
`requires-python = ">=3.10"`, and a hand-rolled TOML fallback parser is
real complexity this "do not overengineer" project doesn't need.

- `Config.DEFAULTS` no longer carries a `"version"` literal — `config.json`
  is the sole *runtime* source of truth (it already was, via
  `UpdateChecker` and `Brain.start()`'s log line)
- `Config.version` now falls back to an honest `UNKNOWN_VERSION =
  "0.0.0-unknown"` sentinel if `config.json` is missing the key, instead
  of silently repeating a literal that itself needed manual updates
- `pyproject.toml`'s version remains the hand-maintained packaging/
  release-tag source, synced by a documented checklist, not by code —
  added a "RELEASE CHECKLIST" section to `docs/MANIFEST.md`
- Updated `tests/test_config.py` for the removed `DEFAULTS["version"]`
  key; added two tests for the new fallback sentinel

### CI now tests the full supported Python range

**Why:** `pyproject.toml` declares `requires-python = ">=3.10"`, but
`.github/workflows/tests.yml` only ever ran on `3.14` — a 3.10/3.11/
3.12/3.13-only breakage would pass CI and ship undetected.

- Added `strategy.matrix.python-version: ["3.10", "3.11", "3.12",
  "3.13", "3.14"]`, with `fail-fast: false` so one version failing
  doesn't cancel the others mid-run
- No Python/test changes — the local suite runs in well under a second,
  so the cost is almost entirely `setup-python` provisioning time per
  job, and GitHub Actions runs the matrix in parallel

### Bug fixes found in a review pass

**Why:** Before pushing, ran a two-agent review pass over the four
commits above and found a real, currently-reproducible crash:

- `MemoryCommand._recall_summary()`/`_search_summary()` indexed
  `item["type"]` directly to filter for notes. The real `data/
  long_memory.json` on this checkout has 82 entries predating v0.0.9's
  `type` tagging, none of which have a `"type"` key — `recall` and
  `search <text>` (whenever the query matched an old entry) crashed
  with `KeyError: 'type'` uncaught, all the way up through
  `Brain.receive()`. No test caught this because tests only construct
  fresh, always-tagged entries in memory, never load real legacy data.
  Both methods now use `item.get("type")` instead, so an untagged
  legacy entry is treated as non-note (excluded from `recall`/`search`,
  but still visible via `history`) instead of crashing.
- `Config.version` used `settings.get("version", UNKNOWN_VERSION)`,
  which only falls back when the key is *absent* — an explicit
  `"version": null` in `config.json` (e.g. a corrupted/partial save)
  would set `self.version = None` instead of the sentinel. Changed to
  `settings.get("version") or UNKNOWN_VERSION`, which also catches
  falsy values.
- Added regression tests: `tests/test_brain.py::TestNotes` gained
  `test_recall_does_not_crash_on_legacy_entries_without_type` and
  `test_search_does_not_crash_on_legacy_entries_without_type`;
  `tests/test_config.py` gained
  `test_version_falls_back_to_unknown_sentinel_when_null_in_file`.

## Changed

- Bumped version to `0.0.10` in `pyproject.toml` and `config.json` —
  now only two files instead of three, since `Config.DEFAULTS` no
  longer holds a copy (this commit's own payoff, demonstrated
  immediately)
- Rewrote `docs/suggestions.md`'s local-LLM entry into a full design doc
  (recommended model, endpoint, class shape, integration point) covering
  the planned v0.1.0 `LanguageModule` — design only, no code yet

## Notes

Run the tests with: `python -m pytest` (113 tests)

This version closes out all four items that were pending in
`docs/suggestions.md` after v0.0.9: Modules lifecycle error handling,
notes-only recall/search, a single runtime source for the version
number, and a full CI Python version matrix. The only remaining
suggestion is the local-LLM design doc's own implementation, deferred
to a future session now that the Modules system it depends on is solid.

---

# v0.0.11 - 03.07.2026

## Fixed

### A review-pass batch of real crashes and data-loss risks

**Why:** A three-agent parallel audit of core/config/utils, memory, and
commands/modules, each cross-checked against the existing test suite,
found several currently-reproducible bugs — some capable of permanently
destroying long-term memory or crashing the app on ordinary, non-exotic
input.

- `LongMemory`/`Facts` now save atomically (temp file + `os.replace`)
  instead of truncating the real file in place; `load()` falls back to
  empty state on corrupt/truncated JSON instead of crashing. Previously,
  a crash mid-write (kill, power loss) left invalid JSON that then
  crashed every subsequent startup permanently, with no recovery short
  of manually deleting the file.
- `Logger` falls back to `INFO` on an invalid `log_level` instead of
  raising `ValueError` on the very first log call — a `config.json`
  typo (`"WARN"`, `"info"`) used to crash startup immediately.
- `main.py` now catches `EOFError` alongside `KeyboardInterrupt` around
  the input loop, so closed/piped stdin gets the same graceful
  `brain.stop()` shutdown Ctrl+C already had, instead of an unhandled
  crash that skips module shutdown and the session summary.
- `MemoryCommand._argument` no longer leaks the command keyword into
  the saved note/forget-target/search-query when the raw message has
  leading whitespace (e.g. `" remember buy milk"` used to store
  `"remember buy milk"` instead of `"buy milk"`).
- `UpdateChecker` now parses the local version first and, if it's the
  `UNKNOWN_VERSION` sentinel (no `version` in `config.json`), logs a
  clear `info`-level "skipping check" message and skips the network
  call entirely — previously this failed silently forever at an
  invisible `debug` level, contradicting the feature's own "always logs
  an outcome" contract.
- `Config._load()` now falls back to defaults on malformed `config.json`
  instead of crashing, consistent with its existing missing-file
  fallback.
- 9 new regression tests across `test_memory.py`, `test_logger.py`,
  `test_main.py`, `test_brain.py`, `test_update_checker.py`, and
  `test_config.py`.

## Added

### Memory visibility: `memory stats`

**Why:** `docs/suggestions.md` #1 — `LongMemory` had grown search/forget
capability and note/chat tagging, but no way to see its *shape*. You
can't plan deduplication or archiving (roadmap v0.1.4) without first
knowing what's accumulating.

- New `memory stats` trigger in `MemoryCommand`, reusing
  `LongMemory.recall()` (no new storage, no new file): reports total
  entry count, note vs. chat counts, and the oldest/newest entry
  timestamps (relies on `LongMemory.entries` always being append-ordered
  — confirmed true through both `remember()` and `forget()`).
- 3 new tests in `tests/test_brain.py::TestMemoryStats`.

### Memory export: `export`

**Why:** `docs/suggestions.md` #2 — the safe half of roadmap v0.1.3
("Backup/restore"); import/restore is the risky half (can overwrite
real data) and is deliberately deferred. This session alone hit two
separate incidents of manual verification scripts polluting the real
`data/long_memory.json` — a one-command snapshot before risky manual
testing would have made both a non-issue.

- New `ExportCommand` (`src/commands/export_command.py`), registered in
  `build_default_registry`. The `export` trigger bundles `Config`'s
  settings, all facts, and the full long-term memory into one JSON file
  written to `data/exports/astra_export_<timestamp>.json` (microsecond-
  precision filename, so two exports in the same second don't silently
  overwrite each other — caught and fixed in a verification pass before
  landing).
  `export_dir` is injectable, following the same convention as every
  other data path in the codebase.
- 4 new tests in `tests/test_export_command.py`, all using an injected
  `tmp_path` so the test suite never writes into the real project's
  `data/exports/` directory.

### A written permission convention

**Why:** `docs/suggestions.md` #3 — nothing in the codebase does
anything risky enough yet to need the full permission/approval system
planned for roadmap v0.1.2, but `check_for_updates` (gating
`UpdateChecker`'s read-only network call) is already a tiny, working
instance of the pattern that system wants generalized. Writing the
convention down now, before the local-LLM/internet features already
designed in `docs/suggestions.md` actually need it, means there's a
designed convention to build against instead of retrofitting one later.

- New "PERMISSION CONVENTION" section in `docs/MANIFEST.md`: any future
  action touching the network or writing files outside `data/` gets its
  own `config.json` boolean, defaulting to the safe choice, named after
  the capability it gates, wired the same way `check_for_updates` is.
  Docs-only — no code changes.

## Changed

- Bumped version to `0.0.11` in `pyproject.toml` and `config.json`.
- Marked `docs/suggestions.md` items #1, #2, and #3 done; remaining open
  items renumbered.

## Notes

Run the tests with: `python -m pytest` (130 tests)

This version was built via a 3-implementer + 3-verifier parallel agent
pass (one pair per feature), each verifier independently re-reading the
diff, re-running the full suite, and checking the implementation against
this project's existing conventions before anything was committed. The
verification pass caught one real bug (the export filename collision,
above) before it shipped.

---
