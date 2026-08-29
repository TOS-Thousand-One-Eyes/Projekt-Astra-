# ASTRA v0.0.21 RC — Review Notes

This candidate builds on Erik's pushed commit `9834f15` and targets
`DEV-need-check`. It is not a release.

## What to inspect

1. Start ASTRA under Erik and Petr separately and confirm both profiles still
   open their own data directories.
2. Run `self learning health` in each profile. A clean store should report
   `healthy`; warnings about old pending items are review reminders, while a
   blocked guidance error means the record is not entering model prompts.
3. Re-run `self learning guidance` and confirm approved preferences still appear.
4. Add and reject a disposable preference, then confirm it disappears from
   guidance and health does not report an active rejected link.
5. Run `diagnostics`; self-learning integrity findings should also appear there.
6. Run `backup create before-review`, `backup list`, and `backup verify latest`.
   Confirm the generated ZIP is under only the active profile directory and
   keep it private.
7. Run `model check`, `vision check`, `image describe`, and `eyes once` on the
   target Windows/Ollama installation. Automated tests cannot judge real model
   output or screen-capture quality.
8. Confirm the push produces one Slack `#Changelog` message headed
   `ASTRA v0.0.21 changelog` with concrete feature/fix bullets.

## Safety notes

- Health inspection does not delete or rewrite learning data.
- Warnings do not automatically reject a candidate.
- Structurally inconsistent active guidance fails closed and is omitted from the
  model prompt until its data is reviewed.
- Profile backups are verified but not automatically restored; this prevents a
  chat command from replacing live personal data.
- The local PIN remains a profile-mix-up guard, not disk encryption.
