import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REMINDER_SCHEMA = "astra-automation/reminders/v1"
DATETIME_FORMAT = "%Y-%m-%d %H:%M"
DATE_FORMAT = "%Y-%m-%d"


class ReminderParseError(ValueError):
    pass


class ReminderManager:
    """Local reminder queue for daily automation workflows."""

    def __init__(self, data_dir=DATA_DIR, now_provider=None):
        self.root = Path(data_dir) / "automation"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "reminders.json"
        self.now_provider = now_provider or datetime.now
        self.load_warning = None
        self.reminders = self._load()

    def create(self, title, due_at, recurrence=None, source="chat"):
        clean_title = " ".join(str(title).split())
        if not clean_title:
            raise ValueError("Reminder title cannot be empty.")
        due = parse_due_at(due_at, now=self.now_provider())
        reminder = {
            "id": self._next_id(),
            "title": clean_title,
            "status": "open",
            "due_at": format_datetime(due),
            "recurrence": normalize_recurrence(recurrence),
            "source": source or "chat",
            "created": timestamp(self.now_provider()),
            "updated": timestamp(self.now_provider()),
            "completed_at": None,
            "events": [{"at": timestamp(self.now_provider()), "event": "created"}],
        }
        self.reminders.append(reminder)
        self._save()
        return reminder

    def list(self, status="open"):
        items = list(self.reminders)
        if status and status != "all":
            items = [item for item in items if item.get("status") == status]
        return sorted(items, key=lambda item: (item.get("due_at") or "", item.get("id") or ""))

    def due(self, now=None):
        reference = now or self.now_provider()
        due_items = []
        for reminder in self.list(status="open"):
            try:
                due_at = parse_due_at(reminder.get("due_at"), now=reference)
            except ReminderParseError:
                continue
            if due_at <= reference:
                due_items.append(reminder)
        return due_items

    def complete(self, identifier):
        reminder = self._find(identifier)
        completed_at = self.now_provider()
        if reminder.get("recurrence") == "daily":
            previous_due = parse_due_at(reminder["due_at"], now=completed_at)
            next_due = previous_due + timedelta(days=1)
            while next_due <= completed_at:
                next_due += timedelta(days=1)
            reminder["due_at"] = format_datetime(next_due)
            reminder["status"] = "open"
            reminder["completed_at"] = timestamp(completed_at)
            reminder["events"].append(
                {
                    "at": timestamp(completed_at),
                    "event": "completed-instance",
                    "next_due_at": reminder["due_at"],
                }
            )
        else:
            reminder["status"] = "done"
            reminder["completed_at"] = timestamp(completed_at)
            reminder["events"].append({"at": timestamp(completed_at), "event": "completed"})
        reminder["updated"] = timestamp(completed_at)
        self._save()
        return reminder

    def _find(self, identifier):
        query = str(identifier).strip().lower()
        if not query:
            raise FileNotFoundError("Reminder identifier cannot be empty.")
        exact = [item for item in self.reminders if item.get("id", "").lower() == query]
        if exact:
            return exact[0]
        title_matches = [item for item in self.reminders if query in item.get("title", "").lower()]
        if len(title_matches) == 1:
            return title_matches[0]
        if len(title_matches) > 1:
            raise ValueError(f"Reminder identifier is ambiguous: {identifier}")
        raise FileNotFoundError(f"Reminder not found: {identifier}")

    def _load(self):
        if not self.path.exists():
            return []
        try:
            with open(self.path, "r", encoding="utf-8-sig") as handle:
                loaded = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
            self.load_warning = f"{self.path.name} could not be loaded ({error}); starting with no reminders."
            return []
        if isinstance(loaded, dict) and isinstance(loaded.get("reminders"), list):
            return [item for item in loaded["reminders"] if isinstance(item, dict)]
        if isinstance(loaded, list):
            return [item for item in loaded if isinstance(item, dict)]
        self.load_warning = f"{self.path.name} has an unsupported shape; starting with no reminders."
        return []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.tmp")
        payload = {"schema": REMINDER_SCHEMA, "reminders": self.reminders}
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def _next_id(self):
        pattern = re.compile(r"^REM-(\d+)$")
        highest = 0
        for reminder in self.reminders:
            match = pattern.match(str(reminder.get("id", "")))
            if match:
                highest = max(highest, int(match.group(1)))
        return f"REM-{highest + 1:04d}"


def parse_due_at(value, now=None):
    reference = now or datetime.now()
    text = " ".join(str(value).strip().split())
    if not text:
        raise ReminderParseError("Reminder due time cannot be empty.")
    lowered = text.lower()
    if lowered.startswith("today "):
        return parse_due_at(reference.strftime(DATE_FORMAT) + " " + text[6:], now=reference)
    if lowered.startswith("tomorrow "):
        tomorrow = reference + timedelta(days=1)
        return parse_due_at(tomorrow.strftime(DATE_FORMAT) + " " + text[9:], now=reference)
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
            return datetime.strptime(text + " 09:00", DATETIME_FORMAT)
        return datetime.strptime(text, DATETIME_FORMAT)
    except ValueError as error:
        raise ReminderParseError("Use YYYY-MM-DD HH:MM, YYYY-MM-DD, today HH:MM, or tomorrow HH:MM.") from error


def normalize_recurrence(value):
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"daily", "every day", "day"}:
        return "daily"
    raise ReminderParseError("Only daily recurrence is supported right now.")


def format_datetime(value):
    return value.strftime(DATETIME_FORMAT)


def timestamp(value=None):
    return (value or datetime.now()).isoformat(timespec="seconds")
