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