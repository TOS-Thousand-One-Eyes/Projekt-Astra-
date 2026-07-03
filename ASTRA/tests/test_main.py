import builtins

import pytest

import main as main_module
from config.config import Config
from memory.memory_manager import MemoryManager
from utils.logger import Logger


@pytest.fixture
def isolated_main(monkeypatch, tmp_path):
    monkeypatch.setattr(main_module, "Config", lambda: Config(path=tmp_path / "config.json"))
    monkeypatch.setattr(main_module, "MemoryManager", lambda: MemoryManager(data_dir=tmp_path))


class TestBlankInput:

    def test_blank_and_whitespace_lines_never_reach_brain(self, monkeypatch, isolated_main):
        received = []
        original_receive = main_module.Brain.receive

        def spy_receive(self, message):
            received.append(message)
            return original_receive(self, message)

        monkeypatch.setattr(main_module.Brain, "receive", spy_receive)

        inputs = iter(["", "   ", "bye"])
        monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))

        main_module.main()

        assert received == ["bye"]


class TestKeyboardInterrupt:

    def test_ctrl_c_stops_the_brain_cleanly(self, monkeypatch, isolated_main):
        logger = Logger()
        monkeypatch.setattr(main_module, "Logger", lambda **kwargs: logger)

        def raise_interrupt(prompt=""):
            raise KeyboardInterrupt

        monkeypatch.setattr(builtins, "input", raise_interrupt)

        main_module.main()

        assert any("stopped" in entry for entry in logger.get_logs())


class TestStartupInterrupt:

    def test_ctrl_c_during_startup_exits_cleanly_without_a_traceback(self, monkeypatch, isolated_main):
        def interrupted_start(self):
            raise KeyboardInterrupt

        monkeypatch.setattr(main_module.Brain, "start", interrupted_start)

        main_module.main()


class TestEOFError:

    def test_closed_stdin_stops_the_brain_cleanly(self, monkeypatch, isolated_main):
        logger = Logger()
        monkeypatch.setattr(main_module, "Logger", lambda **kwargs: logger)

        def raise_eof(prompt=""):
            raise EOFError

        monkeypatch.setattr(builtins, "input", raise_eof)

        main_module.main()

        assert any("stopped" in entry for entry in logger.get_logs())
