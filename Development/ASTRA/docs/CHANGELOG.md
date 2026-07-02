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

