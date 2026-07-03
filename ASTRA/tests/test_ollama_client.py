import pytest

from utils.ollama_client import OllamaClient


def test_ensure_available_accepts_known_model():
    seen = []

    def request_json(url, method="GET", data=None, timeout=3):
        seen.append((url, method, data, timeout))
        return {"models": [{"name": "qwen3:4b"}]}

    client = OllamaClient("http://localhost:11434", "qwen3:4b", request_json=request_json)
    client.ensure_available()

    assert seen == [("http://localhost:11434/api/tags", "GET", None, 3)]


def test_ensure_available_raises_when_model_is_missing():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {"models": [{"name": "llama3.2:1b"}]},
    )

    with pytest.raises(ValueError, match="qwen3:4b"):
        client.ensure_available()


def test_generate_posts_prompt_and_returns_cleaned_response():
    seen = []

    def request_json(url, method="GET", data=None, timeout=3):
        seen.append((url, method, data, timeout))
        return {"response": "<think>internal</think>\nHello from Astra"}

    client = OllamaClient("http://localhost:11434", "qwen3:4b", request_json=request_json)
    response = client.generate("hello")

    assert response == "Hello from Astra"
    assert seen == [
        (
            "http://localhost:11434/api/generate",
            "POST",
            {"model": "qwen3:4b", "prompt": "hello", "stream": False},
            60,
        )
    ]


def test_generate_raises_on_empty_cleaned_response():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {"response": "<think>only hidden</think>"},
    )

    with pytest.raises(ValueError, match="empty response"):
        client.generate("hello")
