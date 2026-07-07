from config.config import Config
from core.brain import Brain
from memory.memory_manager import MemoryManager
from modules.language_module import LanguageModule
from modules.modules import Modules
from utils.logger import Logger
from utils.ollama_client import OllamaClient
from utils.update_checker import UpdateChecker
from vision.semantic_vision import LocalVisionDescriber


def main():
    config = Config()
    logger = Logger(level=config.log_level, log_to_file=config.log_to_file)
    memory = MemoryManager()
    modules = Modules(logger)

    if config.use_language_fallback:
        language_client = OllamaClient(
            config.language_base_url,
            config.language_model,
            generate_timeout=config.language_generate_timeout,
        )
        modules.add_module(LanguageModule(language_client, logger))

    vision_describer = None
    if config.use_vision_model:
        vision_client = OllamaClient(
            config.vision_base_url,
            config.vision_model,
            generate_timeout=config.vision_generate_timeout,
        )
        vision_describer = LocalVisionDescriber(client=vision_client, source="vision")

    update_checker = UpdateChecker(config.version, logger) if config.check_for_updates else None

    brain = Brain(
        logger,
        config,
        memory,
        modules,
        update_checker=update_checker,
        vision_describer=vision_describer,
    )

    try:
        brain.start()
        while brain.is_running:
            message = input("You: ")
            if not message.strip():
                continue
            brain.receive(message)
    except (KeyboardInterrupt, EOFError):
        print()
        # A Ctrl+C during startup (e.g. mid update-check) lands here before
        # the brain ever reached RUNNING - nothing to stop in that case.
        if brain.is_running:
            brain.stop()


if __name__ == "__main__":
    main()
