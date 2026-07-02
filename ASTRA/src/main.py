from config.config import Config
from core.brain import Brain
from utils.logger import Logger
from memory.memory_manager import MemoryManager
from modules.modules import Modules


def main():
    logger = Logger()
    config = Config()
    memory = MemoryManager()
    modules = Modules()

    brain = Brain(logger, config, memory, modules)

    brain.start()

    while brain.is_running:
        message = input("You: ")
        brain.receive(message)


if __name__ == "__main__":
    main()
