import pytest

from commands.registry import CommandRegistry
from conftest import StubModule
from core.brain import Brain
from memory.memory_manager import MemoryManager
from modules.language_module import LanguageModule
from modules.module import Module
from modules.modules import Modules
from utils.logger import Logger


class FailingModule(Module):

    name = "failing"

    def start(self):
        raise RuntimeError("boom")

    def stop(self):
        raise RuntimeError("boom")


class FailingCommand:

    stops_brain = False

    def handle(self, message, normalized):
        raise RuntimeError("command boom")


class TestLifecycle:

    def test_brain_starts_offline(self, brain):
        assert brain.state == Brain.OFFLINE
        assert not brain.is_running

    def test_start_moves_to_running(self, brain):
        brain.start()
        assert brain.state == Brain.RUNNING
        assert brain.is_running

    def test_stop_moves_to_offline(self, running_brain):
        running_brain.stop()
        assert running_brain.state == Brain.OFFLINE
        assert not running_brain.is_running

    def test_cannot_start_twice(self, running_brain):
        with pytest.raises(ValueError):
            running_brain.start()

    def test_cannot_stop_when_offline(self, brain):
        with pytest.raises(ValueError):
            brain.stop()

    def test_receive_refused_when_offline(self, brain):
        response = brain.receive("hi")
        assert "not running" in response
        assert brain.memory.recall() == []

    def test_farewell_stops_the_brain(self, running_brain):
        response = running_brain.receive("bye")
        assert "Goodbye" in response
        assert running_brain.state == Brain.OFFLINE

    def test_explicit_empty_command_registry_is_not_replaced_by_default(self, config, memory):
        empty_registry = CommandRegistry([])
        brain = Brain(Logger(), config, memory, Modules(Logger()), commands=empty_registry)
        assert brain.commands is empty_registry


class TestLifecycleRecovery:

    def test_start_failure_returns_to_offline_and_reraises_the_real_error(self, config, memory):
        memory.long_memory.entries.append({"timestamp": "not-a-timestamp", "entry": "corrupt"})
        brain = Brain(Logger(), config, memory, Modules(Logger()))

        with pytest.raises(ValueError, match="not-a-timestamp"):
            brain.start()

        assert brain.state == Brain.OFFLINE

    def test_start_can_be_retried_after_a_failed_start(self, config, memory):
        memory.long_memory.entries.append({"timestamp": "not-a-timestamp", "entry": "corrupt"})
        brain = Brain(Logger(), config, memory, Modules(Logger()))

        with pytest.raises(ValueError):
            brain.start()

        memory.long_memory.entries.clear()
        brain.start()
        assert brain.state == Brain.RUNNING

    def test_retried_start_raises_the_real_error_again_not_invalid_transition(self, config, memory):
        memory.long_memory.entries.append({"timestamp": "not-a-timestamp", "entry": "corrupt"})
        brain = Brain(Logger(), config, memory, Modules(Logger()))

        with pytest.raises(ValueError):
            brain.start()
        with pytest.raises(ValueError) as excinfo:
            brain.start()

        assert "Invalid state transition" not in str(excinfo.value)

    def test_start_failure_is_logged_as_an_error(self, config, memory):
        memory.long_memory.entries.append({"timestamp": "not-a-timestamp", "entry": "corrupt"})
        brain = Brain(Logger(), config, memory, Modules(Logger()))

        with pytest.raises(ValueError):
            brain.start()

        logs = brain.logger.get_logs()
        assert any("ERROR" in entry and "Startup failed" in entry for entry in logs)

    def test_stop_failure_returns_to_offline_and_reraises_the_real_error(self, running_brain):
        running_brain._session_started_at = "not-a-datetime"

        with pytest.raises(TypeError):
            running_brain.stop()

        assert running_brain.state == Brain.OFFLINE

    def test_brain_can_be_started_again_after_a_failed_stop(self, running_brain):
        running_brain._session_started_at = "not-a-datetime"

        with pytest.raises(TypeError):
            running_brain.stop()

        running_brain.start()
        assert running_brain.state == Brain.RUNNING

    def test_stop_failure_is_logged_as_an_error(self, running_brain):
        running_brain._session_started_at = "not-a-datetime"

        with pytest.raises(TypeError):
            running_brain.stop()

        logs = running_brain.logger.get_logs()
        assert any("ERROR" in entry and "Shutdown failed" in entry for entry in logs)


class TestUpdateCheck:

    def test_start_calls_update_checker_when_present(self, config, memory):
        class StubUpdateChecker:
            def __init__(self):
                self.checked = False

            def check(self):
                self.checked = True

        update_checker = StubUpdateChecker()
        brain = Brain(Logger(), config, memory, Modules(Logger()), update_checker=update_checker)
        brain.start()
        assert update_checker.checked is True

    def test_no_check_when_update_checker_is_none(self, running_brain):
        assert running_brain.update_checker is None


class TestModulesLifecycle:

    def test_start_starts_every_module(self, config, memory):
        modules = Modules(Logger())
        stub = StubModule()
        modules.add_module(stub)
        brain = Brain(Logger(), config, memory, modules)
        brain.start()
        assert stub.started is True

    def test_stop_stops_every_module(self, config, memory):
        modules = Modules(Logger())
        stub = StubModule()
        modules.add_module(stub)
        brain = Brain(Logger(), config, memory, modules)
        brain.start()
        brain.stop()
        assert stub.stopped is True

    def test_start_reaches_running_even_if_a_module_fails(self, config, memory):
        modules = Modules(Logger())
        modules.add_module(FailingModule())
        brain = Brain(Logger(), config, memory, modules)
        brain.start()
        assert brain.state == Brain.RUNNING

    def test_stop_reaches_offline_even_if_a_module_fails(self, config, memory):
        modules = Modules(Logger())
        modules.add_module(FailingModule())
        brain = Brain(Logger(), config, memory, modules)
        brain.start()
        brain.stop()
        assert brain.state == Brain.OFFLINE

    def test_start_all_still_starts_remaining_modules_after_one_fails(self, config, memory):
        modules = Modules(Logger())
        modules.add_module(FailingModule())
        stub = StubModule()
        modules.add_module(stub)
        brain = Brain(Logger(), config, memory, modules)
        brain.start()
        assert stub.started is True


class TestCommands:

    def test_greeting(self, running_brain):
        assert running_brain.receive("hi") == "Hello!"

    def test_greeting_ignores_case_and_punctuation(self, running_brain):
        assert running_brain.receive("  Hello!  ") == "Hi there!"

    def test_trigger_matches_with_a_space_before_the_punctuation(self, running_brain):
        assert running_brain.receive("hello !") == "Hi there!"

    def test_farewell_stops_the_brain_with_a_space_before_the_punctuation(self, running_brain):
        response = running_brain.receive("bye !")
        assert "Goodbye" in response
        assert running_brain.state == Brain.OFFLINE

    def test_who_are_you(self, running_brain):
        response = running_brain.receive("who are you?")
        assert running_brain.config.name in response

    def test_help_lists_commands(self, running_brain):
        response = running_brain.receive("help")
        assert "remember" in response
        assert "recall" in response

    def test_unknown_message_is_echoed(self, running_brain):
        assert running_brain.receive("something random") == "I heard: something random"

    def test_unknown_message_uses_language_module_when_available(self, config, memory):
        class StubClient:
            def ensure_available(self):
                return None

            def generate(self, prompt):
                return f"Local reply: {prompt}"

        modules = Modules(Logger())
        modules.add_module(LanguageModule(StubClient()))
        brain = Brain(Logger(), config, memory, modules)
        brain.start()

        assert brain.receive("something random") == "Local reply: something random"

    def test_unknown_message_falls_back_to_echo_when_language_module_runtime_fails(self, config, memory):
        class StubClient:
            def ensure_available(self):
                return None

            def generate(self, prompt):
                raise OSError("connection dropped")

        modules = Modules(Logger())
        modules.add_module(LanguageModule(StubClient()))
        brain = Brain(Logger(), config, memory, modules)
        brain.start()

        assert brain.receive("something random") == "I heard: something random"

    def test_blank_message_does_not_reach_language_module(self, config, memory):
        calls = []

        class StubClient:
            def ensure_available(self):
                return None

            def generate(self, prompt):
                calls.append(prompt)
                return "should not happen"

        modules = Modules(Logger())
        modules.add_module(LanguageModule(StubClient()))
        brain = Brain(Logger(), config, memory, modules)
        brain.start()

        brain.receive("   ")

        assert calls == []

    def test_stray_shell_command_is_not_echoed(self, running_brain):
        response = running_brain.receive(r"C:\Python\python.exe c:/Development/ASTRA/src/main.py")
        assert "I heard" not in response
        assert "shell command" in response


class TestFailureFlagging:

    def test_failing_command_does_not_crash_dispatch(self):
        registry = CommandRegistry([FailingCommand()])
        result = registry.dispatch("anything")
        assert "went wrong" in result.response

    def test_failing_command_is_logged_as_an_error(self):
        logger = Logger()
        registry = CommandRegistry([FailingCommand()], logger=logger)
        registry.dispatch("anything")

        logs = logger.get_logs()
        assert any("ERROR" in entry and "FailingCommand" in entry and "command boom" in entry for entry in logs)

    def test_failing_command_without_logger_does_not_crash(self):
        registry = CommandRegistry([FailingCommand()])
        result = registry.dispatch("anything")
        assert result.response

    def test_brain_flags_a_failing_command_instead_of_crashing(self, config, memory):
        brain = Brain(
            Logger(),
            config,
            memory,
            Modules(Logger()),
            commands=CommandRegistry([FailingCommand()], logger=Logger()),
        )
        brain.start()

        response = brain.receive("anything")

        assert "went wrong" in response
        assert brain.state == Brain.RUNNING

    def test_brains_default_registry_is_wired_to_brains_own_logger(self, config, memory):
        logger = Logger()
        brain = Brain(logger, config, memory, Modules(Logger()))
        assert brain.commands.logger is logger

    def test_non_string_message_does_not_crash_dispatch(self):
        registry = CommandRegistry([FailingCommand()])
        result = registry.dispatch(None)
        assert "went wrong" in result.response

    def test_non_string_message_failure_is_logged(self):
        logger = Logger()
        registry = CommandRegistry([FailingCommand()], logger=logger)
        registry.dispatch(None)

        logs = logger.get_logs()
        assert any("ERROR" in entry and "normalize" in entry for entry in logs)


class TestFacts:

    def test_learn_and_query_fact(self, running_brain):
        running_brain.receive("my name is Erik")
        assert running_brain.receive("what is my name?") == "Your name is Erik."

    def test_query_unknown_fact(self, running_brain):
        response = running_brain.receive("what is my age?")
        assert "don't know" in response

    def test_facts_summary(self, running_brain):
        running_brain.receive("my name is Erik")
        response = running_brain.receive("facts")
        assert "your name is Erik" in response

    def test_repeated_trailing_punctuation_is_stripped_from_learned_value(self, running_brain):
        running_brain.receive("my mood is great!!")
        assert running_brain.receive("what is my mood?") == "Your mood is great."

    def test_repeated_trailing_punctuation_is_stripped_from_query(self, running_brain):
        running_brain.receive("my name is Erik")
        assert running_brain.receive("what's my name??") == "Your name is Erik."

    def test_whitespace_only_fact_value_is_not_learned(self, running_brain):
        response = running_brain.receive("my nickname is  ?")
        assert "I'll remember" not in response
        assert running_brain.memory.all_facts() == {}

    def test_whitespace_only_fact_key_is_not_learned(self, running_brain):
        response = running_brain.receive("my   is blue")
        assert "I'll remember" not in response
        assert running_brain.memory.all_facts() == {}

    def test_trigger_with_an_embedded_newline_still_matches(self, brain):
        assert "Goodbye" in brain.process("bye!\n!")

    def test_falsy_fact_value_is_still_reported_as_known(self, running_brain, memory):
        memory.facts.facts["age"] = 0
        assert running_brain.receive("what is my age?") == "Your age is 0."


class TestPersonalization:

    def test_greeting_uses_known_name_for_hi(self, running_brain):
        running_brain.receive("my name is Erik")
        assert running_brain.receive("hi") == "Hello, Erik!"

    def test_greeting_uses_known_name_for_hello(self, running_brain):
        running_brain.receive("my name is Erik")
        assert running_brain.receive("hello") == "Hi there, Erik!"

    def test_greeting_uses_known_name_for_hey(self, running_brain):
        running_brain.receive("my name is Erik")
        assert running_brain.receive("hey") == "Hey, Erik!"

    def test_how_are_you_stays_generic_even_with_known_name(self, running_brain):
        running_brain.receive("my name is Erik")
        response = running_brain.receive("how are you")
        assert "Erik" not in response

    def test_startup_greeting_uses_known_name(self, config, memory):
        memory.learn("name", "Erik")
        brain = Brain(Logger(), config, memory, Modules(Logger()))
        brain.start()
        assert any("Hello, Erik! I am" in entry for entry in brain.logger.get_logs())


class TestNotes:

    def test_remember_note(self, running_brain):
        response = running_brain.receive("remember buy milk")
        assert "buy milk" in response

    def test_remember_note_with_leading_whitespace(self, running_brain):
        response = running_brain.receive(" remember buy milk")
        assert response == "Got it, I'll remember: buy milk"

    def test_recall_shows_recent_entries(self, running_brain):
        running_brain.receive("remember buy milk")
        response = running_brain.receive("recall")
        assert "buy milk" in response

    def test_recall_when_empty(self, brain, memory):
        assert "don't remember anything" in brain.process("recall")

    def test_conversation_is_stored_in_memory(self, running_brain):
        running_brain.receive("hi")
        entries = [item["entry"] for item in running_brain.memory.recall_long()]
        assert "hi" in entries
        assert "Hello!" in entries

    def test_remember_note_is_tagged_as_note(self, running_brain):
        running_brain.receive("remember buy milk")
        notes = [item for item in running_brain.memory.recall_long() if item["entry"] == "buy milk"]
        assert len(notes) == 1
        assert notes[0]["type"] == "note"

    def test_forget_removes_a_note(self, running_brain):
        running_brain.receive("remember buy milk")
        response = running_brain.receive("forget buy milk")
        assert "forgot" in response
        entries = [item["entry"] for item in running_brain.memory.recall_long()]
        assert "buy milk" not in entries

    def test_forget_when_nothing_matches(self, running_brain):
        response = running_brain.receive("forget bicycle")
        assert "couldn't find" in response

    def test_forget_does_not_remove_a_chat_entry_with_the_same_text(self, running_brain):
        running_brain.receive("test")
        running_brain.receive("remember test")
        running_brain.receive("forget test")

        entries = running_brain.memory.recall_long()
        chat_entries = [item for item in entries if item["type"] == "chat" and item["entry"] == "test"]
        note_entries = [item for item in entries if item["type"] == "note" and item["entry"] == "test"]
        assert chat_entries
        assert not note_entries

    def test_forget_with_no_matching_note_does_not_touch_short_term_recall(self, running_brain):
        running_brain.receive("test")
        response = running_brain.receive("forget test")

        assert "couldn't find" in response
        assert "test" in running_brain.memory.recall()

    def test_search_finds_matching_entries(self, running_brain):
        running_brain.receive("remember buy milk")
        response = running_brain.receive("search milk")
        assert "buy milk" in response

    def test_search_when_nothing_matches(self, running_brain):
        response = running_brain.receive("search bicycle")
        assert "couldn't find" in response

    def test_recall_does_not_crash_on_legacy_entries_without_type(self, running_brain, memory):
        memory.long_memory.entries.append({"timestamp": "2020-01-01T00:00:00", "entry": "legacy chat"})
        response = running_brain.receive("recall")
        assert "don't remember anything" in response

    def test_search_does_not_crash_on_legacy_entries_without_type(self, running_brain, memory):
        memory.long_memory.entries.append({"timestamp": "2020-01-01T00:00:00", "entry": "legacy chat"})
        response = running_brain.receive("search legacy")
        assert "couldn't find" in response

    def test_history_does_not_crash_on_entries_missing_entry_or_timestamp(self, running_brain, memory):
        memory.long_memory.entries.append({"type": "chat"})
        response = running_brain.receive("history")
        assert isinstance(response, str)

    def test_search_notes_only_excludes_chat_echo(self, running_brain):
        running_brain.receive("remember buy milk")
        response = running_brain.receive("search milk")
        assert "buy milk" in response
        assert "remember buy milk" not in response
        assert "Got it, I'll remember" not in response

    def test_recall_notes_only_excludes_chat_echo(self, running_brain):
        running_brain.receive("remember buy milk")
        response = running_brain.receive("recall")
        assert "buy milk" in response
        assert "remember buy milk" not in response
        assert "Got it, I'll remember" not in response

    def test_history_shows_everything_including_chat(self, running_brain):
        running_brain.receive("remember buy milk")
        response = running_brain.receive("history")
        assert "remember buy milk" in response


class TestMemoryStats:

    def test_stats_when_empty(self, running_brain):
        response = running_brain.receive("memory stats")
        assert "don't have any memory" in response

    def test_stats_does_not_crash_on_entries_missing_timestamp(self, running_brain, memory):
        memory.long_memory.entries.append({"entry": "legacy", "type": "chat"})
        response = running_brain.receive("memory stats")
        assert "Memory stats" in response

    def test_stats_reports_counts_and_timestamps(self, running_brain):
        running_brain.receive("remember buy milk")
        running_brain.receive("remember walk the dog")
        running_brain.receive("hi")

        entries = running_brain.memory.recall_long()
        total_count = len(entries)
        note_count = len([item for item in entries if item.get("type") == "note"])
        chat_count = total_count - note_count
        oldest = entries[0]["timestamp"]
        newest = entries[-1]["timestamp"]

        response = running_brain.receive("memory stats")

        assert f"total entries: {total_count}" in response
        assert f"notes: {note_count}" in response
        assert f"chat: {chat_count}" in response
        assert oldest in response
        assert newest in response

    def test_stats_counts_notes_separately_from_chat(self, running_brain):
        running_brain.receive("remember buy milk")
        running_brain.receive("hi")
        response = running_brain.receive("memory stats")
        assert "notes: 1" in response


class TestPreferences:

    def test_recall_defaults_to_last_five_notes(self, running_brain):
        for i in range(6):
            running_brain.receive(f"remember note {i}")
        response = running_brain.receive("recall")
        assert "note 5" in response
        assert "note 1" in response
        assert "note 0" not in response

    def test_recall_shortens_with_response_length_preference(self, running_brain):
        running_brain.receive("my response length is short")
        for i in range(5):
            running_brain.receive(f"remember note {i}")
        response = running_brain.receive("recall")
        assert "note 4" in response
        assert "note 3" in response
        assert "note 2" not in response

    def test_history_shortens_with_response_length_preference(self, running_brain):
        running_brain.receive("my response length is short")
        for i in range(5):
            running_brain.receive(f"remember note {i}")
        response = running_brain.receive("history")
        entry_lines = [line for line in response.splitlines() if line.startswith("- [")]
        assert len(entry_lines) == 2

    def test_response_length_preference_is_case_insensitive(self, running_brain):
        running_brain.receive("my response length is SHORT")
        for i in range(5):
            running_brain.receive(f"remember note {i}")
        response = running_brain.receive("recall")
        assert "note 2" not in response

    def test_unrecognized_response_length_value_keeps_default(self, running_brain):
        running_brain.receive("my response length is long")
        for i in range(5):
            running_brain.receive(f"remember note {i}")
        response = running_brain.receive("recall")
        assert "note 0" in response

    def test_recall_does_not_crash_on_non_string_response_length_fact(self, running_brain, memory):
        memory.facts.facts["response length"] = True
        running_brain.receive("remember buy milk")
        response = running_brain.receive("recall")
        assert "buy milk" in response

    def test_non_string_response_length_fact_logs_a_warning(self, running_brain, memory):
        memory.facts.facts["response length"] = True
        running_brain.receive("remember buy milk")
        running_brain.receive("recall")

        logs = running_brain.logger.get_logs()
        assert any("WARNING" in entry and "response length" in entry for entry in logs)

    def test_valid_response_length_fact_logs_no_warning(self, running_brain):
        running_brain.receive("my response length is short")
        running_brain.receive("remember buy milk")
        running_brain.receive("recall")

        logs = running_brain.logger.get_logs()
        assert not any("WARNING" in entry and "response length" in entry for entry in logs)

    def test_non_string_response_length_fact_without_logger_does_not_crash(self, memory):
        from commands.memory_command import MemoryCommand

        memory.facts.facts["response length"] = True
        memory.remember("buy milk", entry_type="note")
        command = MemoryCommand(memory)

        assert "buy milk" in command.handle("recall", "recall")

    def test_repeated_trailing_punctuation_does_not_leak_into_preference_value(self, running_brain):
        running_brain.receive("my response length is short..")
        for i in range(5):
            running_brain.receive(f"remember note {i}")
        response = running_brain.receive("recall")
        assert "note 2" not in response


class TestDiagnostics:

    @pytest.fixture
    def clean_config(self, tmp_path):
        import json

        path = tmp_path / "config.json"
        path.write_text(json.dumps({"version": "1.2.3"}), encoding="utf-8")
        from config.config import Config

        return Config(path=path)

    def test_status_reports_all_clear_when_nothing_went_wrong(self, clean_config, memory):
        brain = Brain(Logger(), clean_config, memory, Modules(Logger()))
        brain.start()
        response = brain.receive("status")
        assert "no warnings" in response

    def test_diagnostics_trigger_works_like_status(self, clean_config, memory):
        brain = Brain(Logger(), clean_config, memory, Modules(Logger()))
        brain.start()
        assert brain.receive("diagnostics") == brain.receive("status")

    def test_status_reports_config_warnings_after_startup(self, running_brain):
        # The conftest config points at a missing file, so it carries the
        # "no version value" load warning - status should resurface it.
        response = running_brain.receive("status")
        assert "config:" in response
        assert "version" in response

    def test_status_reports_memory_warnings_after_startup(self, clean_config, tmp_path):
        (tmp_path / "long_memory.json").write_text("{not valid json", encoding="utf-8")
        memory = MemoryManager(data_dir=tmp_path)
        brain = Brain(Logger(), clean_config, memory, Modules(Logger()))
        brain.start()

        response = brain.receive("status")

        assert "memory:" in response
        assert "long_memory.json" in response

    def test_status_reports_file_logging_disabled_after_a_write_failure(self, clean_config, memory, tmp_path):
        clean_config.log_to_file = True
        logger = Logger(log_to_file=True, log_path=tmp_path / "blocked" / "astra.log")
        (tmp_path / "blocked").write_text("a file where the log directory should be", encoding="utf-8")
        brain = Brain(logger, clean_config, memory, Modules(Logger()))
        brain.start()

        response = brain.receive("status")

        assert "file logging is off" in response

    def test_status_does_not_report_file_logging_when_it_is_off_by_config(self, clean_config, memory):
        brain = Brain(Logger(), clean_config, memory, Modules(Logger()))
        brain.start()
        response = brain.receive("status")
        assert "file logging" not in response

    def test_status_is_listed_in_help(self, running_brain):
        response = running_brain.receive("help")
        assert "diagnostics" in response


class TestSessionSummary:

    def test_stop_logs_session_summary_with_counts(self, running_brain):
        running_brain.receive("hi")
        running_brain.receive("my name is Erik")
        running_brain.stop()

        summary_lines = [line for line in running_brain.logger.get_logs() if "Session summary" in line]
        assert len(summary_lines) == 1
        assert "4 messages exchanged" in summary_lines[0]
        assert "1 new facts learned" in summary_lines[0]

    def test_message_count_does_not_carry_over_between_sessions(self, brain):
        brain.start()
        brain.receive("hi")
        brain.stop()

        brain.start()
        brain.receive("hey")
        brain.stop()

        summary_lines = [line for line in brain.logger.get_logs() if "Session summary" in line]
        assert len(summary_lines) == 2
        assert "2 messages exchanged" in summary_lines[0]
        assert "2 messages exchanged" in summary_lines[1]

    def test_message_count_is_not_inflated_by_remembering_a_note(self, running_brain):
        running_brain.receive("hi")
        running_brain.receive("remember buy milk")
        running_brain.stop()

        summary_lines = [line for line in running_brain.logger.get_logs() if "Session summary" in line]
        assert len(summary_lines) == 1
        assert "4 messages exchanged" in summary_lines[0]


class TestStartupBriefing:

    def test_first_session_message_when_memory_empty(self, brain):
        brain.start()
        assert any("first session" in entry for entry in brain.logger.get_logs())

    def test_last_seen_message_when_prior_entry_exists(self, config, memory):
        memory.long_memory.remember("previous chat")
        brain = Brain(Logger(), config, memory, Modules(Logger()))
        brain.start()
        logs = brain.logger.get_logs()
        assert any("Last seen" in entry and "ago" in entry for entry in logs)

    def test_config_load_warning_is_surfaced_at_startup(self, config, memory):
        config.load_warnings.append("test warning: something is misconfigured")
        brain = Brain(Logger(), config, memory, Modules(Logger()))
        brain.start()
        logs = brain.logger.get_logs()
        assert any("WARNING" in entry and "test warning" in entry for entry in logs)

    def test_memory_load_warning_is_surfaced_at_startup(self, config, tmp_path):
        (tmp_path / "long_memory.json").write_text("{not valid json", encoding="utf-8")
        memory = MemoryManager(data_dir=tmp_path)
        brain = Brain(Logger(), config, memory, Modules(Logger()))
        brain.start()
        logs = brain.logger.get_logs()
        assert any("WARNING" in entry and "long_memory.json" in entry for entry in logs)


class TestChatVisibility:

    def test_responses_are_visible_even_at_error_log_level(self, config, memory):
        brain = Brain(Logger(level="ERROR"), config, memory, Modules(Logger()))
        brain.start()
        brain.receive("hi")

        assert any("Hello!" in entry for entry in brain.logger.get_logs())

    def test_status_command_output_is_visible_even_at_error_log_level(self, config, memory):
        brain = Brain(Logger(level="ERROR"), config, memory, Modules(Logger()))
        brain.start()
        brain.receive("status")

        assert any("needs attention" in entry or "no warnings" in entry for entry in brain.logger.get_logs())


class TestPersistenceFailure:

    def test_receive_survives_a_long_memory_save_failure(self, running_brain, memory, monkeypatch):
        def failing_save():
            raise OSError("disk full")

        monkeypatch.setattr(memory.long_memory, "save", failing_save)

        response = running_brain.receive("hi")

        assert response == "Hello!"
        assert running_brain.state == Brain.RUNNING

    def test_long_memory_save_failure_is_logged_as_an_error(self, running_brain, memory, monkeypatch):
        def failing_save():
            raise OSError("disk full")

        monkeypatch.setattr(memory.long_memory, "save", failing_save)

        running_brain.receive("hi")

        logs = running_brain.logger.get_logs()
        assert any("ERROR" in entry and "long-term memory" in entry and "disk full" in entry for entry in logs)
