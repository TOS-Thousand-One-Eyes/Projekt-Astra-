# PROJECT_STATE.md

# ASTRA
Version: 0.0.8
Status: Active Development

---

## Current Architecture

ASTRA/
│
├── docs/
│   ├── architecture/
│   ├── journal/
│   ├── research/
│   ├── CHANGELOG.md
│   ├── MANIFEST.md
│   ├── PROJECT_STATE.md
│   ├── ROADMAP.md
│   └── suggestions.md
│
├── src/
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── registry.py
│   │   ├── greeting_command.py
│   │   ├── fact_command.py
│   │   ├── memory_command.py
│   │   ├── help_command.py
│   │   └── exit_command.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── config.py
│   ├── core/
│   │   ├── __init__.py
│   │   └── brain.py
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── facts.py
│   │   ├── long_memory.py
│   │   ├── memory_manager.py
│   │   └── short_memory.py
│   ├── modules/
│   │   ├── __init__.py
│   │   └── modules.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   └── update_checker.py
│   └── main.py
│
├── tests/
│   ├── conftest.py
│   ├── test_brain.py
│   ├── test_config.py
│   ├── test_logger.py
│   ├── test_main.py
│   ├── test_memory.py
│   └── test_update_checker.py
│
├── data/            (gitignored - runtime memory files)
├── config.json
├── pyproject.toml
├── pytest.ini
├── README.md
├── LICENSE
└── .gitignore

---

## Implemented

### Brain
- Holds a formal lifecycle state: OFFLINE → STARTING → RUNNING → STOPPING → OFFLINE.
- State transitions are validated and logged; invalid transitions raise an error.
- `is_running` property drives the main loop.
- `receive()` refuses messages when not RUNNING.
- Dispatches every message to a `CommandRegistry` and only reacts to the
  result (`response`, `stops_brain`) — it does not know about individual
  commands or their trigger words.
- Uses dependency injection for Logger, Config, MemoryManager, Modules,
  and (optionally) a CommandRegistry.

### Commands
- `Command` base class: `handle(message, normalized) -> str | None`, plus
  `help_text` and `stops_brain` metadata.
- `CommandRegistry.dispatch()` tries each command in order, falls back to
  the `"I heard: ..."` echo, and returns a `DispatchResult`.
- One class per command: `GreetingCommand`, `FactCommand`, `MemoryCommand`,
  `HelpCommand`, `ExitCommand`.
- `build_default_registry(config, memory)` in `commands/registry.py` is the
  single place that wires concrete commands together.

### Config
- Loads settings from `config.json` in the project root.
- Missing file or missing keys fall back to `DEFAULTS` in code.
- File path is injectable for testing.

### Memory
- MemoryManager routes to ShortMemory (session), LongMemory (persistent
  JSON with timestamps), and Facts (persistent key/value store).
- LongMemory → `data/long_memory.json`, Facts → `data/facts.json`.
- All file paths are injectable so tests never touch real data.

### Logger
- Timestamps, console output, in-memory log list.
- Levels: `DEBUG < INFO < WARNING < ERROR`; messages below the configured
  level are filtered out (not printed, stored, or written to file).
- Convenience methods: `debug()`, `info()`, `warning()`, `error()`.
- Optional file output to `data/astra.log` (path injectable for testing),
  controlled by `config.json`'s `log_level` and `log_to_file` keys.

### Update Checker
- `UpdateChecker` fetches `config.json`'s `version` field from the GitHub
  repo's `main` branch (a plain unauthenticated HTTPS GET — the repo is
  public) and compares it against the local version.
- `UpdateChecker` gets `logger` injected (like Brain) and logs its own
  result directly — `Brain.start()` just calls `update_checker.check()`
  and doesn't interpret a return value.
- Always logs an outcome, never stays silent in code: `"Astra is up to
  date."` or the newer-version sentence with a repo link go through
  `logger.info()`; any network error, timeout, or malformed/unexpected
  fetch result (`None`, wrong type, bad version string) goes through
  `logger.debug()` instead of being swallowed — Logger's own level
  filtering (not application code) decides whether it's shown, so it's
  silent by default at `log_level: INFO` but visible with `DEBUG`.
- Offline First is preserved: ASTRA never blocks or crashes on startup
  without internet, but a failed check is still a real, filterable log
  entry rather than a discarded exception.
- Controlled by `config.json`'s `check_for_updates` key (default `true`);
  when `false`, `main.py` never constructs an `UpdateChecker` and no
  network call happens at all.
- `fetch` is injectable so tests never touch the real network.

### Packaging
- `pyproject.toml` (setuptools backend) declares the `astra` package and an
  `astra` console entry point (`main:main`).
- `pip install -e ".[dev]"` from the project root installs Astra in
  editable mode plus `pytest` as a dev dependency — one command sets up a
  fresh machine.
- Running `astra` (instead of `python src/main.py`) works from any working
  directory: `Config`/`MemoryManager`/`Logger` resolve their paths relative
  to `__file__`, not the current directory, so `data/`/`config.json` are
  always found in the real project root regardless of where `astra` is
  invoked from.
- Each `src/` subpackage now has an `__init__.py` so setuptools can
  discover them as regular packages.

### Tests
- pytest suite (58 tests) in `tests/`, configured by `pytest.ini`.
- Covers lifecycle transitions, commands, facts, notes, memory persistence,
  and config loading.
- Run with: `python -m pytest`

### Startup
main.py only:
- creates Logger, Config, MemoryManager, Modules
- creates Brain and calls brain.start()
- loops `while brain.is_running`

Brain controls startup and shutdown internally.

---

## Design Decisions

- Brain never calls print(). Logger is responsible for output.
- main.py should stay as simple as possible.
- Brain owns its lifecycle; nothing else changes its state directly.
- Brain dispatches commands; it does not know individual commands.
- Objects are passed through Dependency Injection.
- File paths are injectable parameters with sensible defaults (testability).
- New behavior gets a test.

---

## Next Planned Feature

See `docs/suggestions.md` for the ranked list.

---

## Learning Progress

Concepts already learned:

- Classes, Objects, __init__(), self
- Imports, Packages
- Dependency Injection
- Basic Architecture
- Logger Pattern
- Startup Flow / Lifecycle state machines
- File persistence (JSON)
- Regular expressions
- Config with defaults fallback
- pytest: tests, fixtures, tmp_path
- Git workflow
- Code Review workflow

---

## Development Workflow

For every feature:

1. Discuss purpose
2. Design together
3. Implement
4. Test
5. Review
6. Commit
7. Update documentation

---

## Notes

VS Code autocomplete is allowed.

Goal is understanding architecture,
not memorizing syntax.

Project philosophy:

"We are building Astra while learning software engineering."
