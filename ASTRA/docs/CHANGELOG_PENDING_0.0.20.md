# Pending CHANGELOG entry — v0.0.20

Status: **review only; not pushed or released**

## Local identity profiles

- Added explicit profiles `Erik` (`erik`) and `Petr` (`petr`).
- Added first-login PIN setup, salted PBKDF2-SHA256 verification, and PIN change.
- Added fully isolated personal runtime stores under `data/users/<user_id>`.
- Added recoverable one-time migration of pre-profile data to Erik.
- Added active actor IDs to structured experience and model context.
- Added `who am i`, `identity status`, and `identity profiles` commands.
- Added GUI profile display, Lock/switch, visible-chat clearing, and a configurable
  15-minute inactivity lock that stops Brain and Eyes.

## Conversation Learning Inbox

- Added `self learning scan` for bounded local-model review of recent conversation.
- Scan output is limited to preferences, corrections, and durable personal/project
  memory notes.
- All model-suggested candidates remain pending even in `auto` mode.
- Approved memory-note candidates enter only the active profile's personal notes.
- The scan treats transcript content as untrusted data and excludes secrets,
  transient UI state, one-time requests, and assistant-only claims by contract.
- The scan does not browse the web or modify local model weights.

## Verification

- Added identity authentication, isolation, migration, prompt, command, and
  fail-closed corruption tests.
- Added conversation scan, review gating, memory approval, and invalid-output tests.
- Full deterministic suite: **471 passed** before final documentation/package checks.
