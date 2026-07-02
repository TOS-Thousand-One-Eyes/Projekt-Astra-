from config.config import Config
from core.brain import Brain
from utils.logger import Logger
from memory.memory_manager import MemoryManager
from modules.modules import Modules


def main():
    config = Config()
    logger = Logger(level=config.log_level, log_to_file=config.log_to_file)
    memory = MemoryManager()
    modules = Modules()

    brain = Brain(logger, config, memory, modules)

    brain.start()

    try:
        while brain.is_running:
            message = input("You: ")
            if not message.strip():
                continue
            brain.receive(message)
    except KeyboardInterrupt:
        print()
        brain.stop()


if __name__ == "__main__":
    main()
