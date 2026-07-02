from commands.base import Command


class MemoryCommand(Command):

    RECALL_TRIGGERS = ("recall", "what do you remember")

    help_text = (
        "- remember <something> - ask me to save a note\n"
        "- recall / what do you remember - see recent memories\n"
        "- search <text> - search everything I remember\n"
        "- forget <text> - remove a memory that matches exactly"
    )

    def __init__(self, memory):
        self.memory = memory

    def handle(self, message, normalized):
        if normalized.startswith("remember "):
            note = message.split(" ", 1)[1].strip()
            self.memory.remember(note, entry_type="note")
            return f"Got it, I'll remember: {note}"

        if normalized.startswith("forget "):
            text = message.split(" ", 1)[1].strip()
            removed = self.memory.forget(text)
            if removed:
                return f"Okay, I forgot: {text}"
            return f"I couldn't find anything matching: {text}"

        if normalized.startswith("search "):
            query = message.split(" ", 1)[1].strip()
            return self._search_summary(query)

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

    def _search_summary(self, query):
        matches = self.memory.search_long(query)
        if not matches:
            return f"I couldn't find anything matching: {query}"
        lines = [f"- [{item['timestamp']}] {item['entry']}" for item in matches]
        return "Here's what I found:\n" + "\n".join(lines)
