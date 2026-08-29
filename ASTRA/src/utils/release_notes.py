import re
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"
PENDING_CHANGELOG_RE = re.compile(
    r"^CHANGELOG_PENDING_(\d+(?:\.\d+)+)\.md$",
    re.IGNORECASE,
)
VERSION_RE = re.compile(r"^\d+(?:\.\d+)*$")
EXCLUDED_SECTIONS = {
    "verification",
    "manual checks",
    "manual checks still required",
}


@dataclass(frozen=True)
class VersionBriefing:
    kind: str
    previous_version: str | None
    current_version: str
    text: str | None
    mark_seen: bool


def build_version_briefing(
    display_name,
    previous_version,
    current_version,
    docs_dir=DOCS_DIR,
):
    """Describe an upgrade for one profile without mutating profile state."""
    current = normalize_version(current_version)
    previous = normalize_version(previous_version)
    name = str(display_name or "User").strip() or "User"

    if current is None:
        return VersionBriefing(
            kind="unknown",
            previous_version=previous,
            current_version=str(current_version or "unknown"),
            text=None,
            mark_seen=False,
        )

    if previous is None:
        return VersionBriefing(
            kind="first_seen",
            previous_version=None,
            current_version=current,
            text=(
                f"Version tracking is now active for {name}. "
                f"This profile was first recorded on ASTRA v{current}."
            ),
            mark_seen=True,
        )

    comparison = compare_versions(current, previous)
    if comparison < 0:
        return VersionBriefing(
            kind="downgrade",
            previous_version=previous,
            current_version=current,
            text=(
                f"{name}, this profile was last used with ASTRA v{previous}, "
                f"but the running checkout is older (v{current}). "
                "The newer last-seen version was kept."
            ),
            mark_seen=False,
        )
    if comparison == 0:
        return VersionBriefing(
            kind="current",
            previous_version=previous,
            current_version=current,
            text=None,
            mark_seen=True,
        )

    releases = load_release_notes(
        previous,
        current,
        docs_dir=docs_dir,
    )
    lines = [
        f"Welcome back, {name}. Last seen on ASTRA v{previous}; "
        f"the installed version is now v{current}.",
        "What's new:",
    ]
    if releases:
        for version, items in releases:
            lines.append(f"- v{version}:")
            lines.extend(f"  - {item}" for item in items)
    else:
        lines.append("- See the project changelog for this version's details.")
    return VersionBriefing(
        kind="upgrade",
        previous_version=previous,
        current_version=current,
        text="\n".join(lines),
        mark_seen=True,
    )


def load_release_notes(
    previous_version,
    current_version,
    docs_dir=DOCS_DIR,
    max_items_per_version=4,
):
    """Load concise bullets for every pending release crossed by an upgrade."""
    previous = normalize_version(previous_version)
    current = normalize_version(current_version)
    if previous is None or current is None:
        return []

    root = Path(docs_dir)
    releases = []
    try:
        paths = list(root.glob("CHANGELOG_PENDING_*.md"))
    except OSError:
        return []
    for path in paths:
        match = PENDING_CHANGELOG_RE.match(path.name)
        if not match:
            continue
        version = normalize_version(match.group(1))
        if version is None:
            continue
        if compare_versions(version, previous) <= 0:
            continue
        if compare_versions(version, current) > 0:
            continue
        try:
            markdown = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError):
            continue
        items = extract_release_items(markdown, max_items=max_items_per_version)
        if items:
            releases.append((version, items))
    return sorted(releases, key=lambda item: version_tuple(item[0]))


def extract_release_items(markdown, max_items=4):
    items = []
    include_section = True
    for raw_line in str(markdown or "").splitlines():
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            title = clean_markdown(stripped[3:]).casefold()
            include_section = title not in EXCLUDED_SECTIONS
            continue
        if stripped.startswith("# "):
            include_section = True
            continue
        if not include_section:
            continue
        if not stripped.startswith("- "):
            continue
        item = clean_markdown(stripped[2:])
        if not item or item in items:
            continue
        items.append(item)
        if len(items) >= max(1, int(max_items)):
            break
    return items


def clean_markdown(value):
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", str(value or ""))
    text = text.replace("`", "").replace("**", "").replace("__", "")
    return " ".join(text.split()).strip()


def normalize_version(value):
    text = str(value or "").strip()
    if not VERSION_RE.fullmatch(text):
        return None
    return ".".join(str(int(part)) for part in text.split("."))


def version_tuple(value):
    normalized = normalize_version(value)
    if normalized is None:
        return ()
    return tuple(int(part) for part in normalized.split("."))


def compare_versions(first, second):
    first_parts = version_tuple(first)
    second_parts = version_tuple(second)
    if not first_parts or not second_parts:
        raise ValueError("Both versions must contain only dotted integers.")
    width = max(len(first_parts), len(second_parts))
    first_parts += (0,) * (width - len(first_parts))
    second_parts += (0,) * (width - len(second_parts))
    return (first_parts > second_parts) - (first_parts < second_parts)
