from commands.base import DispatchResult, looks_like_shell_command, normalize
from commands.action_command import ActionCommand
from commands.code_command import CodeCommand
from commands.diagnostics_command import DiagnosticsCommand
from commands.exit_command import ExitCommand
from commands.experience_command import ExperienceCommand
from commands.export_command import ExportCommand
from commands.fact_command import FactCommand
from commands.greeting_command import GreetingCommand
from commands.help_command import HelpCommand
from commands.jarvis_command import JarvisCommand
from commands.learning_command import LearningCommand
from commands.memory_command import MemoryCommand
from commands.model_command import ModelCommand
from commands.reflection_command import ReflectionCommand
from commands.research_command import ResearchCommand
from commands.reminder_command import ReminderCommand
from commands.speech_command import SpeechCommand
from commands.system_action_command import SystemActionCommand
from commands.vision_command import VisionCommand
from commands.web_command import WebCommand
from memory.context_builder import build_model_prompt


class CommandRegistry:

    def __init__(self, commands, language_module=None, memory=None, context_builder=None, logger=None):
        self.commands = commands
        self.language_module = language_module
        self.memory = memory
        self.context_builder = context_builder or build_model_prompt
        self.logger = logger

    def dispatch(self, message):
        try:
            normalized = normalize(message)
        except Exception as error:
            if self.logger:
                self.logger.error(
                    f"Failed to normalize message {message!r}: {type(error).__name__}: {error}"
                )
            return DispatchResult(
                "Something went wrong handling that. I've logged it so it can be looked into.",
                command_name="normalize-error",
            )
        for command in self.commands:
            try:
                response = command.handle(message, normalized)
            except Exception as error:
                if self.logger:
                    self.logger.error(
                        f"Command '{type(command).__name__}' failed on message {message!r}: "
                        f"{type(error).__name__}: {error}"
                    )
                return DispatchResult(
                    "Something went wrong handling that. I've logged it so it can be looked into.",
                    command_name=type(command).__name__,
                )
            if response is not None:
                return DispatchResult(response, command.stops_brain, command_name=type(command).__name__)
        if looks_like_shell_command(message):
            return DispatchResult(
                "That looks like a shell command, not a chat message - did it get typed into the wrong window?",
                command_name="shell-guard",
            )
        if self.language_module and self.language_module.available and message.strip():
            prompt = self._model_prompt(message)
            response = self.language_module.respond(prompt)
            if response:
                return DispatchResult(response, command_name="LanguageModule")
        return DispatchResult(f"I heard: {message}", command_name="echo")

    def _model_prompt(self, message):
        if not self.memory:
            return message
        return self.context_builder(message, self.memory)


def build_default_registry(
    config,
    memory,
    language_module=None,
    learning=None,
    actions=None,
    speech=None,
    vision=None,
    vision_describer=None,
    code=None,
    reminders=None,
    system_actions=None,
    experience=None,
    reflections=None,
    researcher=None,
    logger=None,
):
    fact = FactCommand(memory, logger=logger)
    note = MemoryCommand(memory, logger=logger)
    greeting = GreetingCommand(config, memory, logger=logger)
    farewell = ExitCommand(config, logger=logger)
    export = ExportCommand(config, memory, logger=logger)
    diagnostics = DiagnosticsCommand(config, memory, logger=logger)
    learning_command = LearningCommand(memory, learning=learning, language_module=language_module, logger=logger)
    research_command = ResearchCommand(learning=learning_command.learning, researcher=researcher, logger=logger)
    model_command = ModelCommand(language_module=language_module, config=config, logger=logger)
    experience_command = ExperienceCommand(experience=experience, logger=logger)
    action_command = ActionCommand(actions=actions, logger=logger)
    reflection_command = ReflectionCommand(
        experience=experience_command.experience,
        reflections=reflections,
        actions=action_command.actions,
        logger=logger,
    )
    system_action_command = SystemActionCommand(system_actions=system_actions, logger=logger)
    reminder_command = ReminderCommand(reminders=reminders, logger=logger)
    speech_command = SpeechCommand(speech=speech, logger=logger)
    vision_command = VisionCommand(
        inspector=vision,
        describer=vision_describer,
        language_module=language_module,
        logger=logger,
    )
    jarvis_command = JarvisCommand(
        memory,
        language_module=language_module,
        learning=learning_command.learning,
        actions=action_command.actions,
        system_actions=system_action_command.system_actions,
        reminders=reminder_command.reminders,
        experience=experience_command.experience,
        reflections=reflection_command.reflections,
        speech=speech_command.speech,
        vision_describer=vision_describer,
        logger=logger,
    )
    web_command = WebCommand(logger=logger)
    code_command = CodeCommand(inspector=code, logger=logger)
    help_command = HelpCommand(
        [
            fact,
            note,
            learning_command,
            research_command,
            model_command,
            experience_command,
            reflection_command,
            action_command,
            system_action_command,
            reminder_command,
            jarvis_command,
            web_command,
            speech_command,
            vision_command,
            code_command,
            greeting,
            farewell,
            export,
            diagnostics,
        ],
        logger=logger,
    )

    return CommandRegistry(
        [
            fact,
            note,
            learning_command,
            research_command,
            model_command,
            experience_command,
            reflection_command,
            action_command,
            system_action_command,
            reminder_command,
            jarvis_command,
            web_command,
            speech_command,
            vision_command,
            code_command,
            help_command,
            greeting,
            farewell,
            export,
            diagnostics,
        ],
        language_module=language_module,
        memory=memory,
        logger=logger,
    )
