import pytest

from modules.module import Module
from modules.modules import Modules


class StubModule(Module):

    name = "stub"

    def __init__(self):
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_module_base_start_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        Module().start()


def test_module_base_stop_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        Module().stop()


def test_modules_starts_empty():
    assert Modules().list_modules() == []


def test_add_module_and_list():
    modules = Modules()
    stub = StubModule()
    modules.add_module(stub)
    assert modules.list_modules() == [stub]


def test_start_all_starts_every_module():
    modules = Modules()
    stub_one, stub_two = StubModule(), StubModule()
    modules.add_module(stub_one)
    modules.add_module(stub_two)
    modules.start_all()
    assert stub_one.started is True
    assert stub_two.started is True


def test_stop_all_stops_every_module():
    modules = Modules()
    stub_one, stub_two = StubModule(), StubModule()
    modules.add_module(stub_one)
    modules.add_module(stub_two)
    modules.stop_all()
    assert stub_one.stopped is True
    assert stub_two.stopped is True
