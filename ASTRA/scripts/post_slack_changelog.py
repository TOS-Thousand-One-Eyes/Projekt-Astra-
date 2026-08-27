"""Post a deterministic GitHub push changelog to a Slack Incoming Webhook."""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

MAX_COMMITS = 12
MAX_FILES = 40
MAX_SECTION_CHARS = 2900


def build_payload(event):
    repository = event.get("repository") or {}
    repo_name = clean(repository.get("full_name") or "unknown repository", 180)
    repo_url = repository.get("html_url") or ""
    branch = clean(str(event.get("ref") or "").removeprefix("refs/heads/"), 120)
    pusher = clean((event.get("pusher") or {}).get("name") or "unknown", 120)
    compare_url = safe_http_url(event.get("compare"))
    commits = [item for item in event.get("commits") or [] if isinstance(item, dict)]

    commit_lines = []
    changed_files = []
    for commit in commits[:MAX_COMMITS]:
        short_id = clean(str(commit.get("id") or "")[:7] or "unknown", 12)
        message = clean(str(commit.get("message") or "").splitlines()[0], 220)
        commit_url = safe_http_url(commit.get("url"))
        marker = f"<{commit_url}|`{short_id}`>" if commit_url else f"`{short_id}`"
        commit_lines.append(f"• {marker} {message or '(no commit message)'}")
        for field in ("added", "modified", "removed"):
            for path in commit.get(field) or []:
                if isinstance(path, str) and path not in changed_files:
                    changed_files.append(path)

    if len(commits) > MAX_COMMITS:
        commit_lines.append(f"• …and {len(commits) - MAX_COMMITS} more commit(s)")
    if not commit_lines:
        commit_lines.append("• Push contained no commit details.")

    component_counts = summarize_components(changed_files)
    component_text = ", ".join(
        f"{name} ({count})" for name, count in component_counts.items()
    ) or "no file list supplied by GitHub"
    file_preview = ", ".join(clean(path, 160) for path in changed_files[:MAX_FILES])
    if len(changed_files) > MAX_FILES:
        file_preview += f", …and {len(changed_files) - MAX_FILES} more"

    title_repo = f"<{repo_url}|{repo_name}>" if safe_http_url(repo_url) else repo_name
    summary = (
        f"*Repository:* {title_repo}\n"
        f"*Branch:* `{branch or 'unknown'}`   *Pushed by:* {pusher}\n"
        f"*Commits:* {len(commits)}   *Changed files:* {len(changed_files)}\n"
        f"*Components:* {component_text}"
    )
    details = "\n".join(commit_lines)
    if file_preview:
        details += f"\n\n*Files:* {file_preview}"
    if compare_url:
        details += f"\n\n<{compare_url}|Open GitHub comparison>"
    details = details[:MAX_SECTION_CHARS]

    fallback = clean(
        f"ASTRA changelog: {repo_name} {branch or 'unknown'} — "
        f"{len(commits)} commit(s), {len(changed_files)} changed file(s).",
        500,
    )
    return {
        "text": fallback,
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "ASTRA changelog"},
            },
            {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
            {"type": "section", "text": {"type": "mrkdwn", "text": details}},
        ],
    }


def summarize_components(paths):
    counts = {}
    for raw_path in paths:
        path = str(raw_path).replace("\\", "/")
        if path.startswith("ASTRA/"):
            path = path[len("ASTRA/"):]
        parts = [part for part in path.split("/") if part]
        if not parts:
            component = "repository"
        elif parts[0] == "src" and len(parts) > 1:
            component = f"src/{parts[1]}"
        elif parts[0] in {"tests", "docs", "scripts"}:
            component = parts[0]
        elif parts[0] == ".github":
            component = "automation"
        else:
            component = parts[0]
        counts[component] = counts.get(component, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def clean(value, limit):
    text = " ".join(str(value or "").split())
    patterns = (
        r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b",
        r"\bsk-[A-Za-z0-9_-]{20,}\b",
        r"https://hooks\.slack(?:-gov)?\.com/services/[A-Za-z0-9/_-]+",
        r"\b(?:0x)?[A-Fa-f0-9]{64}\b",
    )
    for pattern in patterns:
        text = re.sub(pattern, "[REDACTED_SECRET]", text, flags=re.IGNORECASE)
    # Commit messages and paths are untrusted Slack mrkdwn data. Escaping angle
    # brackets prevents <!channel> / user mention injection from a commit title.
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return text[:limit]


def safe_http_url(value):
    text = str(value or "").strip()
    parsed = urlparse(text)
    return text if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def validate_webhook_url(value):
    parsed = urlparse(str(value or "").strip())
    allowed_hosts = {"hooks.slack.com", "hooks.slack-gov.com"}
    if (
        parsed.scheme != "https"
        or parsed.hostname not in allowed_hosts
        or not parsed.path.startswith("/services/")
    ):
        raise ValueError("SLACK_WEBHOOK_URL is not a valid Slack Incoming Webhook URL.")
    return parsed.geturl()


def post_payload(webhook_url, payload, opener=urllib.request.urlopen):
    url = validate_webhook_url(webhook_url)
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with opener(request, timeout=15) as response:
        status = getattr(response, "status", 200)
        if not 200 <= int(status) < 300:
            raise RuntimeError(f"Slack webhook returned HTTP {status}.")


def main():
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "")
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    if not webhook:
        print("Slack changelog skipped: SLACK_WEBHOOK_URL is not configured.")
        return 0
    if not event_path.is_file():
        print("Slack changelog failed: GITHUB_EVENT_PATH is unavailable.", file=sys.stderr)
        return 2

    try:
        event = json.loads(event_path.read_text(encoding="utf-8"))
        post_payload(webhook, build_payload(event))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Slack changelog failed: {error}", file=sys.stderr)
        return 1
    print("Slack changelog posted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
