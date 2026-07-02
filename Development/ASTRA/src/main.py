from config.config import Config
from core.brain import Brain
from utils.logger import Logger
from utils.update_checker import UpdateChecker
from memory.memory_manager import MemoryManager
from modules.modules import Modules


def main():
    config = Config()
    logger = Logger(level=config.log_level, log_to_file=config.log_to_file)
    memory = MemoryManager()
    modules = Modules()
    update_checker = UpdateChecker(config.version, logger) if config.check_for_updates else None

    brain = Brain(logger, config, memory, modules, update_checker=update_checker)

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
