import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SYSTEM_ACTION_SCHEMA = "astra-actions/system-actions/v1"


class SystemActionError(Exception):
    pass


class SystemActionManager:
    """Approval-gated queue for desktop/system actions."""

    def __init__(self, data_dir=DATA_DIR, executor=None):
        self.root = Path(data_dir) / "actions"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "system_actions.json"
        self.executor = executor or SystemActionExecutor()
        self.load_warning = None
        self.actions = self._load()

    def propose(self, kind, target, reason="", source="chat"):
        clean_kind = normalize_kind(kind)
        clean_target = " ".join(str(target).split())
        if not clean_target:
            raise ValueError("System action target cannot be empty.")
        action = {
            "id": self._next_id(),
            "kind": clean_kind,
            "target": clean_target,
            "reason": " ".join(str(reason).split()),
            "source": source or "chat",
            "status": "pending",
            "created": timestamp(),
            "updated": timestamp(),
            "approved_at": None,
            "executed_at": None,
            "result": None,
            "events": [{"at": timestamp(), "event": "proposed"}],
        }
        self.actions.append(action)
        self._save()
        return action

    def list(self, status="pending"):
        items = list(self.actions)
        if status and status != "all":
            items = [item for item in items if item.get("status") == status]
        return sorted(items, key=lambda item: (item.get("status") or "", item.get("id") or ""))

    def approve(self, identifier):
        action = self._find(identifier)
        if action.get("status") != "pending":
            raise SystemActionError(f"Only pending actions can be approved; current status is {action.get('status')}.")
        action["status"] = "approved"
        action["approved_at"] = timestamp()
        action["updated"] = timestamp()
        action.setdefault("events", []).append({"at": timestamp(), "event": "approved"})
        self._save()
        return action

    def reject(self, identifier):
        action = self._find(identifier)
        if action.get("status") in {"executed", "rejected"}:
            raise SystemActionError(f"Cannot reject an action with status {action.get('status')}.")
        action["status"] = "rejected"
        action["updated"] = timestamp()
        action.setdefault("events", []).append({"at": timestamp(), "event": "rejected"})
        self._save()
        return action

    def execute(self, identifier):
        action = self._find(identifier)
        if action.get("status") != "approved":
            raise SystemActionError("System action must be approved before execution.")
        try:
            result = self.executor.execute(action)
        except Exception as error:
            action["status"] = "failed"
            action["result"] = str(error)
            action["updated"] = timestamp()
            action.setdefault("events", []).append({"at": timestamp(), "event": "failed", "error": str(error)})
            self._save()
            raise
        action["status"] = "executed"
        action["executed_at"] = timestamp()
        action["updated"] = timestamp()
        action["result"] = result
        action.setdefault("events", []).append({"at": timestamp(), "event": "executed", "result": result})
        self._save()
        return action

    def _find(self, identifier):
        query = str(identifier).strip().lower()
        if not query:
            raise FileNotFoundError("System action identifier cannot be empty.")
        exact = [item for item in self.actions if item.get("id", "").lower() == query]
        if exact:
            return exact[0]
        target_matches = [item for item in self.actions if query in item.get("target", "").lower()]
        if len(target_matches) == 1:
            return target_matches[0]
        if len(target_matches) > 1:
            raise ValueError(f"System action identifier is ambiguous: {identifier}")
        raise FileNotFoundError(f"System action not found: {identifier}")

    def _load(self):
        if not self.path.exists():
            return []
        try:
            with open(self.path, "r", encoding="utf-8-sig") as handle:
                loaded = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
            self.load_warning = f"{self.path.name} could not be loaded ({error}); starting with no system actions."
            return []
        if isinstance(loaded, dict) and isinstance(loaded.get("actions"), list):
            return [item for item in loaded["actions"] if isinstance(item, dict)]
        if isinstance(loaded, list):
            return [item for item in loaded if isinstance(item, dict)]
        self.load_warning = f"{self.path.name} has an unsupported shape; starting with no system actions."
        return []

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.tmp")
        payload = {"schema": SYSTEM_ACTION_SCHEMA, "actions": self.actions}
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def _next_id(self):
        highest = 0
        for action in self.actions:
            raw = str(action.get("id", ""))
            if raw.startswith("SYS-") and raw[4:].isdigit():
                highest = max(highest, int(raw[4:]))
        return f"SYS-{highest + 1:04d}"


class SystemActionExecutor:
    def execute(self, action):
        kind = normalize_kind(action.get("kind"))
        if kind == "open_path":
            return self._open_path(action.get("target"))
        raise SystemActionError(f"Unsupported system action kind: {kind}")

    def _open_path(self, target):
        path = Path(str(target).strip().strip('"'))
        if not path.exists():
            raise SystemActionError(f"Path does not exist: {target}")
        system = platform.system().lower()
        if system == "windows":
            os.startfile(str(path))  # noqa: S606 - explicit user-approved desktop action.
        elif system == "darwin":
            subprocess.run(["open", str(path)], check=True)
        else:
            subprocess.run(["xdg-open", str(path)], check=True)
        return f"opened:{path}"


def normalize_kind(kind):
    normalized = str(kind or "").strip().lower().replace("-", "_")
    if normalized in {"open", "open_file", "open_path"}:
        return "open_path"
    raise ValueError("Supported system action kinds: open_path.")


def timestamp():
    return datetime.now().isoformat(timespec="seconds")
