import json
import threading

from config.config import Config
from experience.experience_manager import ExperienceManager
from memory.context_builder import _tokens
from utils.ollama_client import OllamaClient


def test_experience_concurrent_records_are_unique_and_valid(tmp_path):
    manager = ExperienceManager(tmp_path)

    def worker(worker_id):
        for index in range(20):
            manager.record_exchange(
                f"u-{worker_id}-{index}",
                f"a-{worker_id}-{index}",
                source="test",
            )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    stored = json.loads(manager.path.read_text(encoding="utf-8"))["exchanges"]
    assert len(stored) == 80
    assert len({item["id"] for item in stored}) == 80


def test_generation_timeouts_are_bounded(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "version": "1",
                "language_generate_timeout": -5,
                "vision_generate_timeout": 999999,
            }
        ),
        encoding="utf-8",
    )
    config = Config(path)
    assert config.language_generate_timeout == 240.0
    assert config.vision_generate_timeout == 240.0
    assert sum("generate_timeout" in warning for warning in config.load_warnings) >= 2


def test_context_tokens_support_non_latin_text():
    assert "東京" in _tokens("東京 旅行 guide")
    assert "привет" in _tokens("Привет мир")


def test_ollama_capabilities_use_show_endpoint():
    calls = []

    def request(url, method="GET", data=None, timeout=3):
        calls.append((url, method, data))
        if url.endswith("/api/show"):
            return {"capabilities": ["completion", "vision"]}
        return {"models": [{"name": "gemma3:4b"}]}

    client = OllamaClient("http://x", "gemma3:4b", request_json=request)
    assert client.capabilities() == ["completion", "vision"]
    assert calls[-1][0].endswith("/api/show")
    assert calls[-1][1] == "POST"


def test_ollama_rejects_non_object_generation_payload():
    client = OllamaClient(
        "http://x",
        "gemma3:4b",
        request_json=lambda *_args, **_kwargs: ["not", "an", "object"],
    )
    try:
        client.generate("hello")
    except ValueError as error:
        assert "invalid response payload" in str(error)
    else:
        raise AssertionError("non-object Ollama payload should fail clearly")


def test_stale_learned_long_memory_is_not_injected_when_learning_store_is_authoritative():
    from memory.context_builder import build_model_prompt

    class Memory:
        def all_facts(self):
            return {}
        def recall_long(self):
            return [
                {
                    "type": "learned",
                    "entry": "Learned subject: Python. OLD STALE SUMMARY",
                    "timestamp": "old",
                }
            ]

    prompt = build_model_prompt("Python", Memory())
    assert "OLD STALE SUMMARY" not in prompt
