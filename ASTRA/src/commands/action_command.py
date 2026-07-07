import re

from actions.action_manager import ActionManager
from commands.base import Command


class ActionCommand(Command):
    help_text = (
        "- task <title> [priority high|normal|low] [due YYYY-MM-DD] - create a tracked task\n"
        "- plan <goal> - create a four-step action plan\n"
        "- tasks / tasks all / tasks done - list tracked tasks\n"
        "- done <task id or title> - complete a task\n"
        "- decide <decision>: <reason> - record a transparent decision\n"
        "- decisions - show recent decisions"
    )

    def __init__(self, actions=None, logger=None):
        super().__init__(logger)
        self.actions = actions or ActionManager()

    def handle(self, message, normalized):
        if normalized.startswith("task "):
            return self._create_task(message.strip()[len("task "):])
        if normalized.startswith("todo "):
            return self._create_task(message.strip()[len("todo "):])
        if normalized.startswith("plan "):
            return self._plan(message.strip()[len("plan "):])
        if normalized in ("tasks", "open tasks", "todo list"):
            return self._list_tasks("open")
        if normalized in ("tasks all", "all tasks"):
            return self._list_tasks("all")
        if normalized in ("tasks done", "done tasks", "completed tasks"):
            return self._list_tasks("done")
        if normalized.startswith("done "):
            return self._complete(message.strip()[len("done "):])
        if normalized.startswith("complete task "):
            return self._complete(message.strip()[len("complete task "):])
        if normalized.startswith("complete "):
            return self._complete(message.strip()[len("complete "):])
        if normalized.startswith("decide "):
            return self._decide(message.strip()[len("decide "):])
        if normalized == "decisions":
            return self._decisions()
        return None

    def _create_task(self, text):
        try:
            title, priority, due = parse_task_text(text)
            task = self.actions.create_task(title, priority=priority, due=due)
        except ValueError as error:
            return f"I couldn't create that task: {error}"
        due_text = f", due {task['due']}" if task.get("due") else ""
        return f"Task created: {task['id']} - {task['title']} (priority {task['priority']}{due_text})."

    def _plan(self, goal):
        try:
            plan = self.actions.plan_goal(goal)
        except ValueError as error:
            return f"I couldn't create that plan: {error}"
        lines = [f"- {task['id']}: {task['title']}" for task in plan["tasks"]]
        return f"Plan created: {plan['id']} for {plan['goal']}.\n" + "\n".join(lines)

    def _list_tasks(self, status):
        tasks = self.actions.list_tasks(status=status)
        if not tasks:
            if status == "done":
                return "No completed tasks yet."
            if status == "all":
                return "No tasks yet."
            return "No open tasks."
        lines = []
        for task in tasks:
            due = f", due {task['due']}" if task.get("due") else ""
            lines.append(
                f"- {task['id']} [{task.get('status')}] {task.get('title')} "
                f"(priority {task.get('priority')}{due})"
            )
        return "Tasks:\n" + "\n".join(lines)

    def _complete(self, identifier):
        try:
            task = self.actions.complete_task(identifier)
        except FileNotFoundError:
            return f"I couldn't find a task matching: {identifier}"
        except ValueError as error:
            return str(error)
        return f"Task completed: {task['id']} - {task['title']}."

    def _decide(self, text):
        title, rationale = split_decision(text)
        try:
            decision = self.actions.record_decision(title, rationale=rationale)
        except ValueError as error:
            return f"I couldn't record that decision: {error}"
        return f"Decision recorded: {decision['id']} - {decision['title']}."

    def _decisions(self):
        decisions = self.actions.list_decisions()
        if not decisions:
            return "No decisions recorded yet."
        lines = []
        for decision in decisions:
            rationale = f" - {decision['rationale']}" if decision.get("rationale") else ""
            lines.append(f"- {decision['id']}: {decision['title']}{rationale}")
        return "Recent decisions:\n" + "\n".join(lines)


def parse_task_text(text):
    cleaned = " ".join(str(text).split())
    priority = "normal"
    due = None

    priority_match = re.search(r"\bpriority\s+(high|normal|low|urgent|medium|default)\b", cleaned, re.I)
    if priority_match:
        priority = priority_match.group(1)
        cleaned = (cleaned[: priority_match.start()] + cleaned[priority_match.end():]).strip()

    due_match = re.search(r"\bdue\s+(\d{4}-\d{2}-\d{2})\b", cleaned, re.I)
    if due_match:
        due = due_match.group(1)
        cleaned = (cleaned[: due_match.start()] + cleaned[due_match.end():]).strip()

    return cleaned, priority, due


def split_decision(text):
    if ":" not in text:
        return text.strip(), ""
    title, rationale = text.split(":", 1)
    return title.strip(), rationale.strip()
