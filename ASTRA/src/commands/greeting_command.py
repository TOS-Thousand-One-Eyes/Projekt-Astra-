from commands.base import Command


class GreetingCommand(Command):

    RESPONSES = {
        "hi": "Hello!",
        "hello": "Hi there!",
        "hey": "Hey!",
        "how are you": "I'm doing well, thanks for asking! How about you?",
        "what's up": "Not much, just waiting for your next message!",
    }

    NAME_TEMPLATES = {
        "hi": "Hello, {name}!",
        "hello": "Hi there, {name}!",
        "hey": "Hey, {name}!",
    }

    IDENTITY_TRIGGERS = ("what is your name", "who are you", "what's your name")

    help_text = (
        "- hi / hello / hey - greet me\n"
        "- how are you - ask how I'm doing\n"
        "- what is your name / who are you - ask who I am"
    )

    def __init__(self, config, memory, logger=None):
        super().__init__(logger)
        self.config = config
        self.memory = memory

    def handle(self, message, normalized):
        if normalized in self.IDENTITY_TRIGGERS:
            return f"I'm {self.config.name}, your personal AI assistant."

        if normalized in self.RESPONSES:
            name = self.memory.get_fact("name")
            if name and normalized in self.NAME_TEMPLATES:
                return self.NAME_TEMPLATES[normalized].format(name=name)
            return self.RESPONSES[normalized]

        return None
