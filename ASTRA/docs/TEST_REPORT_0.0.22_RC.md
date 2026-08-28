# ASTRA v0.0.22 RC — Test Report

Base commit: `8ad04cd`

Candidate status: local review only; not committed or pushed

## Automated verification

- Full deterministic pytest suite with warnings treated as errors: **529 passed**.
- Fixed-hash-seed full suite (`PYTHONHASHSEED=17`, warnings as errors):
  **529 passed**.
- Python compilation of `src`, `tests`, and `scripts`: PASS.
- `git diff --check`: PASS.
- Wheel and source-distribution build for `astra 0.0.22`: PASS.
- 0.0.21 checkout-local PIN/data to stable-root migration integration: PASS.
- One-time per-profile 0.0.22 briefing integration: PASS.
- Token-free Slack payload dry run with real working-tree paths: PASS.

## External/manual limits

- Windows GUI, PowerShell text-to-speech, and real `%LOCALAPPDATA%` behavior
  require the user's Windows review.
- A real Slack post is intentionally deferred until the user accepts the diff
  and authorizes a push.
- No real webhook, PIN, profile data, or production secret is included in this
  candidate or its tests.
