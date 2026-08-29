# ASTRA v0.0.21 RC — Test Report

Date: 2026-08-28

Branch: `DEV-need-check`

Remote base: `9834f15` (`ID, Lock a selflearn fixed`)

Runtime/package/config version: `0.0.21`

## Automated verification

- Editable package build/install with `--no-deps`: PASS (`astra 0.0.21`).
- Full suite with Python warnings treated as errors: **492 passed**.
- Full suite repeated with `PYTHONHASHSEED=937`: **492 passed**.
- Python bytecode compilation for `src`, `tests`, and `scripts`: PASS.
- Installed dependency consistency (`pip check`): PASS.
- JSON/config version check: PASS.
- `git diff --check`: PASS.
- Production-source scan for an assigned Slack webhook or common API-key shape:
  PASS; no assigned secret found.

## New regression coverage

- Clean and damaged self-learning store health reports.
- Runtime blocking of guidance linked to a rejected/missing candidate.
- Stale pending candidate warning and malformed correction-trace detection.
- Newest usable duplicate-guidance selection.
- Re-adding a rejected preference relinks guidance to the replacement candidate.
- `diagnostics` integration for learning-health findings.
- Concurrent long-memory and fact writes persist all 16 test entries without a
  temporary-file collision or leftover file.
- Excessive PBKDF2 work factors fail closed at identity-store load.
- Wikipedia research responses close after bounded reads.
- Versioned Slack blocks contain the current ASTRA version and concrete
  changelog sections without losing secret/mention protections.
- Verified per-profile ZIP backup creation, listing, hash validation, unsafe-path
  rejection, and Erik/Petr isolation.
- Default JSON exports stay inside the active profile directory.

## Existing pushed workflow verification

GitHub Actions for pushed commit `9834f15` completed successfully:

- Tests: Python 3.10, 3.11, 3.12, 3.13, and 3.14 all succeeded.
- Slack changelog: `Post token-free changelog` succeeded; the missing-secret
  fallback step was skipped.

These results verify v0.0.20 on GitHub. At report generation time, v0.0.21 did
not yet have a GitHub Actions result; its target push is `DEV-need-check`.

## Manual checks still required

- Windows GUI login, Lock/switch, inactivity lock, and separate Erik/Petr data.
- Real Ollama `model check` and `vision check`.
- `image describe` and `eyes once` quality/privacy on the target screen.
- One Slack `#Changelog` message after the eventual v0.0.21 push.
- User review of `self learning health`, guidance, and pending candidates using
  real profile data.
- `backup create`, `backup list`, and `backup verify latest` with real profile
  data; keep the generated ZIP private.
