from commands.base import Command
from experience.experience_manager import ExperienceManager


class ExperienceCommand(Command):
    help_text = (
        "- experience recent / experience search <text> / experience stats - inspect structured session memory"
    )

    def __init__(self, experience=None, logger=None):
        super().__init__(logger)
        self.experience = experience or ExperienceManager()

    def handle(self, message, normalized):
        if normalized in ("experience", "experience recent", "experiences"):
            return self._recent()
        if normalized.startswith("experience recent "):
            return self._recent(self._argument(message))
        if normalized == "experience stats":
            return self._stats()
        if normalized == "experience search":
            return "Usage: experience search <text>"
        if normalized.startswith("experience search "):
            return self._search(self._argument(message, words=2))
        return None

    def _recent(self, limit=5):
        exchanges = self.experience.recent(limit)
        if not exchanges:
            return "No structured experiences recorded yet."
        return self._format(exchanges, "Recent experiences:")

    def _search(self, query):
        exchanges = self.experience.search(query)
        if not exchanges:
            return f"No structured experiences matched: {query}"
        return self._format(exchanges, "Matching experiences:")

    def _stats(self):
        stats = self.experience.stats()
        if not stats["total"]:
            return "No structured experiences recorded yet."
        commands = ", ".join(f"{name}: {count}" for name, count in sorted(stats["commands"].items()))
        return (
            "Experience stats:\n"
            f"- total exchanges: {stats['total']}\n"
            f"- oldest: {stats['oldest']}\n"
            f"- newest: {stats['newest']}\n"
            f"- commands: {commands}"
        )

    def _format(self, exchanges, header):
        lines = [header]
        for exchange in exchanges:
            lines.append(
                f"- [{exchange.get('timestamp', 'unknown')}] "
                f"{exchange.get('id', 'unknown')} "
                f"{exchange.get('command', 'unknown')}: "
                f"user={exchange.get('user', '')!r}; assistant={exchange.get('assistant', '')!r}"
            )
        return "\n".join(lines)

    def _argument(self, message, words=1):
        parts = message.strip().split(" ", words)
        return parts[-1].strip()
