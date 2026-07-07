import json
import os
from datetime import datetime
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
REFLECTION_SCHEMA = "astra-experience/reflections/v1"


class ReflectionManager:
    """Deterministic reflection over structured experience records."""

    def __init__(self, data_dir=DATA_DIR):
        self.root = Path(data_dir) / "experience"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "reflections.json"
        self.load_warnings = []
        self.reflections = self._load()

    def reflect(self, exchanges):
        clean_exchanges = [item for item in exchanges if isinstance(item, dict)]
        findings = build_findings(clean_exchanges)
        reflection = {
            "id": self._next_id(),
            "timestamp": timestamp(),
            "exchange_count": len(clean_exchanges),
            "findings": findings,
        }
        self.reflections.append(reflection)
        self._save()
        return reflection

    def recent(self, limit=5):
        return self.reflections[-normalize_limit(limit) :]

    def stats(self):
        total_findings = sum(len(item.get("findings", [])) for item in self.reflections)
        return {
            "total": len(self.reflections),
            "total_findings": total_findings,
            "oldest": self.reflections[0].get("timestamp") if self.reflections else None,
            "newest": self.reflections[-1].get("timestamp") if self.reflections else None,
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
        if isinstance(loaded, dict) and isinstance(loaded.get("reflections"), list):
            return [item for item in loaded["reflections"] if isinstance(item, dict)]
        self.load_warnings.append(f"{self.path.name} has an unsupported shape; starting empty.")
        return []

    def _save(self):
        payload = {"schema": REFLECTION_SCHEMA, "reflections": self.reflections}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix(f"{self.path.suffix}.{os.getpid()}.tmp")
        with open(tmp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        os.replace(tmp_path, self.path)

    def _next_id(self):
        highest = 0
        for reflection in self.reflections:
            raw_id = str(reflection.get("id", ""))
            if raw_id.startswith("REF-"):
                try:
                    highest = max(highest, int(raw_id.split("-", 1)[1]))
                except ValueError:
                    continue
        return f"REF-{highest + 1:04d}"


def build_findings(exchanges):
    if not exchanges:
        return [
            finding(
                "low",
                "No structured experience data",
                0,
                "Use ASTRA normally, then run `reflect` again.",
                "Collect structured experience memory through normal ASTRA sessions",
            )
        ]

    findings = []
    errors = [
        item
        for item in exchanges
        if "Something went wrong handling that" in str(item.get("assistant", ""))
    ]
    if errors:
        findings.append(
            finding(
                "high",
                "Command failures need investigation",
                len(errors),
                "Inspect failing command logs and add a regression test for the failing path.",
                "Investigate reflected command failure and add regression coverage",
            )
        )

    echoes = [item for item in exchanges if item.get("command") == "echo"]
    if echoes:
        findings.append(
            finding(
                "medium",
                "Unrouted messages fell back to echo",
                len(echoes),
                "Teach ASTRA a command for repeated user intents or verify the local model fallback.",
                "Review echo fallback messages and add a command or model route",
            )
        )

    model_issues = [
        item
        for item in exchanges
        if any(
            marker in str(item.get("assistant", "")).lower()
            for marker in (
                "local model unavailable",
                "local model module is not configured",
                "local model did not return",
            )
        )
    ]
    if model_issues:
        findings.append(
            finding(
                "medium",
                "Local model runtime needs attention",
                len(model_issues),
                "Run `model check` and `model smoke`, then fix the Ollama model or endpoint.",
                "Verify and repair local model runtime",
            )
        )

    shell_guards = [item for item in exchanges if item.get("command") == "shell-guard"]
    if shell_guards:
        findings.append(
            finding(
                "low",
                "Shell commands were sent to chat",
                len(shell_guards),
                "Keep shell commands in the terminal path and chat commands in ASTRA.",
                "Document terminal versus chat command routing",
            )
        )

    if not findings:
        findings.append(
            finding(
                "low",
                "No improvement findings in recent experience",
                len(exchanges),
                "Continue collecting structured experiences and run reflection after more usage.",
                "Review structured experience memory after more ASTRA sessions",
            )
        )
    return findings


def finding(severity, title, evidence_count, recommendation, task_title):
    return {
        "severity": severity,
        "title": title,
        "evidence_count": evidence_count,
        "recommendation": recommendation,
        "task_title": task_title,
    }


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
