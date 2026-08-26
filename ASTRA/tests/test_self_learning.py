import json
import threading

from learning.self_learning import SelfLearningManager


def test_implicit_chat_detection_is_disabled(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    assert manager.observe_user_message("Use Czech", previous_assistant="x") is None
    assert manager.status()["implicit_chat_detection"] is False


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


def test_approved_correction_becomes_guidance(tmp_path):
    manager = SelfLearningManager(tmp_path, mode="auto")
    candidate = manager.capture_correction("Do not repeat that behavior.")
    manager.approve(candidate["id"])
    assert manager.guidance()


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
