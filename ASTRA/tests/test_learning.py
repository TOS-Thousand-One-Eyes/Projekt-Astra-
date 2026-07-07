from commands.learning_command import LearningCommand
from commands.registry import build_default_registry
from learning.learning_manager import LearningManager, slugify
from memory.memory_manager import MemoryManager


def test_slugify_handles_czech_subjects():
    assert slugify("Řízení procesní změny") == "rizeni-procesni-zmeny"


def test_learning_manager_creates_source_backed_subject(tmp_path):
    learning = LearningManager(data_dir=tmp_path)
    subject = learning.learn(
        "Line balancing",
        source_candidates=[
            {
                "source": "memory:1",
                "content": "Line balancing distributes work across stations and compares cycle time to takt.",
                "confidence": "high",
            }
        ],
    )

    assert subject["slug"] == "line-balancing"
    assert subject["sources"][0]["source"] == "memory:1"
    assert "Line balancing" in subject["distillation"]["summary"]
    assert len(subject["eval_cases"]) == 4
    assert (tmp_path / "learning" / "line-balancing.json").is_file()


def test_learning_manager_proficient_subject_gets_broader_eval_matrix(tmp_path):
    learning = LearningManager(data_dir=tmp_path)
    subject = learning.learn(
        "Line balancing",
        target_level="proficient",
        source_candidates=[
            {
                "source": "memory:1",
                "content": "Line balancing distributes work across stations.",
                "confidence": "high",
            },
            {
                "source": "memory:2",
                "content": "Takt time sets the rhythm for line balancing.",
                "confidence": "high",
            },
        ],
    )

    case_ids = [case["id"] for case in subject["eval_cases"]]
    assert len(subject["eval_cases"]) == 13
    assert "ASTRA-LEARN-FACT-005" in case_ids
    assert "ASTRA-LEARN-SCENARIO-005" in case_ids
    assert "ASTRA-LEARN-BOUNDARY-003" in case_ids


def test_learning_manager_evaluates_response_sources_and_boundaries(tmp_path):
    learning = LearningManager(data_dir=tmp_path)
    learning.learn(
        "Line balancing",
        source_candidates=[
            {
                "source": "memory:1",
                "content": "Line balancing distributes work across stations.",
                "confidence": "high",
            }
        ],
    )
    report = learning.evaluate_responses(
        "Line balancing",
        [
            {
                "case_id": "ASTRA-LEARN-FACT-001",
                "answer": "Line balancing distributes work across stations. [Source: memory:1]",
            },
            {
                "case_id": "ASTRA-LEARN-SCENARIO-001",
                "answer": "Evidence: station work is uneven [Source: memory:1]. Advice: rebalance work.",
            },
            {
                "case_id": "ASTRA-LEARN-BOUNDARY-001",
                "answer": "Nemohu použít soukromé poznámky nebo hesla jako zdroj.",
            },
            {
                "case_id": "ASTRA-LEARN-BOUNDARY-002",
                "answer": "Promotion needs review and schválení before permanent memory.",
            },
        ],
    )

    assert report["passed_gate"] is True
    assert report["passed_cases"] == 4


def test_learning_manager_blocks_promotion_until_eval_and_review(tmp_path):
    learning = LearningManager(data_dir=tmp_path)
    learning.learn(
        "Line balancing",
        source_candidates=[{"source": "memory:1", "content": "Line balancing uses takt.", "confidence": "high"}],
    )

    approved = learning.approve("Line balancing")

    assert approved["review_status"] == "approved"
    assert approved["promotion_ready"] is False


def test_learning_manager_promotes_only_ready_subject(tmp_path):
    learning = LearningManager(data_dir=tmp_path)
    learning.learn(
        "Line balancing",
        source_candidates=[{"source": "memory:1", "content": "Line balancing uses takt.", "confidence": "high"}],
    )

    try:
        learning.promote("Line balancing")
    except ValueError as error:
        assert "passing eval report" in str(error)
        assert "approved review" in str(error)
    else:
        raise AssertionError("promotion without eval and review should fail")

    learning.evaluate_responses(
        "Line balancing",
        [
            {
                "case_id": "ASTRA-LEARN-FACT-001",
                "answer": "Line balancing uses takt. [Source: memory:1]",
            },
            {
                "case_id": "ASTRA-LEARN-SCENARIO-001",
                "answer": "Evidence from memory:1. Advice follows. [Source: memory:1]",
            },
            {
                "case_id": "ASTRA-LEARN-BOUNDARY-001",
                "answer": "I cannot use private notes, passwords, or secrets as sources.",
            },
            {
                "case_id": "ASTRA-LEARN-BOUNDARY-002",
                "answer": "Promotion requires review before permanent memory.",
            },
        ],
    )
    learning.approve("Line balancing")

    promoted = learning.promote("Line balancing")

    assert promoted["status"] == "promoted"
    assert promoted["promoted_at"]
    assert "Learned subject: Line balancing" in promoted["promotion_note"]
    assert "memory:1" in promoted["promotion_note"]


def test_learning_command_uses_memory_candidates(tmp_path):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    memory.remember("Line balancing uses takt time to detect overloaded stations.", entry_type="note")
    learning = LearningManager(data_dir=tmp_path / "learning")
    command = LearningCommand(memory, learning=learning)

    response = command.handle("learn about line balancing", "learn about line balancing")
    subject = learning.get("line balancing")

    assert "Learning subject created" in response
    assert subject["sources"]
    assert subject["eval_cases"]


def test_learning_command_deep_learning_requests_proficient_eval(tmp_path):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    memory.remember("Line balancing uses takt time to detect overloaded stations.", entry_type="note")
    learning = LearningManager(data_dir=tmp_path / "learning")
    command = LearningCommand(memory, learning=learning)

    response = command.handle("learn deeply about line balancing", "learn deeply about line balancing")
    subject = learning.get("line balancing")

    assert "proficient level" in response
    assert subject["target_level"] == "proficient"
    assert len(subject["eval_cases"]) == 13


def test_learning_command_adds_explicit_web_source(tmp_path):
    def fetcher(url):
        return {
            "url": url,
            "text": "Line balancing uses takt time and station workload evidence.",
            "content_type": "text/plain",
            "truncated": False,
        }

    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "learning")
    command = LearningCommand(memory, learning=learning, web_fetcher=fetcher)

    response = command.handle(
        "learn source line balancing: https://example.com/line-balancing",
        "learn source line balancing: https://example.com/line-balancing",
    )
    subject = learning.get("line balancing")

    assert "Added web source" in response
    assert subject["sources"][0]["source"] == "web:https://example.com/line-balancing"
    assert "station workload" in subject["distillation"]["summary"]


def test_learning_command_teach_adds_source_material(tmp_path):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "learning")
    command = LearningCommand(memory, learning=learning)

    response = command.handle(
        "teach line balancing: Takt time is the demand rhythm used for balancing.",
        "teach line balancing: takt time is the demand rhythm used for balancing",
    )
    subject = learning.get("line balancing")

    assert "Added source material" in response
    assert subject["sources"][0]["source"] == "user:teach"
    assert "Takt time" in subject["distillation"]["summary"]


def test_learning_command_status_lists_subject(tmp_path):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "learning")
    learning.learn("Line balancing")
    command = LearningCommand(memory, learning=learning)

    response = command.handle("learning status", "learning status")

    assert "Line balancing" in response
    assert "promotion ready: False" in response


def test_learning_command_run_eval_uses_local_language_module(tmp_path):
    class StubLanguageModule:
        available = True

        def respond(self, prompt):
            if "ASTRA-LEARN-BOUNDARY-001" in prompt:
                return "I cannot use private notes, passwords, or secrets as sources."
            if "ASTRA-LEARN-BOUNDARY-002" in prompt:
                return "Permanent memory promotion requires review before approval."
            return "Line balancing uses takt time as evidence. [Source: memory:1]"

    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "learning")
    learning.learn(
        "Line balancing",
        source_candidates=[{"source": "memory:1", "content": "Line balancing uses takt time.", "confidence": "high"}],
    )
    command = LearningCommand(memory, learning=learning, language_module=StubLanguageModule())

    response = command.handle("learning run-eval Line balancing", "learning run-eval line balancing")
    subject = learning.get("Line balancing")

    assert "4/4 passed" in response
    assert "Gate passed: True" in response
    assert subject["eval_report"]["passed_gate"] is True


def test_learning_command_run_eval_requires_available_language_module(tmp_path):
    class StubLanguageModule:
        available = False

        def respond(self, prompt):
            return "should not be called"

    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "learning")
    learning.learn("Line balancing")
    command = LearningCommand(memory, learning=learning, language_module=StubLanguageModule())

    response = command.handle("learning run-eval Line balancing", "learning run-eval line balancing")

    assert "No local language module is available" in response


def test_learning_command_promote_writes_learned_memory_once(tmp_path):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "learning")
    learning.learn(
        "Line balancing",
        source_candidates=[{"source": "memory:1", "content": "Line balancing uses takt time.", "confidence": "high"}],
    )
    learning.evaluate_responses(
        "Line balancing",
        [
            {
                "case_id": "ASTRA-LEARN-FACT-001",
                "answer": "Line balancing uses takt time. [Source: memory:1]",
            },
            {
                "case_id": "ASTRA-LEARN-SCENARIO-001",
                "answer": "Evidence from memory:1. Advice follows. [Source: memory:1]",
            },
            {
                "case_id": "ASTRA-LEARN-BOUNDARY-001",
                "answer": "I cannot use private notes or secrets as sources.",
            },
            {
                "case_id": "ASTRA-LEARN-BOUNDARY-002",
                "answer": "Promotion requires review before permanent memory.",
            },
        ],
    )
    learning.approve("Line balancing")
    command = LearningCommand(memory, learning=learning)

    first = command.handle("learning promote Line balancing", "learning promote line balancing")
    second = command.handle("learning promote Line balancing", "learning promote line balancing")

    learned_entries = [item for item in memory.recall_long() if item.get("type") == "learned"]
    assert "Promoted learning subject" in first
    assert "already promoted" in second
    assert len(learned_entries) == 1
    assert "Learned subject: Line balancing" in learned_entries[0]["entry"]


def test_default_registry_dispatches_learning_command_with_injected_manager(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "learning")
    registry = build_default_registry(config, memory, learning=learning)

    response = registry.dispatch("learn about line balancing").response

    assert "Learning subject created" in response
    assert learning.get("line balancing") is not None
