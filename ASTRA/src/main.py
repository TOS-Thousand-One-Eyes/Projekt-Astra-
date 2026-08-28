import builtins
import getpass

from actions.action_manager import ActionManager
from actions.system_action_manager import SystemActionManager
from automation.reminder_manager import ReminderManager
from config.config import Config
from core.brain import Brain
from experience.experience_manager import ExperienceManager
from experience.reflection_manager import ReflectionManager
from identity.identity_manager import (
    AuthenticationError,
    IdentityManager,
    IdentityStoreError,
)
from learning.learning_manager import LearningManager
from learning.self_learning import SelfLearningManager
from memory.memory_manager import MemoryManager
from modules.language_module import LanguageModule
from modules.modules import Modules
from utils.logger import Logger
from utils.ollama_client import OllamaClient
from utils.release_notes import ReleaseNotes
from utils.update_checker import UpdateChecker
from vision.screen_observer import ScreenObserverModule
from vision.semantic_vision import LocalVisionDescriber


def build_runtime(config, logger, identity=None, identity_manager=None):
    private_data = identity.data_dir if identity else None
    memory = (
        MemoryManager(data_dir=private_data)
        if private_data
        else MemoryManager()
    )
    modules = Modules(logger)

    language_module = None
    language_client = None
    if config.use_language_fallback:
        language_client = OllamaClient(
            config.language_base_url,
            config.language_model,
            generate_timeout=config.language_generate_timeout,
            options={
                "num_ctx": config.language_num_ctx,
                "temperature": config.language_temperature,
            },
            keep_alive=config.language_keep_alive,
        )
        language_module = LanguageModule(
            language_client,
            logger,
        )
        modules.add_module(language_module)

    vision_describer = None
    if config.use_vision_model:
        # Reuse the exact same client when possible. On low-RAM hardware this
        # avoids keeping/switching between two independent model identities.
        if (
            language_client
            and config.vision_base_url.rstrip("/")
            == config.language_base_url.rstrip("/")
            and config.vision_model
            == config.language_model
        ):
            vision_client = language_client
            source = "shared-language"
        else:
            vision_client = OllamaClient(
                config.vision_base_url,
                config.vision_model,
                generate_timeout=config.vision_generate_timeout,
                options={
                    "num_ctx": config.vision_num_ctx,
                    "temperature": 0.1,
                },
                keep_alive=config.language_keep_alive,
            )
            source = "vision"
        vision_describer = LocalVisionDescriber(
            client=vision_client,
            source=source,
        )
    elif language_client:
        # gemma3:4b can serve both text and image input. If a user switches the
        # language model to a text-only model, Eyes/vision will fail clearly
        # instead of silently sending data elsewhere.
        vision_describer = LocalVisionDescriber(
            client=language_client,
            source="language",
        )

    learning = (
        LearningManager(data_dir=private_data, language_module=language_module)
        if private_data
        else LearningManager(language_module=language_module)
    )
    self_learning = (
        SelfLearningManager(data_dir=private_data, mode=config.self_learning_mode)
        if private_data
        else SelfLearningManager(mode=config.self_learning_mode)
    )
    actions = ActionManager(data_dir=private_data) if private_data else ActionManager()
    system_actions = (
        SystemActionManager(data_dir=private_data)
        if private_data
        else SystemActionManager()
    )
    reminders = (
        ReminderManager(data_dir=private_data)
        if private_data
        else ReminderManager()
    )
    experience = (
        ExperienceManager(data_dir=private_data)
        if private_data
        else ExperienceManager()
    )
    reflections = (
        ReflectionManager(data_dir=private_data)
        if private_data
        else ReflectionManager()
    )

    screen_observer = ScreenObserverModule(
        describer=vision_describer,
        self_learning=self_learning,
        logger=logger,
        enabled=config.screen_observer_enabled,
        poll_seconds=config.screen_observer_poll_seconds,
        min_analysis_interval=(
            config.screen_observer_min_analysis_interval
        ),
        change_threshold=(
            config.screen_observer_change_threshold
        ),
        notify_threshold=(
            config.screen_observer_notify_threshold
        ),
        notification_cooldown=(
            config.screen_observer_notification_cooldown
        ),
    )
    modules.add_module(screen_observer)

    update_checker = (
        UpdateChecker(config.version, logger)
        if config.check_for_updates
        else None
    )

    brain = Brain(
        logger,
        config,
        memory,
        modules,
        update_checker=update_checker,
        learning=learning,
        self_learning=self_learning,
        vision_describer=vision_describer,
        screen_observer=screen_observer,
        actions=actions,
        system_actions=system_actions,
        reminders=reminders,
        experience=experience,
        reflections=reflections,
        identity=identity,
        identity_manager=identity_manager,
        release_notes=(
            ReleaseNotes(config.path.parent / "docs")
            if identity and identity_manager
            else None
        ),
    )
    return brain


def prompt_cli_identity(manager, input_func=None, pin_reader=None):
    input_func = input_func or builtins.input
    pin_reader = pin_reader or getpass.getpass
    profiles = manager.list_profiles()
    names = "/".join(item["display_name"] for item in profiles)

    while True:
        selected = input_func(f"Profile [{names}]: ").strip()
        try:
            profile = manager.resolve_profile(selected)
        except KeyError:
            print(f"Unknown profile. Choose {names}.")
            continue

        if not profile["pin_configured"]:
            print(f"First login for {profile['display_name']}: create a local PIN.")
            first = pin_reader("New PIN (4-12 digits): ")
            second = pin_reader("Confirm PIN: ")
            if first != second:
                print("PIN entries did not match.")
                continue
            try:
                manager.initialize_pin(profile["id"], first)
            except ValueError as error:
                print(error)
                continue
            return manager.session_after_setup(profile["id"])

        pin = pin_reader("PIN: ")
        try:
            return manager.authenticate(profile["id"], pin)
        except AuthenticationError:
            print("Incorrect PIN.")


def main():
    try:
        identity_manager = IdentityManager()
        identity = prompt_cli_identity(identity_manager)
    except (KeyboardInterrupt, EOFError):
        print()
        return
    except IdentityStoreError as error:
        print(f"Identity startup failed: {error}")
        return

    config = Config()
    logger = Logger(
        level=config.log_level,
        log_to_file=config.log_to_file,
        log_path=identity.data_dir / "astra.log",
    )
    brain = build_runtime(
        config,
        logger,
        identity=identity,
        identity_manager=identity_manager,
    )

    try:
        brain.start()
        while brain.is_running:
            message = input(f"{identity.display_name}: ")
            if not message.strip():
                continue
            brain.receive(message)
    except (KeyboardInterrupt, EOFError):
        print()
        if brain.is_running:
            brain.stop()


if __name__ == "__main__":
    main()
