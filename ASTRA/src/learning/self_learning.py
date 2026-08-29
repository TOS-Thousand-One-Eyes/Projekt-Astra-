import hashlib
import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MODES = {"off", "review", "auto"}
CANDIDATE_TYPES = {"preference", "correction", "memory_note", "screen_observation"}
CANDIDATE_STATUSES = {"pending", "approved", "rejected"}
GUIDANCE_TYPES = {"preference", "correction"}
GUIDANCE_STATUSES = {"active", "inactive"}

_STORE_LOCKS = {}
_STORE_LOCKS_GUARD = threading.Lock()


def _store_lock(path):
    """Return one in-process lock for every physical self-learning store."""
    key = os.path.normcase(str(Path(path).resolve()))
    with _STORE_LOCKS_GUARD:
        return _STORE_LOCKS.setdefault(key, threading.RLock())


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
        self.integrity_warnings = []
        self._lock = _store_lock(self.root)
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
            candidates = self._load_list(self.candidates_path, "candidates")
            candidates_by_id = {}
            for item in candidates:
                candidate_id = str(item.get("id", "")).strip()
                if candidate_id and candidate_id not in candidates_by_id:
                    candidates_by_id[candidate_id] = item
            items = [
                item
                for item in self._load_list(self.guidance_path, "guidance")
                if item.get("status") == "active"
            ]
            items.sort(key=lambda item: item.get("updated", ""), reverse=True)
            usable = []
            fingerprints = set()
            for item in items:
                issues = self._active_guidance_issues(item, candidates_by_id)
                fingerprint = str(item.get("fingerprint", ""))
                if fingerprint in fingerprints:
                    issues.append("duplicate active fingerprint")
                if issues:
                    identifier = item.get("id", "unknown")
                    self._integrity_warn_once(
                        f"Guidance {identifier} was blocked: {', '.join(issues)}."
                    )
                    continue
                fingerprints.add(fingerprint)
                usable.append(item)
            return usable[: max(1, int(limit))]

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

    def health(self, stale_after_days=30, prompt_limit=8, now=None):
        """Audit continual-learning data without changing or deleting it."""
        with self._lock:
            candidates = self._load_list(self.candidates_path, "candidates")
            guidance = self._load_list(self.guidance_path, "guidance")
            issues = []

            def add(severity, code, item_id, message):
                issues.append(_health_issue(severity, code, item_id, message))

            candidate_ids = {}
            active_fingerprints = {}
            reference_now = _normalize_datetime(now) or datetime.now(timezone.utc)
            stale_days = max(1, int(stale_after_days))

            for item in candidates:
                candidate_id = str(item.get("id", "")).strip()
                item_label = candidate_id or "candidate-without-id"
                if not candidate_id:
                    add("error", "candidate_missing_id", item_label, "Candidate has no ID.")
                elif candidate_id in candidate_ids:
                    add(
                        "error",
                        "duplicate_candidate_id",
                        candidate_id,
                        "Candidate ID is duplicated.",
                    )
                else:
                    candidate_ids[candidate_id] = item

                candidate_type = str(item.get("type", ""))
                if candidate_type not in CANDIDATE_TYPES:
                    add(
                        "error",
                        "candidate_invalid_type",
                        item_label,
                        f"Unsupported candidate type: {candidate_type or 'missing'}.",
                    )
                status = str(item.get("status", ""))
                if status not in CANDIDATE_STATUSES:
                    add(
                        "error",
                        "candidate_invalid_status",
                        item_label,
                        f"Unsupported candidate status: {status or 'missing'}.",
                    )

                content = clean_text(item.get("content", ""))
                if not content:
                    add(
                        "error",
                        "candidate_empty_content",
                        item_label,
                        "Candidate content is empty.",
                    )
                expected_fingerprint = hashlib_text(content)
                fingerprint = str(item.get("fingerprint", ""))
                if not fingerprint or fingerprint != expected_fingerprint:
                    add(
                        "error",
                        "candidate_fingerprint_mismatch",
                        item_label,
                        "Candidate fingerprint does not match its content.",
                    )

                if status != "rejected" and candidate_type and fingerprint:
                    duplicate_key = (candidate_type, fingerprint)
                    previous_id = active_fingerprints.get(duplicate_key)
                    if previous_id:
                        add(
                            "error",
                            "duplicate_candidate",
                            item_label,
                            f"Duplicates non-rejected candidate {previous_id}.",
                        )
                    else:
                        active_fingerprints[duplicate_key] = item_label

                if status == "pending":
                    updated = _normalize_datetime(item.get("updated"))
                    if updated is None:
                        add(
                            "warning",
                            "candidate_invalid_timestamp",
                            item_label,
                            "Pending candidate has no valid updated timestamp.",
                        )
                    elif (reference_now - updated).days >= stale_days:
                        add(
                            "warning",
                            "stale_pending_candidate",
                            item_label,
                            f"Pending candidate has waited at least {stale_days} days for review.",
                        )

            active_guidance = [
                item for item in guidance if item.get("status") == "active"
            ]
            usable_guidance = 0
            blocked_guidance = 0
            guidance_fingerprints = {}
            guidance_ids = set()
            for item in guidance:
                guidance_id = str(item.get("id", "")).strip()
                item_label = guidance_id or "guidance-without-id"
                status = str(item.get("status", ""))
                if not guidance_id:
                    add("error", "guidance_missing_id", item_label, "Guidance has no ID.")
                elif guidance_id in guidance_ids:
                    add(
                        "error",
                        "duplicate_guidance_id",
                        item_label,
                        "Guidance ID is duplicated.",
                    )
                else:
                    guidance_ids.add(guidance_id)
                if status not in GUIDANCE_STATUSES:
                    add(
                        "error",
                        "guidance_invalid_status",
                        item_label,
                        f"Unsupported guidance status: {status or 'missing'}.",
                    )
                if str(item.get("type", "")) not in GUIDANCE_TYPES:
                    add(
                        "error",
                        "guidance_invalid_type",
                        item_label,
                        "Guidance type must be preference or correction.",
                    )
                if not clean_text(item.get("text", "")):
                    add("error", "guidance_empty_text", item_label, "Guidance text is empty.")

            active_guidance.sort(
                key=lambda item: item.get("updated", ""),
                reverse=True,
            )
            for item in active_guidance:
                item_label = str(item.get("id", "")).strip() or "guidance-without-id"
                item_issues = self._active_guidance_issues(item, candidate_ids)
                fingerprint = str(item.get("fingerprint", ""))
                previous_id = guidance_fingerprints.get(fingerprint)
                if fingerprint and previous_id:
                    item_issues.append(f"duplicates active guidance {previous_id}")

                if item_issues:
                    blocked_guidance += 1
                    for detail in item_issues:
                        add(
                            "error",
                            "blocked_active_guidance",
                            item_label,
                            detail.capitalize() + ".",
                        )
                else:
                    usable_guidance += 1
                    guidance_fingerprints[fingerprint] = item_label

            capacity = max(1, int(prompt_limit))
            if usable_guidance > capacity:
                add(
                    "warning",
                    "guidance_prompt_overflow",
                    "guidance",
                    f"{usable_guidance - capacity} active guidance item(s) do not fit in the {capacity}-item prompt window.",
                )

            trace_count, trace_issues = self._training_trace_health(set(candidate_ids))
            issues.extend(trace_issues)
            for warning in self.load_warnings:
                add("error", "load_warning", "store", warning)

            error_count = sum(item["severity"] == "error" for item in issues)
            warning_count = sum(item["severity"] == "warning" for item in issues)
            return {
                "healthy": error_count == 0,
                "candidates": len(candidates),
                "pending": sum(item.get("status") == "pending" for item in candidates),
                "active_guidance": len(active_guidance),
                "usable_guidance": usable_guidance,
                "blocked_guidance": blocked_guidance,
                "prompt_limit": capacity,
                "training_traces": trace_count,
                "errors": error_count,
                "warnings": warning_count,
                "issues": issues,
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
                item["candidate_id"] = candidate.get("id")
                item["type"] = candidate.get("type")
                item["text"] = self._guidance_text(candidate)
                item["fingerprint"] = fingerprint
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

    def _training_trace_health(self, candidate_ids):
        if not self.training_path.exists():
            return 0, []
        count = 0
        issues = []
        try:
            with open(
                self.training_path,
                "r",
                encoding="utf-8",
                errors="replace",
            ) as handle:
                for line_number, line in enumerate(handle, start=1):
                    if not line.strip():
                        continue
                    count += 1
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        issues.append(
                            _health_issue(
                                "error",
                                "invalid_training_trace",
                                f"line:{line_number}",
                                "Training trace is not valid JSON.",
                            )
                        )
                        continue
                    if not isinstance(record, dict) or record.get("schema") != "astra-feedback-trace/v1":
                        issues.append(
                            _health_issue(
                                "error",
                                "invalid_training_trace_schema",
                                f"line:{line_number}",
                                "Training trace has an unsupported schema.",
                            )
                        )
                        continue
                    candidate_id = str(record.get("candidate_id", ""))
                    if not candidate_id or candidate_id not in candidate_ids:
                        issues.append(
                            _health_issue(
                                "warning",
                                "orphan_training_trace",
                                f"line:{line_number}",
                                "Training trace does not reference an existing candidate.",
                            )
                        )
        except OSError as error:
            issues.append(
                _health_issue(
                    "error",
                    "training_trace_read_error",
                    "training",
                    f"Training traces could not be read ({error}).",
                )
            )
        return count, issues

    def _active_guidance_issues(self, item, candidates_by_id):
        issues = []
        if not str(item.get("id", "")).strip():
            issues.append("guidance ID is missing")
        if item.get("type") not in GUIDANCE_TYPES:
            issues.append("guidance type is unsupported")
        if not clean_text(item.get("text", "")):
            issues.append("guidance text is empty")
        candidate_id = str(item.get("candidate_id", ""))
        candidate = candidates_by_id.get(candidate_id)
        if not candidate:
            issues.append("linked candidate is missing")
            return issues
        if candidate.get("status") != "approved":
            issues.append(
                f"linked candidate is {candidate.get('status', 'invalid')}, not approved"
            )
        if item.get("type") != candidate.get("type"):
            issues.append("type does not match the linked candidate")
        candidate_fingerprint = str(candidate.get("fingerprint", ""))
        guidance_fingerprint = str(item.get("fingerprint", ""))
        if not guidance_fingerprint or guidance_fingerprint != candidate_fingerprint:
            issues.append("fingerprint does not match the linked candidate")
        return issues

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

    def _integrity_warn_once(self, message):
        if message not in self.integrity_warnings:
            self.integrity_warnings.append(message)


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


def _health_issue(severity, code, item_id, message):
    return {
        "severity": severity,
        "code": code,
        "item_id": str(item_id),
        "message": message,
    }


def _normalize_datetime(value):
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


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
