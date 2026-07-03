from commands.base import DispatchResult, looks_like_shell_command, normalize
from commands.exit_command import ExitCommand
from commands.export_command import ExportCommand
from commands.fact_command import FactCommand
from commands.greeting_command import GreetingCommand
from commands.help_command import HelpCommand
from commands.memory_command import MemoryCommand


class CommandRegistry:

    def __init__(self, commands, language_module=None):
        self.commands = commands
        self.language_module = language_module

    def dispatch(self, message):
        normalized = normalize(message)
        for command in self.commands:
            response = command.handle(message, normalized)
            if response is not None:
                return DispatchResult(response, command.stops_brain)
        if looks_like_shell_command(message):
            return DispatchResult("That looks like a shell command, not a chat message - did it get typed into the wrong window?")
        if self.language_module and self.language_module.available:
            response = self.language_module.respond(message)
            if response:
                return DispatchResult(response)
        return DispatchResult(f"I heard: {message}")


def build_default_registry(config, memory, language_module=None):
    fact = FactCommand(memory)
    note = MemoryCommand(memory)
    greeting = GreetingCommand(config, memory)
    farewell = ExitCommand(config)
    export = ExportCommand(config, memory)
    help_command = HelpCommand([fact, note, greeting, farewell, export])

    return CommandRegistry(
        [fact, note, help_command, greeting, farewell, export],
        language_module=language_module,
    )
