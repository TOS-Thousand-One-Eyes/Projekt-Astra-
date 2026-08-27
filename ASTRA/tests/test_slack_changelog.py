import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "post_slack_changelog.py"
SPEC = importlib.util.spec_from_file_location("post_slack_changelog", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def push_event():
    return {
        "ref": "refs/heads/DEV-need-check",
        "compare": "https://github.com/example/astra/compare/a...b",
        "pusher": {"name": "Erik"},
        "repository": {
            "full_name": "example/astra",
            "html_url": "https://github.com/example/astra",
        },
        "commits": [
            {
                "id": "abcdef012345",
                "message": "Finish Eyes lifecycle\n\nDetails",
                "url": "https://github.com/example/astra/commit/abcdef0",
                "added": ["ASTRA/tests/test_screen_observer.py"],
                "modified": ["ASTRA/src/vision/screen_observer.py"],
                "removed": [],
            }
        ],
    }


def test_build_payload_summarizes_push_without_an_ai_call():
    payload = MODULE.build_payload(push_event())
    rendered = json.dumps(payload, ensure_ascii=False)

    assert "ASTRA changelog" in rendered
    assert "DEV-need-check" in rendered
    assert "Finish Eyes lifecycle" in rendered
    assert "src/vision (1)" in rendered
    assert "tests (1)" in rendered


def test_build_payload_redacts_secret_like_commit_text():
    event = push_event()
    event["commits"][0]["message"] = "Notify <!channel> and rotate sk-" + "a" * 40

    rendered = json.dumps(MODULE.build_payload(event))

    assert "sk-" + "a" * 40 not in rendered
    assert "REDACTED_SECRET" in rendered
    assert "<!channel>" not in rendered


def test_validate_webhook_rejects_non_slack_destination():
    with pytest.raises(ValueError, match="valid Slack Incoming Webhook"):
        MODULE.validate_webhook_url("https://example.com/collect")


def test_post_payload_uses_json_post_without_logging_webhook():
    captured = {}

    class Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    def opener(request, timeout):
        captured["method"] = request.method
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return Response()

    MODULE.post_payload(
        "https://hooks.slack.com/services/T000/B000/secret",
        {"text": "hello"},
        opener=opener,
    )

    assert captured == {
        "method": "POST",
        "timeout": 15,
        "payload": {"text": "hello"},
    }
