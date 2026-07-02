from commands.base import Command


class MemoryCommand(Command):

    RECALL_TRIGGERS = ("recall", "what do you remember")

    help_text = (
        "- remember <something> - ask me to save a note\n"
        "- recall / what do you remember - see recent memories"
    )

    def __init__(self, memory):
        self.memory = memory

    def handle(self, message, normalized):
        if normalized.startswith("remember "):
            note = message.split(" ", 1)[1].strip()
            self.memory.remember(note)
            return f"Got it, I'll remember: {note}"

        if normalized in self.RECALL_TRIGGERS:
            return self._recall_summary()

        return None

    def _recall_summary(self):
        entries = self.memory.recall_long()
        if not entries:
            return "I don't remember anything yet."
        recent = entries[-5:]
        lines = [f"- [{item['timestamp']}] {item['entry']}" for item in recent]
        return "Here's what I remember recently:\n" + "\n".join(lines)
