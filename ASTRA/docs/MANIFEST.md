ASTRA - Developed by Erik Nasticky 06.01.2004, started 01.07.2026

It is my personal project about local AI.. system.. or maybe agent idk yet., I am bored of GPT, Claude and other models available having worse short term memory than me when I drink my ass off.
So I decided to make something I never did, something from scratch while learning to code along the journey.


# GOALS
- Fully offilne
- portable integration

# DEVELOPMENT RULES

These are permanent and apply to every future change, not just the current one:

- Offline First
- Desktop First
- Modular Architecture
- User Ownership
- Pure Python unless explicitly approved
- No LangChain
- No LangGraph
- No external AI frameworks before v0.1
- Do not overengineer
- Keep every commit small
- One commit = one capability
- Preserve backwards compatibility whenever possible
- Do not break existing tests

# RELEASE CHECKLIST

When bumping the version:

- Update `[project] version` in `pyproject.toml`
- Update `"version"` in `config.json`
- Update `Version:` in `docs/PROJECT_STATE.md`
- Add a new dated section to `docs/CHANGELOG.md`

`config.json` is the only version value Astra reads at runtime (see
`src/config/config.py`) — `pyproject.toml`'s version is the packaging/
release-tag source and isn't read by the app. They're synced by hand,
not by code. There's no third Python-level copy to keep in sync anymore:
`Config.DEFAULTS` no longer hardcodes a version literal.

# HEALTH CHECK CHECKLIST

Run this periodically — not just at release time:

- `python -m pytest` — full suite must be green
- `git status` — nothing uncommitted or unpushed lingering
- Version consistency: `pyproject.toml`, `config.json`, and
  `docs/PROJECT_STATE.md`'s `Version:` line all match
- Dead code sweep: for each candidate method, grep every call site
  across `src/` AND `tests/`. A method with zero callers anywhere
  outside its own dedicated unit test is dead — delete it and that
  test, then rerun the full suite. Don't delete something just because
  it looks unused at a glance: check whether it serves a distinct
  purpose a caller actually relies on (e.g. `Brain.process()` looks
  like `receive()`'s poor cousin, but it deliberately skips the
  `is_running` gate — its one test needs exactly that, so it stays)
- `docs/suggestions.md` vs `docs/ROADMAP.md`: confirm suggestions.md's
  open items are still accurate, and pull forward any newly-relevant
  near-term roadmap milestones as concrete, small suggestions
- `docs/PROJECT_STATE.md`'s documented file tree vs. the real
  `src/`/`tests/` layout (`find src tests -name "*.py"`) — catch doc
  drift before it compounds
- GitHub Actions: check the Actions tab manually if `gh` CLI isn't
  available in the current shell (a fresh install needs a new
  terminal/session before it's on `PATH`)

# PERMISSION CONVENTION

Any future action that touches the network, or writes files outside
`data/`, must get its own `config.json` boolean flag before it ships —
not retrofitted after.

- Default the flag to the safe/conservative choice for that specific
  action. Read-only, low-risk things (like `check_for_updates`) can
  reasonably default `true`. Anything higher-risk — a future local-LLM
  network call, or writing files outside `data/` — should default
  `false` until proven safe.
- Name the flag after the capability/action it gates, not the
  underlying mechanism (`check_for_updates`, not `use_urllib`).
- Wiring pattern: add the key to `Config.DEFAULTS` (`Config` picks it
  up automatically like every other setting), then gate the feature's
  construction/call site on it. Existing example: `Config.DEFAULTS`
  has `"check_for_updates": True`, and `main.py` only constructs
  `UpdateChecker` — the only network call anywhere in the codebase —
  with `UpdateChecker(config.version, logger) if config.check_for_updates
  else None`.

This is a lightweight, docs-only convention, not the full permission/
approval system planned for v0.1.2 in `docs/ROADMAP.md` (every action
has clear confirmation, approval rules for sensitive operations — a
much larger scoped feature). It exists so that when the local-LLM/
internet features already planned in `docs/suggestions.md` arrive,
there's a designed convention to build against instead of retrofitting
one under time pressure.

# OBSERVABLE FALLBACKS

Falling back to a safe default instead of crashing is good. Falling
back *silently* is not — it's a different bug wearing a disguise.
Erik caught this directly: a real run showed `Astra v0.0.0-unknown is
starting...` with nothing else explaining why, because an earlier
fallback fix only made things not-crash, not made things visible.

- Every catch-and-recover path must be observable, not just survivable.
  If a fallback triggers (a corrupt file, missing config, a write that
  failed), log it — at `WARNING` or higher, because it means something
  the user can actually go fix (a bad `config.json`, a corrupted memory
  file, a filesystem problem) is happening right now, not a routine
  status update.
- If the object hitting the problem doesn't have a `logger` yet (e.g.
  `Config`, constructed in `main.py` before `Logger` exists), don't skip
  the warning — record it on the object itself (e.g. `self.load_warnings`
  on `Config`, `self.load_warning` on `LongMemory`/`Facts`) so the next
  thing downstream that *does* have a logger surfaces it. `Brain.start()`
  is that place today: it already logs "Config loaded from..." and
  "Memory loaded: N entries..." — any warnings ride right alongside.
- "It didn't crash" is not the same as "it's fine." A safe default that
  quietly masks a real problem (a version that silently becomes
  "unknown", a memory file that silently resets to empty, a log file
  that silently stops being written) is worse than a loud failure,
  because nobody notices until much later, if ever.
- When fixing a bug, verify the fix is *actually visible* when it
  triggers — a test that only checks "didn't raise" isn't enough; check
  that a warning was actually logged, at a level a user would see.