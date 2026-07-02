import re


class Brain:

    GREETINGS = {
        "hi": "Hello!",
        "hello": "Hi there!",
        "hey": "Hey!",
        "how are you": "I'm doing well, thanks for asking! How about you?",
        "what's up": "Not much, just waiting for your next message!",
    }

    FAREWELLS = ("bye", "goodbye", "exit", "quit")

    LEARN_PATTERN = re.compile(r"^(?:remember that )?my (.+?) is (.+?)[.!]?$", re.IGNORECASE)
    QUERY_PATTERN = re.compile(r"^what(?:'s| is) my (.+?)\??$", re.IGNORECASE)

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
        self.logger.log(f"You: {message}")
        self.logger.log(f"{self.config.name}: {response}")
        return response

    def process(self, message):
        stripped = message.strip()
        normalized = self._normalize(message)

        learn_match = self.LEARN_PATTERN.match(stripped)
        if learn_match:
            key, value = learn_match.group(1).strip(), learn_match.group(2).strip()
            self.memory.learn(key, value)
            return f"Got it, I'll remember that your {key} is {value}."

        query_match = self.QUERY_PATTERN.match(stripped)
        if query_match:
            key = query_match.group(1).strip()
            value = self.memory.get_fact(key)
            if value:
                return f"Your {key} is {value}."
            return f"I don't know your {key} yet. Tell me with: my {key} is ..."

        if normalized.startswith("remember "):
            note = message.split(" ", 1)[1].strip()
            self.memory.remember(note)
            return f"Got it, I'll remember: {note}"

        if normalized in ("recall", "what do you remember"):
            return self._recall_summary()

        if normalized in ("facts", "what do you know about me", "what do you know"):
            return self._facts_summary()

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
        lines = [f"- [{item['timestamp']}] {item['entry']}" for item in recent]
        return "Here's what I remember recently:\n" + "\n".join(lines)

    def _facts_summary(self):
        facts = self.memory.all_facts()
        if not facts:
            return "I don't know any facts about you yet. Try: my name is ..."
        lines = [f"- your {key} is {value}" for key, value in facts.items()]
        return "Here's what I know about you:\n" + "\n".join(lines)

    def _help_text(self):
        return (
            "Here's what I can do:\n"
            "- hi / hello / hey - greet me\n"
            "- how are you - ask how I'm doing\n"
            "- what is your name / who are you - ask who I am\n"
            "- my <thing> is <value> - teach me a fact (e.g. my name is Erik)\n"
            "- what is my <thing> - ask me about a fact you taught me\n"
            "- facts / what do you know about me - list everything you've taught me\n"
            "- remember <something> - ask me to save a note\n"
            "- recall / what do you remember - see recent memories\n"
            "- help - show this message\n"
            "- bye / exit / quit - stop the conversation"
        )

    @staticmethod
    def _normalize(message):
        return message.strip().lower().rstrip("?!.")
