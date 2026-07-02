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

