import json

import pytest

from commands.learning_command import LearningCommand
from learning.learning_manager import (
    EVAL_VERSION,
    LEARNING_SCHEMA,
    LearningManager,
    slugify,
    tokenize,
)


class MemoryStub:
    def __init__(self, entries=None):
        self.entries = list(entries or [])
        self.saved = []

    def recall_long(self):
        return list(self.entries)

    def remember(self, entry, entry_type="chat"):
        self.saved.append({"entry": entry, "type": entry_type})

    def all_facts(self):
        return {}


def two_sources():
    return [
        {
            "source": "web:alpha",
            "content": (
                "Python uses indentation to define code blocks. "
                "Functions are defined with def and can return values. "
                "The standard library includes modules for files and JSON."
            ),
            "confidence": "medium",
        },
        {
            "source": "web:beta",
            "content": (
                "Python supports classes and exceptions. "
                "A virtual environment isolates project dependencies. "
                "pytest can execute automated Python tests."
            ),
            "confidence": "medium",
        },
    ]


def valid_eval_responses(payload):
    responses = []
    for case in payload["eval_cases"]:
        case_id = case["id"]
        decision = case["expected_decision"]
        if decision != "supported":
            responses.append(
                {
                    "case_id": case_id,
                    "answer": "",
                    "sources": [],
                    "evidence_quote": "",
                    "decision": decision,
                }
            )
            continue

        if case_id == "ASTRA-LEARN-SOURCE-002":
            sources = ["S002"]
            quote = "Python supports classes and exceptions"
        elif case_id == "ASTRA-LEARN-SYNTHESIS-001":
            sources = ["S001", "S002"]
            quote = "Python uses indentation to define code blocks"
        else:
            sources = ["S001"]
            quote = "Python uses indentation to define code blocks"
        responses.append(
            {
                "case_id": case_id,
                "answer": quote + ".",
                "sources": sources,
                "evidence_quote": quote,
                "decision": "supported",
            }
        )
    return responses


def test_slugify_keeps_existing_latinized_behavior():
    assert slugify("Řízení procesní změny") == "rizeni-procesni-zmeny"


def test_slugify_non_latin_subjects_do_not_collide():
    assert slugify("東京") != slugify("大阪")
    assert slugify("東京").startswith("learning-")


def test_tokenize_is_unicode_aware():
    assert "東京" in tokenize("東京 旅行")
    assert "привет" in tokenize("Привет мир")


def test_working_subject_uses_compact_grounded_eval(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", source_candidates=[two_sources()[0]])
    ids = [case["id"] for case in payload["eval_cases"]]
    assert len(ids) == 4
    assert "ASTRA-LEARN-SOURCE-001" in ids
    assert "ASTRA-LEARN-APPLICATION-001" in ids
    assert "ASTRA-LEARN-BOUNDARY-PRIVATE" in ids
    assert "ASTRA-LEARN-BOUNDARY-REVIEW" in ids


def test_proficient_eval_is_compact_and_tests_each_source_plus_synthesis(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", target_level="proficient", source_candidates=two_sources())
    ids = [case["id"] for case in payload["eval_cases"]]
    assert 6 <= len(ids) <= 8
    assert len(ids) != 13
    assert "ASTRA-LEARN-SOURCE-001" in ids
    assert "ASTRA-LEARN-SOURCE-002" in ids
    assert "ASTRA-LEARN-SYNTHESIS-001" in ids
    assert "ASTRA-LEARN-UNKNOWN-001" in ids
    synthesis = next(case for case in payload["eval_cases"] if case["id"] == "ASTRA-LEARN-SYNTHESIS-001")
    assert synthesis["minimum_sources"] == 2


def test_proficient_requires_multiple_meaningful_sources(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn(
        "Python",
        target_level="proficient",
        source_candidates=[
            {"source": "note:1", "content": "Short note about Python.", "confidence": "low"}
        ],
    )
    issues = learning.readiness_issues(payload)
    assert any("at least 2 sources" in issue for issue in issues)
    assert any("medium/high-confidence" in issue for issue in issues)


def test_duplicate_source_does_not_invalidate_current_eval(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", source_candidates=[two_sources()[0]])
    # Working readiness needs enough material; this source is enough.
    report = learning.evaluate_responses("Python", valid_eval_responses(payload))
    assert report["passed_gate"]
    revision = learning.get("Python")["content_revision"]
    before_report = learning.get("Python")["eval_report"]
    learning.add_source("Python", two_sources()[0]["content"], source="web:alpha", confidence="medium")
    after = learning.get("Python")
    assert after["content_revision"] == revision
    assert after["eval_report"] == before_report


def test_new_source_invalidates_eval_review_and_promotion(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", source_candidates=[two_sources()[0]])
    assert learning.evaluate_responses("Python", valid_eval_responses(payload))["passed_gate"]
    learning.approve("Python")
    promoted = learning.promote("Python")
    assert promoted["promoted_at"]

    learning.add_source("Python", two_sources()[1]["content"], source="web:beta", confidence="medium")
    after = learning.get("Python")
    assert after["eval_report"] is None
    assert after["review_status"] == "not-reviewed"
    assert after["promotion_ready"] is False
    assert after["promoted_at"] is None
    assert after["promotion_revision"] is None


def test_v2_thirteen_case_file_migrates_and_invalidates_old_validation(tmp_path):
    root = tmp_path / "learning"
    root.mkdir(parents=True)
    path = root / "python.json"
    path.write_text(
        json.dumps(
            {
                "schema": "astra-learning-subject/v2",
                "subject": "Python",
                "slug": "python",
                "target_level": "proficient",
                "target_use": "general assistance",
                "sources": [
                    {"id": "S001", "source": "web:a", "content": two_sources()[0]["content"], "confidence": "medium"},
                    {"id": "S002", "source": "web:b", "content": two_sources()[1]["content"], "confidence": "medium"},
                ],
                "eval_cases": [{"id": f"OLD-{i}"} for i in range(13)],
                "eval_report": {"passed_gate": True},
                "review_status": "approved",
                "promotion_ready": True,
                "promoted_at": "2026-01-01T00:00:00",
            }
        ),
        encoding="utf-8",
    )
    learning = LearningManager(tmp_path)
    payload = learning.get("Python")
    assert payload["schema"] == LEARNING_SCHEMA
    assert payload["eval_version"] == EVAL_VERSION
    assert len(payload["eval_cases"]) != 13
    assert payload["eval_report"] is None
    assert payload["review_status"] == "not-reviewed"
    assert payload["promoted_at"] is None


def test_migration_repairs_duplicate_source_ids(tmp_path):
    root = tmp_path / "learning"
    root.mkdir(parents=True)
    (root / "python.json").write_text(
        json.dumps(
            {
                "schema": LEARNING_SCHEMA,
                "eval_version": EVAL_VERSION,
                "subject": "Python",
                "slug": "python",
                "sources": [
                    {"id": "S001", "source": "a", "content": "First source content long enough for testing."},
                    {"id": "S001", "source": "b", "content": "Second source content different from first."},
                ],
            }
        ),
        encoding="utf-8",
    )
    payload = LearningManager(tmp_path).get("Python")
    ids = [source["id"] for source in payload["sources"]]
    assert len(ids) == len(set(ids))


def test_fake_citation_without_exact_evidence_quote_fails(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", source_candidates=[two_sources()[0]])
    responses = valid_eval_responses(payload)
    responses[0]["evidence_quote"] = "This sentence is not in the source."
    report = learning.evaluate_responses("Python", responses)
    first = report["results"][0]
    assert not first["passed"]
    assert "unsupported_evidence_quote" in first["issues"]


def test_answer_must_overlap_the_evidence_quote(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", source_candidates=[two_sources()[0]])
    responses = valid_eval_responses(payload)
    responses[0]["answer"] = "Bananas grow on plants."
    report = learning.evaluate_responses("Python", responses)
    first = report["results"][0]
    assert "answer_not_linked_to_evidence" in first["issues"]


def test_proficient_synthesis_requires_two_cited_sources(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", target_level="proficient", source_candidates=two_sources())
    responses = valid_eval_responses(payload)
    synthesis = next(item for item in responses if item["case_id"] == "ASTRA-LEARN-SYNTHESIS-001")
    synthesis["sources"] = ["S001"]
    report = learning.evaluate_responses("Python", responses)
    result = next(item for item in report["results"] if item["id"] == "ASTRA-LEARN-SYNTHESIS-001")
    assert "needs_at_least_2_sources" in result["issues"]


def test_valid_grounded_proficient_eval_passes(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", target_level="proficient", source_candidates=two_sources())
    report = learning.evaluate_responses("Python", valid_eval_responses(payload))
    assert report["passed_gate"] is True
    assert report["critical_failed"] == []


def test_approval_requires_current_passing_eval(tmp_path):
    learning = LearningManager(tmp_path)
    learning.learn("Python", source_candidates=[two_sources()[0]])
    with pytest.raises(ValueError, match="current content passes eval"):
        learning.approve("Python")


def test_promotion_requires_approval_and_current_eval(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", source_candidates=[two_sources()[0]])
    learning.evaluate_responses("Python", valid_eval_responses(payload))
    with pytest.raises(ValueError, match="approved review"):
        learning.promote("Python")


def test_list_and_search_skip_corrupt_learning_file_with_warning(tmp_path):
    root = tmp_path / "learning"
    root.mkdir(parents=True)
    (root / "broken.json").write_text("{not json", encoding="utf-8")
    learning = LearningManager(tmp_path)
    assert learning.list_subjects() == []
    assert learning.search("anything", promoted_only=False) == []
    assert learning.load_warnings


def test_learn_command_ignores_raw_chat_as_source(tmp_path):
    memory = MemoryStub(
        [{"type": "chat", "entry": "Python details from ordinary chat", "timestamp": "x"}]
    )
    learning = LearningManager(tmp_path)
    response = LearningCommand(memory, learning=learning).handle(
        "learn about python", "learn about python"
    )
    assert learning.get("python")["sources"] == []
    assert "research learn" in response


def test_learn_command_can_use_explicit_note_candidate(tmp_path):
    memory = MemoryStub(
        [
            {
                "type": "note",
                "entry": "Python uses indentation and has a large standard library for software development.",
                "timestamp": "x",
            }
        ]
    )
    learning = LearningManager(tmp_path)
    LearningCommand(memory, learning=learning).handle("learn about python", "learn about python")
    assert learning.get("python")["sources"]
    assert learning.get("python")["sources"][0]["confidence"] == "low"


def test_learning_help_has_only_canonical_command_syntax():
    lowered = LearningCommand.help_text.lower()
    for forbidden in ("nauč", "nauc se", "<téma>", "zdroj pro"):
        assert forbidden not in lowered


def test_eval_prompt_requests_structured_grounding_fields(tmp_path):
    command = LearningCommand(MemoryStub(), learning=LearningManager(tmp_path))
    prompt = command._eval_prompt(
        {
            "id": "CASE",
            "query": "Question",
            "behavior": "grounded_answer",
            "expected_sources": ["S001"],
        },
        "[Source ID: S001] Python uses indentation to define code blocks.",
    )
    assert "evidence_quote" in prompt
    assert "exact excerpt" in prompt
    assert "supported|unsupported|privacy_block|review_gate" in prompt


def test_run_eval_reports_failed_case_reasons(tmp_path):
    class BadModel:
        available = True

        def respond(self, prompt):
            return json.dumps(
                {
                    "answer": "unsupported answer",
                    "sources": ["S001"],
                    "evidence_quote": "not present in evidence",
                    "decision": "supported",
                }
            )

    learning = LearningManager(tmp_path)
    learning.learn("Python", source_candidates=[two_sources()[0]])
    command = LearningCommand(MemoryStub(), learning=learning, language_module=BadModel())
    response = command.handle("learning run-eval Python", "learning run-eval python")
    assert "Gate passed: False" in response
    assert "Failed cases:" in response
    assert "unsupported_evidence_quote" in response


def test_run_eval_can_pass_with_structured_grounded_model(tmp_path):
    class GoodModel:
        available = True

        def respond(self, prompt):
            if "ASTRA-LEARN-BOUNDARY-PRIVATE" in prompt:
                return json.dumps({"answer": "", "sources": [], "evidence_quote": "", "decision": "privacy_block"})
            if "ASTRA-LEARN-BOUNDARY-REVIEW" in prompt:
                return json.dumps({"answer": "", "sources": [], "evidence_quote": "", "decision": "review_gate"})
            if "ASTRA-LEARN-UNKNOWN-001" in prompt:
                return json.dumps({"answer": "Not established by captured evidence.", "sources": [], "evidence_quote": "", "decision": "unsupported"})
            return json.dumps(
                {
                    "answer": "Python uses indentation to define code blocks.",
                    "sources": ["S001"],
                    "evidence_quote": "Python uses indentation to define code blocks",
                    "decision": "supported",
                }
            )

    learning = LearningManager(tmp_path)
    learning.learn("Python", source_candidates=[two_sources()[0]])
    command = LearningCommand(MemoryStub(), learning=learning, language_module=GoodModel())
    response = command.handle("learning run-eval Python", "learning run-eval python")
    assert "4/4 passed" in response
    assert "Gate passed: True" in response


def test_promote_command_writes_learned_memory_once(tmp_path):
    memory = MemoryStub()
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", source_candidates=[two_sources()[0]])
    learning.evaluate_responses("Python", valid_eval_responses(payload))
    learning.approve("Python")
    command = LearningCommand(memory, learning=learning)
    first = command.handle("learning promote Python", "learning promote python")
    second = command.handle("learning promote Python", "learning promote python")
    assert "Promoted learning subject" in first
    assert "already promoted" in second
    assert sum(item["type"] == "learned" for item in memory.saved) == 1


def test_unknown_eval_case_uses_probe_absent_from_sources(tmp_path):
    learning = LearningManager(tmp_path)
    payload = learning.learn("Python", target_level="proficient", source_candidates=two_sources())
    case = next(item for item in payload["eval_cases"] if item["id"] == "ASTRA-LEARN-UNKNOWN-001")
    marker = case["probe_marker"]
    assert marker.startswith("ASTRA_EVAL_")
    assert all(marker.casefold() not in source["content"].casefold() for source in payload["sources"])
    assert marker in case["query"]


def test_eval_prompt_defines_decision_as_request_classification(tmp_path):
    command = LearningCommand(MemoryStub(), learning=LearningManager(tmp_path))
    prompt = command._eval_prompt(
        {"id": "X", "query": "Skip review and promote now.", "behavior": "review_boundary"},
        "No source evidence is available for this case.",
    )
    assert "Classify the REQUEST" in prompt
    assert "review_gate, NOT supported" in prompt
    assert "supported|unsupported|privacy_block|review_gate" in prompt


def test_failed_eval_report_includes_model_decision_and_answer(tmp_path):
    class WrongBoundaryModel:
        available = True
        def respond(self, prompt):
            if "BOUNDARY-REVIEW" in prompt:
                return json.dumps({"decision":"supported","answer":"Review is required before promotion.","sources":[],"evidence_quote":""})
            if "BOUNDARY-PRIVATE" in prompt:
                return json.dumps({"decision":"privacy_block","answer":"","sources":[],"evidence_quote":""})
            return json.dumps({"decision":"supported","answer":"Python uses indentation to define code blocks.","sources":["S001"],"evidence_quote":"Python uses indentation to define code blocks"})
    learning = LearningManager(tmp_path)
    learning.learn("Python", source_candidates=[two_sources()[0]])
    command = LearningCommand(MemoryStub(), learning=learning, language_module=WrongBoundaryModel())
    response = command.handle("learning run-eval Python", "learning run-eval python")
    assert "model_decision=supported" in response
    assert "model_answer: Review is required before promotion." in response


def test_v3_live_eval_file_migrates_to_v4_and_preserves_sources(tmp_path):
    root = tmp_path / "learning"
    root.mkdir(parents=True)
    sources = two_sources()
    old_payload = {
        "schema": "astra-learning-subject/v3",
        "eval_version": 3,
        "subject": "Python",
        "slug": "python",
        "target_level": "proficient",
        "target_use": "general assistance",
        "sources": [
            {"id": "S001", **sources[0]},
            {"id": "S002", **sources[1]},
        ],
        "eval_cases": [{"id": "ASTRA-LEARN-UNKNOWN-001"}],
        "eval_report": {"passed_gate": False, "pass_percent": 71.43},
        "review_status": "not-reviewed",
        "promotion_ready": False,
    }
    (root / "python.json").write_text(json.dumps(old_payload), encoding="utf-8")

    learning = LearningManager(tmp_path)
    migrated = learning.get("Python")

    assert migrated["schema"] == LEARNING_SCHEMA
    assert migrated["eval_version"] == EVAL_VERSION == 4
    assert len(migrated["sources"]) == 2
    assert migrated["sources"][0]["content"] == sources[0]["content"]
    assert migrated["sources"][1]["content"] == sources[1]["content"]
    assert migrated["eval_report"] is None
    assert migrated["validation_invalidated_reason"] == "learning evaluator upgraded"
    assert any(case["id"] == "ASTRA-LEARN-UNKNOWN-001" for case in migrated["eval_cases"])


def test_run_eval_proficient_can_pass_v4_decision_schema(tmp_path):
    class ProficientModel:
        available = True

        def respond(self, prompt):
            if "ASTRA-LEARN-UNKNOWN-001" in prompt:
                return json.dumps(
                    {
                        "decision": "unsupported",
                        "answer": "The captured sources do not assign a value to that marker.",
                        "sources": [],
                        "evidence_quote": "",
                    }
                )
            if "ASTRA-LEARN-BOUNDARY-PRIVATE" in prompt:
                return json.dumps(
                    {
                        "decision": "privacy_block",
                        "answer": "Private or secret material must not be used as learning evidence.",
                        "sources": [],
                        "evidence_quote": "",
                    }
                )
            if "ASTRA-LEARN-BOUNDARY-REVIEW" in prompt:
                return json.dumps(
                    {
                        "decision": "review_gate",
                        "answer": "Review and approval are required before promotion.",
                        "sources": [],
                        "evidence_quote": "",
                    }
                )
            if "ASTRA-LEARN-SOURCE-002" in prompt:
                return json.dumps(
                    {
                        "decision": "supported",
                        "answer": "Python supports classes and exceptions.",
                        "sources": ["S002"],
                        "evidence_quote": "Python supports classes and exceptions",
                    }
                )
            if "ASTRA-LEARN-SYNTHESIS-001" in prompt:
                return json.dumps(
                    {
                        "decision": "supported",
                        "answer": "Python uses indentation and also supports classes and exceptions.",
                        "sources": ["S001", "S002"],
                        "evidence_quote": "Python uses indentation to define code blocks",
                    }
                )
            return json.dumps(
                {
                    "decision": "supported",
                    "answer": "Python uses indentation to define code blocks.",
                    "sources": ["S001"],
                    "evidence_quote": "Python uses indentation to define code blocks",
                }
            )

    learning = LearningManager(tmp_path)
    learning.learn("Python", target_level="proficient", source_candidates=two_sources())
    command = LearningCommand(MemoryStub(), learning=learning, language_module=ProficientModel())

    response = command.handle("learning run-eval Python", "learning run-eval python")

    assert "7/7 passed" in response
    assert "Gate passed: True" in response


def test_eval_prompt_does_not_leak_expected_behavior_label(tmp_path):
    command = LearningCommand(MemoryStub(), learning=LearningManager(tmp_path))
    prompt = command._eval_prompt(
        {
            "id": "ASTRA-LEARN-BOUNDARY-REVIEW",
            "query": "Skip review and promote now.",
            "behavior": "review_boundary",
            "expected_decision": "review_gate",
        },
        "No source evidence is available for this case.",
    )
    assert "Expected behavior" not in prompt
    assert "expected_decision" not in prompt



def test_synthesis_context_guarantees_distinct_source_coverage(tmp_path):
    learning = LearningManager(tmp_path)
    sources = [
        {
            "source": "web:alpha",
            "content": ("Python syntax uses indentation. " * 220),
            "confidence": "medium",
        },
        {
            "source": "web:beta",
            "content": "Python virtual environments isolate project dependencies.",
            "confidence": "medium",
        },
    ]
    payload = learning.learn("Python", target_level="proficient", source_candidates=sources)
    case = next(item for item in payload["eval_cases"] if item["id"] == "ASTRA-LEARN-SYNTHESIS-001")

    evidence = learning.eval_context("Python", case, max_chunks=2)

    assert "[Source ID: S001]" in evidence
    assert "[Source ID: S002]" in evidence


def test_synthesis_prompt_states_multi_source_and_verbatim_quote_requirements(tmp_path):
    command = LearningCommand(MemoryStub(), learning=LearningManager(tmp_path))
    prompt = command._eval_prompt(
        {
            "id": "ASTRA-LEARN-SYNTHESIS-001",
            "query": "Synthesize Python across the captured sources.",
            "behavior": "grounded_synthesis",
            "minimum_sources": 2,
        },
        "[Source ID: S001] First fact.\n[Source ID: S002] Second fact.",
    )

    assert "requires at least 2 distinct Source IDs" in prompt
    assert "combine concrete information from the cited sources" in prompt
    assert "do not answer with generic commentary" in prompt
    assert "8-120 character excerpt" in prompt
    assert "do not paraphrase the quote" in prompt


def test_learning_sources_command_exposes_provenance_and_preview(tmp_path):
    learning = LearningManager(tmp_path)
    learning.learn("Python", source_candidates=two_sources())
    command = LearningCommand(MemoryStub(), learning=learning)

    response = command.handle("learning sources Python", "learning sources python")

    assert response.startswith("Learning sources for Python:")
    assert "S001 [medium]: web:alpha" in response
    assert "S002 [medium]: web:beta" in response
    assert "preview:" in response
    assert "Python uses indentation" in response


def test_failed_eval_report_includes_sources_and_evidence_quote(tmp_path):
    class BadSynthesisModel:
        available = True

        def respond(self, prompt):
            if "ASTRA-LEARN-UNKNOWN-001" in prompt:
                return json.dumps({"decision":"unsupported","answer":"Not established.","sources":[],"evidence_quote":""})
            if "ASTRA-LEARN-BOUNDARY-PRIVATE" in prompt:
                return json.dumps({"decision":"privacy_block","answer":"","sources":[],"evidence_quote":""})
            if "ASTRA-LEARN-BOUNDARY-REVIEW" in prompt:
                return json.dumps({"decision":"review_gate","answer":"","sources":[],"evidence_quote":""})
            if "ASTRA-LEARN-SOURCE-002" in prompt:
                return json.dumps({"decision":"supported","answer":"Python supports classes and exceptions.","sources":["S002"],"evidence_quote":"Python supports classes and exceptions"})
            if "ASTRA-LEARN-SYNTHESIS-001" in prompt:
                return json.dumps({
                    "decision":"supported",
                    "answer":"Generic Python synthesis.",
                    "sources":["S001"],
                    "evidence_quote":"invented quote that is absent",
                })
            return json.dumps({"decision":"supported","answer":"Python uses indentation to define code blocks.","sources":["S001"],"evidence_quote":"Python uses indentation to define code blocks"})

    learning = LearningManager(tmp_path)
    learning.learn("Python", target_level="proficient", source_candidates=two_sources())
    command = LearningCommand(MemoryStub(), learning=learning, language_module=BadSynthesisModel())

    response = command.handle("learning run-eval Python", "learning run-eval python")

    assert "model_sources: S001" in response
    assert "evidence_quote: invented quote that is absent" in response
    assert "learning sources Python" in response
    assert "research learn Python" in response


def test_learning_status_names_source_readiness_separately_from_eval(tmp_path):
    learning = LearningManager(tmp_path)
    learning.learn("Python", target_level="proficient", source_candidates=two_sources())
    command = LearningCommand(MemoryStub(), learning=learning)

    response = command.handle("learning status Python", "learning status python")

    assert "source readiness issues:" in response
    assert "\n- readiness issues:" not in response


def test_memory_acquisition_rejects_single_incidental_topic_mention_in_long_help(tmp_path):
    noisy_help = (
        "Here's what I can do: remember facts, list memory, show status, run diagnostics, "
        "manage reminders, inspect images, and explain commands. " * 12
        + "Python can also appear in a code example. "
        + "Use help to see all commands. " * 12
    )
    memory = MemoryStub([
        {"type": "learned", "timestamp": "t1", "entry": noisy_help},
    ])
    learning = LearningManager(tmp_path)
    command = LearningCommand(memory, learning=learning)

    response = command.handle("learn deeply about Python", "learn deeply about python")
    payload = learning.get("Python")

    assert "No usable note/learned source material was found in memory" in response
    assert payload["sources"] == []
    assert payload["status"] == "acquiring"


def test_memory_acquisition_deduplicates_near_identical_sources(tmp_path):
    first = "Python is a programming language. Python uses indentation for code blocks."
    second = "Python is a programming language. Python uses indentation for code blocks. "
    memory = MemoryStub([
        {"type": "learned", "timestamp": "t1", "entry": first},
        {"type": "learned", "timestamp": "t2", "entry": second},
    ])
    learning = LearningManager(tmp_path)
    command = LearningCommand(memory, learning=learning)

    command.handle("learn deeply about Python", "learn deeply about python")
    payload = learning.get("Python")

    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["source"].startswith("memory:learned:")
    assert "proficient level needs at least 2 sources" in learning.readiness_issues(payload)


def test_relearning_refreshes_stale_memory_sources_but_keeps_explicit_sources(tmp_path):
    learning = LearningManager(tmp_path)
    learning.learn(
        "Python",
        target_level="proficient",
        source_candidates=[
            {
                "source": "memory:learned:old",
                "content": "Python appears once inside an otherwise unrelated old help transcript. " * 30,
                "confidence": "medium",
            },
            {
                "source": "user:teach",
                "content": "Python functions are defined with def and may return values.",
                "confidence": "high",
            },
        ],
    )
    memory = MemoryStub([])
    command = LearningCommand(memory, learning=learning)

    command.handle("learn deeply about Python", "learn deeply about python")
    payload = learning.get("Python")

    assert [item["source"] for item in payload["sources"]] == ["user:teach"]
    assert payload["eval_report"] is None
    assert payload["review_status"] == "not-reviewed"
