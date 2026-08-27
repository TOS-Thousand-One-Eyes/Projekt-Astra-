import hashlib
import json
import os
import re
import threading
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MODES = {"off", "review", "auto"}


class SelfLearningManager:
    """
    Conservative continual-learning layer.

    Chat learning is explicit: callers capture a preference or correction.
    Eyes may queue repeated observations automatically, but screen observations
    never become global behavioral guidance without approval.
    """

    def __init__(self, data_dir=DATA_DIR, mode="review"):
        self.root = Path(data_dir) / "self_learning"
        self.root.mkdir(parents=True, exist_ok=True)
        self.candidates_path = self.root / "candidates.json"
        self.guidance_path = self.root / "guidance.json"
        self.training_path = self.root / "training_examples.jsonl"
        self.load_warnings = []
        self._lock = threading.RLock()
        self._previous_assistant = ""
        self.mode = "review"
        self.set_mode(mode)

    def set_mode(self, mode):
        with self._lock:
            normalized = str(mode or "").strip().lower()
            if normalized not in MODES:
                raise ValueError(
                    f"Unknown self-learning mode: {mode!r}. "
                    f"Use one of: {', '.join(sorted(MODES))}."
                )
            self.mode = normalized
            return self.mode

    def observe_user_message(self, *args, **kwargs):
        """Backward-compatible no-op: implicit language heuristics were removed."""
        return None

    def set_previous_assistant(self, content):
        """Provide the latest assistant reply for an explicit correction trace."""
        with self._lock:
            self._previous_assistant = self._safe_text(content, limit=1600)
            return self._previous_assistant

    def capture_preference(self, content, source="user:explicit"):
        with self._lock:
            if self.mode == "off":
                return None
            text = self._safe_text(content, limit=1200)
            if len(text) < 3:
                raise ValueError("Preference cannot be empty.")
            candidate = self._upsert_candidate(
                candidate_type="preference",
                content=text,
                previous_assistant="",
                source=source,
                confidence="high",
                auto_eligible=True,
            )
            if self.mode == "auto":
                self._activate_guidance(candidate)
            return candidate

    def capture_correction(
        self,
        content,
        previous_assistant="",
        source="user:explicit",
    ):
        with self._lock:
            if self.mode == "off":
                return None
            text = self._safe_text(content, limit=1200)
            if len(text) < 3:
                raise ValueError("Correction cannot be empty.")
            assistant_before = self._safe_text(
                previous_assistant or self._previous_assistant,
                limit=1600,
            )
            candidate = self._upsert_candidate(
                candidate_type="correction",
                content=text,
                previous_assistant=assistant_before,
                source=source,
                confidence="high",
                auto_eligible=True,
            )
            self._append_training_trace(candidate)
            # Corrections can contain factual claims. Even in auto mode they stay
            # review-gated so a single correction cannot poison global guidance.
            return candidate

    def capture_review_candidate(
        self,
        candidate_type,
        content,
        previous_assistant="",
        source="conversation_scan",
        confidence="medium",
    ):
        """Queue a model-suggested candidate without ever auto-activating it."""
        with self._lock:
            if self.mode == "off":
                return None
            normalized_type = str(candidate_type or "").strip().lower()
            if normalized_type not in {"preference", "correction", "memory_note"}:
                raise ValueError(
                    "Conversation candidate type must be preference, correction, or memory_note."
                )
            text = self._safe_text(content, limit=1200)
            if len(text) < 8:
                raise ValueError("Conversation learning candidate is too short.")
            previous = self._safe_text(previous_assistant, limit=1600)
            fingerprint = hashlib_text(text)
            existing = self._load_list(self.candidates_path, "candidates")
            if any(
                item.get("type") == normalized_type
                and item.get("fingerprint") == fingerprint
                for item in existing
            ):
                return None
            return self._upsert_candidate(
                candidate_type=normalized_type,
                content=text,
                previous_assistant=previous,
                source=self._safe_text(source, limit=240),
                confidence=str(confidence or "medium").strip().lower(),
                auto_eligible=False,
            )

    def observe_screen(
        self,
        observation,
        app="",
        title="",
        confidence="medium",
    ):
        with self._lock:
            if self.mode == "off":
                return None
            text = self._safe_text(observation, limit=1200)
            if len(text) < 12:
                return None

            safe_title = self._safe_text(title, limit=200)
            safe_app = self._safe_text(app, limit=120)
            candidate = self._upsert_candidate(
                candidate_type="screen_observation",
                content=text,
                previous_assistant="",
                source=f"eyes:{safe_app or 'unknown'}:{safe_title or 'window'}",
                confidence=str(confidence or "medium").strip().lower(),
                auto_eligible=False,
            )
            if candidate.get("hits", 1) >= 3:
                candidate["review_ready"] = True
                self._replace_candidate(candidate)
            return candidate

    def guidance(self, limit=12):
        with self._lock:
            items = [
                item
                for item in self._load_list(self.guidance_path, "guidance")
                if item.get("status") == "active"
            ]
            items.sort(key=lambda item: item.get("updated", ""), reverse=True)
            return items[: max(1, int(limit))]

    def pending(self, limit=20):
        with self._lock:
            items = [
                item
                for item in self._load_list(self.candidates_path, "candidates")
                if item.get("status") == "pending"
            ]
            items.sort(
                key=lambda item: (
                    bool(item.get("review_ready")),
                    int(item.get("hits", 1)),
                    item.get("updated", ""),
                ),
                reverse=True,
            )
            return items[: max(1, int(limit))]

    def approve(self, candidate_id):
        with self._lock:
            candidates = self._load_list(self.candidates_path, "candidates")
            candidate = _find_candidate(candidates, candidate_id)
            if not candidate:
                raise KeyError(f"Self-learning candidate not found: {candidate_id}")

            candidate["status"] = "approved"
            candidate["updated"] = timestamp()
            self._save_list(self.candidates_path, candidates)

            if candidate.get("type") in {"preference", "correction"}:
                self._activate_guidance(candidate)
            return candidate

    def reject(self, candidate_id):
        with self._lock:
            candidates = self._load_list(self.candidates_path, "candidates")
            candidate = _find_candidate(candidates, candidate_id)
            if not candidate:
                raise KeyError(f"Self-learning candidate not found: {candidate_id}")
            candidate["status"] = "rejected"
            candidate["updated"] = timestamp()
            self._save_list(self.candidates_path, candidates)
            self._deactivate_guidance_for_candidate(candidate.get("id"))
            return candidate

    def status(self):
        with self._lock:
            candidates = self._load_list(self.candidates_path, "candidates")
            guidance = self._load_list(self.guidance_path, "guidance")
            return {
                "mode": self.mode,
                "implicit_chat_detection": False,
                "conversation_scan_review_gated": True,
                "pending": sum(item.get("status") == "pending" for item in candidates),
                "approved": sum(item.get("status") == "approved" for item in candidates),
                "rejected": sum(item.get("status") == "rejected" for item in candidates),
                "active_guidance": sum(item.get("status") == "active" for item in guidance),
                "training_traces": self._training_trace_count(),
            }

    def _upsert_candidate(
        self,
        candidate_type,
        content,
        previous_assistant,
        source,
        confidence,
        auto_eligible=False,
    ):
        candidates = self._load_list(self.candidates_path, "candidates")
        fingerprint = hashlib_text(content)
        for candidate in candidates:
            if (
                candidate.get("type") == candidate_type
                and candidate.get("fingerprint") == fingerprint
                and candidate.get("status") != "rejected"
            ):
                candidate["hits"] = int(candidate.get("hits", 1)) + 1
                candidate["updated"] = timestamp()
                candidate["auto_eligible"] = bool(
                    candidate.get("auto_eligible", False) or auto_eligible
                )
                if previous_assistant:
                    candidate["previous_assistant"] = previous_assistant
                self._save_list(self.candidates_path, candidates)
                return candidate

        candidate = {
            "id": "SL-" + uuid.uuid4().hex[:10],
            "type": candidate_type,
            "content": content,
            "previous_assistant": previous_assistant,
            "source": source,
            "confidence": confidence,
            "auto_eligible": bool(auto_eligible),
            "hits": 1,
            "review_ready": candidate_type != "screen_observation",
            "status": "pending",
            "fingerprint": fingerprint,
            "created": timestamp(),
            "updated": timestamp(),
        }
        candidates.append(candidate)
        self._save_list(self.candidates_path, candidates)
        return candidate

    def _activate_guidance(self, candidate):
        if candidate.get("type") not in {"preference", "correction"}:
            return None
        guidance = self._load_list(self.guidance_path, "guidance")
        fingerprint = candidate.get("fingerprint") or hashlib_text(candidate.get("content", ""))
        for item in guidance:
            if item.get("fingerprint") == fingerprint:
                item["status"] = "active"
                item["updated"] = timestamp()
                item["hits"] = max(
                    int(item.get("hits", 1)),
                    int(candidate.get("hits", 1)),
                )
                self._save_guidance(guidance)
                self._mark_candidate_approved(candidate.get("id"))
                return item

        item = {
            "id": "G-" + uuid.uuid4().hex[:10],
            "candidate_id": candidate.get("id"),
            "type": candidate.get("type"),
            "text": self._guidance_text(candidate),
            "fingerprint": fingerprint,
            "hits": candidate.get("hits", 1),
            "status": "active",
            "created": timestamp(),
            "updated": timestamp(),
        }
        guidance.append(item)
        self._save_guidance(guidance)
        self._mark_candidate_approved(candidate.get("id"))
        return item

    def _guidance_text(self, candidate):
        content = self._safe_text(candidate.get("content", ""), limit=800)
        reviewed_scan = str(candidate.get("source", "")).startswith(
            "conversation_scan:"
        )
        if candidate.get("type") == "preference":
            if reviewed_scan:
                return "Reviewed conversation preference: " + content
            return "Explicit user preference: " + content
        if candidate.get("type") == "correction":
            previous = self._safe_text(candidate.get("previous_assistant", ""), limit=600)
            label = (
                "Reviewed conversation correction"
                if reviewed_scan
                else "Explicit user correction"
            )
            if previous:
                return (
                    f"{label}. Avoid repeating the corrected behavior. "
                    f"Feedback: {content}"
                )
            return f"{label}: " + content
        return content

    def _mark_candidate_approved(self, candidate_id):
        candidates = self._load_list(self.candidates_path, "candidates")
        candidate = _find_candidate(candidates, candidate_id)
        if candidate:
            candidate["status"] = "approved"
            candidate["updated"] = timestamp()
            self._save_list(self.candidates_path, candidates)

    def _replace_candidate(self, replacement):
        candidates = self._load_list(self.candidates_path, "candidates")
        for index, item in enumerate(candidates):
            if item.get("id") == replacement.get("id"):
                candidates[index] = replacement
                self._save_list(self.candidates_path, candidates)
                return

    def _deactivate_guidance_for_candidate(self, candidate_id):
        if not candidate_id:
            return
        guidance = self._load_list(self.guidance_path, "guidance")
        changed = False
        for item in guidance:
            if item.get("candidate_id") == candidate_id and item.get("status") == "active":
                item["status"] = "inactive"
                item["updated"] = timestamp()
                changed = True
        if changed:
            self._save_guidance(guidance)

    def _append_training_trace(self, candidate):
        record = {
            "schema": "astra-feedback-trace/v1",
            "created": timestamp(),
            "candidate_id": candidate.get("id"),
            "assistant_before": candidate.get("previous_assistant", ""),
            "user_feedback": candidate.get("content", ""),
        }
        self.training_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.training_path, "a", encoding="utf-8", errors="backslashreplace") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _training_trace_count(self):
        if not self.training_path.exists():
            return 0
        try:
            with open(
                self.training_path,
                "r",
                encoding="utf-8",
                errors="replace",
            ) as handle:
                return sum(1 for line in handle if line.strip())
        except OSError as error:
            self._warn_once(
                f"{self.training_path.name} could not be read ({error}); training trace count is unavailable."
            )
            return 0

    def _load_list(self, path, label):
        if not path.exists():
            return []
        try:
            value = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self._warn_once(
                f"{path.name} could not be loaded ({error}); {label} start empty."
            )
            return []
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            self._warn_once(
                f"{path.name} has an unsupported shape; {label} start empty."
            )
            return []
        return value

    def _save_list(self, path, items):
        _atomic_json_write(path, items)

    def _save_guidance(self, items):
        active = [item for item in items if item.get("status") == "active"]
        inactive = [item for item in items if item.get("status") != "active"][-100:]
        self._save_list(self.guidance_path, active + inactive)

    def _safe_text(self, value, limit):
        return _redact_sensitive_text(clean_text(value))[:limit]

    def _warn_once(self, message):
        if message not in self.load_warnings:
            self.load_warnings.append(message)


def _find_candidate(items, candidate_id):
    target = str(candidate_id or "").strip().lower()
    if not target:
        return None
    exact = [item for item in items if str(item.get("id", "")).lower() == target]
    if exact:
        return exact[0]
    prefix = [
        item
        for item in items
        if str(item.get("id", "")).lower().startswith(target)
    ]
    return prefix[0] if len(prefix) == 1 else None


def _atomic_json_write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(
        f"{path.suffix}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex[:6]}.tmp"
    )
    tmp.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        errors="backslashreplace",
    )
    os.replace(tmp, path)


def clean_text(value):
    return " ".join(str(value or "").split())


def hashlib_text(value):
    return hashlib.sha256(clean_text(value).encode("utf-8", errors="replace")).hexdigest()


def timestamp():
    return datetime.now().isoformat(timespec="seconds")


def _redact_sensitive_text(text):
    patterns = (
        r"\bsk-or-v1-[A-Za-z0-9_-]{20,}\b",
        r"\bsk-[A-Za-z0-9_-]{20,}\b",
        r"\b(?:0x)?[A-Fa-f0-9]{64}\b",
        r"\b[A-Za-z0-9+/]{40,}={0,2}\b",
    )
    redacted = str(text)
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED_SECRET]", redacted, flags=re.IGNORECASE)
    return redacted
