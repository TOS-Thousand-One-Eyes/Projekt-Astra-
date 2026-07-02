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

## Notes

Run the tests with: `python -m pytest`

---

