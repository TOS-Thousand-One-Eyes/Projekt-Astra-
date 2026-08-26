# ASTRA v0.0.19 RC — Test Report

Status: **review candidate; not pushed**  
Base branch: `DEV`  
Base DEV commit audited: `3cb8f2fdc6618803d73258279a823973f1aff17d`  
Runtime version intentionally remains `0.0.18` until approval.

## Final audit checks in this environment

- Modified production/review Python: `py_compile` **PASS**.
- Shipping compatibility/regression harness: **74/74 PASS**.
- Additional adversarial/private audit harness: **46/46 PASS**.
- Modified review test set now includes the v4 live-eval migration, probe, prompt, diagnostics, and proficient 7/7 regressions.
- `config.json` parse: **PASS**.
- Production source scan for hardcoded localized learning commands/language policy: **PASS**.
- Python AST scan for parse errors and duplicate literal dict keys: **PASS**.
- Review ZIP integrity: checked during packaging.
- GitHub writes during audit: **none**.

## Important limitation

This environment could read the connected GitHub `DEV` tree/file contents for
compatibility checks, but could not materialize a complete repository checkout.
Therefore the **entire existing upstream DEV test suite has not been run here**.

That is deliberately a release gate on the real Windows checkout:

```powershell
python -m pip install -e ".[dev]"
python -m pytest -q
```

Do not push if that suite is red.

## Live checks already learned from this review cycle

The user's Windows live tests exposed and led to fixes for:

- missing Eyes runtime dependencies;
- incorrect Gemma 3 vision capability detection;
- high-confidence cosmetic UI false positives;
- weak/opaque learning-eval behavior.

The new RC keeps those as regression cases and adds stricter learning revision
invalidation, grounding checks, and per-case failure reporting.

## Live-eval v4 regression pass

After the real 5/7 Gemma 3 4B result, the evaluator was revised to v4 and the combined
review harness was rerun:

- shipping/regression subset: **74/74 PASS**;
- adversarial/private audit subset: **46/46 PASS**;
- combined: **120/120 PASS**;
- explicit simulated proficient evaluator: **7/7 PASS** using the v4 decision schema;
- explicit v3 -> v4 migration: source contents preserved and stale eval invalidated;
- modified Python compilation: PASS.

This still does not substitute for the next real local-model run. The purpose of the
new diagnostics is that any remaining Gemma-specific failure will show its actual
classification and answer instead of only an opaque percentage.


## RC3 synthesis-grounding regression pass

After the real 6/7 synthesis failure, five new shipping regressions were added:

- multi-source synthesis context contains distinct Source IDs even when one source has
  many higher-scoring chunks;
- synthesis prompt states the two-source requirement and bans generic meta commentary;
- verbatim quote instructions remain explicit;
- `learning sources <topic>` shows provenance and bounded previews;
- failed reports expose model sources/evidence quote and status separates source readiness.

Current review harness after RC3:

- shipping/regression subset: **79/79 PASS**;
- adversarial/private audit subset: **46/46 PASS**;
- combined: **125/125 PASS**.

The real `gemma3:4b` run remains the release gate; deterministic tests only prove the
context/prompt/validator contract is internally consistent.


## Need-check acquisition regression

Focused `tests/test_learning.py` pass after the live Python-source fix: **38/38 PASS**.
New regressions cover incidental long-entry rejection, near-duplicate memory-source
deduplication, and stale-memory refresh while preserving explicit evidence.
