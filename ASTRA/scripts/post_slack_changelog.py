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
MAX_RELEASE_ITEMS = 30
MAX_SECTION_CHARS = 2900
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?$")
EXCLUDED_CHANGELOG_SECTIONS = {
    "verification",
    "manual checks",
    "manual checks still required",
}


def build_payload(event, release=None):
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
        + (
            f"*Version:* `{clean(release['version'], 80)}`\n"
            if release and release.get("version")
            else ""
        )
        + f"*Commits:* {len(commits)}   *Changed files:* {len(changed_files)}\n"
        f"*Components:* {component_text}"
    )
    release_blocks = format_release_blocks(release)
    if release_blocks:
        detail_blocks = release_blocks
    else:
        details = "\n".join(commit_lines)
        if file_preview:
            details += f"\n\n*Files:* {file_preview}"
        detail_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": details[:MAX_SECTION_CHARS],
                },
            }
        ]
    if compare_url:
        detail_blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"<{compare_url}|Open GitHub comparison>",
                },
            }
        )

    version = clean((release or {}).get("version", ""), 80)
    release_items = [
        item.get("text", "")
        for section in (release or {}).get("sections", [])
        for item in section.get("items", [])
        if item.get("text")
    ]
    if version and release_items:
        fallback = clean(f"ASTRA v{version}: {release_items[0]}", 500)
    else:
        fallback = clean(
            f"ASTRA changelog: {repo_name} {branch or 'unknown'} — "
            f"{len(commits)} commit(s), {len(changed_files)} changed file(s).",
            500,
        )
    header = f"ASTRA v{version} changelog" if version else "ASTRA changelog"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header[:150]},
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": summary}},
    ]
    blocks.extend(detail_blocks)
    return {
        "text": fallback,
        "blocks": blocks,
    }


def load_release_notes(project_root):
    root = Path(project_root)
    config_path = root / "config.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Could not load the ASTRA version from config.json: {error}") from error
    version = str(config.get("version", "")).strip() if isinstance(config, dict) else ""
    if not VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"ASTRA config.json has an invalid version: {version!r}.")

    candidates = (
        root / "docs" / f"CHANGELOG_PENDING_{version}.md",
        root / "docs" / f"CHANGELOG_{version}.md",
    )
    changelog_path = next((path for path in candidates if path.is_file()), None)
    if changelog_path is None:
        return {"version": version, "sections": [], "source": None}
    try:
        markdown = changelog_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"Could not read {changelog_path.name}: {error}") from error
    return {
        "version": version,
        "sections": parse_release_sections(markdown),
        "source": changelog_path.name,
    }


def parse_release_sections(markdown):
    sections = []
    current = None
    current_item = None
    for raw_line in str(markdown or "").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            title = strip_markdown(stripped[3:])
            if title.casefold() in EXCLUDED_CHANGELOG_SECTIONS:
                current = None
            else:
                current = {"title": title, "items": []}
                sections.append(current)
            current_item = None
            continue
        if stripped.startswith("# "):
            current = None
            current_item = None
            continue
        if current is None:
            continue
        if stripped.startswith("- "):
            text = strip_markdown(stripped[2:])
            if text:
                current_item = {"text": text}
                current["items"].append(current_item)
            continue
        if current_item and stripped and not stripped.startswith("#"):
            current_item["text"] += " " + strip_markdown(stripped)

    return [section for section in sections if section["items"]]


def format_release_blocks(release):
    if not release or not release.get("sections"):
        return []
    blocks = []
    remaining = MAX_RELEASE_ITEMS
    first = True
    for section in release["sections"]:
        if remaining <= 0:
            break
        title = clean(section.get("title", "Changes"), 160)
        items = section.get("items", [])[:remaining]
        if not items:
            continue
        prefix = (
            f"*What's new in v{clean(release.get('version', ''), 80)}:*\n\n"
            if first
            else ""
        )
        lines = [prefix + f"*{title}*"]
        for item in items:
            line = f"• {clean(item.get('text', ''), 500)}"
            candidate = "\n".join(lines + [line])
            if len(candidate) > MAX_SECTION_CHARS:
                blocks.append(slack_section("\n".join(lines)))
                lines = [f"*{title} (continued)*", line]
            else:
                lines.append(line)
        remaining -= len(items)
        blocks.append(slack_section("\n".join(lines)))
        first = False
    total_items = sum(len(section.get("items", [])) for section in release["sections"])
    if total_items > MAX_RELEASE_ITEMS:
        blocks.append(
            slack_section(
                f"• …and {total_items - MAX_RELEASE_ITEMS} more change(s)"
            )
        )
    return blocks


def format_release_notes(release):
    return "\n\n".join(
        block["text"]["text"]
        for block in format_release_blocks(release)
    )


def slack_section(text):
    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": str(text)[:MAX_SECTION_CHARS]},
    }


def strip_markdown(value):
    text = " ".join(str(value or "").split())
    return re.sub(r"[*_`]+", "", text).strip()


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
        project_root = Path(__file__).resolve().parents[1]
        release = load_release_notes(project_root)
        post_payload(webhook, build_payload(event, release=release))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Slack changelog failed: {error}", file=sys.stderr)
        return 1
    print("Slack changelog posted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
