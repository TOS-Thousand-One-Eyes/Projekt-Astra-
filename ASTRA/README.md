# ASTRA

Astra is my long-term AI project.

## Goal

Build a personal AI assistant that can gradually evolve into a modular, local-first AI platform.

Core goals:

- speak
- see
- use the internet (when needed)
- learn from experience
- assist with programming
- automate daily tasks
- become my second brain

## Setup

```
pip install -e ".[dev]"
astra
```

## Learning commands

ASTRA now has a local-first learning workflow:

```
learn about <topic>
learn deeply about <topic>
nauč se <téma>
teach <topic>: <source text>
learn source <topic>: <url>
learning status
learning status <topic>
learning eval <topic>
learning run-eval <topic>
learning approve <topic>
learning promote <topic>
```

Learning subjects are stored in `data/learning` and are not promotion-ready until
they have both review approval and a passing eval report.
`learn deeply about <topic>` creates a proficient-level subject with a broader
13-case eval matrix. `learn source <topic>: <url>` fetches an explicit web source
and adds its readable text to the subject.
`learning run-eval <topic>` uses the local language module when it is available;
without a running local model, ASTRA keeps the eval prompts available for manual
answer collection. `learning promote <topic>` is the final gate: it only writes
an approved, eval-passing subject into long memory as a `learned` entry.

## Research commands

ASTRA can run bounded web research for source-backed learning:

```
research <topic>
web research <topic>
research learn <topic>
research learn proficient <topic>
research learn <topic> with <n> sources
```

`research <topic>` searches for a small number of public web candidates, fetches
readable text from HTTP/HTTPS pages, and prints source URLs plus short snippets.
`research learn <topic>` adds fetched sources directly into a proficient
learning subject so the normal eval, approval, and promotion gates still apply.

## Model runtime commands

ASTRA can explicitly inspect and verify the local language model runtime:

```
model status
model list
model use <installed-model-name>
model check
model smoke
model ask <prompt>
```

`model status` reports the configured model state without making a network call.
`model list` shows installed Ollama models, `model use <installed-model-name>`
switches the runtime client and persists the chosen model to `config.json`,
`model check` verifies the configured local model through the language module,
`model smoke` asks for a minimal response, and `model ask <prompt>` sends a
direct prompt to the local model after the same availability check.
When the local language module handles normal chat fallback, ASTRA now builds a
memory-aware prompt from relevant facts, notes, and promoted `learned` entries.
If no useful context exists, the original message is sent unchanged.

Vision-capable image description is configured separately from normal language
fallback. Keep it disabled until an Ollama vision model is installed locally:

```json
{
  "use_vision_model": true,
  "vision_base_url": "http://localhost:11434",
  "vision_model": "llava:latest",
  "vision_generate_timeout": 240
}
```

`jarvis verify` checks this separate vision client when configured. Because
Ollama model metadata does not prove image capability by itself, ASTRA still
requires a real `image describe <path>` smoke before claiming visual
understanding is fully ready.

## Experience memory commands

ASTRA records structured user/assistant exchanges in `data/experience`:

```
experience recent
experience recent <limit>
experience search <text>
experience stats
```

This is separate from free-form long memory. Each exchange keeps the user
message, assistant response, command handler, timestamp, and session id so
JARVIS can inspect what actually happened and use it as evidence for later
reflection or improvement work.

## Reflection commands

ASTRA can turn recent structured experience into improvement findings:

```
reflect
reflect recent <limit>
reflect tasks
reflections
```

`reflect` analyzes recent structured exchanges for concrete signals such as
command failures, echo fallback, model runtime problems, and shell commands sent
to chat. `reflect tasks` records the same reflection and creates tracked action
items from the findings.

## Action and JARVIS commands

ASTRA can also track local tasks, plans, and decisions:

```
task <title> [priority high|normal|low] [due YYYY-MM-DD]
plan <goal>
tasks
tasks all
tasks done
done <task id or title>
decide <decision>: <reason>
decisions
jarvis status
jarvis improve
jarvis capabilities
jarvis audit
jarvis verify
jarvis self-check
briefing
```

Action data is stored in `data/actions`. `jarvis status` combines memory,
learning, and open tasks into one operational briefing. `jarvis capabilities`
prints a deterministic capability audit with `ok`, `partial`, and `gap`
statuses for the implemented JARVIS layers, including memory, learning,
proficiency gating, model runtime, actions, reminders, speech, vision, web,
code inspection, and known partial capabilities such as model-backed image
description requiring a vision-capable local model. `jarvis verify` runs a
runtime self-check for the current session and reports `pass`, `warn`, and
`fail` status for core JARVIS layers.

## System action commands

ASTRA can queue explicit desktop actions behind an approval gate:

```
system propose open <path>
system actions
system actions all
system approve <id>
system reject <id>
system run <id>
```

System actions are stored in `data/actions/system_actions.json`. Nothing is
executed until it has been approved and then explicitly run.

## Reminder and automation commands

ASTRA can track one-off and daily reminders:

```
remind me to <thing> at <YYYY-MM-DD HH:MM>
remind me to <thing> at <YYYY-MM-DD>
remind me to <thing> at today <HH:MM>
remind me to <thing> at tomorrow <HH:MM>
remind me to <thing> every day at <HH:MM>
reminders
reminders due
reminders all
reminder done <id or title>
```

Reminder data is stored in `data/automation`. Daily reminders roll forward to
the next due time when completed.

## Web command

ASTRA has an explicit, bounded web fetch command:

```
web fetch <url>
fetch url <url>
```

Only full `http://` and `https://` URLs are accepted. Fetched content is trimmed
to a safe local summary; ASTRA does not browse automatically.

## Speech and vision commands

ASTRA can use a local speech adapter and inspect explicit local image files:

```
speak <text>
say <text>
listen [seconds]
speech listen [seconds]
voice input [seconds]
speech status
image inspect <path>
see image <path>
vision status
vision check
image describe <path> [question]
describe image <path> [question]
vision describe <path> [question]
```

Speech currently uses Windows SAPI and System.Speech when available. Listening
is explicit, bounded to 1-30 seconds, and does not enable passive background
capture. Image inspection supports PNG, JPEG, and GIF metadata without external
dependencies. `image describe` sends an explicit local image to the separately
configured Ollama vision client when `use_vision_model` is enabled, or falls
back to the language module client if no dedicated vision client is injected.
It requires a vision-capable local model. `vision status` reports whether the
image-description client is configured and whether it came from the dedicated
vision runtime or the language fallback. `vision check` verifies model
availability through the configured client without sending an image.

## Programming command

ASTRA can inspect Python source files locally:

```
code inspect <path>
```

The command reports line count, classes, functions, imports, and TODO/FIXME
markers. It is read-only.

## Principles

- Offline First
- Desktop First
- Modular Architecture
- User Ownership

## Vision

Astra is designed to be a long-term companion that grows together with its owner.

It is built around modularity, local execution and user ownership rather than dependence on a single AI provider.

---

Project started: 2026-07-01
