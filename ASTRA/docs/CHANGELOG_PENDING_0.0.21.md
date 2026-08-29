# Pending CHANGELOG entry — v0.0.21

Status: **`DEV-need-check` review candidate; not released**

## Learning Health Guard

- Added `self learning health`, a read-only integrity report for candidates,
  active guidance, correction traces, stale review items, and prompt capacity.
- Active guidance is now checked before prompt injection. Records linked to a
  missing, rejected, or mismatched candidate are blocked instead of trusted.
- Added visibility through the normal `diagnostics` command.
- Fixed re-adding an explicitly rejected preference so reactivated guidance is
  linked to the new approved candidate rather than the rejected historical ID.

## Reliability and security debugging

- Fixed reproducible concurrent-write failures in long memory and facts by
  serializing mutations and using process/thread/UUID-unique temporary files.
- Returned copies from long-memory/fact reads so callers cannot accidentally
  mutate persistent in-memory state without a save.
- Closed bounded Wikipedia research responses after every read.
- Rejected corrupted PIN records with an excessive PBKDF2 iteration count before
  authentication can be forced into an unreasonable local computation.
- Removed the stale nested `ASTRA/.github/workflows/tests.yml`; GitHub workflow
  files remain only at repository root.
- Fixed the default `export` location so Erik and Petr no longer write personal
  memory exports into one shared directory.

## Verified profile backups

- Added `backup create [label]`, `backup list`, and `backup verify <file|latest>`.
- Backups contain only the active profile's persistent memory, learning,
  experience, action, and reminder stores.
- Every ZIP includes a manifest with per-file sizes and SHA-256 hashes and is
  verified before it is accepted.
- Backup creation and verification reject unsafe paths, symlinks, temporary
  files, duplicate archive entries, and profiles above the 128 MiB safety limit.
- Restore remains deliberately manual so a chat command cannot overwrite live
  profile data.

## Versioned Slack changelog

- Slack messages now lead with `ASTRA v<version> changelog` and concrete feature
  and fix bullets from the matching versioned Markdown changelog.
- Commit, branch, changed-file, component, comparison-link, secret-redaction,
  and mention-injection protections remain in place without AI token use.

## Verification

- Added regression coverage for integrity gating, stale candidates, malformed
  traces, preference reactivation, concurrent memory writes, PIN work-factor
  bounds, diagnostics integration, research response cleanup, profile backups,
  export isolation, and versioned Slack rendering.
- Full deterministic suite: **492 passed** with warnings treated as errors, then
  **492 passed** again with a fixed hash seed.
