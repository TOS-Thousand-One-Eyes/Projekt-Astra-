# Suggestions

Ideas for what to tackle next, roughly in order of impact vs. effort.

`docs/ROADMAP.md` has the longer-term version-gated milestone sequence
(v0.1.1 onward) — items here are that roadmap's nearest milestones scoped
down to a concrete, small, single-commit-sized first step, the same way
every item in this file has been scoped so far. Reconciled against the
roadmap on 2026-07-03.

Done items are kept at the bottom for history.

---

## 1. A preference fact that actually changes behavior (preview of roadmap v0.1.1)

v0.1.1 wants persistent communication-style/language/priority preferences.
The existing `Facts` system (`my <thing> is <value>`) is already a
general-purpose key-value store — it doesn't need a new subsystem, it
needs one more consumer. `GreetingCommand` already proved the pattern
(reads the `name` fact, changes its response). Pick one more: e.g.
`my response length is short` consulted by `MemoryCommand`'s `history`/
`recall` (currently a hardcoded last-5) to actually shorten output. Small,
reuses what exists, and proves "preferences change behavior" generalizes
beyond the one greeting case before investing in anything dedicated.

## 2. Local LLM as a fallback brain

Per the "Offline First" principle: instead of `I heard: ...` for unmatched
input, a `LanguageModule` should pass the message to a local Ollama model.
Rule-based commands stay instant and free; only unmatched input goes to the
model — this is the bridge from "chatbot with if-statements" to "actual AI
assistant." The `Modules` hardening this depended on already landed (error
handling + required `logger`, see Done below), so a flaky/unreachable Ollama
server can no longer brick the Brain.

**Recommended model — recalibrated against Erik's actual hardware** (Intel
i5-10310U, 4 cores/8 threads @ 2.21GHz, integrated Intel UHD graphics with
no dedicated VRAM, 16GB RAM — confirmed models needing up to ~8-10GB RAM
are a fine normal target, not just the lightest option): `qwen3:4b` or
`qwen3:8b` (~2.5-5.2GB disk, ~5-9GB RAM) as the real default — the earlier
`llama3.2:1b` recommendation was written before hardware specs were known
and undersells what this machine can actually run. `deepseek-r1:8b` is a
reasoning-focused alternative in the same weight class (note: its distilled
models emit `<think>...</think>` reasoning traces in the response by
default — the response parser needs to handle/strip that, unlike plain
Qwen3/Llama-family models). Keep `llama3.2:1b`/`qwen2.5:0.5b` in mind as
the "still works even when the machine is busy with other things" fallback
— **CPU-only inference speed (no GPU) is the more relevant constraint here
than RAM headroom**: a bigger model will simply respond slower, not fail to
fit.

Qwen3 and DeepSeek-R1 (local) need **zero new client code** — they're just
different `model` string values on the same `OllamaClient` described below,
not separate integrations.

**Recommended endpoint:** Ollama's local server (`http://localhost:11434`)
exposes `POST /api/generate` (single-turn: `{"model": ..., "prompt": ...,
"stream": false}` in, generated text in the `response` field out) and
`POST /api/chat` (message history: `{"model": ..., "messages": [{"role":
"user", "content": ...}], "stream": false}` in, text in `message.content`
out). First cut should use `/api/generate` — the codebase has no
conversation-history concept threaded into a fallback yet, so `/api/chat`'s
`messages` list would always be exactly one message, a needless complication.
`/api/chat` is the natural v2 once `ShortMemory`'s session log can be
passed through as real chat history.

**Class shape:** an `OllamaClient` utility mirroring `UpdateChecker`'s
constructor-injection style (`base_url`, `model`, a short 2-3s timeout for
a `GET /api/tags` liveness+model-availability pre-flight, a longer 30-120s
timeout for the actual generate call, since a cold model can take several
seconds to load into RAM on its first call — reusing `UpdateChecker`'s 3s
default would misfire constantly on generation). `urllib.error.URLError`
means the server itself isn't reachable (connection refused); `urllib.
error.HTTPError` with a 404 and a `{"error": "model '...' not found, try
pulling it first"}` body means the server is up but the model isn't pulled
— both are real, expected failure modes, not edge cases.

`LanguageModule(Module)` wraps `OllamaClient` and implements `start()` as
the `/api/tags` pre-flight — on failure it simply raises a clear error
(e.g. `ConnectionError("Ollama not reachable")`), letting `Modules.
start_all()`'s now-hardened try/except catch it, log `"Module 'language'
failed to start: ..."`, and move on — no crash, no special-cased logger
dependency needed inside `LanguageModule` itself. The module tracks its
own `available` flag so callers know whether to bother consulting it.

**Integration point:** `CommandRegistry.dispatch()` (`src/commands/
registry.py`) currently always falls back to `return DispatchResult(f"I
heard: {message}")` when no command matches. This needs a way to consult
the `LanguageModule` first when it's available — e.g. `CommandRegistry`
gains an optional `language_module` param, consulted only when no command
matched *and* the module reports itself available, falling through to the
existing `I heard: ...` string otherwise, so an unreachable Ollama server
degrades to today's exact baseline behavior, not a broken one.

Reminder per the permanent development rules: no LangChain, no LangGraph,
no `ollama` pip package — stdlib `urllib.request`/`urllib.error`/`json`
only, same as `UpdateChecker`.

This is a design only, not yet implemented — no `LanguageModule`,
`OllamaClient`, or registry wiring code exists yet.

## 3. TFT coaching via screen access (correctly placed: far out, two dependencies)

Erik's real near-term want, raised this session: Astra watching the screen
during a TFT match and coaching live. Honest scope check before this goes
anywhere: it needs **both** a working local LLM (#2 above) **and** Vision
(roadmap v0.2.2 — "OCR, screenshots, basic 'what's on screen'"), neither of
which exists yet. It's also not really an LLM-reasoning problem underneath
— TFT patches every ~2 weeks and rotates trait/item sets every ~4 months,
so a generic local model's training data goes stale fast regardless of
which one is running; real coaching value needs live/curated current-meta
data as grounding context fed into the model, not just a bigger model.
Correctly sequenced this stays a v0.2.2+ idea, not something to reach for
early — flagging it here so it's on record and roadmap-placed rather than
forgotten, not because it's next.

## 4. Deduplicate the `StubModule` test double

`tests/test_modules.py` and `tests/test_brain.py::TestModulesLifecycle`
each define an identical local `StubModule(Module)` (`name`/`started`/
`stopped` tracking) instead of sharing one from `tests/conftest.py`,
where `memory`/`config`/`brain`/`running_brain` are already centralized.
Flagged in a review pass, never actually fixed. Pure test hygiene, zero
behavior change, five-minute fix whenever someone's next in that file.

---

## Done

- ~~**Memory visibility**~~ — Done in v0.0.11: `memory stats` chat
  trigger reports total/note/chat entry counts and oldest/newest
  timestamps, reusing `LongMemory.recall()`; covered by
  `tests/test_brain.py::TestMemoryStats`.
- ~~**Memory export**~~ — Done in v0.0.11: `export` chat trigger bundles
  `Config` settings, all facts, and the full long-term memory into a
  timestamped JSON file under `data/exports/`; covered by
  `tests/test_export_command.py`.
- ~~**A permission convention**~~ — Done in v0.0.11: "PERMISSION
  CONVENTION" section added to `docs/MANIFEST.md`, docs-only.
- ~~**Module lifecycle needs error handling**~~ — Done in v0.0.10:
  `Modules` now takes a required `logger` (injected the same way
  `UpdateChecker` is) and `start_all()`/`stop_all()` catch a failing
  module's exception, log it by name via `logger.error()`, and keep
  going instead of stranding `Brain.start()`/`stop()` mid-transition;
  covered by `tests/test_modules.py` and
  `tests/test_brain.py::TestModulesLifecycle`.
- ~~**Notes-only recall/search**~~ — Done in v0.0.10: `recall`,
  `what do you remember`, and `search <text>` now filter to
  `type == "note"` entries only, so `search milk` no longer surfaces the
  raw `remember buy milk` command echo or the bot's own confirmation as
  false hits; a new `history` trigger shows the last 5 entries
  unfiltered (notes and chat both) for anyone who wants the old mixed
  view; covered by `tests/test_brain.py::TestNotes`.
- ~~**Sync the version number from one place**~~ — Done in v0.0.10:
  `Config.DEFAULTS` no longer carries a hardcoded version literal —
  `config.json` is the sole runtime source of truth, falling back to an
  honest `"0.0.0-unknown"` sentinel (instead of a silently-stale
  duplicate) if the file is missing the key; `pyproject.toml`'s version
  stays the hand-maintained packaging/release-tag source (neither
  `importlib.metadata` nor stdlib TOML parsing are safe zero-dependency
  options here — confirmed `importlib.metadata.version("astra")`
  returns a stale value on an editable install lagging behind
  `pyproject.toml`, and `tomllib` needs 3.11+ while this project
  supports 3.10+); the remaining two-literal sync is now a reminder in
  the release checklist in `docs/MANIFEST.md`; covered by
  `tests/test_config.py`.
- ~~**CI only tests one Python version**~~ — Done in v0.0.10:
  `.github/workflows/tests.yml` now runs the suite across
  `python-version: ["3.10", "3.11", "3.12", "3.13", "3.14"]` with
  `fail-fast: false`, actually exercising the `requires-python = ">=3.10"`
  claim in `pyproject.toml` instead of testing 3.14 alone.
- ~~**Startup briefing steps**~~ — Done in v0.0.9: `Brain.start()` logs
  the current date/time and how long ago the previous session's last
  memory entry was (or "This is our first session!"); covered by
  `tests/test_brain.py::TestStartupBriefing`.
- ~~**Session summary on shutdown**~~ — Done in v0.0.9: `Brain.stop()`
  logs messages exchanged, new facts learned, and session duration, via
  a new `utils/time_format.format_duration()` helper; covered by
  `tests/test_time_format.py` and `tests/test_brain.py::TestSessionSummary`.
- ~~**Real Modules system**~~ — Done in v0.0.9: base `Module` class
  (`name`, `start()`, `stop()`), `Modules.start_all()`/`stop_all()`, and
  `Brain.start()`/`stop()` now actually drive module lifecycle instead of
  holding an inert placeholder list; covered by `tests/test_modules.py`
  and `tests/test_brain.py::TestModulesLifecycle`.
- ~~**Use facts to personalize Astra**~~ — Done in v0.0.9: `GreetingCommand`
  and `Brain.start()`'s greeting now use the known `name` fact for
  `hi`/`hello`/`hey` (e.g. "Hello, Erik!"); scoped to greeting only.
- ~~**Continuous Integration (GitHub Actions)**~~ — Done in v0.0.9:
  `.github/workflows/tests.yml` runs `python -m pytest` on every push and
  pull request.
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
