# ASTRA v0.0.19 RC — Review Notes

This is the **full-audit review package**, not a release and not a GitHub commit.

Review the files in Visual Studio, then run the local checklist in
`docs/TEST_CHECKLIST_0.0.19_RC.md`. The most important live test is the learning
flow, including an old `python` subject migration and a fresh proficient subject.

Nothing should be pushed until:

1. the full local `python -m pytest -q` suite passes;
2. the learning eval behaves sensibly on the real local model;
3. Eyes stays useful without cosmetic false-positive spam;
4. the code review is accepted explicitly.

Documentation for this RC:

- `docs/PATCH_NOTES_0.0.19_RC.md`
- `docs/CHANGELOG_PENDING_0.0.19.md`
- `docs/AUDIT_REPORT_0.0.19_RC.md`
- `docs/TEST_REPORT_0.0.19_RC.md`
- `docs/TEST_CHECKLIST_0.0.19_RC.md`

## Live-eval review checkpoint

The original full-audit RC was **not** accepted after its first real learning run.
That run exposed evaluator ambiguity and triggered the v4 fix documented in the patch
notes and audit report. This package supersedes that evaluator logic but is still a
review candidate: rerun `learning run-eval python` locally before any GitHub push.


## RC3 checkpoint — synthesis

The second live run reached 6/7 and proved evaluator v4 fixed the prior boundary issues.
RC3 addresses the remaining synthesis contract mismatch while keeping the gate strict.

Before any push, run `learning sources python` and then `learning run-eval python` on the
real local model. A 7/7 result is desirable only if the displayed sources are genuinely
useful Python evidence; source quality must not be hidden by a looser validator.


## Live-learning acquisition hardening (need-check branch)

A real `learn deeply about python` run exposed that automatic memory acquisition
accepted long help/history entries that only mentioned the subject incidentally,
and near-identical help responses could masquerade as independent sources.

Fixed before the need-check branch snapshot:

- automatic memory sources now require topical relevance, not just one token hit;
- a single subject mention inside a long generic entry is rejected;
- near-identical memory candidates are deduplicated before capture;
- rerunning `learn about` / `learn deeply about` refreshes automatically captured
  `memory:` sources instead of keeping stale junk forever;
- explicit `user:teach` and `web:` evidence is preserved during that refresh;
- deep learning still does not silently use the network: when local evidence is
  insufficient, ASTRA stays in acquisition mode and points to `research learn` or
  `teach` rather than pretending to be proficient.

## need-check handoff

The live Python test exposed source-acquisition false positives. The current
bundle rejects incidental long-entry mentions, deduplicates near-identical
memory candidates, and refreshes stale automatic `memory:` sources while
preserving explicit evidence. Focused learning regression: 38/38 PASS.
