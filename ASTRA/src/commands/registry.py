from commands.base import DispatchResult, looks_like_shell_command, normalize
from commands.diagnostics_command import DiagnosticsCommand
from commands.exit_command import ExitCommand
from commands.export_command import ExportCommand
from commands.fact_command import FactCommand
from commands.greeting_command import GreetingCommand
from commands.help_command import HelpCommand
from commands.memory_command import MemoryCommand


class CommandRegistry:

    def __init__(self, commands, language_module=None, logger=None):
        self.commands = commands
        self.language_module = language_module
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
                "Something went wrong handling that. I've logged it so it can be looked into."
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
                    "Something went wrong handling that. I've logged it so it can be looked into."
                )
            if response is not None:
                return DispatchResult(response, command.stops_brain)
        if looks_like_shell_command(message):
            return DispatchResult("That looks like a shell command, not a chat message - did it get typed into the wrong window?")
        if self.language_module and self.language_module.available and message.strip():
            response = self.language_module.respond(message)
            if response:
                return DispatchResult(response)
        return DispatchResult(f"I heard: {message}")


def build_default_registry(config, memory, language_module=None, logger=None):
    fact = FactCommand(memory, logger=logger)
    note = MemoryCommand(memory, logger=logger)
    greeting = GreetingCommand(config, memory, logger=logger)
    farewell = ExitCommand(config, logger=logger)
    export = ExportCommand(config, memory, logger=logger)
    diagnostics = DiagnosticsCommand(config, memory, logger=logger)
    help_command = HelpCommand([fact, note, greeting, farewell, export, diagnostics], logger=logger)

    return CommandRegistry(
        [fact, note, help_command, greeting, farewell, export, diagnostics],
        language_module=language_module,
        logger=logger,
    )
