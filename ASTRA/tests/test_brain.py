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

    def test_stray_shell_command_is_not_echoed(self, running_brain):
        response = running_brain.receive(r"C:\Python\python.exe c:/Development/ASTRA/src/main.py")
        assert "I heard" not in response
        assert "shell command" in response


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

    def test_repeated_trailing_punctuation_does_not_leak_into_preference_value(self, running_brain):
        running_brain.receive("my response length is short..")
        for i in range(5):
            running_brain.receive(f"remember note {i}")
        response = running_brain.receive("recall")
        assert "note 2" not in response


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
