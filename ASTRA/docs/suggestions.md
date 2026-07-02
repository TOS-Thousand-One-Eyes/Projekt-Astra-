# Suggestions

Ideas for what to tackle next, roughly in order of impact vs. effort.

Done items are kept at the bottom for history.

---

## 1. Logger: file output + levels

`docs/PROJECT_STATE.md` already names this as a planned feature, and the
roadmap has it as v0.0.8. Right now `Logger` only prints and keeps an
in-memory list. Adding `INFO/WARNING/ERROR/DEBUG` levels and optional file
output (e.g. `data/astra.log`) will make it much easier to debug once Astra
does more than chat. The new `config.json` is the natural place for settings
like `log_level` and `log_to_file`.

## 2. Packaging / entry point

Add a `pyproject.toml` with a proper `[project]` section and an entry point
script so you can run `astra` instead of `python src/main.py` and always
from the right working directory. It would also declare `pytest` as a dev
dependency, so a fresh machine can set up with one `pip install` command.

## 3. Memory: forget/search, not just append

`LongMemory` only grows forever right now (and every test run of the real
app adds more). Worth adding:
- `search(query)` to find relevant past entries instead of just "last 5"
- `forget(entry)` / a way to prune old or wrong memories
- separating raw conversation transcript from "notes you explicitly asked
  Astra to remember" (right now `remember <note>` and normal chat both land
  in the same list)

## 4. Continuous Integration (GitHub Actions)

Now that there's a test suite, a tiny GitHub Actions workflow
(`.github/workflows/tests.yml`) that runs `python -m pytest` on every push
would guard every future commit automatically — even ones made late at night.
It's about 15 lines of YAML.

## 5. Use facts to personalize Astra

Astra already knows `my name is Erik`, but never uses it. On startup (the
lifecycle now reports loaded facts, so the data is right there), greet the
user by name: "Hello Erik! I am Astra." Same for responses — small touch,
big personality payoff, and it's the first time memory feeds back into
behavior, which is the whole point of the project.

## 6. Real Modules system

`Modules` is still a placeholder holding the strings `"Module1"` and
`"Module2"`. Design the real thing: a base `Module` class with `name`,
`start()`, `stop()`, and let the Brain start/stop modules as part of its
lifecycle (the lifecycle hooks now exist for exactly this). Voice, vision,
and internet from the roadmap would each become a module.

## 7. Session summary on shutdown

The Brain now has a proper `STOPPING` phase — use it. On shutdown, log a
small session summary: how many messages were exchanged, how many new facts
were learned, session duration. Cheap to build (ShortMemory already holds
the session), and makes the lifecycle feel alive.

## 8. Startup briefing steps

`PROJECT_STATE.md` lists the planned startup sequence (system check, time
check, reminders, morning briefing...). The lifecycle's `STARTING` phase is
now the natural home for these. Start with the easy ones: report the current
date/time and how long since the last session (LongMemory timestamps already
make this possible).

## 9. Local LLM as a fallback brain

Per the "Offline First" principle: instead of `I heard: ...` for unknown
input, a `LanguageModule` could pass the message to a local model (e.g. via
Ollama). Rule-based commands stay instant and free; only unmatched input
goes to the model. This is the bridge from "chatbot with if-statements" to
"actual AI assistant" — but it deserves the Modules system (#6) first.
Note: per the permanent development rules, no external AI frameworks
(LangChain, LangGraph, etc.) before v0.1 — a direct Ollama HTTP call is fine,
a framework wrapper is not.

---

## Done

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
