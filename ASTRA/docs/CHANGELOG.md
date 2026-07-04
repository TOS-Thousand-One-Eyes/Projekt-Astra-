# CHANGELOG

All notable changes to this project will be documented here.

The format is inspired by "Keep a Changelog".

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

# v0.0.12 - 03.07.2026

## Added

### A preference fact that actually changes behavior

**Why:** `docs/suggestions.md` #1 — proves "preferences change behavior"
generalizes beyond `GreetingCommand`'s `name` usage, before investing in
anything dedicated for roadmap v0.1.1. The existing `Facts` key-value
store (`my <thing> is <value>`) already covers teaching the preference;
this needed exactly one more consumer.

- Teaching `my response length is short` now shortens `MemoryCommand`'s
  `recall`/`history` triggers from the hardcoded last-5 to the last 2
  (`_entry_limit()`); any other value, or no preference at all, keeps
  the default of 5. `search` stays intentionally uncapped, unaffected.
- 5 new tests in `tests/test_brain.py::TestPreferences`.

## Fixed

### A second review-pass batch of real bugs (4-agent full re-audit)

**Why:** After the preference feature landed, a fresh 4-agent pass (1
verifier for the new feature, 3 covering the whole codebase again —
core/config/utils, memory, commands/modules) found several more real,
verified bugs, including one that silently broke the brand-new
preference feature itself.

- **`Brain`'s "messages exchanged" session-summary count was
  unreliable**: it was inferred from short-memory length, but
  `remember <note>` writes an extra memory entry beyond the normal
  message/response pair (inflating the count) and `forget <text>`
  removes entries from short memory too (deflating it). `Brain` now
  tracks the count itself, directly, in `receive()` — decoupled from
  `MemoryManager`'s internal bookkeeping entirely.
- **`FactCommand`'s regexes only stripped a single trailing punctuation
  character** (`[.!]?`/`\??`), unlike the shared `normalize()` (which
  strips a whole run). `my mood is great!!` silently learned `"great!"`
  instead of `"great"` — and `my response length is short..` (one extra
  trailing dot) silently broke the brand-new preference feature above,
  since `"short."` != `"short"`. Now uses `[.!?]*$`, matching
  `normalize()`'s behavior.
- **`LongMemory.search()`/`forget()` and `MemoryCommand`'s
  `_stats_summary()`/`_format_entries()` assumed every entry has
  `"entry"`/`"timestamp"` keys**, the same class of bug already fixed
  for `"type"` in an earlier release — a hand-edited or oddly-shaped
  `long_memory.json` entry could crash `recall`/`search`/`history`/
  `memory stats`. All now use `.get(...)` with fallbacks.
- **`Config._load()` crashed on syntactically-valid JSON that isn't an
  object** (e.g. `config.json` containing just `null` or `42`) — the
  existing malformed-JSON guard only caught actual parse errors. Now
  falls back to defaults for any non-dict result too.
- **`Logger`'s file-write path had no error handling** — a disk-full,
  permission, or blocked-path failure while `log_to_file=True` crashed
  the entire running session on the very next log call, the same class
  of unguarded-I/O bug already fixed elsewhere this session. Now caught
  and silently skipped; console output and the in-memory log are
  unaffected.
- **`MemoryCommand._entry_limit()` assumed the `response length` fact
  value is always a string** — a hand-edited `facts.json` with a
  non-string value crashed `recall`/`history`. Now guarded with
  `isinstance(preference, str)`.
- **`ExportCommand` wrote its export file non-atomically**, unlike
  `LongMemory`/`Facts` (fixed earlier this session) — a crash mid-write
  could leave a truncated backup file. Now uses the same temp-file +
  `os.replace` pattern.
- **`Brain.__init__`'s `commands or build_default_registry(...)`**
  would silently discard an explicitly-passed falsy `commands` value
  and build the default registry instead. Changed to an explicit
  `is not None` check. (Currently latent — no caller passes a falsy
  value — but a real correctness gap in the constructor's contract.)
- 8 new regression tests across `test_brain.py`, `test_config.py`,
  `test_logger.py`, `test_memory.py`, and `test_export_command.py`.

## Changed

- Bumped version to `0.0.12` in `pyproject.toml` and `config.json`.
- Marked `docs/suggestions.md` #1 (preference fact) done; remaining
  open items renumbered.

## Notes

Run the tests with: `python -m pytest` (148 tests)

Same process as v0.0.11: implement, then re-audit with fresh parallel
agents rather than trusting the implementation pass alone. This time
the audit ran twice — once against the new feature specifically, once
against the whole codebase — and both passes found real, previously
unnoticed bugs, including one (`FactCommand`'s punctuation stripping)
that silently undermined the very feature just added in this same
version.

---

# v0.0.13 - 03.07.2026

## Fixed

### Fallbacks were surviving errors but hiding them — now they're loud

**Why:** Erik caught this directly, running the real app: a startup log
showing `Astra v0.0.0-unknown is starting...` with no explanation why.
The root cause was several fallback paths added in v0.0.11/v0.0.12
(`Config`, `LongMemory`, `Facts`, `Logger`, `UpdateChecker`) that all
correctly avoided crashing, but gave zero indication that anything had
gone wrong — a misconfigured `config.json` looked identical to a
correctly-configured one from the outside. "Didn't crash" isn't the
same as "fine" if the failure is invisible. New permanent rule in
`docs/MANIFEST.md`: "OBSERVABLE FALLBACKS."

- **`Config`** gained `self.load_warnings` (a list): set when
  `config.json` is malformed, isn't a JSON object, or is missing a
  `"version"` value. `Config` is constructed before `Logger` exists in
  `main.py`, so it can't log directly — the warning rides on the object
  itself until something downstream can surface it.
- **`LongMemory`/`Facts`** gained `self.load_warning`: set when a
  corrupt file falls back to empty state (this is data loss, not a
  routine "first run" case — those stay silent, correctly, since an
  actually-missing file isn't an error). `MemoryManager.load_warnings()`
  aggregates both.
- **`Brain.start()`** now logs every warning from `config.load_warnings`
  and `memory.load_warnings()` at `WARNING`, right alongside the
  existing "Config loaded from..." / "Memory loaded: N entries..." lines
  — the natural place, since `main.py` stays as simple as possible per
  Design Decisions.
- **`Logger`**'s own file-write failure (disk full, permission denied, a
  blocked path) used to be caught and silently passed. Now it's logged
  once as a `WARNING` (console + in-memory `logs`, since the file
  itself is what's broken) and `log_to_file` is disabled for the rest
  of the session, so the failure doesn't repeat on every call.
- **`UpdateChecker`**'s unknown-local-version case was already visible
  (an `info`-level "Skipping update check" message, added in v0.0.12) but
  underdelivered on the check's actual purpose. Upgraded to `warning`
  (it's a config problem, not routine status) and it now still fetches
  and reports the latest available version — skipping only the
  meaningless "are you up to date" comparison, not the whole check.
- 13 new regression tests, several of which specifically assert a
  `WARNING` log line appears (not just "didn't raise") — a fallback
  test that only checks survival isn't enough per the new convention.

## Added

### Two follow-ups written down, not built

- `docs/suggestions.md` #1: a `diagnostics`/`status` chat trigger to
  read `Config.load_warnings`/`MemoryManager.load_warnings()`/whether
  `Logger` disabled file output — all already tracked, just not
  queryable after the startup log scrolls by. Preview of roadmap
  v0.1.8 ("Observability").
- `docs/suggestions.md` #2: `MemoryCommand._entry_limit()`'s non-string
  `response length` fact guard still falls back silently — deliberately
  not fixed this round, since `Command` subclasses don't take a
  `logger` today and giving every command one is a real DI change, not
  a one-line fix. Written down instead of silently left as a loose end.

## Changed

- Bumped version to `0.0.13` in `pyproject.toml` and `config.json`.

## Notes

Run the tests with: `python -m pytest` (162 tests)

Reproduced the exact reported scenario before calling this fixed: a
`config.json` missing its `"version"` key now logs
`WARNING config.json has no "version" value; update checks will be
skipped until it's set.` immediately after `Astra v0.0.0-unknown is
starting...`, instead of leaving that line unexplained.

---

# v0.0.14 - 03.07.2026

## Fixed

- `Brain.receive()` logged `You: {message}` at INFO right after the
  terminal's own `input("You: ")` prompt had already echoed the same
  text — every message a user typed appeared twice in a row for no
  reason. Erik caught this running the real app ("why should It get
  my text twice?"). Removed the redundant log call; the assistant's
  reply is still logged (it's the only line that's actually new
  information).
- Confirmed the "Astra doesn't know about a new GitHub version" report
  from the same session was not a bug: the update checker compares
  local vs. the *published* `config.json` on GitHub, and the newer
  local commits (through v0.0.13) hadn't been pushed yet, so "up to
  date" was the correct answer at the time. Resolves itself once this
  round is pushed.

## Changed

- Bumped version to `0.0.14` in `pyproject.toml` and `config.json`.

## Notes

Run the tests with: `python -m pytest` (162 tests)

---

# v0.0.15 - 03.07.2026

## Added

### Local Ollama fallback for unmatched chat, merged from a parallel branch

**Why:** While this session's bug-fix rounds were in progress, a separate
`copilot/analyze-project-changes` branch was merged directly into GitHub's
`main` (PR #6) — independently, with no coordination with this session. It
implemented `docs/suggestions.md`'s "Local LLM" item for real, so Erik had
it merged in rather than discarded.

- Added `src/utils/ollama_client.py`: stdlib-only Ollama client
  (`urllib.request` + `json`), with a `GET /api/tags` preflight and
  `POST /api/generate` inference call
- Added `src/modules/language_module.py`: `LanguageModule(Module)` wraps
  `OllamaClient`, tracks `available`, raises a clear startup error when
  Ollama is unreachable, and disables itself if generation later fails
- `CommandRegistry` now accepts an optional `language_module` and consults
  it only after normal command matching and the stray-shell-command guard,
  falling back to the existing echo when the module is absent, unavailable,
  or returns nothing
- `Brain` auto-wires the first module named `language` into the default
  registry, keeping the coupling one-way (`Brain` still does not know
  command trigger words)
- `main.py` gates the feature behind new `config.json` settings:
  `use_language_fallback` (default `false`, per the permission convention),
  `language_base_url`, and `language_model`
- `<think>...</think>` blocks are stripped from local-model output before
  it's shown, so reasoning-trace models like DeepSeek-R1 degrade cleanly
- New tests in `tests/test_ollama_client.py` plus additions to
  `tests/test_modules.py` and `tests/test_brain.py`

### Test hygiene merged from the same branch

- Deduplicated the shared `StubModule` test double into `tests/conftest.py`
  (closes `docs/suggestions.md`'s dedupe item), removing the duplicate
  definitions from `tests/test_modules.py` and `tests/test_brain.py`

## Changed

- The same parallel branch had independently re-implemented this session's
  v0.0.12 "response length" preference feature under different constant
  names (`SHORT_ENTRY_LIMIT = 3` vs. this branch's `SHORT_LIMIT = 2`),
  including its own duplicate tests. Per Erik's explicit instruction, this
  session's already-shipped implementation and tests were kept as-is and
  the incoming duplicate was dropped — same feature, one implementation.
- Bumped version to `0.0.15` in `pyproject.toml` and `config.json`.

## Notes

Run the tests with: `python -m pytest` (173 tests)

Merge process: created a `backup/pre-merge-2026-07-03` branch pointing at
pre-merge local `main` before touching anything, then resolved each
conflict by hand (not a blanket `-X ours`/`-X theirs`) — genuinely new,
non-overlapping work (the Ollama fallback, the `StubModule` dedup) was
kept from the incoming branch; the one real feature collision (response
length preference) was resolved in favor of this session's existing,
already-tested implementation. Full suite re-run after resolution, before
committing the merge.

---

# v0.0.16 - 03.07.2026

## Fixed

### A 6-agent post-merge audit found real bugs the merged-in branch shipped without noticing

**Why:** The Ollama fallback merged in from the parallel branch (v0.0.15)
had never been audited against this project's own conventions — it
arrived as finished code, not as work-in-progress reviewed here. A
6-way parallel audit (core/config, commands, memory, modules+Ollama,
utils+main.py, tests+docs) went through it, and the rest of the merge
result, looking specifically for anything the merge introduced or missed.

- **`LanguageModule.respond()` silently swallowed runtime failures** —
  confirmed independently by three of the six auditors as the most
  serious finding. It caught any exception from the local model, set
  `available = False`, and returned `None` with zero logging anywhere;
  `CommandRegistry` then quietly reverted to the `"I heard: ..."` echo.
  If Ollama dropped mid-session, Astra silently downgraded for the rest
  of the session with no trace in the logs — exactly the anti-pattern
  `docs/MANIFEST.md`'s OBSERVABLE FALLBACKS section exists to prevent,
  just never applied to this feature since it didn't go through that
  process. `LanguageModule` now takes an optional `logger` (same
  constructor-injection convention as `Modules`/`UpdateChecker`) and
  logs a `WARNING` with the actual error when a runtime failure
  disables it; `main.py` passes the existing logger through.
- **`Facts.load()`/`LongMemory.load()` had no wrong-JSON-shape guard**,
  unlike `Config._load()`, which already checks `isinstance(loaded,
  dict)`. A `facts.json`/`long_memory.json` that's syntactically valid
  JSON but the wrong shape (e.g. a list instead of an object) parsed
  without error and silently set `self.facts`/`self.entries` to the
  wrong type — worse than a silent fallback, this crashed **uncaught**
  on the first `recall`/`search`/`forget`/fact command afterward, and
  `main.py`'s loop only catches `KeyboardInterrupt`/`EOFError`. Both now
  check the loaded shape the same way `Config` does, falling back to
  empty state with a `load_warning`, surfaced the same way as every
  other fallback.
- **`LongMemory.search()`/`forget()` crashed on a non-string but
  present `"entry"` value** (e.g. a hand-edited `"entry": 42`) — the
  existing `.get("entry", "")` guard only covers a *missing* key, not a
  wrong-typed one, and `.lower()` doesn't exist on an `int`. Both now
  coerce with `str(...)` before comparing.
- **An unclosed `<think>` tag leaked the model's raw reasoning trace**
  — `OllamaClient`'s stripping regex required a closing `</think>`, so
  a response truncated mid-thought (a real failure mode for local
  models hitting a length limit) passed through completely unstripped,
  literal tag and all. Now also strips from an unclosed `<think>` to
  the end of the response.
- **An empty/whitespace-only message could reach the network** — the
  blank-input guard only existed in `main.py`'s input loop;
  `CommandRegistry.dispatch()` had no guard of its own, so any other
  caller could send blank input straight to the local model. Now
  guarded in `dispatch()` itself.
- **`LanguageModule.start()` reported every failure as "Ollama not
  reachable"**, even when the server responded with a real HTTP error
  (e.g. model not pulled) rather than being unreachable — collapsing
  two different, actionable problems into one message, losing a
  distinction the original design (`docs/suggestions.md`) called for.
  Now catches `urllib.error.HTTPError` separately and reports the
  status code.

## Changed

- Fixed a merge-resolution artifact in `tests/test_brain.py` (a missing
  blank line between `TestNotes` and `TestMemoryStats`) and a stale
  self-referential cross-link in `docs/suggestions.md`'s TFT-coaching
  item (pointed at itself as "#3 above" and still described the local
  LLM as not yet built, after it had already shipped).
- Bumped version to `0.0.16` in `pyproject.toml` and `config.json`.

## Notes

Run the tests with: `python -m pytest` (185 tests)

Process: 6 parallel read-only audit agents, each scoped to a different
area, none aware of the others' findings — 3 independently flagged the
same `LanguageModule` bug, which is a stronger signal than any one of
them finding it alone. Every fix above has a new regression test that
asserts the actual fixed behavior (a warning is logged, a wrong-shaped
file falls back cleanly, a non-string entry doesn't crash, an unclosed
tag is stripped, a blank message never reaches `generate()`), not just
"didn't crash" — per this project's standing rule that a fallback test
must prove the fallback is visible, not just survivable. A second round
of 6 fresh audit agents follows to re-verify these fixes before
anything is reported back for a push decision.

---

# v0.0.17 - 03.07.2026

## Fixed

### Two more real bugs found by the second (re-verification) audit round

**Why:** The second round of 6 agents didn't just confirm the v0.0.16
fixes — two of them found the v0.0.16 fixes were each one step short of
complete, in the same general direction (a shape check that covered the
container but not its contents; a tag-stripping fix that covered one
malformed case but not its mirror image).

- **`LongMemory.load()`'s wrong-shape guard only checked the top-level
  JSON was a list, not that each element was a dict** — a file like
  `[1, 2, 3]` passed the guard and landed straight in `self.entries`.
  Worse than the original bug: `Brain.start()`'s `_log_last_seen()`
  unconditionally reads `long_entries[-1]["timestamp"]`, so this
  crashed the entire app at startup, before any user input, with no
  warning printed. Now validates every element is a dict too, falling
  back to empty state with a `load_warning` like every other case.
- **The unclosed-`<think>`-tag fix only handled a missing closing tag,
  not a missing opening one** — a stray `</think>` with no matching
  `<think>` before it (a malformed model response, not currently
  reachable through the non-streamed `/api/generate` call but worth
  covering defensively) still leaked straight through. `OllamaClient`
  now also strips up to an orphaned closing tag.

## Notes

Run the tests with: `python -m pytest` (187 tests)

Both of these were found by agents specifically instructed to
re-verify round-1 fixes rather than trust them — reinforces that
"tests pass" and "the fix is complete" aren't the same claim; the
round-1 fixes for these two spots were real improvements, just not the
full shape of the problem.

---

# v0.0.18 - 04.07.2026

## Added

### Diagnostics on demand (`diagnostics` / `status`)

First concrete step toward roadmap v0.1.8 "Observability": a new
`DiagnosticsCommand` re-reports, at any point in a session, everything
already tracked about its health — `Config.load_warnings`,
`MemoryManager.load_warnings()`, and whether `Logger` had to disable
file logging after a write failure. No new tracking anywhere; it's a
way to ask "did anything go wrong?" after the startup log scrolled away.

### Commands can log (observable fallbacks reach the command layer)

`Command` now takes an optional injected `logger` with a `warn()`
helper; `build_default_registry()` wires Brain's logger into every
command. First user: a non-text `response length` fact (hand-corrupted
`facts.json`) now logs a WARNING instead of silently using the default
entry limit — the last silent fallback the 2026-07-03 audit flagged.

## Fixed

### The six deferred findings from the 2026-07-03 six-agent audit

Each landed as its own commit:

- **Brain stuck-state**: a crash mid-`start()`/`stop()` left the state
  machine stranded at STARTING/STOPPING; a retry then raised a
  confusing "Invalid state transition" instead of the real error. Both
  now log the failure at ERROR, escape back to OFFLINE, and re-raise.
- **Modules error handler**: the `except` block read `module.name`
  directly, so a malformed module without `.name` crashed the handler
  itself; now falls back to the class name.
- **Config type validation**: a hand-edited `"use_language_fallback":
  "false"` (string) was truthy and silently flipped the flag on; every
  loaded key is now type-checked against `DEFAULTS`, keeping the
  default and warning on mismatch.
- **Ollama `<think>` stripping**: literal `<think>`/`</think>` text in
  a real answer got eaten as reasoning markup; all patterns are now
  anchored to the response start, where reasoning models actually emit
  their think block.
- **Update checker version comparison**: `"1.2"` vs `"1.2.0"` compared
  as different (tuple comparison); tuples are now zero-padded to the
  same length first.
- **Atomic-write temp paths**: `Facts`/`LongMemory` used a fixed
  `path.tmp` name; two Astra processes saving at once could interleave
  writes. The name now embeds the PID.

### Eight more findings from a same-day 3-agent follow-up audit

- **Logger**: the file-write-failure warning's own `print()` lacked the
  `UnicodeEncodeError` fallback the primary print already had — the
  failure handler could crash from inside itself.
- **Config**: a non-UTF-8 `config.json` (PowerShell's `Out-File`
  default is UTF-16) crashed startup with a raw traceback instead of
  falling back to defaults with a warning.
- **Config**: an unknown `log_level` (e.g. `"debug"`, `"VERBOSE"`)
  silently became INFO; casing is now normalized and genuinely unknown
  values warn.
- **main**: Ctrl+C during startup (e.g. mid update-check) escaped as a
  raw traceback; `brain.start()` is now inside the interrupt handler's
  scope, and `stop()` only runs if the brain reached RUNNING.
- **tests**: `test_main.py` made real HTTPS calls through the
  un-stubbed update checker on every run; the fixture now disables
  `check_for_updates`.
- **normalize()**: `"bye !"` normalized to `"bye "` (trailing space)
  and missed every exact trigger — the brain didn't stop; whitespace is
  now stripped along with punctuation.
- **FactCommand**: `"my nickname is  ?"` learned an empty fact; a
  hand-edited falsy value (`0`) was denied by the query while `facts`
  listed it. Blank keys/values are rejected; the query checks
  `is not None`.
- **export**: the config section omitted `language_generate_timeout`
  (its test asserted the exact stale key set, masking the omission).

A 2-agent verification recheck over the full session diff confirmed
every fix and found only two nits (a misleading word in the recovery
log message; `\r\n` missing from normalize's strip set), both fixed.

## Notes

Run the tests with: `python -m pytest` (246 tests)

No test touches the real network or the real `data/` directory anymore.
