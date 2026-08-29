from utils.release_notes import (
    build_version_briefing,
    compare_versions,
    extract_release_items,
    load_release_notes,
)


def write_release(root, version, bullets):
    path = root / f"CHANGELOG_PENDING_{version}.md"
    body = "\n".join(f"- {item}" for item in bullets)
    path.write_text(f"# v{version}\n\n## Added\n\n{body}\n", encoding="utf-8")


def test_upgrade_briefing_lists_every_crossed_release(tmp_path):
    write_release(tmp_path, "0.0.20", ["Added **profiles**."])
    write_release(tmp_path, "0.0.21", ["Added `verified_backups`."])
    write_release(tmp_path, "0.0.22", ["Added persistent version tracking."])

    briefing = build_version_briefing(
        "Petr",
        "0.0.19",
        "0.0.22",
        docs_dir=tmp_path,
    )

    assert briefing.kind == "upgrade"
    assert briefing.mark_seen is True
    assert "Last seen on ASTRA v0.0.19" in briefing.text
    assert "installed version is now v0.0.22" in briefing.text
    assert "v0.0.20" in briefing.text
    assert "v0.0.21" in briefing.text
    assert "v0.0.22" in briefing.text
    assert "verified_backups" in briefing.text


def test_first_seen_initializes_tracking_without_claiming_an_upgrade(tmp_path):
    briefing = build_version_briefing("Erik", None, "0.0.22", docs_dir=tmp_path)

    assert briefing.kind == "first_seen"
    assert briefing.mark_seen is True
    assert "first recorded on ASTRA v0.0.22" in briefing.text


def test_same_version_does_not_repeat_the_update_message(tmp_path):
    briefing = build_version_briefing(
        "Erik",
        "0.0.22",
        "0.0.22",
        docs_dir=tmp_path,
    )

    assert briefing.kind == "current"
    assert briefing.text is None
    assert briefing.mark_seen is True


def test_older_checkout_warns_without_downgrading_last_seen(tmp_path):
    briefing = build_version_briefing(
        "Petr",
        "0.0.22",
        "0.0.21",
        docs_dir=tmp_path,
    )

    assert briefing.kind == "downgrade"
    assert briefing.mark_seen is False
    assert "checkout is older" in briefing.text


def test_release_loader_excludes_versions_outside_the_upgrade_range(tmp_path):
    write_release(tmp_path, "0.0.19", ["Old."])
    write_release(tmp_path, "0.0.20", ["Current range."])
    write_release(tmp_path, "0.0.23", ["Future."])

    assert load_release_notes("0.0.19", "0.0.22", docs_dir=tmp_path) == [
        ("0.0.20", ["Current range."])
    ]


def test_release_item_cleanup_preserves_identifier_underscores():
    items = extract_release_items("- Added `last_seen_version` with **safe storage**.\n")

    assert items == ["Added last_seen_version with safe storage."]


def test_release_items_exclude_verification_and_manual_sections():
    markdown = """# v0.0.22

## Added
- User-facing change.

## Verification
- 500 tests passed.

## Manual checks still required
- Push to Slack.
"""

    assert extract_release_items(markdown, max_items=10) == ["User-facing change."]


def test_dotted_version_comparison_zero_pads_short_versions():
    assert compare_versions("1.2", "1.2.0") == 0
    assert compare_versions("1.2.1", "1.2") == 1
