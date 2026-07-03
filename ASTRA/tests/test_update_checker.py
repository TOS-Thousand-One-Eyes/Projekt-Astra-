from utils.logger import Logger
from utils.update_checker import UpdateChecker


def test_logs_up_to_date_when_versions_equal():
    logger = Logger()
    checker = UpdateChecker("0.0.8", logger, fetch=lambda: "0.0.8")
    checker.check()
    assert any("up to date" in entry for entry in logger.get_logs())


def test_logs_up_to_date_when_local_is_newer():
    logger = Logger()
    checker = UpdateChecker("0.1.0", logger, fetch=lambda: "0.0.8")
    checker.check()
    assert any("up to date" in entry for entry in logger.get_logs())


def test_logs_message_when_remote_is_newer():
    logger = Logger()
    checker = UpdateChecker("0.0.8", logger, fetch=lambda: "0.0.9")
    checker.check()
    logs = logger.get_logs()
    assert any("0.0.9" in entry and checker.repo_url in entry for entry in logs)
    assert not any("up to date" in entry for entry in logs)


def test_version_comparison_handles_different_segment_counts():
    logger = Logger()
    checker = UpdateChecker("0.9", logger, fetch=lambda: "0.10.0")
    checker.check()
    assert any("0.10.0" in entry for entry in logger.get_logs())


def test_fetch_error_is_logged_at_debug_not_swallowed():
    def failing_fetch():
        raise OSError("no internet")

    logger = Logger(level="DEBUG")
    checker = UpdateChecker("0.0.8", logger, fetch=failing_fetch)
    checker.check()
    logs = logger.get_logs()
    assert any("DEBUG" in entry and "Update check failed" in entry for entry in logs)


def test_fetch_error_is_filtered_out_by_default_log_level():
    def failing_fetch():
        raise OSError("no internet")

    logger = Logger()
    checker = UpdateChecker("0.0.8", logger, fetch=failing_fetch)
    checker.check()
    assert logger.get_logs() == []


def test_malformed_remote_version_is_logged_at_debug():
    logger = Logger(level="DEBUG")
    checker = UpdateChecker("0.0.8", logger, fetch=lambda: "not-a-version")
    checker.check()
    assert any("Update check failed" in entry for entry in logger.get_logs())


def test_none_fetch_result_is_logged_at_debug_not_swallowed():
    logger = Logger(level="DEBUG")
    checker = UpdateChecker("0.0.8", logger, fetch=lambda: None)
    checker.check()
    assert any("Update check failed" in entry for entry in logger.get_logs())


def test_wrong_type_fetch_result_is_logged_at_debug_not_swallowed():
    logger = Logger(level="DEBUG")
    checker = UpdateChecker("0.0.8", logger, fetch=lambda: 8)
    checker.check()
    assert any("Update check failed" in entry for entry in logger.get_logs())


def test_unknown_local_version_is_logged_at_info_not_swallowed():
    logger = Logger()
    checker = UpdateChecker("0.0.0-unknown", logger, fetch=lambda: "9.9.9")
    checker.check()
    logs = logger.get_logs()
    assert any("Skipping update check" in entry for entry in logs)


def test_unknown_local_version_never_calls_fetch():
    def fetch():
        raise AssertionError("fetch should not be called when local version is unknown")

    logger = Logger()
    checker = UpdateChecker("0.0.0-unknown", logger, fetch=fetch)
    checker.check()
