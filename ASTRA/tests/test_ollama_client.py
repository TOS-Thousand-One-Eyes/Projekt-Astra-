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


def test_list_models_returns_sorted_model_metadata():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {
            "models": [
                {
                    "name": "zeta:latest",
                    "size": 123,
                    "details": {"parameter_size": "7B"},
                    "capabilities": ["completion"],
                },
                {
                    "model": "alpha:latest",
                    "details": {"parameter_size": "3B"},
                    "capabilities": ["completion", "tools"],
                },
            ]
        },
    )

    assert client.list_models() == [
        {
            "name": "alpha:latest",
            "size": None,
            "parameter_size": "3B",
            "capabilities": ["completion", "tools"],
        },
        {
            "name": "zeta:latest",
            "size": 123,
            "parameter_size": "7B",
            "capabilities": ["completion"],
        },
    ]


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


def test_generate_with_images_posts_base64_image_payload(tmp_path):
    image = tmp_path / "sample.png"
    image.write_bytes(b"image-bytes")
    seen = []

    def request_json(url, method="GET", data=None, timeout=3):
        seen.append((url, method, data, timeout))
        return {"response": "A small sample image."}

    client = OllamaClient("http://localhost:11434", "llava:latest", request_json=request_json)
    response = client.generate_with_images("describe", [image])

    assert response == "A small sample image."
    assert seen == [
        (
            "http://localhost:11434/api/generate",
            "POST",
            {
                "model": "llava:latest",
                "prompt": "describe",
                "images": ["aW1hZ2UtYnl0ZXM="],
                "stream": False,
            },
            60,
        )
    ]


def test_generate_strips_unclosed_think_block():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {
            "response": "<think>reasoning that got cut off before it could close"
        },
    )

    with pytest.raises(ValueError, match="empty response"):
        client.generate("hello")


def test_generate_keeps_a_mid_text_literal_think_tag_as_content():
    # Reasoning models emit <think> at the start; a <think> appearing after
    # real content is a literal mention, not markup - it used to truncate
    # everything after it.
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {
            "response": "Reasoning models wrap their reasoning in <think> tags."
        },
    )

    response = client.generate("hello")

    assert response == "Reasoning models wrap their reasoning in <think> tags."


def test_generate_keeps_literal_tags_in_an_answer_after_a_real_think_block():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {
            "response": "<think>how do I explain this</think>Wrap reasoning in <think> and </think> tags."
        },
    )

    response = client.generate("hello")

    assert response == "Wrap reasoning in <think> and </think> tags."


def test_generate_strips_repeated_leading_think_blocks():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {
            "response": "<think>first</think>\n<think>second</think>\nActual answer"
        },
    )

    response = client.generate("hello")

    assert response == "Actual answer"


def test_generate_strips_orphan_closing_think_tag_with_no_opener():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {
            "response": "stray reasoning fragment</think>Actual answer"
        },
    )

    response = client.generate("hello")

    assert response == "Actual answer"
    assert "</think>" not in response


def test_generate_raises_on_empty_cleaned_response():
    client = OllamaClient(
        "http://localhost:11434",
        "qwen3:4b",
        request_json=lambda url, method="GET", data=None, timeout=3: {"response": "<think>only hidden</think>"},
    )

    with pytest.raises(ValueError, match="empty response"):
        client.generate("hello")
