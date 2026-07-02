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