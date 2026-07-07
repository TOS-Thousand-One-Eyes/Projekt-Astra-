from actions.action_manager import ActionManager
from commands.base import Command
from experience.experience_manager import ExperienceManager
from experience.reflection_manager import ReflectionManager


class ReflectionCommand(Command):
    help_text = (
        "- reflect / reflect tasks / reflections - analyze experience memory and turn findings into tasks"
    )

    def __init__(self, experience=None, reflections=None, actions=None, logger=None):
        super().__init__(logger)
        self.experience = experience or ExperienceManager()
        self.reflections = reflections or ReflectionManager()
        self.actions = actions or ActionManager()

    def handle(self, message, normalized):
        if normalized in ("reflect", "reflect recent", "reflection"):
            return self._reflect()
        if normalized.startswith("reflect recent "):
            return self._reflect(self._argument(message, words=2))
        if normalized == "reflect tasks":
            return self._reflect_tasks()
        if normalized in ("reflections", "reflection history"):
            return self._history()
        return None

    def _reflect(self, limit=50):
        reflection = self.reflections.reflect(self.experience.recent(limit))
        return self._format_reflection(reflection)

    def _reflect_tasks(self):
        reflection = self.reflections.reflect(self.experience.recent(50))
        created = self._create_tasks(reflection)
        lines = [self._format_reflection(reflection), "Created reflection tasks:"]
        if not created:
            lines.append("- none")
        else:
            lines.extend(f"- {task['id']}: {task['title']}" for task in created)
        return "\n".join(lines)

    def _history(self):
        reflections = self.reflections.recent()
        if not reflections:
            return "No reflections recorded yet."
        lines = ["Recent reflections:"]
        for reflection in reflections:
            lines.append(
                f"- {reflection.get('id', 'unknown')} at {reflection.get('timestamp', 'unknown')}: "
                f"{len(reflection.get('findings', []))} finding(s)"
            )
        return "\n".join(lines)

    def _create_tasks(self, reflection):
        created = []
        existing_titles = {
            task.get("title")
            for task in self.actions.list_tasks(status="all")
            if task.get("source") == f"reflection:{reflection['id']}"
        }
        for finding in reflection.get("findings", []):
            title = finding.get("task_title")
            if not title or title in existing_titles:
                continue
            created.append(
                self.actions.create_task(
                    title,
                    priority=severity_to_priority(finding.get("severity")),
                    source=f"reflection:{reflection['id']}",
                    notes=finding.get("recommendation", ""),
                )
            )
        return created

    def _format_reflection(self, reflection):
        lines = [
            f"Reflection {reflection.get('id', 'unknown')}:",
            f"- exchanges analyzed: {reflection.get('exchange_count', 0)}",
        ]
        for finding in reflection.get("findings", []):
            lines.append(
                f"- [{finding.get('severity', 'low')}] {finding.get('title', 'Finding')} "
                f"({finding.get('evidence_count', 0)} evidence): {finding.get('recommendation', '')}"
            )
        return "\n".join(lines)

    def _argument(self, message, words=1):
        parts = message.strip().split(" ", words)
        return parts[-1].strip()


def severity_to_priority(severity):
    if severity == "high":
        return "high"
    if severity == "low":
        return "low"
    return "normal"
