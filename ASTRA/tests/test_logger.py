import builtins

from utils.logger import Logger


def test_default_level_filters_debug_but_keeps_info():
    logger = Logger()
    logger.log("debug message", "DEBUG")
    logger.log("info message", "INFO")
    logs = logger.get_logs()
    assert not any("debug message" in entry for entry in logs)
    assert any("info message" in entry for entry in logs)


def test_default_level_lets_warning_and_error_through():
    logger = Logger()
    logger.log("warn", "WARNING")
    logger.log("err", "ERROR")
    logs = logger.get_logs()
    assert any("warn" in entry for entry in logs)
    assert any("err" in entry for entry in logs)


def test_debug_level_lets_debug_through():
    logger = Logger(level="DEBUG")
    logger.log("debug message", "DEBUG")
    assert any("debug message" in entry for entry in logger.get_logs())


def test_invalid_level_falls_back_to_info_instead_of_crashing():
    logger = Logger(level="bogus")
    logger.log("debug message", "DEBUG")
    logger.log("info message", "INFO")
    logs = logger.get_logs()
    assert not any("debug message" in entry for entry in logs)
    assert any("info message" in entry for entry in logs)


def test_error_level_filters_out_info_and_warning():
    logger = Logger(level="ERROR")
    logger.log("info msg", "INFO")
    logger.log("warn msg", "WARNING")
    logger.log("err msg", "ERROR")
    logs = logger.get_logs()
    assert not any("info msg" in entry for entry in logs)
    assert not any("warn msg" in entry for entry in logs)
    assert any("err msg" in entry for entry in logs)


def test_unlabeled_log_call_defaults_to_info():
    logger = Logger(level="WARNING")
    logger.log("plain message")
    assert logger.get_logs() == []


def test_convenience_methods_map_to_correct_levels():
    logger = Logger(level="DEBUG")
    logger.debug("d")
    logger.info("i")
    logger.warning("w")
    logger.error("e")
    logs = logger.get_logs()
    assert any("DEBUG" in entry and "d" in entry for entry in logs)
    assert any("INFO" in entry and "i" in entry for entry in logs)
    assert any("WARNING" in entry and "w" in entry for entry in logs)
    assert any("ERROR" in entry and "e" in entry for entry in logs)


def test_no_file_written_when_log_to_file_is_false(tmp_path):
    path = tmp_path / "astra.log"
    logger = Logger(log_to_file=False, log_path=path)
    logger.log("hello")
    assert not path.exists()


def test_file_output_writes_expected_line(tmp_path):
    path = tmp_path / "astra.log"
    logger = Logger(log_to_file=True, log_path=path)
    logger.log("hello world")
    content = path.read_text(encoding="utf-8")
    assert "hello world" in content
    assert "INFO" in content


def test_file_output_creates_parent_directory(tmp_path):
    path = tmp_path / "nested" / "logs" / "astra.log"
    logger = Logger(log_to_file=True, log_path=path)
    logger.log("hi")
    assert path.exists()


def test_file_output_appends_across_multiple_calls(tmp_path):
    path = tmp_path / "astra.log"
    logger = Logger(log_to_file=True, log_path=path)
    logger.log("first")
    logger.log("second")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_filtered_message_not_written_to_file(tmp_path):
    path = tmp_path / "astra.log"
    logger = Logger(level="ERROR", log_to_file=True, log_path=path)
    logger.log("info message", "INFO")
    assert not path.exists()


def test_get_logs_only_contains_entries_that_passed_filter():
    logger = Logger(level="WARNING")
    logger.log("debug", "DEBUG")
    logger.log("info", "INFO")
    logger.log("warn", "WARNING")
    assert len(logger.get_logs()) == 1
    assert "warn" in logger.get_logs()[0]


def test_file_write_failure_does_not_crash_the_logger(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    log_path = blocker / "astra.log"
    logger = Logger(log_to_file=True, log_path=log_path)

    logger.log("hello")

    assert any("hello" in entry for entry in logger.get_logs())


def test_file_write_failure_is_logged_loudly_not_silently(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    log_path = blocker / "astra.log"
    logger = Logger(log_to_file=True, log_path=log_path)

    logger.log("hello")

    assert any("WARNING" in entry and "Logging to file failed" in entry for entry in logger.get_logs())


def test_file_write_failure_disables_further_file_write_attempts(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    log_path = blocker / "astra.log"
    logger = Logger(log_to_file=True, log_path=log_path)

    logger.log("first")
    assert logger.log_to_file is False

    warning_count_before = len(logger.get_logs())
    logger.log("second")
    warning_count_after = len(logger.get_logs())
    assert warning_count_after == warning_count_before + 1


def test_log_call_with_invalid_level_falls_back_to_info_instead_of_crashing():
    logger = Logger()
    logger.log("message", level="TRACE")
    logs = logger.get_logs()
    assert any("INFO" in entry and "message" in entry for entry in logs)


def test_file_write_failure_warning_survives_a_print_encoding_failure(tmp_path, monkeypatch):
    calls = []

    def flaky_print(*args, **kwargs):
        calls.append(args)
        if len(calls) == 2:  # the failure entry's own first print attempt
            raise UnicodeEncodeError("charmap", "x", 0, 1, "bad char")

    monkeypatch.setattr(builtins, "print", flaky_print)
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    logger = Logger(log_to_file=True, log_path=blocker / "astra.log")

    logger.log("hello")

    assert len(calls) == 3
    assert any("Logging to file failed" in entry for entry in logger.get_logs())


def test_print_failure_falls_back_to_ascii_instead_of_crashing(monkeypatch):
    calls = []

    def flaky_print(*args, **kwargs):
        calls.append(args)
        if len(calls) == 1:
            raise UnicodeEncodeError("charmap", "x", 0, 1, "bad char")

    monkeypatch.setattr(builtins, "print", flaky_print)
    logger = Logger()

    logger.log("hello ❤")

    assert len(calls) == 2
    assert any("hello" in entry for entry in logger.get_logs())


def test_file_write_survives_a_non_encodable_character(tmp_path):
    # A lone surrogate (e.g. from a model response that json parsed happily)
    # is not encodable to UTF-8; the file write must not crash or kill
    # file logging - it lands in the file escaped instead.
    path = tmp_path / "astra.log"
    logger = Logger(log_to_file=True, log_path=path)

    logger.log("reply: hi \ud83d there")

    assert logger.log_to_file is True
    content = path.read_text(encoding="utf-8")
    assert "reply: hi" in content


def test_chat_output_is_not_filtered_by_log_level():
    logger = Logger(level="ERROR")
    logger.chat("Astra: Hello!")
    assert any("Astra: Hello!" in entry for entry in logger.get_logs())


def test_chat_output_is_written_to_file_when_enabled(tmp_path):
    path = tmp_path / "astra.log"
    logger = Logger(level="ERROR", log_to_file=True, log_path=path)
    logger.chat("Astra: Hello!")
    assert "Astra: Hello!" in path.read_text(encoding="utf-8")
