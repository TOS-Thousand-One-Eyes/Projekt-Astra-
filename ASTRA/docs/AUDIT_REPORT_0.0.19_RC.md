# ASTRA v0.0.19 RC — Full Audit Report

Status: **pre-ship review candidate**  
Base: `DEV` / Astra `0.0.18`  
GitHub writes performed during this audit: **none**

## Audit method

The RC was reviewed in multiple independent passes rather than treating the
first green test run as release-ready:

1. learning/eval state-machine and persistence pass;
2. self-learning poisoning/review pass;
3. Eyes privacy/actionability/threading pass;
4. model runtime/config/GUI compatibility pass;
5. existing DEV behavior/backward-compatibility pass;
6. adversarial regression + static structure scan.

The important lesson from the audit was that passing isolated RC tests was not
enough: several bugs existed specifically **between** subsystems.

## Findings closed

### Critical / high

1. **Stale learning approval after content change**
   - Risk: new source could inherit an old passing eval and approval.
   - Fix: content revision hash + mandatory invalidation of eval/review/promotion.

2. **Evaluator asked for citations but could not prove grounding**
   - Risk: general model knowledge or fabricated answer could pass with a source
     ID attached.
   - Fix: exact `evidence_quote` verified against cited source plus answer/evidence
     overlap check.

3. **Validator required `evidence_quote`, prompt omitted it**
   - Risk: genuine model answers failed for a field the model was never asked to
     provide; live eval scores were artificially bad.
   - Fix: structured eval prompt explicitly requires exact evidence quote.

4. **Old v2/13-case reports could survive conceptual evaluator changes**
   - Risk: an old pass could be mistaken for a current gate.
   - Fix: evaluator versioning + migration invalidation.

5. **Factual correction auto-poisoning**
   - Risk: one user correction could become global guidance without review.
   - Fix: corrections always queue for review; only explicit preferences may
     auto-activate in auto mode.

6. **Stale promoted long-memory summary competing with current learning**
   - Risk: after a new source invalidated a subject, model context could still
     receive the old compact promoted summary from LongMemory.
   - Fix: LearningManager is the sole authority for source-backed learned
     context; LongMemory context uses explicit notes/facts only.

7. **Eyes event bypassed Brain/Experience**
   - Risk: alert visible to user but absent from reflection/history and unable to
     participate coherently in higher layers.
   - Fix: event callback into Brain + thread-safe Experience record.

8. **All-monitor screenshot privacy exposure**
   - Risk: `mss.monitors[0]` captures the bounding box of every display while
     privacy filtering only knows the foreground window.
   - Fix: primary monitor only by default.

### Medium

9. Gemma vision false-negative due to `/api/tags` capability inference.
10. Greyed/inactive UI accepted as high-confidence actionable observation.
11. Eyes baseline overwritten by skipped/busy samples.
12. Shared text-only model switch could leave Eyes in a failure loop.
13. Self-learning and Experience concurrent JSON write races.
14. Rejected self-learning candidate could leave active guidance behind.
15. Duplicate source IDs in migrated learning payloads.
16. ASCII-only retrieval degraded non-Latin subjects and notes.
17. Non-Latin subjects could collide on a generic slug.
18. Proficient learning could appear ready with thin/untrusted material.
19. Proficient synthesis could pass with only one cited source.
20. Eval summary hid individual case failures and reasons.
21. Corrupt list/search learning files were silently disruptive instead of
    skipped with warnings.
22. Diagnostics omitted warnings from newly introduced managers.
23. Export omitted new model/theme/Eyes/self-learning configuration.
24. GUI quick actions accidentally removed existing Ollama controls.
25. Fixed temp names remained in new model/theme persistence paths.
26. Generation timeouts accepted nonsensical out-of-range numeric values.
27. Ollama response handling assumed a JSON object without checking shape.
28. Eyes event callback return value was ignored.

### Cleanup

29. Removed hardcoded localized learning command aliases/help.
30. Removed implicit language-specific chat preference heuristics.
31. Preserved existing command constructor positional prefixes where new
    dependencies were added.
32. Restored shared-language vision-check wording expected by existing DEV
    behavior while retaining integrated Eyes.
33. Restored existing GUI quick actions alongside the new Eyes/Self-Learn
    shortcuts.

## Test result in this environment

- Production + review test files compile successfully.
- Shipping compatibility/regression harness after the audit: **68/68 passed**.
- Additional adversarial/private audit harness: **46/46 passed**.
- Static AST scan: no duplicate literal dict keys, mutable-default findings, or
  parse errors in modified production Python.
- Localized-command/language-policy production scan: clean.
- Fixed `.tmp` suffix scan in modified production: clean.
- Real GitHub `DEV` was read for compatibility, but never modified.

## What is intentionally not claimed

- The connected GitHub repository cannot be bulk-cloned into this execution
  environment, so the complete existing DEV test suite was **not** executed here.
- Real Windows desktop behavior beyond the user's live Eyes tests cannot be
  fully reproduced in this Linux sandbox.
- Real `gemma3:4b` quality is probabilistic; the deterministic eval/vision
  guards reduce trust in model self-reporting but do not make a 4B model perfect.
- Self-learning does not modify model weights. Training traces are groundwork
  for a later reviewed fine-tune/LoRA workflow.

The local full-suite run and the user's real learning test are release gates,
not optional follow-ups.

## Post-audit live-model finding: eval decision ambiguity

The first real proficient `python` run after the audit produced 5/7 (71.43%). The
only failures were the unsupported-evidence case and review-gate boundary, both with
`wrong_decision:answer->...`.

Root-cause review found two evaluator defects rather than a source-learning failure:

1. The unsupported case requested "a deliberately unsupported detail" without naming
   a concrete detail, so a model could legitimately answer a supported fact instead.
2. The enum value `answer` conflated "the request is evidence-supported" with "I wrote
   an explanatory answer". A small model could correctly explain that review is needed
   while still selecting `answer`.

Resolution: evaluator v4 uses unambiguous request-state decisions, a source-absent
synthetic probe, and more diagnostic failure output. A migration regression test
specifically covers an existing v3 `python.json` with a 71.43% failed report.


## Post-v4 live finding: synthesis context/prompt mismatch

The next real local run improved from 5/7 to **6/7 (85.71%)**. The v4 unsupported and
review-gate fixes worked. The only remaining failure was:

`ASTRA-LEARN-SYNTHESIS-001`: `needs_at_least_2_sources`,
`unsupported_evidence_quote`.

Review found an evaluator fairness bug: the validator required at least two distinct
source citations, but `eval_context()` ranked chunks globally and did not guarantee that
multiple sources appeared in the model's evidence window. The prompt also described
citation generically and did not expose the case's `minimum_sources=2` requirement.

RC3 fixes both sides without lowering the gate. Multi-source cases select one relevant
chunk per distinct source first, and the prompt states the minimum citation count plus a
strict verbatim quote requirement. Diagnostics expose the model's source list and quote.

The model answer from the live failure was also generic/meta-level. That may indicate the
captured Python material itself is weak or off-topic. This is now inspectable directly via
`learning sources python`; source quality remains a legitimate reason for the gate to fail.


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
