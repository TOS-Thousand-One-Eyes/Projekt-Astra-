# PROJECT_STATE.md

# ASTRA
Version: 0.0.18
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
│   │   ├── diagnostics_command.py
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
├── LICENCE
└── .gitignore

---

## Implemented

### Brain
- Holds a formal lifecycle state: OFFLINE → STARTING → RUNNING → STOPPING → OFFLINE.
- State transitions are validated and logged; invalid transitions raise an error.
- A crash mid-`start()`/`stop()` can't strand the state machine: both wrap
  their bodies in try/except that logs the failure at `ERROR`, escapes back
  to `OFFLINE` (there's a `STARTING → OFFLINE` escape transition for this),
  and re-raises the original exception — so a retried `start()` reports the
  real problem instead of "Invalid state transition".
- `is_running` property drives the main loop.
- `receive()` refuses messages when not RUNNING.
- Dispatches every message to a `CommandRegistry` and only reacts to the
  result (`response`, `stops_brain`) — it does not know about individual
  commands or their trigger words.
- `receive()` surfaces the response via `logger.chat()` — a
  level-independent output path — so a `log_level` of WARNING/ERROR mutes
  diagnostics, never Astra's replies. A failed `memory.remember()` save
  (disk full, locked file) is logged at `ERROR` and the conversation
  continues instead of the REPL dying with a raw traceback.
- The startup last-seen line parses the newest long-memory entry's
  timestamp defensively: a hand-edited missing/malformed timestamp logs a
  `WARNING` and skips the line instead of making Astra unstartable.
- Uses dependency injection for Logger, Config, MemoryManager, Modules,
  and (optionally) a CommandRegistry.
- On `stop()`, logs a session summary: messages exchanged, new facts
  learned, and session duration (via `utils/time_format.format_duration`).
  Message count is tracked directly by `Brain` itself (incremented once
  per `receive()`), not inferred from short-memory length — a command
  like `remember <note>` writes an extra memory entry beyond the normal
  message/response pair, which used to inflate the count.
- On `start()`, logs the current date/time and, using the last LongMemory
  entry's timestamp, how long ago the previous session ended (or "This is
  our first session!" if LongMemory is empty).

### Commands
- `Command` base class: `handle(message, normalized) -> str | None`, plus
  `help_text` and `stops_brain` metadata. Every command also takes an
  optional injected `logger` (held by `Command.__init__`), with a `warn()`
  helper that no-ops when none was injected — commands log their own
  observable fallbacks (first user: `MemoryCommand._entry_limit()` warns
  on a non-text `response length` fact instead of silently defaulting).
- `normalize()` strips trailing whitespace along with punctuation
  (`"bye !"` → `"bye"`), so exact-trigger matches don't miss on a space
  before the punctuation.
- `CommandRegistry.dispatch()` tries each command in order, falls back to
  a local `LanguageModule` when one is available, and finally to the
  `"I heard: ..."` echo; it returns a `DispatchResult`. A stray shell
  invocation pasted into the chat (e.g. `python.exe ... main.py`) still gets
  its own clearer message instead of going to the generic echo or local LLM
  (`looks_like_shell_command` in `commands/base.py`).
- One class per command: `GreetingCommand`, `FactCommand`, `MemoryCommand`,
  `ExportCommand`, `DiagnosticsCommand`, `HelpCommand`, `ExitCommand`.
- `build_default_registry(config, memory, language_module=None, logger=None)`
  in `commands/registry.py` is the single place that wires concrete commands
  together, including the optional local-language fallback; it passes its
  `logger` into every command it builds.
- `DiagnosticsCommand` (`diagnostics` / `status` triggers) re-reports, on
  demand, everything already tracked about this session's health:
  `Config.load_warnings`, `MemoryManager.load_warnings()`, and whether
  `Logger` had to disable file logging after a write failure (config asks
  for it but the logger turned itself off). First concrete step toward
  roadmap v0.1.8 "Observability" — no new tracking, just a way to ask
  after the startup log has scrolled away.
- `FactCommand` won't learn a blank key or value (`my nickname is  ?`
  falls through instead of storing an empty fact), and the query path
  checks key *membership* so any stored fact — even a hand-edited `0` or
  `null` — is reported the same way `facts` lists it. `Facts.load()`
  normalizes hand-edited keys to the stripped/lowercased form `learn()`
  writes (with a load warning), so a `"Name"` key can't be listed by the
  summary yet unreachable by lookups.
- `GreetingCommand` personalizes `hi`/`hello`/`hey` with the known `name`
  fact when one has been learned (e.g. "Hello, Erik!"); `Brain.start()`'s
  own greeting log line does the same.
- `ExportCommand` (`export` trigger) bundles `Config`'s settings, all facts,
  and the full long-term memory into one timestamped JSON file under
  `data/exports/` — see "Export" under Memory below.
- `FactCommand`'s `my <thing> is <value>` / `what is my <thing>` regexes
  strip a whole run of trailing punctuation (`[.!?]*$`), not just one
  character — matches `commands/base.py`'s shared `normalize()`, so
  `my mood is great!!` learns `great`, not `great!`.

### Config
- Loads settings from `config.json` in the project root.
- Missing file, missing keys, malformed JSON, non-UTF-8 encoding (e.g. a
  config.json saved as UTF-16 by PowerShell's `Out-File`), or
  syntactically-valid JSON that isn't an object (e.g. `null`, a bare
  number, a list) all fall back to `DEFAULTS` in code (a corrupt/
  hand-edited `config.json` no longer crashes startup — it's treated the
  same as a missing file). A UTF-8 BOM (PowerShell's
  `Out-File -Encoding utf8` default) is tolerated via `utf-8-sig` — same
  for `facts.json`/`long_memory.json`, where a BOM used to silently reset
  the user's memory to empty.
- Loaded values are type-checked against their `DEFAULTS` entry
  (`_validated()`): booleans must be real JSON booleans (a hand-edited
  `"use_language_fallback": "false"` string can't silently flip the flag
  on), numbers must be numeric (bools excluded), strings must be strings;
  a mismatch keeps the default and records a load warning. `log_level` is
  additionally value-checked: casing is normalized (`"debug"` → `"DEBUG"`)
  and an unknown level falls back to `INFO` with a warning instead of
  Logger's silent coercion.
- File path is injectable for testing.
- `version` is the one exception: it's not in `DEFAULTS` — `config.json`
  is the sole runtime source of truth, falling back to an honest
  `UNKNOWN_VERSION = "0.0.0-unknown"` sentinel if the key is missing. See
  the "RELEASE CHECKLIST" in `docs/MANIFEST.md` for how the version is
  kept in sync with `pyproject.toml` (by hand, not by code).
- Every fallback above (malformed JSON, wrong-shape JSON, missing
  version) is recorded in `self.load_warnings` — `Config` is constructed
  before `Logger` exists in `main.py`, so it can't log directly, but
  `Brain.start()` (which has both) logs each one at `WARNING` right
  after "Config loaded from...". A silently-defaulted config used to
  look identical to a correctly-configured one; now it doesn't (see
  MANIFEST.md's "OBSERVABLE FALLBACKS").
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
- `Modules`' error handlers use `getattr(module, "name",
  type(module).__name__)` so a malformed module object without a `name`
  can't crash the handler itself.
- `OllamaClient` strips a reasoning model's `<think>` markup only at the
  *leading* position of the response (where reasoning models emit it) —
  a literal `<think>`/`</think>` later in a real answer is kept as
  content. A lone leading `</think>` (template-swallowed opener) is
  stripped only when no `<think>` appeared anywhere in the raw response.

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
  `memory stats` trigger reports total/note/chat counts and the
  oldest/newest entry timestamps.
- `recall`/`history`'s last-5 cap is a preference: teaching the fact
  `my response length is short` shortens both to the last 2 entries
  instead (`MemoryCommand._entry_limit()`, first proof that a taught
  fact generalizes beyond `GreetingCommand`'s `name` usage).
- `LongMemory.save()`/`Facts.save()` write atomically (temp file +
  `os.replace`) and `load()` falls back to empty state instead of
  crashing on truncated/corrupt JSON — a mid-write crash or hand-edited
  bad file no longer permanently bricks startup. The temp file name
  embeds the PID (`facts.json.<pid>.tmp`) so two Astra processes saving
  at overlapping times can't interleave writes into the same temp file.
- `LongMemory.search()`/`forget()` and `MemoryCommand`'s formatting/stats
  helpers all use `.get(...)` with fallbacks for an entry's `"entry"`/
  `"timestamp"` keys, not just `"type"` — a hand-edited or
  oddly-shaped `long_memory.json` entry can't crash `recall`/`search`/
  `history`/`memory stats` anymore.
- A corrupt-file fallback on `LongMemory`/`Facts` sets `self.load_warning`
  (a data-loss event, not routine status); `MemoryManager.load_warnings()`
  aggregates both, and `Brain.start()` logs each at `WARNING` right after
  "Memory loaded: N entries...". Resetting to empty memory used to be
  indistinguishable from a genuinely empty first run — now it isn't.

### Export
- `ExportCommand` (`export` trigger) bundles `Config`'s settings (every
  key: `name`/`version`/`log_level`/`log_to_file`/`check_for_updates`/
  `use_language_fallback`/`language_base_url`/`language_model`/
  `language_generate_timeout`), all facts, and the full `LongMemory` into
  one JSON file written to
  `data/exports/astra_export_<timestamp>.json` (microsecond-precision
  filename so two exports in the same second never overwrite each other).
- Safe half of roadmap v0.1.3 ("Backup/restore") — a manual snapshot
  before any risky manual testing or before an eventual import/restore
  feature exists. `export_dir` is injectable, same convention as every
  other data path in the codebase.
- Writes atomically (temp file + `os.replace`), same convention as
  `LongMemory`/`Facts`.

### Logger
- Timestamps, console output, in-memory log list.
- Levels: `DEBUG < INFO < WARNING < ERROR`; messages below the configured
  level are filtered out (not printed, stored, or written to file).
- An invalid `log_level` (e.g. a `config.json` typo) falls back to `INFO`
  instead of crashing on the first log call.
- A failure writing to the log file (disk full, permission denied, a
  blocked path) doesn't crash the whole running session — but it isn't
  silent either: it's logged once as a `WARNING` (console + in-memory
  `logs`, since the file path is the thing that's broken) and
  `log_to_file` is disabled for the rest of the session so the failure
  doesn't repeat on every subsequent call.
- Every console print (the normal path *and* the file-failure warning)
  goes through one `_print()` helper that falls back to ASCII on a
  `UnicodeEncodeError`, so an unprintable character can't crash the
  logger from either path. The file write opens with
  `errors="backslashreplace"` for the same reason — a lone surrogate
  (which Python's `json` happily produces from a model response) is
  written escaped instead of raising out of `log()`.
- `chat(message)` is the conversation output path: same timestamped
  entry (labeled `CHAT`), same in-memory list and file output, but never
  filtered by `log_level` — the log stream doubles as the chat UI, so
  level filtering must mute diagnostics, not Astra's replies.
  `Brain.receive()` uses it for every response line.
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
  logged at `warning` (visible by default, not an invisible `debug` level)
  — it's a configuration problem worth noticing, not a routine status.
  The comparison against remote is skipped (nothing to compare against),
  but the check still fetches and reports the latest available version
  on its own, so a genuinely reachable update isn't hidden just because
  the local version is unknown.
- Controlled by `config.json`'s `check_for_updates` key (default `true`);
  when `false`, `main.py` never constructs an `UpdateChecker` and no
  network call happens at all.
- `fetch` is injectable so tests never touch the real network.
- Version tuples are zero-padded to the same length before comparing, so
  `"1.2"` vs `"1.2.0"` counts as up to date instead of a spurious update.

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
- pytest suite (265 tests) in `tests/`, configured by `pytest.ini`.
- Covers lifecycle transitions (including mid-transition crash recovery),
  commands, facts, notes, memory search/forget/stats, export,
  preference-backed output length, modules, local Ollama fallback
  (including think-strip anchoring), session summary, startup briefing,
  diagnostics/status, memory persistence (including corrupt-file fallback,
  entries missing keys, and PID-unique temp paths), config loading
  (including malformed-JSON, wrong-shape-JSON, non-UTF-8, and
  wrong-type-value fallback), and that every fallback above is actually
  logged, not just survived (`load_warnings` reaching a `WARNING` log
  line, not merely "didn't raise").
- No test touches the real network or the real `data/` directory — all
  paths and fetchers are injected.
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
- conditionally adds `LanguageModule(OllamaClient(...), logger)` when
  `config.use_language_fallback` is enabled
- creates Brain and calls brain.start()
- loops `while brain.is_running`
- catches both `KeyboardInterrupt` (Ctrl+C) and `EOFError` (closed/piped
  stdin) around `brain.start()` *and* the input loop — a Ctrl+C during
  startup (e.g. mid update-check) exits cleanly instead of dumping a raw
  traceback, and `brain.stop()` is only called when the brain actually
  reached RUNNING; either interrupt during the loop still routes through
  `brain.stop()` for the same graceful shutdown.

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
