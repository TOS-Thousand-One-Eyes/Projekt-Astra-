import json
import os
import threading
from datetime import datetime
from pathlib import Path

from utils.file_store import atomic_json_write, interprocess_file_lock

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
EXPERIENCE_SCHEMA = "astra-experience/exchanges/v1"


class ExperienceManager:
    """Structured local record of user/assistant exchanges."""

    def __init__(self, data_dir=DATA_DIR):
        self.root = Path(data_dir) / "experience"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "exchanges.json"
        self.load_warnings = []
        self._lock = threading.RLock()
        self.exchanges = self._load()

    def record_exchange(
        self,
        user_message,
        assistant_response,
        command_name=None,
        session_id=None,
        source="brain",
        actor_id=None,
    ):
        with self._lock, interprocess_file_lock(self.path):
            exchanges = self._read_for_write()
            self.exchanges = exchanges
            exchange = {
                "id": self._next_id(),
                "timestamp": timestamp(),
                "session_id": session_id,
                "actor_id": actor_id,
                "source": source or "brain",
                "command": command_name or "unknown",
                "user": str(user_message),
                "assistant": str(assistant_response),
            }
            exchanges.append(exchange)
            self._write(exchanges)
            self.exchanges = exchanges
            return dict(exchange)

    def recent(self, limit=5):
        with self._lock:
            count = normalize_limit(limit)
            return [dict(item) for item in self.exchanges[-count:]]

    def search(self, query, limit=10):
        text = str(query or "").strip().lower()
        if not text:
            return []
        with self._lock:
            matches = [
                exchange
                for exchange in self.exchanges
                if text in str(exchange.get("user", "")).lower()
                or text in str(exchange.get("assistant", "")).lower()
                or text in str(exchange.get("command", "")).lower()
            ]
            return [dict(item) for item in matches[-normalize_limit(limit, default=10):]]

    def stats(self):
        with self._lock:
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
        try:
            return self._read()
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as error:
            self.load_warnings.append(
                f"{self.path.name} could not be loaded ({error}); "
                "starting empty in read-only recovery mode."
            )
            return []

    def _read(self):
        if not self.path.exists():
            return []
        with open(self.path, "r", encoding="utf-8-sig") as handle:
            loaded = json.load(handle)
        if isinstance(loaded, list):
            return [item for item in loaded if isinstance(item, dict)]
        if isinstance(loaded, dict) and isinstance(loaded.get("exchanges"), list):
            return [item for item in loaded["exchanges"] if isinstance(item, dict)]
        raise ValueError("expected an exchange list or exchanges object")

    def _read_for_write(self):
        try:
            return self._read()
        except (json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as error:
            raise OSError(
                f"Refusing to overwrite unreadable {self.path.name}: {error}"
            ) from error

    def _save(self):
        with self._lock, interprocess_file_lock(self.path):
            self._read_for_write()
            self._write(self.exchanges)

    def _write(self, exchanges):
        payload = {"schema": EXPERIENCE_SCHEMA, "exchanges": exchanges}
        atomic_json_write(
            self.path,
            payload,
            replace_func=os.replace,
            errors="backslashreplace",
        )

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
