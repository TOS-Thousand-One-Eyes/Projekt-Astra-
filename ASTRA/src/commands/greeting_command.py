from commands.base import Command


class GreetingCommand(Command):

    RESPONSES = {
        "hi": "Hello!",
        "hello": "Hi there!",
        "hey": "Hey!",
        "how are you": "I'm doing well, thanks for asking! How about you?",
        "what's up": "Not much, just waiting for your next message!",
    }

    IDENTITY_TRIGGERS = ("what is your name", "who are you", "what's your name")

    help_text = (
        "- hi / hello / hey - greet me\n"
        "- how are you - ask how I'm doing\n"
        "- what is your name / who are you - ask who I am"
    )

    def __init__(self, config):
        self.config = config

    def handle(self, message, normalized):
        if normalized in self.IDENTITY_TRIGGERS:
            return f"I'm {self.config.name}, your personal AI assistant."

        if normalized in self.RESPONSES:
            return self.RESPONSES[normalized]

        return None
