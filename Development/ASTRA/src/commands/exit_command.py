from commands.base import Command


class ExitCommand(Command):

    TRIGGERS = ("bye", "goodbye", "exit", "quit")
    help_text = "- bye / exit / quit - stop the conversation"
    stops_brain = True

    def __init__(self, config):
        self.config = config

    def handle(self, message, normalized):
        if normalized not in self.TRIGGERS:
            return None

        return f"Goodbye! - {self.config.name}"
