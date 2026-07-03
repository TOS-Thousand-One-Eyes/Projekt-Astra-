import re

from commands.base import Command


class FactCommand(Command):

    LEARN_PATTERN = re.compile(r"^(?:remember that )?my (.+?) is (.+?)[.!?]*$", re.IGNORECASE)
    QUERY_PATTERN = re.compile(r"^what(?:'s| is) my (.+?)[.!?]*$", re.IGNORECASE)
    SUMMARY_TRIGGERS = ("facts", "what do you know about me", "what do you know")

    help_text = (
        "- my <thing> is <value> - teach me a fact (e.g. my name is Erik)\n"
        "- what is my <thing> - ask me about a fact you taught me\n"
        "- facts / what do you know about me - list everything you've taught me"
    )

    def __init__(self, memory):
        self.memory = memory

    def handle(self, message, normalized):
        stripped = message.strip()

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

        if normalized in self.SUMMARY_TRIGGERS:
            return self._summary()

        return None

    def _summary(self):
        facts = self.memory.all_facts()
        if not facts:
            return "I don't know any facts about you yet. Try: my name is ..."
        lines = [f"- your {key} is {value}" for key, value in facts.items()]
        return "Here's what I know about you:\n" + "\n".join(lines)
