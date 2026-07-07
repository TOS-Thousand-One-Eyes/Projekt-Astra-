import json
import os
import re
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
TASK_SCHEMA = "astra-actions/tasks/v1"
DECISION_SCHEMA = "astra-actions/decisions/v1"


class ActionManager:
    """Local-first task and decision store for ASTRA."""

    def __init__(self, data_dir=DATA_DIR):
        self.root = Path(data_dir) / "actions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.tasks_path = self.root / "tasks.json"
        self.decisions_path = self.root / "decisions.json"
        self.load_warnings = []
        self.tasks = self._load_tasks()
        self.decisions = self._load_decisions()

    def create_task(
        self,
        title,
        priority="normal",
        due=None,
        source="chat",
        notes="",
        plan_id=None,
        save=True,
    ):
        clean_title = " ".join(str(title).split())
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        task = {
            "id": self._next_id("TASK", self.tasks),
            "title": clean_title,
            "status": "open",
            "priority": normalize_priority(priority),
            "due": normalize_due(due),
            "source": source or "chat",
            "notes": notes or "",
            "plan_id": plan_id,
            "created": timestamp(),
            "updated": timestamp(),
            "completed_at": None,
            "events": [{"at": timestamp(), "event": "created", "source": source or "chat"}],
        }
        self.tasks.append(task)
        if save:
            self._save_tasks()
        return task

    def plan_goal(self, goal, steps=None):
        clean_goal = " ".join(str(goal).split())
        if not clean_goal:
            raise ValueError("Plan goal cannot be empty.")
        plan_id = self._next_id("PLAN", [task for task in self.tasks if task.get("plan_id")])
        default_steps = steps or [
            "define the desired outcome",
            "collect source material and constraints",
            "implement the smallest verifiable change",
            "run checks and record evidence",
        ]
        created = []
        for step in default_steps:
            created.append(
                self.create_task(
                    f"{clean_goal}: {step}",
                    priority="normal",
                    source=f"plan:{plan_id}",
                    notes=f"Goal: {clean_goal}",
                    plan_id=plan_id,
                    save=False,
                )
            )
        self._save_tasks()
        self.record_decision(
            f"Created action plan {plan_id}",
            rationale=f"Goal: {clean_goal}",
            impact=f"Created {len(created)} task(s).",
            source="action-manager",
        )
        return {"id": plan_id, "goal": clean_goal, "tasks": created}

    def list_tasks(self, status="open"):
        items = list(self.tasks)
        if status and status != "all":
            items = [task for task in items if task.get("status") == status]
        return sorted(items, key=task_sort_key)

    def complete_task(self, identifier):
        task = self._find_task(identifier)
        if task.get("status") != "done":
            task["status"] = "done"
            task["completed_at"] = timestamp()
            task["updated"] = timestamp()
            task.setdefault("events", []).append({"at": timestamp(), "event": "completed"})
            self._save_tasks()
        return task

    def record_decision(self, title, rationale="", impact="", source="chat"):
        clean_title = " ".join(str(title).split())
        if not clean_title:
            raise ValueError("Decision title cannot be empty.")
        decision = {
            "id": self._next_id("DEC", self.decisions),
            "title": clean_title,
            "rationale": " ".join(str(rationale).split()),
            "impact": " ".join(str(impact).split()),
            "source": source or "chat",
            "created": timestamp(),
        }
        self.decisions.append(decision)
        self._save_decisions()
        return decision

    def list_decisions(self, limit=5):
        try:
            count = int(limit)
        except (TypeError, ValueError):
            count = 5
        if count <= 0:
            count = 5
        return self.decisions[-count:]

    def _find_task(self, identifier):
        query = str(identifier).strip().lower()
        if not query:
            raise FileNotFoundError("Task identifier cannot be empty.")
        exact = [task for task in self.tasks if task.get("id", "").lower() == query]
        if exact:
            return exact[0]
        title_matches = [task for task in self.tasks if query in task.get("title", "").lower()]
        if len(title_matches) == 1:
            return title_matches[0]
        if len(title_matches) > 1:
            raise ValueError(f"Task identifier is ambiguous: {identifier}")
        raise FileNotFoundError(f"Task not found: {identifier}")

    def _load_tasks(self):
        loaded = self._load_json(self.tasks_path, {"schema": TASK_SCHEMA, "tasks": []})
        if isinstance(loaded, list):
            return loaded
        if isinstance(loaded, dict) and isinstance(loaded.get("tasks"), list):
            return [task for task in loaded["tasks"] if isinstance(task, dict)]
        self.load_warnings.append(f"{self.tasks_path.name} has an unsupported shape; starting with no tasks.")
        return []

    def _load_decisions(self):
        loaded = self._load_json(self.decisions_path, {"schema": DECISION_SCHEMA, "decisions": []})
        if isinstance(loaded, list):
            return loaded
        if isinstance(loaded, dict) and isinstance(loaded.get("decisions"), list):
            return [decision for decision in loaded["decisions"] if isinstance(decision, dict)]
        self.load_warnings.append(
            f"{self.decisions_path.name} has an unsupported shape; starting with no decisions."
        )
        return []

    def _load_json(self, path, default):
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                return json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
            self.load_warnings.append(f"{path.name} could not be loaded ({error}); starting empty.")
            return default

    def _save_tasks(self):
        self._save_json(self.tasks_path, {"schema": TASK_SCHEMA, "tasks": self.tasks})

    def _save_decisions(self):
        self._save_json(self.decisions_path, {"schema": DECISION_SCHEMA, "decisions": self.decisions})

    def _save_json(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_suffix(f"{path.suffix}.{os.getpid()}.tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)

    def _next_id(self, prefix, items):
        pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
        highest = 0
        for item in items:
            for candidate in (item.get("id"), item.get("plan_id")):
                match = pattern.match(str(candidate or ""))
                if match:
                    highest = max(highest, int(match.group(1)))
        return f"{prefix}-{highest + 1:04d}"


def task_sort_key(task):
    status_rank = {"open": 0, "blocked": 1, "done": 2}.get(task.get("status"), 9)
    priority_rank = {"high": 0, "normal": 1, "low": 2}.get(task.get("priority"), 1)
    return (status_rank, priority_rank, task.get("due") or "9999-12-31", task.get("id", ""))


def normalize_priority(value):
    normalized = str(value or "normal").strip().lower()
    aliases = {"urgent": "high", "important": "high", "medium": "normal", "default": "normal"}
    normalized = aliases.get(normalized, normalized)
    return normalized if normalized in {"high", "normal", "low"} else "normal"


def normalize_due(value):
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        raise ValueError("Due date must use YYYY-MM-DD.")
    return text


def timestamp():
    return datetime.now().isoformat(timespec="seconds")
