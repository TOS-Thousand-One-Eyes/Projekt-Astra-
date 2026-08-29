# Pending CHANGELOG entry — v0.0.22

Status: **`DEV-need-check` review candidate; not released**

## Update-safe profile identity

- Moved the default private data root out of the replaceable source checkout to
  the operating system's per-user application-data directory. On Windows this
  is `%LOCALAPPDATA%\ASTRA`; `ASTRA_DATA_DIR` remains an explicit override.
- Existing PIN hashes and personal profile stores under the old `ASTRA/data`
  location are copied forward without deleting or weakening the originals.
- Erik and Petr keep independent salted PBKDF2 PIN records. A configured PIN is
  reloaded on every process start and cannot be silently re-created or replaced.
- Added per-profile `last_seen_version` and `last_seen_at` metadata beside the
  profile's PIN record. The PIN hash itself is unchanged when version state is
  updated.
- After a successful login on a newer installed version, ASTRA now displays a
  deterministic summary of every available versioned changelog crossed since
  that profile was last seen. The same version is not announced again.
- Downgrading to an older checkout does not roll back the profile's recorded
  version. Missing or invalid release notes do not block authentication.
- CLI and Tkinter GUI use the same Brain startup path, and the update notice is
  emitted through the unfiltered chat channel even at `ERROR` log level.

## Identity persistence hardening

- Identity writes now reload the latest on-disk payload before changing one
  profile, preventing two manager instances from overwriting each other's PIN
  or version updates with stale cached state.
- Added an operating-system file lock around profile mutations so concurrent
  CLI and GUI processes serialize read/modify/write operations.
- Legacy profile-tree migration preserves both Erik and Petr data, skips
  symlinks, never overwrites a durable destination file, and retains the source
  as a recoverable copy.
- `identity status` and `identity profiles` now expose each profile's recorded
  last-seen version without ever accepting or revealing a PIN in chat.

## Runtime debugging fixes

- Closed the `urllib.error.HTTPError` response owned by a failed Ollama startup
  check before translating it to `ConnectionError`. Python 3.14 previously
  reported this production error path as a leaked resource under `-W error`.

## Slack changelog correctness and safety

- GitHub Actions now checks out full history and obtains changed paths from a
  local, argument-safe `git diff`; Actions push payloads intentionally omit the
  per-commit `added`, `modified`, and `removed` arrays.
- Versioned release notes no longer replace commit and file details. Slack gets
  both the human changelog and bounded Git metadata.
- File collection is independent of the 12-commit preview limit, component
  summaries are escaped and length-bounded, and crafted paths cannot create
  Slack channel mentions.
- Markdown cleanup now preserves technical identifiers such as
  `last_seen_version`.

## Verification

- Confirmed the pre-change checkout had no `ASTRA/data/identity/profiles.json`;
  the old source-relative default therefore reproduced first-login setup in a
  fresh checkout.
- Created an isolated `.venv` and installed the editable `.[dev]` dependency
  set for deterministic local verification.
- Baseline full suite with Python 3.14 and warnings as errors reproduced one
  failure: **491 passed, 1 failed** (`HTTPError` resource leak).
- After the first identity, briefing, Slack, and resource fixes: **520 passed**
  with warnings treated as errors.
- Parsed all changed Python files successfully and kept `config.json` and
  `pyproject.toml` synchronized at `0.0.22`.
- Confirmed the prior v0.0.21 GitHub workflow run `33176947047` succeeded and
  its Slack message reached `#changelog`; that real message exposed the
  incorrect zero-file count fixed in this version.

## Manual checks still required

- Log in as Erik and Petr on the target Windows desktop, restart ASTRA, and
  confirm neither profile is asked to create its PIN again.
- If an old `ASTRA/data` directory exists on that machine, confirm its hashes
  and profile files are copied to `%LOCALAPPDATA%\ASTRA` and the source remains.
- Push the final v0.0.22 commit, wait for both GitHub workflows, then verify the
  exact v0.0.22 message and non-zero changed-file count in Slack `#changelog`.
