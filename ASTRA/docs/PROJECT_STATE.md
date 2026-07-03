# PROJECT_STATE.md

# ASTRA
Version: 0.0.12
Status: Active Development

---

## Current Architecture

ASTRA/
│
├── .github/
│   └── workflows/
│       └── tests.yml
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
│   │   ├── export_command.py
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
│   │   ├── language_module.py
│   │   ├── module.py
│   │   └── modules.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py
│   │   ├── ollama_client.py
│   │   ├── time_format.py
│   │   └── update_checker.py
│   └── main.py
│
├── tests/
│   ├── conftest.py
│   ├── test_brain.py
│   ├── test_config.py
│   ├── test_export_command.py
│   ├── test_logger.py
│   ├── test_main.py
│   ├── test_memory.py
│   ├── test_modules.py
│   ├── test_ollama_client.py
│   ├── test_time_format.py
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
- On `stop()`, logs a session summary: messages exchanged, new facts
  learned, and session duration (via `utils/time_format.format_duration`).
- On `start()`, logs the current date/time and, using the last LongMemory
  entry's timestamp, how long ago the previous session ended (or "This is
  our first session!" if LongMemory is empty).

### Commands
- `Command` base class: `handle(message, normalized) -> str | None`, plus
  `help_text` and `stops_brain` metadata.
- `CommandRegistry.dispatch()` tries each command in order, falls back to
  a local `LanguageModule` when one is available, and finally to the
  `"I heard: ..."` echo; it returns a `DispatchResult`. A stray shell
  invocation pasted into the chat (e.g. `python.exe ... main.py`) still gets
  its own clearer message instead of going to the generic echo or local LLM
  (`looks_like_shell_command` in `commands/base.py`).
- One class per command: `GreetingCommand`, `FactCommand`, `MemoryCommand`,
  `ExportCommand`, `HelpCommand`, `ExitCommand`.
- `build_default_registry(config, memory, language_module=None)` in
  `commands/registry.py` is the single place that wires concrete commands
  together, including the optional local-language fallback.
- `GreetingCommand` personalizes `hi`/`hello`/`hey` with the known `name`
  fact when one has been learned (e.g. "Hello, Erik!"); `Brain.start()`'s
  own greeting log line does the same.
- `ExportCommand` (`export` trigger) bundles `Config`'s settings, all facts,
  and the full long-term memory into one timestamped JSON file under
  `data/exports/` — see "Export" under Memory below.

### Config
- Loads settings from `config.json` in the project root.
- Missing file, missing keys, or malformed JSON all fall back to
  `DEFAULTS` in code (a corrupt/hand-edited `config.json` no longer
  crashes startup — it's treated the same as a missing file).
- File path is injectable for testing.
- `version` is the one exception: it's not in `DEFAULTS` — `config.json`
  is the sole runtime source of truth, falling back to an honest
  `UNKNOWN_VERSION = "0.0.0-unknown"` sentinel if the key is missing. See
  the "RELEASE CHECKLIST" in `docs/MANIFEST.md` for how the version is
  kept in sync with `pyproject.toml` (by hand, not by code).
- Local-language fallback is gated by `use_language_fallback` (default
  `false` per the permission convention) plus `language_base_url` and
  `language_model` settings; `main.py` only constructs the fallback module
  when the flag is enabled.

### Modules
- `Module` (`src/modules/module.py`) is the base class for a Brain-managed
  subsystem: a `name` attribute, `start()`/`stop()` (both raise
  `NotImplementedError` in the base, matching `Command.handle()`'s
  convention).
- `Modules` holds a list of `Module` instances (`add_module()`,
  `list_modules()`) and drives them together via `start_all()`/`stop_all()`.
- `Modules(logger)` requires a logger, injected the same way as
  `UpdateChecker`. `start_all()`/`stop_all()` catch a failing module's
  exception, log it via `logger.error()` (including the module's `name`),
  and keep going — a broken module is skipped, never crashes the Brain or
  strands its state machine.
- `Brain.start()`/`stop()` call `self.modules.start_all()`/`stop_all()` as
  part of the lifecycle and always log how many modules ran, even zero.
- `LanguageModule` (`src/modules/language_module.py`) is the first real
  optional subsystem: it wraps a local `OllamaClient`, preflights model
  availability on `start()`, tracks an `available` flag, and safely degrades
  back to the old echo behavior if startup or generation fails.

### Memory
- MemoryManager routes to ShortMemory (session), LongMemory (persistent
  JSON with timestamps), and Facts (persistent key/value store).
- LongMemory → `data/long_memory.json`, Facts → `data/facts.json`.
- All file paths are injectable so tests never touch real data.
- Every LongMemory entry is tagged with a `type` (`"chat"` by default,
  `"note"` for `remember <note>`), separating routine transcript from
  explicit notes.
- `LongMemory.search(query)` (case-insensitive substring, uncapped) and
  `LongMemory.forget(entry_text)` (case-insensitive exact match, returns
  count removed) are exposed through `MemoryManager` and as
  `search <text>` / `forget <text>` chat commands; `forget()` clears the
  entry from both `LongMemory` and `ShortMemory`.
- `MemoryCommand` filters `recall`/`search` to `type == "note"` entries
  only, so chat transcript noise doesn't drown out real notes; a
  `history` trigger shows the unfiltered last 5 entries (notes + chat); a
  learned `response length = short` fact lowers `history`/`recall` to the
  last 3 entries instead; a `memory stats` trigger reports total/note/chat
  counts and the oldest/newest entry timestamps.
- `LongMemory.save()`/`Facts.save()` write atomically (temp file +
  `os.replace`) and `load()` falls back to empty state instead of
  crashing on truncated/corrupt JSON — a mid-write crash or hand-edited
  bad file no longer permanently bricks startup.

### Export
- `ExportCommand` (`export` trigger) bundles `Config`'s settings
  (`name`/`version`/`log_level`/`log_to_file`/`check_for_updates`), all
  facts, and the full `LongMemory` into one JSON file written to
  `data/exports/astra_export_<timestamp>.json` (microsecond-precision
  filename so two exports in the same second never overwrite each other).
- Safe half of roadmap v0.1.3 ("Backup/restore") — a manual snapshot
  before any risky manual testing or before an eventual import/restore
  feature exists. `export_dir` is injectable, same convention as every
  other data path in the codebase.

### Logger
- Timestamps, console output, in-memory log list.
- Levels: `DEBUG < INFO < WARNING < ERROR`; messages below the configured
  level are filtered out (not printed, stored, or written to file).
- An invalid `log_level` (e.g. a `config.json` typo) falls back to `INFO`
  instead of crashing on the first log call.
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
- An unparseable local version (the `UNKNOWN_VERSION` sentinel, e.g. on a
  fresh checkout with no `version` in `config.json`) is checked first and
  logged at `info` ("Skipping update check: local version is unknown.")
  instead of silently failing forever at an invisible `debug` level — no
  network call is even made in that case.
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
- pytest suite (143 tests) in `tests/`, configured by `pytest.ini`.
- Covers lifecycle transitions, commands, facts, notes, memory search/
  forget/stats, export, preference-backed output length, modules, local
  Ollama fallback, session summary, startup briefing, memory persistence
  (including corrupt-file fallback), and config loading (including malformed-
  JSON fallback).
- Run with: `python -m pytest`

### Continuous Integration
- `.github/workflows/tests.yml` runs `python -m pytest` on every push and
  pull request (Ubuntu, `pip install -e ".[dev]"`), across a matrix of
  `python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]` (`fail-fast:
  false`) — actually exercising `pyproject.toml`'s
  `requires-python = ">=3.10"` claim instead of testing one version.

### Startup
main.py only:
- creates Logger, Config, MemoryManager, Modules
- conditionally adds `LanguageModule(OllamaClient(...))` when
  `config.use_language_fallback` is enabled
- creates Brain and calls brain.start()
- loops `while brain.is_running`
- catches both `KeyboardInterrupt` (Ctrl+C) and `EOFError` (closed/piped
  stdin) around the input loop, routing either through `brain.stop()` for
  the same graceful shutdown — a closed pipe no longer skips module
  shutdown and the session summary the way Ctrl+C already didn't.

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
