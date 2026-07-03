from config.config import Config
from core.brain import Brain
from memory.memory_manager import MemoryManager
from modules.language_module import LanguageModule
from modules.modules import Modules
from utils.logger import Logger
from utils.ollama_client import OllamaClient
from utils.update_checker import UpdateChecker


def main():
    config = Config()
    logger = Logger(level=config.log_level, log_to_file=config.log_to_file)
    memory = MemoryManager()
    modules = Modules(logger)

    if config.use_language_fallback:
        language_client = OllamaClient(config.language_base_url, config.language_model)
        modules.add_module(LanguageModule(language_client, logger))

    update_checker = UpdateChecker(config.version, logger) if config.check_for_updates else None

    brain = Brain(logger, config, memory, modules, update_checker=update_checker)

    brain.start()

    try:
        while brain.is_running:
            message = input("You: ")
            if not message.strip():
                continue
            brain.receive(message)
    except (KeyboardInterrupt, EOFError):
        print()
        brain.stop()


if __name__ == "__main__":
    main()
