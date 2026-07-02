# Suggestions

Ideas for what to tackle next, roughly in order of impact vs. effort.

---

## 1. Command registry instead of if/elif chains

`Brain.process()` currently matches commands with a growing chain of
`if normalized == ...`. Fine for now, but it won't scale once you add more
commands. Consider a dict of `{pattern: handler_function}` (or a decorator
like `@command("hi", "hello")`) so adding a command doesn't mean editing a
giant method.

## 2. Tests

There are no automated tests yet. Even a handful of `pytest` tests for
`Brain.process()` and `LongMemory` would catch regressions like the
`main.py` loop bug that was in this codebase before today's fix — that kind
of bug is invisible until you run the program, and a test would have caught
it instantly.

## 3. Packaging / entry point

Imports currently work because Python 3 supports namespace packages, but
there are stale `__init__.py` `.pyc` files in `__pycache__` from an earlier
version that *did* have `__init__.py` files. Pick one approach on purpose:
either add real (empty) `__init__.py` files back for clarity, or add a
`pyproject.toml` with a proper `[project]` section and an entry point script
(so you can run `astra` instead of `python src/main.py` and always from the
right working directory).

## 4. Logger: file output + levels

`docs/PROJECT_STATE.md` already names this as a planned feature. Right now
`Logger` only prints and keeps an in-memory list. Adding `INFO/WARNING/ERROR/DEBUG`
levels and optional file output (e.g. `data/astra.log`) will make it much
easier to debug once Astra does more than chat.

## 5. Config from file, not hardcoded

`Config` currently hardcodes `name` and `version` in code. Moving this to a
`config.yaml` or `.env` (with `data/` and `.env` already gitignored) will
matter as soon as you add API keys for internet access, voice, or vision —
you don't want those hardcoded or committed.

## 6. Memory: forget/search, not just append

`LongMemory` only grows forever right now. Worth adding:
- `search(query)` to find relevant past entries instead of just "last 5"
- `forget(entry)` / a way to prune old or wrong memories
- separating raw conversation transcript from "facts you explicitly asked
  Astra to remember" (right now `remember <note>` and normal chat both land
  in the same list)

## 7. Input handling hardening

`main.py` will currently crash with a `KeyboardInterrupt` traceback on
Ctrl+C, and an empty `Enter` press just echoes back "I heard: ". Small
quality-of-life fixes: catch `KeyboardInterrupt` for a clean exit, and skip
processing on blank input.

## 8. Pick the very next roadmap item

Per `docs/ROADMAP.md`, v0.0.6 is "Brain Lifecycle" and v0.0.7 is "Config
System" — both are natural next steps and build directly on the fixes made
today (start/stop lifecycle logging is already back in `Brain`, so
formalizing lifecycle states like `STARTING → RUNNING → STOPPING → OFFLINE`
with hooks would be a small, satisfying next commit).
