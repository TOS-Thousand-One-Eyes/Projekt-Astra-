import builtins
import json

import pytest

import main as main_module
from config.config import Config
from memory.memory_manager import MemoryManager
from utils.logger import Logger


@pytest.fixture
def isolated_main(monkeypatch, tmp_path):
    # check_for_updates off so main() never constructs an UpdateChecker -
    # tests must not depend on the network.
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps({"version": "0.0.0", "check_for_updates": False}),
        encoding="utf-8",
    )
    monkeypatch.setattr(main_module, "Config", lambda: Config(path=config_path))
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


class TestVisionRuntimeWiring:

    def test_configured_vision_model_is_passed_to_brain(self, monkeypatch, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text(
            json.dumps(
                {
                    "version": "0.0.0",
                    "check_for_updates": False,
                    "use_vision_model": True,
                    "vision_base_url": "http://127.0.0.1:11435",
                    "vision_model": "llava:test",
                    "vision_generate_timeout": 12,
                }
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(main_module, "Config", lambda: Config(path=config_path))
        monkeypatch.setattr(main_module, "MemoryManager", lambda: MemoryManager(data_dir=tmp_path))
        captured = {}
        original_init = main_module.Brain.__init__

        def spy_init(self, logger, config, memory, modules, **kwargs):
            captured["vision_describer"] = kwargs.get("vision_describer")
            return original_init(self, logger, config, memory, modules, **kwargs)

        monkeypatch.setattr(main_module.Brain, "__init__", spy_init)
        inputs = iter(["bye"])
        monkeypatch.setattr(builtins, "input", lambda prompt="": next(inputs))

        main_module.main()

        describer = captured["vision_describer"]
        assert describer is not None
        assert describer.client.base_url == "http://127.0.0.1:11435"
        assert describer.client.model == "llava:test"
        assert describer.client.generate_timeout == 12
