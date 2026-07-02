import pytest

from config.config import Config
from core.brain import Brain
from memory.memory_manager import MemoryManager
from modules.modules import Modules
from utils.logger import Logger


@pytest.fixture
def memory(tmp_path):
    return MemoryManager(data_dir=tmp_path)


@pytest.fixture
def config(tmp_path):
    return Config(path=tmp_path / "config.json")


@pytest.fixture
def brain(config, memory):
    return Brain(Logger(), config, memory, Modules())


@pytest.fixture
def running_brain(brain):
    brain.start()
    return brain
