import pytest

from conftest import StubModule
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


def test_module_base_start_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        Module().start()


def test_module_base_stop_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        Module().stop()


def test_modules_requires_logger():
    with pytest.raises(TypeError):
        Modules()


def test_modules_starts_empty():
    assert Modules(Logger()).list_modules() == []


def test_add_module_and_list():
    modules = Modules(Logger())
    stub = StubModule()
    modules.add_module(stub)
    assert modules.list_modules() == [stub]


def test_start_all_starts_every_module():
    modules = Modules(Logger())
    stub_one, stub_two = StubModule(), StubModule()
    modules.add_module(stub_one)
    modules.add_module(stub_two)
    modules.start_all()
    assert stub_one.started is True
    assert stub_two.started is True


def test_stop_all_stops_every_module():
    modules = Modules(Logger())
    stub_one, stub_two = StubModule(), StubModule()
    modules.add_module(stub_one)
    modules.add_module(stub_two)
    modules.stop_all()
    assert stub_one.stopped is True
    assert stub_two.stopped is True


def test_start_all_continues_when_a_module_raises():
    modules = Modules(Logger())
    modules.add_module(FailingModule())
    stub = StubModule()
    modules.add_module(stub)
    modules.start_all()
    assert stub.started is True


def test_start_all_logs_the_failing_modules_name():
    logger = Logger()
    modules = Modules(logger)
    modules.add_module(FailingModule())
    modules.start_all()
    logs = logger.get_logs()
    assert any("failing" in entry and "ERROR" in entry for entry in logs)


def test_stop_all_continues_when_a_module_raises():
    modules = Modules(Logger())
    modules.add_module(FailingModule())
    stub = StubModule()
    modules.add_module(stub)
    modules.stop_all()
    assert stub.stopped is True


def test_stop_all_logs_the_failing_modules_name():
    logger = Logger()
    modules = Modules(logger)
    modules.add_module(FailingModule())
    modules.stop_all()
    logs = logger.get_logs()
    assert any("failing" in entry and "ERROR" in entry for entry in logs)


class NamelessFailingModule:

    def start(self):
        raise RuntimeError("boom")

    def stop(self):
        raise RuntimeError("boom")


def test_start_all_survives_a_failing_module_without_a_name():
    logger = Logger()
    modules = Modules(logger)
    modules.add_module(NamelessFailingModule())
    modules.start_all()
    logs = logger.get_logs()
    assert any("NamelessFailingModule" in entry and "ERROR" in entry for entry in logs)


def test_stop_all_survives_a_failing_module_without_a_name():
    logger = Logger()
    modules = Modules(logger)
    modules.add_module(NamelessFailingModule())
    modules.stop_all()
    logs = logger.get_logs()
    assert any("NamelessFailingModule" in entry and "ERROR" in entry for entry in logs)


def test_language_module_start_marks_it_available():
    class StubClient:
        def ensure_available(self):
            return None

    module = LanguageModule(StubClient())
    module.start()
    assert module.available is True


def test_language_module_start_raises_clear_error_when_ollama_is_unreachable():
    class StubClient:
        def ensure_available(self):
            raise OSError("connection refused")

    module = LanguageModule(StubClient())

    with pytest.raises(ConnectionError, match="Ollama not reachable"):
        module.start()


def test_language_module_start_distinguishes_http_error_from_unreachable():
    import urllib.error

    class StubClient:
        def ensure_available(self):
            raise urllib.error.HTTPError("http://localhost:11434/api/tags", 404, "not found", {}, None)

    module = LanguageModule(StubClient())

    with pytest.raises(ConnectionError, match="HTTP 404"):
        module.start()


def test_language_module_runtime_failure_disables_it_and_returns_none():
    class StubClient:
        def ensure_available(self):
            return None

        def generate(self, prompt):
            raise OSError("connection dropped")

    module = LanguageModule(StubClient())
    module.start()

    assert module.respond("hello") is None
    assert module.available is False


def test_language_module_runtime_failure_logs_a_warning_when_logger_is_present():
    class StubClient:
        def ensure_available(self):
            return None

        def generate(self, prompt):
            raise OSError("connection dropped")

    logger = Logger()
    module = LanguageModule(StubClient(), logger)
    module.start()
    module.respond("hello")

    logs = logger.get_logs()
    assert any("WARNING" in entry and "Local language model failed" in entry for entry in logs)


def test_language_module_runtime_failure_without_logger_does_not_crash():
    class StubClient:
        def ensure_available(self):
            return None

        def generate(self, prompt):
            raise OSError("connection dropped")

    module = LanguageModule(StubClient())
    module.start()

    assert module.respond("hello") is None
