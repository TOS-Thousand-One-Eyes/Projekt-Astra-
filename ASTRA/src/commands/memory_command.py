from commands.base import Command


class MemoryCommand(Command):

    RECALL_TRIGGERS = ("recall", "what do you remember")
    HISTORY_TRIGGERS = ("history",)
    STATS_TRIGGERS = ("memory stats",)
    DEFAULT_LIMIT = 5
    SHORT_LIMIT = 2

    help_text = (
        "- remember <something> - ask me to save a note\n"
        "- recall / what do you remember - see your recent notes\n"
        "- search <text> - search your notes\n"
        "- history - see everything, notes and chat both\n"
        "- memory stats - see counts and oldest/newest entry timestamps\n"
        "- forget <text> - remove a memory that matches (case-insensitive)"
    )

    def __init__(self, memory):
        self.memory = memory

    def handle(self, message, normalized):
        if normalized.startswith("remember "):
            note = self._argument(message)
            self.memory.remember(note, entry_type="note")
            return f"Got it, I'll remember: {note}"

        if normalized.startswith("forget "):
            text = self._argument(message)
            removed = self.memory.forget(text)
            if removed:
                return f"Okay, I forgot: {text}"
            return f"I couldn't find anything matching: {text}"

        if normalized.startswith("search "):
            query = self._argument(message)
            return self._search_summary(query)

        if normalized in self.HISTORY_TRIGGERS:
            return self._history_summary()

        if normalized in self.STATS_TRIGGERS:
            return self._stats_summary()

        if normalized in self.RECALL_TRIGGERS:
            return self._recall_summary()

        return None

    def _argument(self, message):
        return message.strip().split(" ", 1)[1].strip()

    def _recall_summary(self):
        notes = [item for item in self.memory.recall_long() if item.get("type") == "note"]
        if not notes:
            return "I don't remember anything yet."
        return self._format_entries(notes[-self._entry_limit():], "Here's what I remember recently:")

    def _search_summary(self, query):
        matches = [item for item in self.memory.search_long(query) if item.get("type") == "note"]
        if not matches:
            return f"I couldn't find anything matching: {query}"
        return self._format_entries(matches, "Here's what I found:")

    def _history_summary(self):
        entries = self.memory.recall_long()
        if not entries:
            return "I don't remember anything yet."
        return self._format_entries(entries[-self._entry_limit():], "Here's everything recently, notes and chat:")

    def _entry_limit(self):
        preference = self.memory.get_fact("response length")
        if isinstance(preference, str) and preference.lower() == "short":
            return self.SHORT_LIMIT
        return self.DEFAULT_LIMIT

    def _stats_summary(self):
        entries = self.memory.recall_long()
        if not entries:
            return "I don't have any memory yet."
        notes = [item for item in entries if item.get("type") == "note"]
        chat_count = len(entries) - len(notes)
        oldest = entries[0].get("timestamp", "unknown")
        newest = entries[-1].get("timestamp", "unknown")
        return (
            "Memory stats:\n"
            f"- total entries: {len(entries)}\n"
            f"- notes: {len(notes)}\n"
            f"- chat: {chat_count}\n"
            f"- oldest: {oldest}\n"
            f"- newest: {newest}"
        )

    def _format_entries(self, entries, header):
        lines = [f"- [{item.get('timestamp', 'unknown')}] {item.get('entry', '')}" for item in entries]
        return header + "\n" + "\n".join(lines)
