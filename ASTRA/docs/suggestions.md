# Suggestions

Ideas for what to tackle next, roughly in order of impact vs. effort.

Done items are kept at the bottom for history.

---

## 1. Continuous Integration (GitHub Actions)

Now that there's a test suite, a tiny GitHub Actions workflow
(`.github/workflows/tests.yml`) that runs `python -m pytest` on every push
would guard every future commit automatically — even ones made late at night.
It's about 15 lines of YAML.

## 2. Use facts to personalize Astra

Astra already knows `my name is Erik`, but never uses it. On startup (the
lifecycle now reports loaded facts, so the data is right there), greet the
user by name: "Hello Erik! I am Astra." Same for responses — small touch,
big personality payoff, and it's the first time memory feeds back into
behavior, which is the whole point of the project.

## 3. Real Modules system

`Modules` is still a placeholder holding the strings `"Module1"` and
`"Module2"`. Design the real thing: a base `Module` class with `name`,
`start()`, `stop()`, and let the Brain start/stop modules as part of its
lifecycle (the lifecycle hooks now exist for exactly this). Voice, vision,
and internet from the roadmap would each become a module.

## 4. Session summary on shutdown

The Brain now has a proper `STOPPING` phase — use it. On shutdown, log a
small session summary: how many messages were exchanged, how many new facts
were learned, session duration. Cheap to build (ShortMemory already holds
the session), and makes the lifecycle feel alive.

## 5. Startup briefing steps

`PROJECT_STATE.md` lists the planned startup sequence (system check, time
check, reminders, morning briefing...). The lifecycle's `STARTING` phase is
now the natural home for these. Start with the easy ones: report the current
date/time and how long since the last session (LongMemory timestamps already
make this possible).

## 6. Local LLM as a fallback brain

Per the "Offline First" principle: instead of `I heard: ...` for unknown
input, a `LanguageModule` could pass the message to a local model (e.g. via
Ollama). Rule-based commands stay instant and free; only unmatched input
goes to the model. This is the bridge from "chatbot with if-statements" to
"actual AI assistant" — but it deserves the Modules system (#3) first.
Note: per the permanent development rules, no external AI frameworks
(LangChain, LangGraph, etc.) before v0.1 — a direct Ollama HTTP call is fine,
a framework wrapper is not.

---

## Done

- ~~**Memory: forget/search, not just append**~~ — Done in v0.0.9:
  `LongMemory.search()`/`forget()`, `remember <note>` now tagged `"note"`
  separately from ordinary chat (`"chat"`), and `search`/`forget` chat
  commands; covered by `tests/test_memory.py` and `tests/test_brain.py`.
- ~~**Packaging / entry point**~~ — Done in v0.0.8: added `pyproject.toml`
  (setuptools) with an `astra` console-script entry point (`main:main`)
  and `pytest` as a `[dev]` extra; `pip install -e ".[dev]"` sets up a
  fresh machine in one command; `src/` subpackages gained `__init__.py`
  for clean packaging; verified `astra` runs correctly from an unrelated
  working directory.
- ~~**Logger: file output + levels**~~ — Done in v0.0.8: `Logger` now
  filters by level (`DEBUG < INFO < WARNING < ERROR`), gained
  `debug()/info()/warning()/error()` convenience methods, and supports
  optional file output to `data/astra.log`, controlled by the new
  `log_level`/`log_to_file` keys in `config.json`; covered by
  `tests/test_logger.py`.
- ~~**Input handling hardening**~~ — Done in v0.0.7: Ctrl+C is caught and
  routed through `brain.stop()` for a clean lifecycle shutdown instead of a
  raw traceback; blank/whitespace-only input is skipped before it reaches
  `brain.receive()`; covered by `tests/test_main.py`.
- ~~**Command registry instead of if/elif chains**~~ — Done in v0.0.7:
  `src/commands/` now holds one class per command (`GreetingCommand`,
  `FactCommand`, `MemoryCommand`, `HelpCommand`, `ExitCommand`) behind a
  `CommandRegistry`; `Brain` only dispatches and no longer knows individual
  commands or trigger words.
- ~~**Permanent development rules**~~ — Done in v0.0.7: recorded in
  `docs/MANIFEST.md` (pure Python, no AI frameworks before v0.1, small
  single-capability commits, never break tests).
- ~~**Tests**~~ — Done in v0.0.6: 29 pytest tests covering Brain, memory,
  and config, with injectable paths so tests never touch real data.
- ~~**Config from file, not hardcoded**~~ — Done in v0.0.6: `Config` loads
  `config.json` with defaults fallback.
- ~~**Brain Lifecycle (roadmap v0.0.6)**~~ — Done in v0.0.6: validated
  `OFFLINE → STARTING → RUNNING → STOPPING → OFFLINE` transitions, `is_running`,
  farewell-driven shutdown.
- ~~**Packaging cleanup (stale `.pyc`)**~~ — Superseded by #2; the namespace
  packages work, the remaining task is a real `pyproject.toml`.
