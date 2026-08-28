# Pending CHANGELOG entry — v0.0.22

Status: **`DEV-need-check` review candidate; not released**

## Persistent profile identity

- Moved the default Erik/Petr identity and personal runtime root outside the
  source checkout to the operating system's stable user-data directory.
- Added recoverable migration of the old checkout-local PIN records and profile
  data without deleting or overwriting the legacy originals.
- Added an explicit `ASTRA_DATA_DIR` override for portable and test installs.
- Serialized identity updates across threads, manager instances, and local
  processes; every mutation reloads the latest store before writing.
- Fixed the PIN-change race where a stale manager could verify an old PIN and
  overwrite a PIN that another runtime had already changed.

## Per-profile update briefing

- Added independent `last_seen_version` state for Erik and Petr.
- CLI and GUI now show the concrete current-version changelog once per profile
  after an update, even when diagnostic INFO logs are filtered.
- A version is marked as seen only after its briefing is successfully displayed.
- Release-note parsing is bounded, excludes verification-only sections, and
  rejects malformed version identifiers.

## Accurate Slack changelog

- The GitHub workflow now checks out full history and derives changed files from
  the actual before/after Git diff instead of relying on missing push metadata.
- Versioned release notes no longer hide commit and changed-file details.
- Added safe handling for new branches, invalid revisions, hostile Slack link
  delimiters, mention injection, secrets, and malformed Unicode.
- The changelog remains deterministic and token-free.

## Reliability and security debugging

- Closed HTTP error response streams in the language module, web fetcher,
  researcher, Ollama client, and update checker.
- Tightened config and update version parsing so non-numeric versions cannot be
  treated as newer releases.
- Passed Windows text-to-speech content over process standard input so spoken
  text cannot be interpreted as PowerShell code.
- Corrected stale documentation about the configured `gemma3:4b` model and the
  already-pushed v0.0.21 review commit.

## Verification

- Added regression coverage for stable data paths, legacy identity migration,
  per-profile version state, briefing delivery order, stale PIN writers, Git
  diff changelogs, Slack rendering and URL safety, HTTP cleanup, malformed
  versions, Unicode payloads, and PowerShell argument isolation.
- Full deterministic suite: **529 passed** with warnings treated as errors and
  **529 passed** again with a fixed hash seed.

## Manual checks still required

- From an existing 0.0.21 checkout whose `ASTRA/data` is retained, confirm the
  existing Erik and Petr PINs migrate and still authenticate.
- From a clean copy with no old identity file, confirm one final PIN setup writes
  to the stable user-data directory and survives a second source-folder update.
- Confirm the first 0.0.22 login shows this briefing once for each profile.
- Confirm the next review push posts version, release bullets, commits, and a
  non-zero changed-file list to Slack `#Changelog`.
