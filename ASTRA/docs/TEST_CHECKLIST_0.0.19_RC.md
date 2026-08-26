# ASTRA v0.0.19 RC — Local Test Checklist

Do this **before any GitHub push**.

## 1. Apply the review overlay to a disposable/local DEV copy

Keep your current working copy/branch recoverable. This is still an RC.

## 2. Install/update the same Python environment Astra actually uses

From the `ASTRA` directory:

```powershell
python -m pip install -e ".[dev]"
```

Verify Eyes dependencies:

```powershell
python -c "import mss, PIL, psutil; print('Eyes dependencies OK')"
```

## 3. Full existing test suite — mandatory

```powershell
python -m pytest -q
```

Do not push if anything is red. Save the complete failure output rather than
fixing tests by simply weakening assertions.

## 4. GUI smoke

```powershell
.\run_astra_gui.bat
```

Check:

- Dark mode opens correctly.
- Theme toggle survives restart.
- Existing Ollama On/Off/Light Model quick actions still exist.
- Eyes and Self Learn quick actions exist.
- Model dropdown refreshes installed/registered Ollama models.
- Switching to `gemma3:4b` succeeds without restarting Astra.

## 5. Model / Eyes smoke

Inside Astra:

```text
model status
model check
vision check
eyes status
eyes once
```

Expected:

- `gemma3:4b` is recognized as vision-capable.
- `eyes once` returns a useful observation or a normal non-noteworthy result,
  not a dependency/capability error.
- A merely greyed UI control must not become an actionable alert.

Then optionally:

```text
eyes on
```

Leave it running long enough to confirm it does not spam normal UI changes.

## 6. Existing `python` learning migration test

Your old learning file is useful because it exercised the 13-case evaluator.

```text
learning status python
learning eval python
```

Expected after first access:

- old evaluator state is migrated/inactivated;
- proficient matrix is no longer 13 repetitive cases;
- old pass/approval cannot survive the evaluator/content revision change.

Then:

```text
learning run-eval python
```

If it fails, the response must list **which cases failed and why**. A failed
grounded case should say things such as missing/unsupported evidence quote,
wrong decision, missing source, etc. Do not chase 100% by weakening the gate.

## 7. Fresh learning test

For a clean web-backed test:

```text
research learn python typing with 2 sources
learning status python typing
learning run-eval python typing
```

Or for a fully manual/offline source test:

```text
learn deeply about python-audit
teach python-audit: Python uses indentation to delimit code blocks. Functions are created with def, parameters are declared in parentheses, and return sends a value back to the caller. Exceptions can be handled with try and except, and modules can be imported to reuse code.
teach python-audit: A Python virtual environment isolates project dependencies from the system interpreter. pytest discovers test functions and fixtures, executes assertions, and reports failing cases. JSON data can be read and written with the standard json module.
learning status python-audit
learning run-eval python-audit
```

Only after a **current** eval gate passes:

```text
learning approve python-audit
learning promote python-audit
```

Then ask a normal question related to the learned material and confirm the
current learning store is used.

## 8. Invalidation test — mandatory

After a subject has passed/been approved, add one genuinely new source:

```text
teach python-audit: Python context managers use the with statement to manage setup and cleanup around a resource, commonly files or locks. Objects can implement __enter__ and __exit__ to define context-manager behavior.
learning status python-audit
```

Expected immediately:

- eval passed = false;
- review = not-reviewed;
- promotion ready = false;
- a new eval is required.

If the old approval survives, stop: that is a release blocker.

## 9. Self-learning test

```text
self learning status
self learning preference Keep answers compact when a short answer is enough.
self learning status
self learning correction This correction should require review rather than becoming global guidance immediately.
self learning review
```

Expected:

- explicit preference can activate according to current mode;
- correction remains review-gated;
- normal chat does not silently create language/style rules.

## 10. Diagnostics / export

```text
status
export
```

Check the export JSON contains `gui_theme`, model context settings,
self-learning mode, and Eyes settings.

## Release gate

Only consider a push after:

- full `python -m pytest -q` is green;
- Visual Studio review is clean;
- learning migration test behaves as above;
- fresh grounded eval behaves sensibly;
- invalidation test passes;
- Eyes does not spam false positives;
- you explicitly approve the RC.

## Live learning retest after evaluator v4

Do **not** delete the existing learning subject. The first read of an old v3 subject
should migrate it to v4 while preserving its source material.

Run:

```text
learning status python
learning run-eval python
```

Expected migration behavior:

- captured sources remain present;
- the old 71.43% v3 eval is not treated as current authorization;
- the regenerated proficient matrix remains compact (typically 7 cases with two sources);
- `ASTRA-LEARN-UNKNOWN-001` contains a synthetic `ASTRA_EVAL_...` probe;
- boundary decisions use `privacy_block` / `review_gate`, not the old ambiguous labels.

If a case still fails, copy the new failed-case output. It now includes
`model_decision=...` and `model_answer: ...`, which is enough to distinguish a model
reasoning failure from an evaluator/parser bug.


## RC3 live synthesis retest

First inspect what ASTRA actually captured:

```text
learning sources python
```

Check that both `S001` and `S002` are genuinely useful evidence **about Python**, not
merely ASTRA/project notes that happen to contain the word "Python".

Then run:

```text
learning run-eval python
```

For `ASTRA-LEARN-SYNTHESIS-001` the model now receives evidence from distinct sources
and is explicitly told to cite at least two Source IDs. If it still fails, the output
will include `model_sources:` and `evidence_quote:`.

Interpretation:

- correct/relevant sources + invented/paraphrased quote -> model grounding failure;
- only one `model_sources` entry despite two relevant evidence sources -> model instruction failure;
- sources themselves are weak/off-topic -> **do not weaken the gate**; add evidence with
  `research learn python` or `teach python: ...`, then rerun.


## Live acquisition check

1. Run `learn deeply about python`.
2. Run `learning sources python`.
3. Confirm generic ASTRA help/history text is **not** accepted merely because it
   contains one incidental `python` mention.
4. If local evidence is absent, use `research learn python` or explicit `teach`.
5. Only then rerun `learning run-eval python`.
