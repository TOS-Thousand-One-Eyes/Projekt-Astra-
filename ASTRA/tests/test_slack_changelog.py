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
        "before": "a" * 40,
        "after": "b" * 40,
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
    assert "Finish Eyes lifecycle" in rendered
    assert "ASTRA/src/vision/screen_observer.py" in rendered
    assert payload["text"].startswith("ASTRA v0.0.20:")


def test_actions_push_without_file_arrays_uses_git_diff_paths():
    event = push_event()
    for commit in event["commits"]:
        commit.pop("added", None)
        commit.pop("modified", None)
        commit.pop("removed", None)
    captured = {}

    class Result:
        returncode = 0
        stdout = (
            b"ASTRA/src/identity/identity_manager.py\0"
            b"ASTRA/tests/test_identity.py\0"
        )

    def runner(command, **kwargs):
        captured["command"] = command
        captured.update(kwargs)
        return Result()

    paths = MODULE.collect_changed_files(event, Path("repo"), runner=runner)
    payload = MODULE.build_payload(event, changed_files=paths)
    rendered = json.dumps(payload, ensure_ascii=False)

    assert captured["command"][:3] == ["git", "diff", "--name-only"]
    assert paths == [
        "ASTRA/src/identity/identity_manager.py",
        "ASTRA/tests/test_identity.py",
    ]
    assert "Changed files:* 2" in rendered
    assert "src/identity (1)" in rendered


def test_file_collection_is_not_limited_by_commit_preview():
    event = push_event()
    event["commits"] = []
    for index in range(13):
        event["commits"].append(
            {
                "id": f"{index:040x}",
                "message": f"Commit {index}",
                "modified": [f"ASTRA/src/component_{index}/file.py"],
            }
        )

    rendered = json.dumps(MODULE.build_payload(event), ensure_ascii=False)

    assert "Commits:* 13" in rendered
    assert "Changed files:* 13" in rendered
    assert "ASTRA/src/component_12/file.py" in rendered


def test_component_names_cannot_create_slack_mentions():
    event = push_event()
    event["commits"][0]["modified"] = ["ASTRA/src/<!channel>/x.py"]
    event["commits"][0]["added"] = []

    rendered = json.dumps(MODULE.build_payload(event), ensure_ascii=False)

    assert "<!channel>" not in rendered
    assert "src/&lt;!channel&gt; (1)" in rendered


def test_component_summary_respects_slack_section_limit():
    files = [f"ASTRA/src/component_{index:04d}/file.py" for index in range(1000)]
    payload = MODULE.build_payload(push_event(), changed_files=files)
    summary = payload["blocks"][1]["text"]["text"]

    assert len(summary) <= MODULE.MAX_SECTION_CHARS


def test_non_utf8_git_path_is_replaced_before_slack_json_encoding():
    event = push_event()

    class Result:
        returncode = 0
        stdout = b"ASTRA/src/vision/invalid-\xff.py\0"

    paths = MODULE.collect_changed_files(
        event,
        Path("repo"),
        runner=lambda *args, **kwargs: Result(),
    )
    payload = MODULE.build_payload(event, changed_files=paths)

    json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert "\ufffd" in paths[0]


def test_slack_link_delimiters_in_event_urls_are_rejected():
    event = push_event()
    event["compare"] = "https://example.com/compare|<!channel>"
    event["commits"][0]["url"] = "https://example.com/commit|<!channel>"

    rendered = json.dumps(MODULE.build_payload(event), ensure_ascii=False)

    assert "<!channel>" not in rendered
    assert "Open GitHub comparison" not in rendered


def test_strip_markdown_preserves_identifier_underscores():
    assert MODULE.strip_markdown("Added `last_seen_version`.") == (
        "Added last_seen_version."
    )


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


def test_post_payload_rejects_non_2xx_response():
    class Response:
        status = 500

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    with pytest.raises(RuntimeError, match="HTTP 500"):
        MODULE.post_payload(
            "https://hooks.slack.com/services/T000/B000/secret",
            {"text": "hello"},
            opener=lambda *_args, **_kwargs: Response(),
        )


def test_current_version_has_matching_nonempty_changelog():
    project_root = Path(__file__).resolve().parents[1]

    release = MODULE.load_release_notes(project_root)

    assert release["source"] == f"CHANGELOG_PENDING_{release['version']}.md"
    assert release["sections"]
