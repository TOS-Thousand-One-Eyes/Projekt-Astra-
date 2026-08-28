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


def release_notes(version="0.0.20"):
    return {
        "version": version,
        "source": f"CHANGELOG_PENDING_{version}.md",
        "sections": [
            {
                "title": "Learning",
                "items": [
                    {"text": "Added self-learning health checks."},
                    {"text": "Fixed stale guidance links."},
                ],
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


def test_build_payload_leads_with_versioned_release_notes():
    payload = MODULE.build_payload(push_event(), release=release_notes())
    rendered = json.dumps(payload, ensure_ascii=False)

    assert "ASTRA v0.0.20 changelog" in rendered
    assert "What's new in v0.0.20" in rendered
    assert "Added self-learning health checks" in rendered
    assert "Fixed stale guidance links" in rendered
    assert payload["text"].startswith("ASTRA v0.0.20:")


def test_load_release_notes_reads_matching_versioned_changelog(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "config.json").write_text(
        json.dumps({"version": "0.0.21"}),
        encoding="utf-8",
    )
    (tmp_path / "docs" / "CHANGELOG_PENDING_0.0.21.md").write_text(
        """# v0.0.21

## Learning Health Guard

- Added integrity checks that continue
  across a wrapped Markdown line.

## Verification

- 482 tests passed.
""",
        encoding="utf-8",
    )

    release = MODULE.load_release_notes(tmp_path)

    assert release["version"] == "0.0.21"
    assert release["source"] == "CHANGELOG_PENDING_0.0.21.md"
    assert release["sections"] == [
        {
            "title": "Learning Health Guard",
            "items": [
                {
                    "text": (
                        "Added integrity checks that continue across a wrapped "
                        "Markdown line."
                    )
                }
            ],
        }
    ]


def test_release_notes_are_redacted_and_cannot_create_slack_mentions():
    release = release_notes()
    release["sections"][0]["items"][0]["text"] = (
        "Notify <!channel> with sk-" + "a" * 40
    )

    rendered = json.dumps(
        MODULE.build_payload(push_event(), release=release),
        ensure_ascii=False,
    )

    assert "<!channel>" not in rendered
    assert "sk-" + "a" * 40 not in rendered
    assert "REDACTED_SECRET" in rendered


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
