import pytest

from core.brain import Brain
from modules.modules import Modules
from utils.logger import Logger


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


class TestUpdateCheck:

    def test_logs_update_message_when_available(self, config, memory):
        class StubUpdateChecker:
            def check(self):
                return "A newer version of Astra (v9.9.9) is available. Download it at https://example.com"

        logger = Logger()
        brain = Brain(logger, config, memory, Modules(), update_checker=StubUpdateChecker())
        brain.start()
        assert any("newer version" in entry for entry in logger.get_logs())

    def test_no_log_when_no_update_available(self, config, memory):
        class StubUpdateChecker:
            def check(self):
                return None

        logger = Logger()
        brain = Brain(logger, config, memory, Modules(), update_checker=StubUpdateChecker())
        brain.start()
        assert not any("newer version" in entry for entry in logger.get_logs())

    def test_no_check_when_update_checker_is_none(self, running_brain):
        assert running_brain.update_checker is None


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


class TestNotes:

    def test_remember_note(self, running_brain):
        response = running_brain.receive("remember buy milk")
        assert "buy milk" in response

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
