"""Read bounded, user-facing update notes from versioned changelog files."""

import re
from dataclasses import dataclass
from pathlib import Path


VERSION_PATTERN = re.compile(
    r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?P<suffix>[-+][A-Za-z0-9.-]+)?$"
)
EXCLUDED_SECTIONS = {
    "verification",
    "tests",
    "manual checks",
    "manual checks still required",
}
MAX_SECTIONS = 6
MAX_ITEMS = 16
MAX_ITEM_CHARS = 320
MAX_BRIEFING_CHARS = 4000


@dataclass(frozen=True)
class Release:
    version: str
    sections: tuple


class ReleaseNotes:
    def __init__(self, docs_dir):
        self.docs_dir = Path(docs_dir)

    def updates_since(self, last_seen_version, current_version):
        current_key = version_key(current_version)
        if current_key is None:
            return []
        if last_seen_version:
            last_key = version_key(last_seen_version)
            if last_key is None or last_key >= current_key:
                return []
        else:
            last_key = None

        releases = []
        if self.docs_dir.is_dir():
            for path in self.docs_dir.glob("CHANGELOG_PENDING_*.md"):
                version = version_from_path(path)
                key = version_key(version)
                if key is None or key > current_key:
                    continue
                if last_key is None and key != current_key:
                    continue
                if last_key is not None and key <= last_key:
                    continue
                release = parse_release(path, version)
                if release:
                    releases.append(release)
        return sorted(releases, key=lambda item: version_key(item.version))

    def briefing(self, last_seen_version, current_version):
        current = str(current_version or "").strip()
        if version_key(current) is None:
            return None
        if last_seen_version and version_key(last_seen_version) >= version_key(current):
            return None

        releases = self.updates_since(last_seen_version, current)
        if last_seen_version:
            lines = [
                f"Astra was updated from v{last_seen_version} to v{current}.",
                "What's new:",
            ]
        else:
            lines = [f"What's new in Astra v{current}:"]

        remaining = MAX_ITEMS
        for release in releases:
            if len(releases) > 1:
                lines.append(f"v{release.version}")
            for title, items in release.sections[:MAX_SECTIONS]:
                if remaining <= 0:
                    break
                selected = items[:remaining]
                if not selected:
                    continue
                lines.append(f"{title}:")
                lines.extend(f"- {item}" for item in selected)
                remaining -= len(selected)
        if not releases:
            lines.append("- This profile is now running the current version.")
        elif remaining <= 0:
            lines.append("- More details are available in the version changelog.")
        return "\n".join(lines)[:MAX_BRIEFING_CHARS]


def parse_release(path, version=None):
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return None
    version = str(version or version_from_path(path) or "").strip()
    if version_key(version) is None:
        return None

    sections = []
    current = None
    current_item = None
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## ") and not stripped.startswith("### "):
            title = plain_text(stripped[3:])
            current = None
            current_item = None
            if title and title.casefold() not in EXCLUDED_SECTIONS:
                current = [title, []]
                sections.append(current)
            continue
        if stripped.startswith("# "):
            current = None
            current_item = None
            continue
        if current is None:
            continue
        if stripped.startswith("- "):
            item = plain_text(stripped[2:])[:MAX_ITEM_CHARS]
            if item:
                current[1].append(item)
                current_item = len(current[1]) - 1
            continue
        if current_item is not None and stripped and not stripped.startswith("#"):
            continuation = plain_text(stripped)
            if continuation:
                joined = f"{current[1][current_item]} {continuation}"
                current[1][current_item] = joined[:MAX_ITEM_CHARS]

    clean_sections = tuple(
        (title, tuple(items)) for title, items in sections if items
    )
    return Release(version=version, sections=clean_sections)


def version_from_path(path):
    match = re.fullmatch(r"CHANGELOG_PENDING_(.+)\.md", Path(path).name)
    return match.group(1) if match else None


def version_key(version):
    match = VERSION_PATTERN.fullmatch(str(version or "").strip())
    if not match:
        return None
    return tuple(int(match.group(name)) for name in ("major", "minor", "patch"))


def plain_text(value):
    text = str(value or "")
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", text)
    # Preserve underscores inside identifiers such as ASTRA_DATA_DIR and
    # last_seen_version; they are content, not emphasis markers.
    text = re.sub(r"[*`>#]+", "", text)
    return " ".join(text.split()).strip()
