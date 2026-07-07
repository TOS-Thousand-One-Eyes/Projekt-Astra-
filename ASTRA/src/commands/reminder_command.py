import re

from automation.reminder_manager import ReminderManager, ReminderParseError
from commands.base import Command


class ReminderCommand(Command):
    help_text = (
        "- remind me to <thing> at <YYYY-MM-DD HH:MM> - create a reminder\n"
        "- remind me to <thing> every day at <HH:MM> - create a daily reminder\n"
        "- reminders / reminders due / reminders all - list reminders\n"
        "- reminder done <id or title> - complete a reminder"
    )

    def __init__(self, reminders=None, logger=None):
        super().__init__(logger)
        self.reminders = reminders or ReminderManager()

    def handle(self, message, normalized):
        if normalized.startswith("remind me to "):
            return self._create(message.strip()[len("remind me to "):])
        if normalized.startswith("reminder done "):
            return self._complete(message.strip()[len("reminder done "):])
        if normalized.startswith("reminder complete "):
            return self._complete(message.strip()[len("reminder complete "):])
        if normalized in ("reminders", "open reminders"):
            return self._list("open")
        if normalized in ("reminders all", "all reminders"):
            return self._list("all")
        if normalized in ("reminders due", "due reminders"):
            return self._due()
        return None

    def _create(self, text):
        try:
            title, due_at, recurrence = parse_reminder_text(text)
            reminder = self.reminders.create(title, due_at=due_at, recurrence=recurrence)
        except (ValueError, ReminderParseError) as error:
            return f"I couldn't create that reminder: {error}"
        recurrence = f", {reminder['recurrence']}" if reminder.get("recurrence") else ""
        return f"Reminder created: {reminder['id']} - {reminder['title']} at {reminder['due_at']}{recurrence}."

    def _complete(self, identifier):
        try:
            reminder = self.reminders.complete(identifier)
        except FileNotFoundError:
            return f"I couldn't find a reminder matching: {identifier}"
        except ValueError as error:
            return str(error)
        if reminder.get("recurrence") == "daily" and reminder.get("status") == "open":
            return f"Reminder instance completed: {reminder['id']} - next at {reminder['due_at']}."
        return f"Reminder completed: {reminder['id']} - {reminder['title']}."

    def _list(self, status):
        reminders = self.reminders.list(status=status)
        if not reminders:
            return "No reminders."
        return "Reminders:\n" + "\n".join(format_reminder(item) for item in reminders)

    def _due(self):
        due = self.reminders.due()
        if not due:
            return "No due reminders."
        return "Due reminders:\n" + "\n".join(format_reminder(item) for item in due)


def parse_reminder_text(text):
    daily = re.match(r"(.+?)\s+every\s+day\s+at\s+(\d{2}:\d{2})$", text.strip(), re.I)
    if daily:
        title = daily.group(1).strip()
        due_at = "today " + daily.group(2)
        return title, due_at, "daily"
    dated = re.match(r"(.+?)\s+at\s+(.+)$", text.strip(), re.I)
    if dated:
        return dated.group(1).strip(), dated.group(2).strip(), None
    return "", "", None


def format_reminder(reminder):
    recurrence = f", {reminder['recurrence']}" if reminder.get("recurrence") else ""
    return (
        f"- {reminder['id']} [{reminder.get('status')}] {reminder.get('title')} "
        f"at {reminder.get('due_at')}{recurrence}"
    )
