import pytest

from modules.module import Module
from modules.modules import Modules
from utils.logger import Logger


class StubModule(Module):

    name = "stub"

    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


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
