from commands.base import Command


class ExitCommand(Command):

    TRIGGERS = ("bye", "goodbye", "exit", "quit", "ctrl+d", "ctrl d", "control d")
    help_text = "- bye / exit / quit / q / :q / ctrl+d - stop the conversation"
    stops_brain = True

    def __init__(self, config, logger=None):
        super().__init__(logger)
        self.config = config

    def handle(self, message, normalized):
        if normalized not in self.TRIGGERS:
            return None

        return f"Goodbye! - {self.config.name}"
