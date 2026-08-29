from utils.release_notes import ReleaseNotes, parse_release, version_key


def write_release(docs, version, body):
    path = docs / f"CHANGELOG_PENDING_{version}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def test_release_parser_keeps_user_changes_and_excludes_verification(tmp_path):
    path = write_release(
        tmp_path,
        "0.0.22",
        """# Pending CHANGELOG entry — v0.0.22
## Added
- Stable **profile data** outside the checkout.
  This survives source updates.
## Verification
- 500 tests passed.
""",
    )

    release = parse_release(path)

    assert release.version == "0.0.22"
    assert release.sections == (
        ("Added", ("Stable profile data outside the checkout. This survives source updates.",)),
    )


def test_release_parser_preserves_identifier_underscores(tmp_path):
    path = write_release(
        tmp_path,
        "0.0.22",
        "## Added\n- Added `ASTRA_DATA_DIR` and `last_seen_version`.\n",
    )

    release = parse_release(path)

    assert release.sections[0][1][0] == (
        "Added ASTRA_DATA_DIR and last_seen_version."
    )


def test_briefing_shows_only_versions_after_last_seen(tmp_path):
    write_release(tmp_path, "0.0.21", "## Fixed\n- Old fix.\n")
    write_release(tmp_path, "0.0.22", "## Added\n- New profile briefing.\n")
    notes = ReleaseNotes(tmp_path)

    briefing = notes.briefing("0.0.21", "0.0.22")

    assert "updated from v0.0.21 to v0.0.22" in briefing
    assert "New profile briefing" in briefing
    assert "Old fix" not in briefing


def test_first_seen_profile_gets_only_current_release(tmp_path):
    write_release(tmp_path, "0.0.21", "## Fixed\n- Old fix.\n")
    write_release(tmp_path, "0.0.22", "## Added\n- Current change.\n")

    briefing = ReleaseNotes(tmp_path).briefing(None, "0.0.22")

    assert "What's new in Astra v0.0.22" in briefing
    assert "Current change" in briefing
    assert "Old fix" not in briefing


def test_no_briefing_when_profile_already_saw_current_or_newer_version(tmp_path):
    notes = ReleaseNotes(tmp_path)
    assert notes.briefing("0.0.22", "0.0.22") is None
    assert notes.briefing("0.0.23", "0.0.22") is None


def test_missing_changelog_still_returns_a_bounded_generic_briefing(tmp_path):
    briefing = ReleaseNotes(tmp_path).briefing("0.0.21", "0.0.22")
    assert "current version" in briefing
    assert len(briefing) < 4000


def test_versions_require_numeric_major_minor_patch():
    assert version_key("0.0.22") == (0, 0, 22)
    assert version_key("1.2") is None
    assert version_key("1.two.3") is None
