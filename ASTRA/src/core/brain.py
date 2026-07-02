class Brain:

    GREETINGS = {
        "hi": "Hello!",
        "hello": "Hi there!",
        "hey": "Hey!",
        "how are you": "I'm doing well, thanks for asking! How about you?",
        "what's up": "Not much, just waiting for your next message!",
    }

    FAREWELLS = ("bye", "goodbye", "exit", "quit")

    def __init__(self, logger, config, memory, modules):
        self.state = "OFFLINE"
        self.logger = logger
        self.config = config
        self.memory = memory
        self.modules = modules

    def start(self):
        self.state = "STARTING"
        self.logger.log(f"{self.config.name} v{self.config.version} is starting...")
        self.logger.log(f"Hello! I am {self.config.name}.")
        self.state = "RUNNING"
        self.logger.log("Brain is ready.")

    def stop(self):
        self.state = "STOPPING"
        self.logger.log(f"Stopping {self.config.name}...")
        self.state = "OFFLINE"
        self.logger.log(f"{self.config.name} stopped.")

    def receive(self, message):
        self.memory.remember(message)
        response = self.process(message)
        self.memory.remember(response)
        return response

    def process(self, message):
        normalized = self._normalize(message)

        if normalized.startswith("remember "):
            note = message.split(" ", 1)[1].strip()
            self.memory.remember(note)
            return f"Got it, I'll remember: {note}"

        if normalized in ("recall", "what do you remember"):
            return self._recall_summary()

        if normalized in ("help", "commands", "what can you do"):
            return self._help_text()

        if normalized in ("what is your name", "who are you", "what's your name"):
            return f"I'm {self.config.name}, your personal AI assistant."

        if normalized in self.GREETINGS:
            return self.GREETINGS[normalized]

        if normalized in self.FAREWELLS:
            return f"Goodbye! - {self.config.name}"

        return f"I heard: {message}"

    def _recall_summary(self):
        entries = self.memory.recall_long()
        if not entries:
            return "I don't remember anything yet."
        recent = entries[-5:]
        lines = [f"- {item['entry']}" for item in recent]
        return "Here's what I remember recently:\n" + "\n".join(lines)

    def _help_text(self):
        return (
            "Here's what I can do:\n"
            "- hi / hello / hey - greet me\n"
            "- how are you - ask how I'm doing\n"
            "- what is your name / who are you - ask who I am\n"
            "- remember <something> - ask me to save a note\n"
            "- recall / what do you remember - see recent memories\n"
            "- help - show this message\n"
            "- bye / exit / quit - stop the conversation"
        )

    @staticmethod
    def _normalize(message):
        return message.strip().lower().rstrip("?!.")
