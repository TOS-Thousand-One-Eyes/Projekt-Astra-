import json
import threading

from commands.learning_command import LearningCommand
from config.config import Config
from experience.experience_manager import ExperienceManager
from learning.self_learning import SelfLearningManager
from memory.memory_manager import MemoryManager


class ScanLanguageModule:
    available = True

    def __init__(self, response):
        self.response = response
        self.prompts = []

    def respond(self, prompt):
        self.prompts.append(prompt)
        return self.response


def test_implicit_chat_detection_is_disabled(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    assert manager.observe_user_message("Use Czech", previous_assistant="x") is None
    assert manager.status()["implicit_chat_detection"] is False
    assert manager.status()["conversation_scan_review_gated"] is True


def test_explicit_preference_auto_activates_in_auto_mode(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    candidate = manager.capture_preference("Keep answers concise.")
    assert candidate["type"] == "preference"
    assert manager.guidance()[0]["text"].endswith("Keep answers concise.")


def test_explicit_correction_is_review_gated_even_in_auto(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    candidate = manager.capture_correction(
        "That behavior was incorrect.", previous_assistant="Old behavior"
    )
    assert candidate["status"] == "pending"
    assert manager.guidance() == []
    assert manager.status()["training_traces"] == 1


def test_explicit_correction_uses_latest_assistant_reply_in_training_trace(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="review")
    manager.set_previous_assistant("The earlier ASTRA answer")

    candidate = manager.capture_correction("Use the corrected behavior.")
    trace = json.loads(manager.training_path.read_text(encoding="utf-8").strip())

    assert candidate["previous_assistant"] == "The earlier ASTRA answer"
    assert trace["assistant_before"] == "The earlier ASTRA answer"


def test_approved_correction_becomes_guidance(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    candidate = manager.capture_correction("Do not repeat that behavior.")
    manager.approve(candidate["id"])
    assert manager.guidance()


def test_model_suggested_preference_stays_review_gated_in_auto_mode(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    candidate = manager.capture_review_candidate(
        "preference",
        "Use short technical explanations.",
        source="conversation_scan:EXP-0001",
    )
    assert candidate["status"] == "pending"
    assert manager.guidance() == []


def test_conversation_scan_does_not_requeue_rejected_candidate(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="review")
    candidate = manager.capture_review_candidate(
        "memory_note",
        "The project server is called Orion.",
    )
    manager.reject(candidate["id"])

    repeated = manager.capture_review_candidate(
        "memory_note",
        "The project server is called Orion.",
    )

    assert repeated is None
    assert manager.pending() == []


def test_rejecting_candidate_deactivates_linked_guidance(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    candidate = manager.capture_preference("Keep answers concise.")
    assert manager.guidance()
    manager.reject(candidate["id"])
    assert manager.guidance() == []


def test_screen_observation_never_auto_activates_global_guidance(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    for _ in range(3):
        candidate = manager.observe_screen(
            "The same Python traceback appears after every run.",
            app="Code.exe",
            title="project.py",
            confidence="high",
        )
    assert candidate["hits"] == 3
    assert candidate["review_ready"] is True
    assert manager.guidance() == []


def test_screen_observation_redacts_secret_like_tokens(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="review")
    candidate = manager.observe_screen(
        "Terminal shows sk-or-v1-" + "a" * 48,
        app="cmd.exe",
        title="terminal",
    )
    assert "sk-or-v1-" not in candidate["content"]
    assert "REDACTED_SECRET" in candidate["content"]


def test_corrupt_self_learning_file_falls_back_with_warning(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="review")
    manager.candidates_path.write_text("{broken", encoding="utf-8")
    assert manager.pending() == []
    assert manager.load_warnings


def test_parallel_preference_and_screen_writes_leave_valid_json(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="review")

    def preferences():
        for i in range(20):
            manager.capture_preference(f"Preference number {i}")

    def eyes():
        for i in range(20):
            manager.observe_screen(
                f"Repeated workflow observation number {i}",
                app="Code.exe",
                title="project.py",
            )

    threads = [threading.Thread(target=preferences), threading.Thread(target=eyes)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    data = json.loads(manager.candidates_path.read_text(encoding="utf-8"))
    assert len(data) == 40


def test_self_learning_mode_command_persists_and_guidance_is_reviewable(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"version": "0.0.19", "self_learning_mode": "review"}),
        encoding="utf-8",
    )
    config = Config(config_path)
    manager = SelfLearningManager(tmp_path / "runtime", mode="review")
    command = LearningCommand(
        MemoryManager(data_dir=tmp_path / "memory"),
        self_learning=manager,
        config=config,
    )

    response = command.handle("self learning mode auto", "self learning mode auto")
    captured = command.handle(
        "self learning preference Keep answers concise.",
        "self learning preference keep answers concise.",
    )
    guidance = command.handle("self learning guidance", "self learning guidance")

    assert "Persisted to config.json" in response
    assert json.loads(config_path.read_text(encoding="utf-8"))["self_learning_mode"] == "auto"
    assert "Captured and activated preference" in captured
    assert "Keep answers concise" in guidance


def test_conversation_scan_queues_preference_and_memory_note_for_review(tmp_path):
    runtime = tmp_path / "runtime"
    experience = ExperienceManager(data_dir=runtime)
    experience.record_exchange(
        "I prefer answers with no more than three bullets.",
        "Understood.",
        command_name="LanguageModule",
    )
    experience.record_exchange(
        "Our test server is called Orion.",
        "Thanks.",
        command_name="LanguageModule",
    )
    language = ScanLanguageModule(
        json.dumps(
            {
                "candidates": [
                    {
                        "type": "preference",
                        "content": "Use no more than three bullets in answers.",
                        "exchange_id": "EXP-0001",
                    },
                    {
                        "type": "memory_note",
                        "content": "The user's test server is called Orion.",
                        "exchange_id": "EXP-0002",
                    },
                ]
            }
        )
    )
    manager = SelfLearningManager(runtime, mode="auto")
    memory = MemoryManager(data_dir=runtime)
    command = LearningCommand(
        memory,
        self_learning=manager,
        language_module=language,
        experience=experience,
    )

    response = command.handle("self learning scan", "self learning scan")

    assert "queued 2 candidate" in response
    assert len(manager.pending()) == 2
    assert manager.guidance() == []
    assert "untrusted data" in language.prompts[0]


def test_approved_conversation_memory_note_enters_personal_notes(tmp_path):
    manager = SelfLearningManager(tmp_path / "runtime", mode="review")
    memory = MemoryManager(data_dir=tmp_path / "memory")
    candidate = manager.capture_review_candidate(
        "memory_note",
        "The project test server is called Orion.",
    )
    command = LearningCommand(memory, self_learning=manager)

    response = command.handle(
        f"self learning approve {candidate['id']}",
        f"self learning approve {candidate['id'].lower()}",
    )

    assert "personal memory note" in response
    notes = [item for item in memory.recall_long() if item.get("type") == "note"]
    assert notes[0]["entry"] == "The project test server is called Orion."


def test_conversation_scan_rejects_invalid_model_json_without_queueing(tmp_path):
    experience = ExperienceManager(data_dir=tmp_path)
    experience.record_exchange("I like concise answers.", "Okay.")
    manager = SelfLearningManager(tmp_path, mode="review")
    command = LearningCommand(
        MemoryManager(data_dir=tmp_path / "memory"),
        self_learning=manager,
        language_module=ScanLanguageModule("not json"),
        experience=experience,
    )

    response = command.handle("self learning scan", "self learning scan")

    assert "invalid learning scan" in response
    assert manager.pending() == []
