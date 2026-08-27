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

## Full integration recheck

The actual `DEV-need-check` branch was cloned at `a2203c1` and the complete
repository suite was run. The initial result was 428 passed / 6 failed. All six
failures were stale compatibility assertions that contradicted already-documented
v4 contracts: the stable ASTRA system prompt, LearningManager-only promoted
knowledge, and the compact evaluator replacing the retired 13-case matrix.

After aligning those regressions and closing newly found integration gaps:

- full suite: **449/449 PASS**;
- self-learning mode and Eyes enabled state persist atomically;
- explicit correction traces retain the prior ASTRA answer;
- active guidance is inspectable with `self learning guidance`;
- text-only models fail `vision check` clearly;
- a stale Eyes-on setting cannot prevent ASTRA startup;
- quick Eyes off/on cannot spawn a duplicate worker while a model call is stuck;
- CI is in repository-root `.github/workflows`, where GitHub actually discovers it;
- optional Slack push changelogs are deterministic and consume no AI tokens.

No push or Slack message has been performed. The remaining gates are the user's
Windows/Ollama live checks and review of the uncommitted diff.
