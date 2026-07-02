from utils.update_checker import UpdateChecker


def test_no_message_when_versions_equal():
    checker = UpdateChecker("0.0.8", fetch=lambda: "0.0.8")
    assert checker.check() is None


def test_no_message_when_local_is_newer():
    checker = UpdateChecker("0.1.0", fetch=lambda: "0.0.8")
    assert checker.check() is None


def test_message_when_remote_is_newer():
    checker = UpdateChecker("0.0.8", fetch=lambda: "0.0.9")
    message = checker.check()
    assert message is not None
    assert "0.0.9" in message
    assert checker.repo_url in message


def test_none_when_fetch_raises_network_error():
    def failing_fetch():
        raise OSError("no internet")

    checker = UpdateChecker("0.0.8", fetch=failing_fetch)
    assert checker.check() is None


def test_none_when_remote_version_is_malformed():
    checker = UpdateChecker("0.0.8", fetch=lambda: "not-a-version")
    assert checker.check() is None


def test_none_when_fetch_returns_none():
    checker = UpdateChecker("0.0.8", fetch=lambda: None)
    assert checker.check() is None


def test_none_when_fetch_returns_wrong_type():
    checker = UpdateChecker("0.0.8", fetch=lambda: 8)
    assert checker.check() is None


def test_version_comparison_handles_different_segment_counts():
    checker = UpdateChecker("0.9", fetch=lambda: "0.10.0")
    message = checker.check()
    assert message is not None
    assert "0.10.0" in message
