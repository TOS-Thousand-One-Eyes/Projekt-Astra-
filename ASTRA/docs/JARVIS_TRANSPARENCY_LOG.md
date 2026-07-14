# JARVIS / ASTRA Transparency Log

## 2026-07-06

### Decision

Implement JARVIS-style learning inside the ASTRA project itself, not in the earlier VLT vault tooling.

### Why

The requested active target is:

`C:\GIT Repo\Projekt-Astra-\ASTRA`

ASTRA already has a memory manager, command registry, local-first architecture, tests, and Ollama integration points. The right next step is therefore a native learning subsystem that fits ASTRA's existing command/memory design.

### Changes

- Added `src/learning/learning_manager.py`
  - creates learning subjects under `data/learning`
  - stores sources, distillation, eval cases, eval reports, review status, and promotion readiness
  - evaluates responses against expected sources and boundary behavior
- Added `src/learning/__init__.py`
  - exposes `LearningManager`
- Added `src/commands/learning_command.py`
  - supports `learn about <topic>`
  - supports `nauč se <téma>` and `nauc se <tema>`
  - supports `teach <topic>: <source text>`
  - supports `zdroj pro <téma>: <text>`
  - supports `learning status`, `learning status <topic>`, `learning eval <topic>`, and `learning approve <topic>`
- Updated `src/commands/registry.py`
  - registers `LearningCommand`
  - includes learning help text in `help`
- Updated `src/core/brain.py`
  - allows injected `learning` manager for tests and future runtime wiring
- Updated `pyproject.toml`
  - includes the new `learning` package
- Updated `README.md`
  - documents the new learning commands
- Added `tests/test_learning.py`
  - covers Czech slugging, subject creation, source-backed distillation, response eval, promotion gating, command memory candidates, teach command, status listing, and registry dispatch

### Safety / Boundaries

- No external network access is required.
- Runtime learning data is stored under ignored `data/learning`.
- A subject is not promotion-ready until it has both approval and a passing eval report.
- Learning uses existing ASTRA memory candidates first and asks for stronger source text when memory has no evidence.

### Current Limitations

- This is not yet full autonomous internet research.
- It can run learning eval prompts through the local language module when that module is available.
- It does not yet perform real desktop actions.
- It is a working local-first learning foundation that moves ASTRA toward the requested JARVIS behavior.

### Validation

- Created local `.venv` because the system Python did not have `pytest`.
- Installed project dev dependencies with `pip install -e ".[dev]"` into `.venv`.
- Added `.venv/` to `.gitignore` so the local environment is not tracked.
- Ran a dependency-free compile/smoke check before installing pytest.
- First full test run found one real bug:
  - `LearningManager.approve()` crashed when `eval_report` was still `None`.
  - Reason: approval before evaluation is allowed, but must not imply promotion readiness.
  - Fix: treat missing eval report as `{}` and keep `promotion_ready: false`.
- After adding Brain/registry injection and README docs, final test result:
  - `273 passed`

### Action Layer Improvement

After the first native learning layer, the next missing JARVIS capability was
operational follow-through: the assistant could learn topics, but it could not
turn work into tracked tasks or record decisions in a durable audit trail.

Implemented:

- Added `src/actions/action_manager.py`
  - stores local tasks under `data/actions/tasks.json`
  - stores transparent decisions under `data/actions/decisions.json`
  - supports task creation, goal planning, listing, completion, and decision logging
  - uses atomic temp-file replacement like the existing memory stores
- Added `src/actions/__init__.py`
  - exposes `ActionManager`
- Added `src/commands/action_command.py`
  - supports `task`, `todo`, `plan`, `tasks`, `done`, `decide`, and `decisions`
- Added `src/commands/jarvis_command.py`
  - supports `jarvis status`, `briefing`, and `jarvis improve`
  - combines memory count, learning subjects, promotion-ready subjects, open tasks, and the next task
- Updated `src/commands/registry.py`
  - registers the new action and JARVIS commands
  - shares the same `ActionManager` and `LearningManager` instances between commands in one runtime
- Updated `src/core/brain.py`
  - allows injected `actions` manager for tests and future runtime wiring
- Updated `pyproject.toml`
  - includes the new `actions` package
- Added `tests/test_actions.py`
  - covers task persistence, due date validation, planning, command listing/completion, decisions, and shared JARVIS status state
- Updated `README.md`
  - documents the new action and JARVIS commands

Reason:

- A JARVIS-style assistant needs an action memory, not only a knowledge memory.
- Decisions must be explicit and inspectable instead of hidden in chat history.
- The implementation remains local-first and does not require admin rights, cloud services, or network access.

### Local Learning Eval Runner

The next gap was that ASTRA could generate eval prompts and evaluate supplied
answers, but could not yet run those prompts through its own local language
module.

Implemented:

- Updated `src/commands/learning_command.py`
  - adds `learning run-eval <topic>`
  - uses the injected local language module when it is available
  - sends every learning eval case to the model
  - evaluates returned answers through `LearningManager.evaluate_responses`
  - stores the resulting `eval_report` on the learning subject
  - returns a clear fallback message when no local language module is available
- Updated `src/commands/registry.py`
  - passes the default registry language module into `LearningCommand`
- Updated `tests/test_learning.py`
  - covers successful model-backed eval
  - covers the no-language-module fallback
- Updated `README.md`
  - documents `learning run-eval <topic>`

Reason:

- This makes the proficiency gate executable from chat when a local model is running.
- The command still degrades safely when Ollama or another local language backend is unavailable.

Validation:

- Full project test suite after the action layer and local eval runner:
  - `281 passed`

### Explicit Web Fetch

ASTRA's long-term goals include using the internet when needed. The safe first
step is explicit URL fetching, not autonomous browsing.

Implemented:

- Added `src/utils/web_fetcher.py`
  - fetches only full `http://` and `https://` URLs
  - uses a request timeout and max byte limit
  - extracts readable text from simple HTML
  - rejects local file and other non-web schemes
- Added `src/commands/web_command.py`
  - supports `web fetch <url>` and `fetch url <url>`
  - returns content type, truncation marker, and readable summary text
- Updated `src/commands/registry.py`
  - registers `WebCommand`
  - includes web fetch in `help`
- Added `tests/test_web_command.py`
  - covers HTML extraction, scheme rejection, command output, and error reporting without real network access
- Updated `README.md`
  - documents the explicit web command and its boundaries

Reason:

- This gives ASTRA a verifiable internet entry point while avoiding hidden or uncontrolled browsing.
- It stays dependency-free and testable offline.

Validation:

- Full project test suite after explicit web fetch:
  - `285 passed`

### Speech And Vision Foundation

The README goals include `speak` and `see`. The next practical step was to add
local, explicit, testable foundations for both without pretending that ASTRA has
full scene understanding yet.

Implemented:

- Added `src/speech/speech_manager.py`
  - normalizes text
  - uses Windows SAPI through PowerShell when running on Windows
  - reports a clear unsupported-platform error elsewhere
  - supports dependency injection for tests
- Added `src/commands/speech_command.py`
  - supports `speak <text>` and `say <text>`
- Added `src/vision/image_inspector.py`
  - inspects explicit local image files
  - detects PNG, JPEG, and GIF
  - reports format, dimensions, and file size
  - has no external dependencies
- Added `src/commands/vision_command.py`
  - supports `image inspect <path>` and `see image <path>`
- Updated `src/commands/registry.py`
  - registers speech and vision commands
  - includes them in `help`
- Updated `src/core/brain.py`
  - allows injected speech and vision adapters for tests and future runtime wiring
- Updated `pyproject.toml`
  - includes the new `speech` and `vision` packages
- Added `tests/test_speech_vision.py`
  - covers speech adapter behavior, unsupported platform handling, speech command injection,
    PNG metadata inspection, unsupported image handling, vision command output, and registry dispatch
- Updated `README.md`
  - documents `speak`, `say`, `image inspect`, and `see image`

Reason:

- `speak` and `see` were explicit long-term JARVIS capabilities.
- The implementation gives ASTRA real local command surfaces now, while keeping the limits honest:
  image inspection is metadata-level vision, not a multimodal model.

Validation:

- Full project test suite after speech and vision foundations:
  - `292 passed`

### Programming Assistance Foundation

The README goals include assisting with programming. The next practical
implementation step was a read-only code inspection command that can understand
Python file structure locally.

Implemented:

- Added `src/dev/code_inspector.py`
  - parses Python files with the standard `ast` module
  - reports line count, classes, functions, imports, and TODO/FIXME markers
  - reports syntax errors without crashing ASTRA
- Added `src/commands/code_command.py`
  - supports `code inspect <path>`
- Updated `src/commands/registry.py`
  - registers `CodeCommand`
  - includes it in `help`
- Updated `src/core/brain.py`
  - allows injected code inspector for tests and future runtime wiring
- Updated `pyproject.toml`
  - includes the new `dev` package
- Added `tests/test_code_command.py`
  - covers Python structure inspection, unsupported files, syntax errors, command output, and registry dispatch
- Updated `README.md`
  - documents `code inspect <path>`

Reason:

- This gives ASTRA a concrete programming-assistance surface without granting write access or making autonomous code edits.
- It is intentionally read-only until action permissions and review gates are stronger.

Validation:

- Full project test suite after programming assistance foundation:
  - `297 passed`

### Reminder Automation Foundation

The README goals include automating daily tasks. The next practical layer is a
local reminder queue that ASTRA can inspect from chat and include in the JARVIS
briefing.

Implemented:

- Added `src/automation/reminder_manager.py`
  - stores reminders under `data/automation/reminders.json`
  - supports one-off reminders
  - supports daily recurring reminders
  - reports due reminders using an injectable clock for testability
  - uses atomic temp-file replacement
- Added `src/automation/__init__.py`
  - exposes `ReminderManager`
- Added `src/commands/reminder_command.py`
  - supports `remind me to <thing> at <YYYY-MM-DD HH:MM>`
  - supports `remind me to <thing> at today <HH:MM>`
  - supports `remind me to <thing> at tomorrow <HH:MM>`
  - supports `remind me to <thing> every day at <HH:MM>`
  - supports `reminders`, `reminders due`, `reminders all`, and `reminder done <id or title>`
- Updated `src/commands/jarvis_command.py`
  - includes open reminders, due reminders, and next reminder in `jarvis status`
  - suggests daily reminders from `jarvis improve`
- Updated `src/commands/registry.py`
  - registers `ReminderCommand`
  - shares one reminder manager between reminders and JARVIS status
- Updated `src/core/brain.py`
  - allows injected reminder manager for tests and future runtime wiring
- Updated `pyproject.toml`
  - includes the new `automation` package
- Added `tests/test_reminders.py`
  - covers due parsing, invalid time rejection, persistence, one-off completion,
    daily roll-forward, command behavior, and shared JARVIS status state
- Updated `README.md`
  - documents reminder and daily automation commands

Reason:

- This turns daily task automation into an inspectable local queue.
- It intentionally does not install OS scheduled tasks yet; ASTRA can own the data and surface due work first.

Validation:

- Full project test suite after reminder automation foundation:
  - `304 passed`

### Proficient Learning And Web Sources

The original JARVIS requirement asks for learning a requested subject until the
assistant becomes proficient. The earlier ASTRA learning layer could create a
subject and accept manual source text, but it did not distinguish working-level
learning from proficient-level learning and could not ingest explicit web
sources into the learning subject.

Implemented:

- Updated `src/learning/learning_manager.py`
  - keeps working-level learning at the original four eval cases
  - adds a 13-case proficient eval matrix for `target_level="proficient"`
  - covers five fact cases, five scenario cases, and three boundary cases
  - adds an uncertainty boundary check for unsupported questions
- Updated `src/commands/learning_command.py`
  - adds `learn deeply about <topic>`
  - adds `learn proficient about <topic>`
  - adds `learn source <topic>: <url>`
  - fetches explicit URLs through the existing bounded web fetcher
  - stores web source text as `web:<url>` evidence in the learning subject
- Updated `tests/test_learning.py`
  - covers proficient eval case generation
  - covers deep-learning command behavior
  - covers explicit web-source ingestion without real network access
- Updated `README.md`
  - documents deep/proficient learning and explicit web-source ingestion

Reason:

- Proficiency needs a stronger eval gate than basic learning.
- Explicit web source ingestion lets ASTRA learn from real source material without uncontrolled browsing.

Validation:

- Full project test suite after proficient learning and web-source ingestion:
  - `307 passed`

### Approval-Gated System Actions

The requested JARVIS direction requires more than notes and chat commands: it
needs a safe bridge toward real desktop/system actions. The first implementation
step is an explicit approval queue.

Implemented:

- Added `src/actions/system_action_manager.py`
  - stores system actions under `data/actions/system_actions.json`
  - supports pending, approved, rejected, executed, and failed states
  - requires approval before execution
  - currently supports explicit local `open_path` actions only
  - uses an injectable executor for tests and future platform adapters
- Updated `src/actions/__init__.py`
  - exposes `SystemActionManager` and `SystemActionError`
- Added `src/commands/system_action_command.py`
  - supports `system propose open <path>`
  - supports `system actions`, `system actions all`
  - supports `system approve <id>`, `system reject <id>`, and `system run <id>`
- Updated `src/commands/jarvis_command.py`
  - includes pending and approved system action counts in `jarvis status`
  - suggests `system propose open <path>` from `jarvis improve`
- Updated `src/commands/registry.py`
  - registers `SystemActionCommand`
  - shares one system action manager with JARVIS status
- Updated `src/core/brain.py`
  - allows injected system action manager for tests and future runtime wiring
- Added `tests/test_system_actions.py`
  - covers approval gating, execution through an injected executor, persistence,
    command flow, rejection, and shared JARVIS status state
- Updated `README.md`
  - documents the system action approval workflow

Reason:

- Real desktop action needs explicit approval boundaries.
- Starting with `open_path` gives ASTRA a concrete system action without broad shell execution.

Validation:

- First full run found a test mutability issue:
  - `approve()` returns the same action dictionary later updated by `execute()`
  - test was corrected to assert approval before execution
- Full project test suite after approval-gated system actions:
  - `313 passed`

### Local Model Runtime Commands

JARVIS already had an Ollama client and language module, but there was no
explicit chat command to verify the runtime from inside ASTRA. That made the
Open WebUI/Ollama gap harder to diagnose because model availability was only
visible indirectly through fallback behavior.

Implemented:

- Added `src/commands/model_command.py`
  - supports `model status`
  - supports `model check`
  - supports `model smoke`
  - supports `model ask <prompt>`
  - verifies availability through the injected language module client
  - keeps tests isolated from real network access through stubs
- Updated `src/commands/registry.py`
  - registers `ModelCommand`
  - includes model commands in `help`
- Updated `src/commands/jarvis_command.py`
  - reports local model configured/available state in `jarvis status`
  - suggests `model check` and `model smoke` from `jarvis improve`
- Added `tests/test_model_command.py`
  - covers unconfigured runtime state
  - covers successful and failed availability checks
  - covers direct prompt and smoke prompt behavior
  - covers shared model state in `jarvis status`
- Updated `README.md`
  - documents the local model runtime commands

Reason:

- A JARVIS-style assistant needs a direct operational check for the local model,
  not only an implicit fallback.
- `model smoke` gives a small repeatable runtime proof before running larger
  learning evals.

Validation:

- Targeted model command test suite:
  - `6 passed`
- Full project test suite after local model runtime commands:
  - `319 passed`
- README heading check:
  - no duplicate command sections found

### Structured Experience Memory

ASTRA already saved raw chat text in long memory, but JARVIS needs a more
audit-ready record of what actually happened in each exchange. Raw text alone
does not show which command handled the message, which response belonged to
which prompt, or which session produced the interaction.

Implemented:

- Added `src/experience/experience_manager.py`
  - stores structured exchanges under `data/experience/exchanges.json`
  - records user message, assistant response, command handler, timestamp,
    session id, and source
  - supports recent entries, search, and command-count stats
  - uses the same atomic write pattern as the other local stores
- Added `src/commands/experience_command.py`
  - supports `experience recent`
  - supports `experience recent <limit>`
  - supports `experience search <text>`
  - supports `experience stats`
- Updated `src/commands/base.py`
  - `DispatchResult` now carries an optional `command_name`
- Updated `src/commands/registry.py`
  - attaches the handling command name to dispatch results
  - registers `ExperienceCommand`
- Updated `src/core/brain.py`
  - creates a session id on start
  - records every `receive()` exchange into structured experience memory
  - logs an error but keeps chatting if structured experience persistence fails
- Updated `src/commands/jarvis_command.py`
  - reports structured experience count in `jarvis status`
  - suggests inspecting experience memory when it is empty
- Updated `pyproject.toml`
  - includes the new `experience` package
- Added `tests/test_experience.py`
  - covers persistence, search, stats, command output, Brain integration, and
    shared JARVIS status state
- Updated `README.md`
  - documents the experience memory commands

Reason:

- A JARVIS-style assistant should learn from experience, not only from manually
  saved notes.
- Grouping each user prompt with its assistant response and command handler
  makes later debugging, reflection, and improvement work evidence-based.

Validation:

- Targeted experience and Brain integration tests:
  - `7 passed`
- Full project test suite after structured experience memory:
  - `324 passed`
- README heading check:
  - no duplicate command sections found

### Experience Reflection Loop

Structured experience memory made the exchanges auditable, but JARVIS still
needed a way to turn those records into concrete improvement findings. This
change adds a deterministic reflection loop over recent experiences.

Implemented:

- Added `src/experience/reflection_manager.py`
  - stores reflection reports under `data/experience/reflections.json`
  - detects command failures from error responses
  - detects echo fallback as missing routing or model fallback evidence
  - detects local model runtime issues from model command responses
  - detects shell commands sent to chat
  - records findings with severity, evidence count, recommendation, and task
    title
- Added `src/commands/reflection_command.py`
  - supports `reflect`
  - supports `reflect recent <limit>`
  - supports `reflect tasks`
  - supports `reflections`
  - can create tracked action tasks from reflection findings
- Updated `src/commands/registry.py`
  - registers `ReflectionCommand`
  - shares the same experience and action managers with reflection
- Updated `src/commands/jarvis_command.py`
  - reports reflection count in `jarvis status`
  - suggests `reflect` when structured experiences exist but no reflection has
    been recorded
- Updated `src/core/brain.py`
  - allows injected reflection manager and surfaces reflection load warnings
- Updated `src/experience/__init__.py`
  - exports `ReflectionManager`
- Added `tests/test_reflection.py`
  - covers echo/model issue detection
  - covers reflection persistence
  - covers command formatting
  - covers task creation from reflection findings
  - covers shared reflection count in `jarvis status`
- Updated `README.md`
  - documents the reflection commands

Reason:

- The user asked for a JARVIS that can learn and improve, not just store chat.
- Reflection turns recorded experience into evidence-backed improvement work
  without relying on broad or opaque AI judgment.

Validation:

- Targeted reflection, experience, and JARVIS status tests:
  - `11 passed`
- Full project test suite after experience reflection loop:
  - `329 passed`
- README heading check:
  - no duplicate command sections found

### Learning Promotion To Long Memory

The learning layer could create source-backed subjects, run evals, and mark a
subject as promotion-ready, but it still lacked the final operational step that
turns verified learning into durable memory. This left the JARVIS learning loop
incomplete: a subject could be ready for promotion without being promoted.

Implemented:

- Updated `src/learning/learning_manager.py`
  - adds `promote(subject)`
  - blocks promotion unless the subject has a passing eval report, approved
    review, and `promotion_ready: true`
  - records `status: promoted`
  - records `promoted_at`
  - builds a durable `promotion_note` with summary, concepts, sources, eval
    score, and review state
  - exposes promoted state through `list_subjects()`
- Updated `src/commands/learning_command.py`
  - adds `learning promote <topic>`
  - writes the promotion note into long memory as entry type `learned`
  - avoids duplicate long-memory writes when a subject is already promoted
- Updated `src/commands/jarvis_command.py`
  - reports promoted learning subject count in `jarvis status`
  - suggests `learning promote <subject>` when a verified subject is ready but
    not yet promoted
- Updated `tests/test_learning.py`
  - covers blocked promotion without eval and review
  - covers successful manager-level promotion
  - covers command-level long-memory write and idempotency
- Updated `README.md`
  - documents `learning promote <topic>`

Reason:

- The original JARVIS goal explicitly asks ASTRA to learn a requested subject
  until it is proficient. A subject that only says "promotion-ready" is not
  yet durable knowledge.
- Promotion must be gated, because writing unverified learning into permanent
  memory would make future answers less trustworthy.

Validation:

- Targeted learning and JARVIS status tests:
  - `16 passed`
- Full project test suite after learning promotion:
  - `331 passed`
- README heading check:
  - no duplicate command sections found

### Memory-Aware Local Model Context

ASTRA could already promote verified learning into long memory, but the local
language fallback still received only the raw user message. That meant promoted
knowledge was durable but not actually available to model-backed answers unless
the user manually pasted it back in.

Implemented:

- Added `src/memory/context_builder.py`
  - builds a local model prompt from stable facts, relevant notes, and promoted
    `learned` memory entries
  - returns the original user message unchanged when no context is available
  - labels memory items with bracketed ids so model answers can cite them
  - instructs the model not to invent missing context
- Updated `src/commands/registry.py`
  - passes memory into `CommandRegistry`
  - uses `build_model_prompt()` only for the normal language fallback path
  - keeps explicit commands and direct `model ask` behavior unchanged
- Updated `tests/test_memory.py`
  - covers raw prompt behavior without context
  - covers facts, notes, and learned memory in the generated prompt
- Updated `tests/test_brain.py`
  - covers that the local language module receives memory context through
    `Brain.receive()`
- Updated `README.md`
  - documents memory-aware model fallback behavior

Reason:

- A JARVIS-style assistant should answer with its durable memory, not merely
  store that memory passively.
- Keeping raw-message behavior when no context exists preserves existing simple
  fallback behavior.

Validation:

- Targeted memory context and language fallback tests:
  - `4 passed`
- Full project test suite after memory-aware local model context:
  - `334 passed`
- README heading check:
  - no duplicate command sections found

### JARVIS Capability Self-Audit

ASTRA had many JARVIS layers implemented, but there was no single command that
mapped the original goal to current evidence. That made it too easy to overstate
completion or miss known gaps.

Implemented:

- Updated `src/commands/jarvis_command.py`
  - adds `jarvis capabilities`
  - adds `jarvis audit`
  - reports deterministic `ok`, `partial`, and `gap` status lines
  - covers persistent memory, memory-aware model context, learning, proficiency
    gates, local model runtime, experience memory, reflection, tasks,
    approval-gated system actions, reminders, explicit web fetch, speech
    output, image inspection, code inspection, and transparent logging
  - explicitly keeps known gaps visible: speech-to-text input and autonomous
    open-ended web research are not implemented
- Updated `jarvis improve`
  - now suggests `jarvis capabilities` so improvement work can start from
    evidence rather than intuition
- Added `tests/test_jarvis_command.py`
  - covers direct capability audit output
  - covers available local model reporting
  - covers dispatch through `build_default_registry`
- Updated `README.md`
  - documents `jarvis capabilities` and `jarvis audit`

Reason:

- The active goal is broad: "JARVIS with all functions" plus additional
  improvements. A completion claim needs a requirement-by-requirement audit,
  not just a passing test suite.
- The audit command gives ASTRA a built-in way to show what is implemented,
  what depends on runtime state, and what remains missing.

Validation:

- Targeted JARVIS capability tests:
  - `3 passed`
- Full project test suite after capability audit:
  - `337 passed`

### Bounded Web Research for Learning

ASTRA could fetch one explicit URL and attach it to a learning subject, but it
could not start from a topic and gather candidate web sources. That left the
"learn this subject" workflow dependent on the user manually finding every
source.

Implemented:

- Added `src/research/web_researcher.py`
  - searches the public web through a bounded default search URL
  - falls back to Wikipedia OpenSearch and full-text search when the default
    search endpoint returns no parseable results
  - limits fetched sources to a small configurable count
  - fetches only normalized HTTP/HTTPS pages through the existing web fetcher
  - records failed sources without aborting the whole research run
  - returns source URLs, snippets, readable text, content type, and truncation
    state
- Added `src/commands/research_command.py`
  - adds `research <topic>`
  - adds `web research <topic>`
  - adds `research learn <topic>`
  - adds `research learn proficient <topic>`
  - supports `research learn <topic> with <n> sources`
  - sends fetched source text into the existing proficient learning workflow
- Updated `src/commands/registry.py`
  - registers `ResearchCommand`
  - shares the same `LearningManager` instance with `LearningCommand`
- Updated `src/commands/jarvis_command.py`
  - reports bounded web research as an implemented JARVIS capability
  - suggests `research learn <topic>` when no learning subjects exist
- Updated `pyproject.toml`
  - packages the new `research` module
- Updated `README.md`
  - documents research commands and their relationship to learning gates
- Added `tests/test_research_command.py`
  - covers bounded source fetching
  - covers failed source capture
  - covers command output
  - covers `research learn` creating a proficient subject
  - covers registry dispatch sharing state with learning commands
- Updated `tests/test_jarvis_command.py`
  - expects bounded web research as an implemented capability

Reason:

- The original JARVIS goal asks ASTRA to learn a requested subject efficiently.
  Web-backed source discovery is a practical part of that, but it must remain
  bounded and auditable.
- Research output still enters the existing eval, approval, and promotion
  gates. Fetched web text is not treated as trusted long-term memory until it
  passes those gates.

Validation:

- Targeted research and JARVIS audit tests:
  - `9 passed`
- Live research smoke:
  - `WebResearcher().research("line balancing manufacturing", max_results=1)`
    fetched 1 source through fallback search
- Full project test suite after bounded web research:
  - `343 passed`

### Explicit Speech-to-Text Input

ASTRA could speak text aloud, but it could not accept voice input. That left the
speech layer one-way and kept `jarvis capabilities` reporting speech-to-text as
a missing JARVIS function.

Implemented:

- Updated `src/speech/speech_manager.py`
  - adds `listen_once(seconds=5)`
  - uses Windows `System.Speech.Recognition.SpeechRecognitionEngine`
  - loads dictation grammar for one explicit utterance
  - clamps recognition timeout to 1-30 seconds
  - returns a compact transcript or a clear `SpeechError`
  - adds `status()` with text-to-speech, speech-to-text, and passive listening
    flags
- Updated `src/commands/speech_command.py`
  - adds `listen [seconds]`
  - adds `speech listen [seconds]`
  - adds `voice input [seconds]`
  - adds `speech status`
  - returns `Heard: <transcript>` without automatically executing the transcript
- Updated `src/commands/jarvis_command.py`
  - reports speech-to-text input as an implemented capability when
    `SpeechManager.listen_once()` is present
  - records that passive listening is disabled
- Updated `README.md`
  - documents the new speech input commands
  - removes speech-to-text from the known missing capability list
- Updated `tests/test_speech_vision.py`
  - covers Windows speech recognition runner arguments
  - covers timeout clamping
  - covers unsupported recognition platform behavior
  - covers command-level listening and speech status output
  - covers default registry dispatch for `voice input`
- Updated `tests/test_jarvis_command.py`
  - expects speech-to-text as an implemented JARVIS capability

Reason:

- A JARVIS-style assistant needs voice input as well as voice output.
- The implementation is explicit and bounded so ASTRA does not introduce
  passive microphone capture or background listening without a separate design.

Validation:

- Targeted speech and JARVIS audit tests:
  - `14 passed`
- Live speech status smoke:
  - platform: Windows
  - text-to-speech: true
  - speech-to-text: true
  - passive listening: false
- Full project test suite after explicit speech-to-text input:
  - `347 passed`

### Model-Backed Image Description

ASTRA could inspect image metadata, but it could not ask a local vision model to
describe visible content. That left the vision layer useful for file validation
but not for JARVIS-style visual understanding.

Implemented:

- Updated `src/utils/ollama_client.py`
  - adds `generate_with_images(prompt, image_paths)`
  - base64-encodes explicit local image files
  - sends Ollama `/api/generate` payloads with `images`
  - reuses the existing reasoning-block response cleanup
- Added `src/vision/semantic_vision.py`
  - adds `LocalVisionDescriber`
  - validates image metadata through `ImageInspector`
  - builds a cautious prompt that asks the model to mention uncertainty
  - requires a client with `generate_with_images()`
- Updated `src/commands/vision_command.py`
  - adds `image describe <path> [question]`
  - adds `describe image <path> [question]`
  - adds `vision describe <path> [question]`
  - preserves `image inspect <path>` metadata behavior
- Updated `src/commands/registry.py`
  - passes the local language module client into `VisionCommand`
  - adds optional `vision_describer` injection for tests and future runtime
    wiring
- Updated `src/commands/jarvis_command.py`
  - reports image metadata inspection as implemented
  - reports model-backed image description as runtime-dependent partial until a
    local vision-capable model is verified
- Updated `README.md`
  - documents image description commands and the vision-capable model
    requirement
- Updated tests
  - `tests/test_ollama_client.py` covers image payload generation
  - `tests/test_speech_vision.py` covers `LocalVisionDescriber`, command
    formatting, and registry dispatch
  - `tests/test_jarvis_command.py` covers the updated capability audit

Reason:

- A JARVIS-style assistant needs visual understanding, not only image metadata.
- The implementation stays explicit: ASTRA describes only a user-provided local
  image path and does not scan folders or watch the screen.

Validation:

- Targeted Ollama, vision, and JARVIS audit tests:
  - `27 passed`
- Live vision describe smoke without configured vision model:
  - returned a clear runtime message instead of a traceback:
    `No vision-capable local model is configured. Use a local Ollama model that supports image input.`
- Full project test suite after model-backed image description:
  - `351 passed`

### JARVIS Runtime Self-Check

ASTRA had `jarvis capabilities`, which maps implemented features and known
gaps. That is useful, but it does not prove the current session is ready to use
runtime-dependent layers such as Ollama, speech, and model-backed vision.

Implemented:

- Updated `src/commands/jarvis_command.py`
  - adds `jarvis verify`
  - adds `jarvis self-check`
  - adds `jarvis runtime-check`
  - reports `pass`, `warn`, and `fail` checks for the current session
  - verifies memory API, learning gate API, local model availability,
    model-backed image description readiness, speech runtime, task/decision
    stores, approval-gated system actions, reminders, experience/reflection,
    and the transparent log
  - runs `client.ensure_available()` for the local model when a model module is
    configured
  - keeps model-backed image description as a warning until a real
    vision-capable model/image smoke has been run
- Updated `src/commands/registry.py`
  - shares the same speech adapter between `SpeechCommand` and `JarvisCommand`
    so runtime verification checks the same adapter used by `listen` and
    `speak`
- Updated `README.md`
  - documents `jarvis verify` and `jarvis self-check`
- Updated `tests/test_jarvis_command.py`
  - covers self-check without a configured model
  - covers a passing local model availability check
  - covers dispatch through `build_default_registry`

Reason:

- The requested end state is "fully functional", so ASTRA needs an observable
  runtime readiness check, not only a list of implemented commands.
- Warnings are intentional for optional runtime dependencies. For example,
  model-backed image description cannot be honestly marked fully ready until a
  local vision-capable model has been verified with a real image.

Validation:

- Targeted JARVIS command tests:
  - `6 passed`
- Live `jarvis verify` smoke with default temporary runtime:
  - `pass=8 warn=2 fail=0`
  - warnings were expected for unconfigured local model runtime and
    unconfigured vision-capable image model
- Full project test suite after runtime self-check:
  - `354 passed`

### Separate Vision Model Runtime Configuration

The previous model-backed image description layer could send image payloads to
Ollama, but its runtime wiring was coupled to the normal language fallback
client. That made `jarvis verify` less precise: a text-only local model could
look like an image payload client because the transport supports an `images`
field, even when a dedicated vision model had not been configured.

Implemented:

- Updated `src/config/config.py`
  - adds `use_vision_model`
  - adds `vision_base_url`
  - adds `vision_model`
  - adds `vision_generate_timeout`
- Updated `config.json`
  - documents the new vision runtime keys while keeping `use_vision_model`
    disabled by default
- Updated `src/main.py`
  - creates a separate Ollama-backed `LocalVisionDescriber` only when
    `use_vision_model` is enabled
- Updated `src/core/brain.py`
  - accepts `vision_describer` dependency injection and passes it to the
    default command registry
- Updated `src/commands/registry.py`
  - passes the explicit `vision_describer` to both `VisionCommand` and
    `JarvisCommand` when one is configured
  - avoids treating the language-module fallback describer as a dedicated
    vision model
- Updated `src/commands/jarvis_command.py`
  - reports local vision model configuration in `jarvis status`
  - verifies a dedicated vision client separately from the language module
  - keeps image description as a warning until a real `image describe <path>`
    smoke is run
- Updated `src/commands/export_command.py`
  - includes the new vision config values in exports
- Updated `README.md`
  - documents the separate vision model config and verification boundary

Reason:

- The original JARVIS goal includes "see", but visual understanding should not
  be inferred from a text model being configured.
- Keeping `use_vision_model` disabled by default avoids accidental downloads or
  runtime failures on machines without a local vision-capable model.

Validation so far:

- Targeted config/export/main/Brain/JARVIS tests:
  - `49 passed`
- Targeted JARVIS/registry regression after live smoke found fallback
  misclassification:
  - `9 passed`
- Live `jarvis status` / `jarvis verify` smoke with current `config.json`:
  - language model `llama3.2:1b` is configured but not installed locally
  - `local vision model configured: false`
  - `jarvis verify` reports `pass=8 warn=2 fail=0`
  - image description warning now correctly says the image payload route is
    present through the language model fallback, not through a dedicated vision
    model
- Full project test suite after the fix:
  - `361 passed`

### Direct Vision Runtime Status Command

After adding separate vision configuration, ASTRA still needed a direct command
to inspect that layer without reading the larger `jarvis verify` output.

Implemented:

- Updated `src/vision/semantic_vision.py`
  - stores the source of the image-description client as `vision`, `language`,
    or `none`
- Updated `src/commands/vision_command.py`
  - adds `vision status`
  - adds `vision check`
  - reports configured state, source, model, and base URL
  - verifies availability through `client.ensure_available()` when possible
- Updated `src/main.py`
  - marks the configured dedicated vision runtime as source `vision`
- Updated `README.md`
  - documents `vision status` and `vision check`
- Updated `tests/test_speech_vision.py`
  - covers unconfigured vision runtime
  - covers explicit vision client availability checks
  - covers language fallback source reporting

Reason:

- A separate runtime should have a separate diagnostic command.
- The command makes it visible whether image description is using a dedicated
  vision model or merely the language fallback transport.

Validation so far:

- Targeted speech/vision and JARVIS tests:
  - `25 passed`
- Live `vision status` / `vision check` smoke with current `config.json`:
  - status reports `configured: true`, `source: language`, model
    `llama3.2:1b`
  - check correctly reports that `llama3.2:1b` is not installed locally
- Full project test suite after direct vision runtime commands:
  - `364 passed`

### Local Model Runtime Self-Healing

Live runtime verification showed that ASTRA was configured for
`llama3.2:1b`, but the local Ollama installation only had `llama3.2:3b`
available. That left the language fallback implemented but not usable in the
current session.

Implemented:

- Updated `src/utils/ollama_client.py`
  - adds `list_models()` for `/api/tags`
  - returns sorted model metadata including parameter size and capabilities
- Updated `src/commands/model_command.py`
  - adds `model list`
  - adds `model use <installed-model-name>`
  - validates the requested model against installed Ollama models
  - updates the runtime client model
  - persists the selected model back to `config.json`
- Updated `src/commands/registry.py`
  - passes `config` into `ModelCommand` so model switches can be persisted
- Updated `config.json`
  - changes `language_model` from unavailable `llama3.2:1b` to installed
    `llama3.2:3b`
- Updated `src/commands/vision_command.py`
  - clarifies that a language fallback client is not a dedicated vision model
    when running `vision check`
- Updated `README.md`
  - documents `model list` and `model use`
- Updated tests
  - `tests/test_model_command.py` covers model listing, switching, persistence,
    and rejection of uninstalled models
  - `tests/test_ollama_client.py` covers model-list parsing
  - `tests/test_speech_vision.py` covers the clearer language-fallback vision
    check wording

Reason:

- A JARVIS-style assistant should be able to diagnose and repair a common local
  model mismatch from chat, not require manual editing of `config.json`.
- Runtime availability is part of "fully functional"; using an installed local
  model moves ASTRA from implemented-but-unavailable to actually usable for
  model-backed answers.

Validation so far:

- Local Ollama inventory:
  - installed model: `llama3.2:3b`
- Targeted model/Ollama/vision/JARVIS tests:
  - `45 passed`
- Live runtime smoke with current `config.json`:
  - `model list` marks `llama3.2:3b` as current
  - `model check` reports `Local model available: llama3.2:3b`
  - `model smoke` returned a local model response (`AstrA-OK`)
  - `vision check` correctly reports a language fallback client, not a
    dedicated vision model
  - `jarvis verify` reports `pass=9 warn=1 fail=0`
- Full project test suite after local model runtime self-healing:
  - `368 passed`

### Ollama Runtime Toggle And Lower-HW Model Recommendation

The local language fallback could be inspected and switched between installed
models, but it still required manual `config.json` edits to turn Ollama use on
or off. The current configured model, `llama3.2:3b`, also remains the largest
runtime cost on weak machines.

Implemented:

- Updated `src/commands/model_command.py`
  - adds `model on` / `model enable`
  - adds `model off` / `model disable`
  - adds `ollama on` / `ollama enable`
  - adds `ollama off` / `ollama disable`
  - persists `use_language_fallback` changes to `config.json`
  - stops the current session's language module when disabling Ollama fallback
  - verifies the current language module when enabling fallback in a session
  - asks for an ASTRA restart when enabling fallback but no language module was
    created for the current session
  - adds `model recommend-light`
  - recommends `gemma3:1b` as the lower-HW text model candidate
  - keeps `llama3.2:1b` visible as the same-family option, but notes that it is
    not quite half the published size of `llama3.2:3b`
- Updated `README.md`
  - documents the new on/off commands and the lighter model workflow
- Updated `tests/test_model_command.py`
  - covers disabling fallback, enabling fallback, restart-required behavior,
    and the lightweight recommendation text

Reason:

- The user should be able to turn local Ollama fallback on or off from ASTRA
  chat instead of hand-editing JSON.
- ASTRA should not switch `config.json` directly to a model that is not proven
  installed locally. The safer flow is: show the recommendation, install it
  outside ASTRA, then run `model use gemma3:1b`.
- `gemma3:1b` is the practical lower-HW recommendation because the official
  Ollama listing puts it below half the size of the currently configured
  `llama3.2:3b` model. `llama3.2:1b` remains a conservative same-family
  fallback if behavior compatibility matters more than hitting the 1/2 target.

Validation:

- Targeted model command tests:
  - `13 passed`
- Full project test suite after the runtime toggle and recommendation:
  - `380 passed`
- Live command smoke with current `config.json`:
  - `model recommend-light` reports `gemma3:1b`, install command
    `ollama pull gemma3:1b`, and switch command `model use gemma3:1b`
- Current `config.json` was intentionally left on installed model
  `llama3.2:3b` until the lighter model is actually installed locally.
