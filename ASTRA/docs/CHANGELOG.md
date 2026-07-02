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

