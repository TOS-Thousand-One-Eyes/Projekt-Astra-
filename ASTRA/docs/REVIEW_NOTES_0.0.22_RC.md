# ASTRA v0.0.22 RC — Review Notes

Base: `DEV-need-check` commit `8ad04cd` (v0.0.21)

Status: local review only; not committed or pushed

Hearing is intentionally excluded from this candidate at the user's request.

## What to verify on Windows

1. Keep the existing 0.0.21 `ASTRA/data` directory in place and apply this
   candidate over that checkout.
2. Start CLI or GUI and log in with the existing Erik/Petr PIN. Do not create a
   replacement PIN if the old identity file is still present.
3. Run `identity storage`. The root should be `%LOCALAPPDATA%\Astra`, and the
   active profile should end in `users\erik` or `users\petr`.
4. Confirm the 0.0.22 "What's new" message appears once for Erik. Restart and
   confirm it does not repeat. Repeat independently for Petr.
5. Create a harmless fact for one profile, restart from the review folder, and
   confirm the same PIN and fact survive.
6. Test **Lock / switch** and **Change PIN** once. Confirm the other profile is
   unaffected.
7. Run `python -m pytest -q -W error` from the `ASTRA` directory.

If `%LOCALAPPDATA%\Astra` already contains a new test identity, automatic
migration correctly refuses to overwrite it with an older checkout. Move that
test directory aside (do not delete it) before testing the first 0.0.21 migration.

## Slack gate

The formatter has a local dry-run pass, but the real Slack `#Changelog` message
can only be verified after an approved push triggers GitHub Actions. It should
contain `ASTRA v0.0.22 changelog`, concrete release bullets, commit details, and
a non-zero changed-file count.

Do not commit or push until these Windows checks are accepted.
