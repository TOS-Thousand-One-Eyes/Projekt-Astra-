import json
import os
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EXPERIENCE_SCHEMA = "astra-experience/exchanges/v1"


class ExperienceManager:
    """Structured local record of user/assistant exchanges."""

    def __init__(self, data_dir=DATA_DIR):
        self.root = Path(data_dir) / "experience"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "exchanges.json"
        self.load_warnings = []
        self.exchanges = self._load()

    def record_exchange(self, user_message, assistant_response, command_name=None, session_id=None, source="brain"):
        exchange = {
            "id": self._next_id(),
            "timestamp": timestamp(),
            "session_id": session_id,
            "source": source or "brain",
            "command": command_name or "unknown",
            "user": str(user_message),
            "assistant": str(assistant_response),
        }
        self.exchanges.append(exchange)
        self._save()
        return exchange

    def recent(self, limit=5):
        count = normalize_limit(limit)
        return self.exchanges[-count:]

    def search(self, query, limit=10):
        text = str(query or "").strip().lower()
        if not text:
            return []
        matches = [
            exchange
            for exchange in self.exchanges
            if text in str(exchange.get("user", "")).lower()
            or text in str(exchange.get("assistant", "")).lower()
            or text in str(exchange.get("command", "")).lower()
        ]
        return matches[-normalize_limit(limit, default=10) :]

    def stats(self):
        command_counts = {}
        for exchange in self.exchanges:
            command = exchange.get("command") or "unknown"
            command_counts[command] = command_counts.get(command, 0) + 1
        return {
            "total": len(self.exchanges),
            "oldest": self.exchanges[0].get("timestamp") if self.exchanges else None,
            "newest": self.exchanges[-1].get("timestamp") if self.exchanges else None,
            "commands": command_counts,
        }

    def _load(self):
        if not self.path.exists():
            return []
        try:
            with open(self.path, "r", encoding="utf-8-sig") as handle:
                loaded = json.load(handle)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as error:
            self.load_warnings.append(f"{self.path.name} could not be loaded ({error}); starting empty.")
            return []
        if isinstance(loaded, list):
            return [item for item in loaded if isinstance(item, dict)]
        if isinstance(loaded, dict) and isinstance(loaded.get("exchanges"), list):
            return [item for item in loaded["exchanges"] if isinstance(item, dict)]
        self.load_warnings.append(f"{self.path.name} has an unsupported shape; starting empty.")
        return []

    def _save(self):
        payload = {"schema": EXPERIENCE_SCHEMA, "exchanges": self.exchanges}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def _next_id(self):
        highest = 0
        for exchange in self.exchanges:
            raw_id = str(exchange.get("id", ""))
            if raw_id.startswith("EXP-"):
                try:
                    highest = max(highest, int(raw_id.split("-", 1)[1]))
                except ValueError:
                    continue
        return f"EXP-{highest + 1:04d}"


def normalize_limit(value, default=5):
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = default
    if count <= 0:
        count = default
    return count


def timestamp():
    return datetime.now().isoformat(timespec="seconds")
