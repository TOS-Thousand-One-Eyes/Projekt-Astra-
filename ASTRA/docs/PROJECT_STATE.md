# PROJECT_STATE.md

# ASTRA
Version: 0.0.6
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
│   ├── config/
│   │   └── config.py
│   ├── core/
│   │   └── brain.py
│   ├── memory/
│   │   ├── facts.py
│   │   ├── long_memory.py
│   │   ├── memory_manager.py
│   │   └── short_memory.py
│   ├── modules/
│   │   └── modules.py
│   ├── utils/
│   │   └── logger.py
│   └── main.py
│
├── tests/
│   ├── conftest.py
│   ├── test_brain.py
│   ├── test_config.py
│   └── test_memory.py
│
├── data/            (gitignored - runtime memory files)
├── config.json
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
- Farewells (bye/exit/quit) stop the Brain through its own lifecycle.
- Commands: greetings, facts (`my X is Y` / `what is my X`), `remember`,
  `recall`, `facts`, `help`.
- Uses dependency injection for Logger, Config, MemoryManager, Modules.

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
- Basic Logger class: timestamps, console output, in-memory log list.
- Designed to become the central logging system (levels + file output planned).

### Tests
- pytest suite (29 tests) in `tests/`, configured by `pytest.ini`.
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
- Objects are passed through Dependency Injection.
- File paths are injectable parameters with sensible defaults (testability).
- New behavior gets a test.

---

## Next Planned Feature

See `docs/suggestions.md` for the ranked list. Top candidates:

1. Command registry instead of if/elif chains
2. Input hardening (Ctrl+C, blank input)
3. Logger levels + file output (roadmap v0.0.8)

---

## Future Logger

Logger will eventually support:

- INFO / WARNING / ERROR / DEBUG
- Console output
- File output
- Colored output

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
