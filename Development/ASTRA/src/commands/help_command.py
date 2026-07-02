from commands.base import Command


class HelpCommand(Command):

    TRIGGERS = ("help", "commands", "what can you do")
    help_text = "- help - show this message"

    def __init__(self, other_commands):
        self.other_commands = other_commands

    def handle(self, message, normalized):
        if normalized not in self.TRIGGERS:
            return None

        lines = [command.help_text for command in self.other_commands if command.help_text]
        lines.append(self.help_text)
        return "Here's what I can do:\n" + "\n".join(lines)
