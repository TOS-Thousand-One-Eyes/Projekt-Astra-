# ASTRA v0.0.20 RC — Test Report

Status: **review candidate; not pushed**

Base branch: `DEV-need-check`

Base commit audited: `a2203c1`

Runtime/package/config version: `0.0.20`

## Automated verification

- Full deterministic repository suite: **471/471 PASS**.
- Production and test Python compilation: **PASS**.
- Python AST parsing and duplicate literal dictionary-key audit: **PASS**.
- `config.json` parse and runtime/package version synchronization: **PASS**.
- Installed dependency consistency (`pip check`): **PASS**.
- Setuptools package manifest includes `identity`: **PASS**.
- Production Slack webhook-secret scan: **no hardcoded webhook found**.
- Repository-root GitHub test and Slack workflows: **present**.
- `git diff --check`: **PASS**.

## Identity coverage

- Default Erik/Petr profiles and case-insensitive resolution.
- First PIN setup, validation, independent salts/hashes, authentication failure,
  PIN change, and fail-closed corrupt-store handling.
- Separate per-profile memory, learning, self-learning, experience, tasks,
  system actions, reminders, reflections, and optional logs.
- Recoverable/idempotent pre-profile migration to Erik without deletion.
- Active actor ID in experience records and the local-model context.
- Identity status/switch safety messages and profile-aware greetings.
- Inactivity lock decision boundaries and busy-runtime suppression.

## Conversation Learning Inbox coverage

- Valid local-model JSON queues preference and memory-note candidates.
- Suggested candidates stay pending in `auto` mode.
- Approved memory notes enter personal note memory.
- Invalid model JSON queues nothing.
- Rejected candidates are not requeued by later scans.
- No real Ollama, web research, Slack, or GitHub write is used by tests.

## Remaining live Windows checks

Tkinter login/lock dialogs, real PIN entry, real Ollama scan quality, Windows
screen capture, and the first Slack delivery require the user's machine. Follow
`docs/REVIEW_NOTES_0.0.20_RC.md` before approving a push.
