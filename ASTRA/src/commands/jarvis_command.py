import importlib
from pathlib import Path

from actions.action_manager import ActionManager
from actions.system_action_manager import SystemActionManager
from automation.reminder_manager import ReminderManager
from commands.base import Command
from experience.experience_manager import ExperienceManager
from experience.reflection_manager import ReflectionManager
from learning.learning_manager import LearningManager
from speech.speech_manager import SpeechManager


class JarvisCommand(Command):
    help_text = (
        "- jarvis status / briefing - show memory, learning, and action status\n"
        "- jarvis improve - suggest the next practical project improvements\n"
        "- jarvis capabilities / jarvis audit - show implemented capabilities and gaps\n"
        "- jarvis verify / jarvis self-check - verify runtime readiness for JARVIS layers"
    )

    def __init__(
        self,
        memory,
        language_module=None,
        learning=None,
        actions=None,
        system_actions=None,
        reminders=None,
        experience=None,
        reflections=None,
        speech=None,
        vision_describer=None,
        logger=None,
    ):
        super().__init__(logger)
        self.memory = memory
        self.language_module = language_module
        self.learning = learning or LearningManager()
        self.actions = actions or ActionManager()
        self.system_actions = system_actions or SystemActionManager()
        self.reminders = reminders or ReminderManager()
        self.experience = experience or ExperienceManager()
        self.reflections = reflections or ReflectionManager()
        self.speech = speech or SpeechManager()
        self.vision_describer = vision_describer

    def handle(self, message, normalized):
        if normalized in ("jarvis", "jarvis status", "briefing", "daily briefing"):
            return self._status()
        if normalized == "jarvis improve":
            return self._improve()
        if normalized in ("jarvis capabilities", "jarvis audit"):
            return self._capabilities()
        if normalized in ("jarvis verify", "jarvis self-check", "jarvis runtime-check"):
            return self._verify()
        return None

    def _status(self):
        facts = self.memory.all_facts()
        entries = self.memory.recall_long()
        subjects = self.learning.list_subjects()
        promotion_ready = len([item for item in subjects if item.get("promotion_ready")])
        promoted_subjects = len([item for item in subjects if item.get("promoted")])
        open_tasks = self.actions.list_tasks(status="open")
        next_task = open_tasks[0] if open_tasks else None
        open_reminders = self.reminders.list(status="open")
        due_reminders = self.reminders.due()
        next_reminder = open_reminders[0] if open_reminders else None
        experience_stats = self.experience.stats()
        reflection_stats = self.reflections.stats()
        pending_system_actions = self.system_actions.list(status="pending")
        approved_system_actions = self.system_actions.list(status="approved")
        model_configured = self.language_module is not None
        model_available = bool(model_configured and getattr(self.language_module, "available", False))
        model_client = getattr(self.language_module, "client", None)
        model_name = getattr(model_client, "model", None) or "none"
        vision_client, vision_source = self._vision_client()
        vision_configured = bool(
            vision_source == "vision"
            and vision_client
            and callable(getattr(vision_client, "generate_with_images", None))
        )
        vision_model_name = getattr(vision_client, "model", None) if vision_configured else "none"

        lines = [
            "JARVIS status:",
            f"- facts: {len(facts)}",
            f"- long memory entries: {len(entries)}",
            f"- local model configured: {str(model_configured).lower()}",
            f"- local model available: {str(model_available).lower()}",
            f"- local model: {model_name}",
            f"- local vision model configured: {str(vision_configured).lower()}",
            f"- local vision model: {vision_model_name}",
            f"- structured experiences: {experience_stats['total']}",
            f"- reflections: {reflection_stats['total']}",
            f"- learning subjects: {len(subjects)}",
            f"- promotion-ready subjects: {promotion_ready}",
            f"- promoted learning subjects: {promoted_subjects}",
            f"- open tasks: {len(open_tasks)}",
            f"- pending system actions: {len(pending_system_actions)}",
            f"- approved system actions: {len(approved_system_actions)}",
            f"- open reminders: {len(open_reminders)}",
            f"- due reminders: {len(due_reminders)}",
        ]
        if next_task:
            lines.append(f"- next task: {next_task['id']} - {next_task['title']}")
        else:
            lines.append("- next task: none")
        if next_reminder:
            lines.append(f"- next reminder: {next_reminder['id']} - {next_reminder['title']} at {next_reminder['due_at']}")
        else:
            lines.append("- next reminder: none")
        return "\n".join(lines)

    def _improve(self):
        suggestions = []
        if not self.actions.list_tasks(status="open"):
            suggestions.append("Create tracked tasks for the next project goal with `plan <goal>`.")
        if not self.system_actions.list(status="pending"):
            suggestions.append("Queue desktop actions safely with `system propose open <path>`.")
        if not (self.language_module and getattr(self.language_module, "available", False)):
            suggestions.append("Verify the local model runtime with `model check` and `model smoke`.")
        if not self.reminders.list(status="open"):
            suggestions.append("Create daily automation with `remind me to <thing> every day at HH:MM`.")
        if not self.learning.list_subjects():
            suggestions.append("Create a learning subject with `learn about <topic>` and add source material.")
            suggestions.append("Gather web-backed sources with `research learn <topic>`.")
        ready_unpromoted = [
            item
            for item in self.learning.list_subjects()
            if item.get("promotion_ready") and not item.get("promoted")
        ]
        if ready_unpromoted:
            suggestions.append(f"Promote verified learning with `learning promote {ready_unpromoted[0]['subject']}`.")
        if not self.experience.stats()["total"]:
            suggestions.append("Build structured experience memory through normal chat, then inspect it with `experience recent`.")
        if self.experience.stats()["total"] and not self.reflections.stats()["total"]:
            suggestions.append("Run `reflect` to turn recent experience into improvement findings.")
        if not self.memory.all_facts():
            suggestions.append("Teach ASTRA stable user facts with `my <thing> is <value>`.")
        suggestions.append("Review implemented capabilities and gaps with `jarvis capabilities`.")
        suggestions.append("Verify runtime readiness with `jarvis verify`.")
        suggestions.append("Keep decisions auditable with `decide <decision>: <reason>`.")
        return "Suggested improvements:\n" + "\n".join(f"- {item}" for item in suggestions)

    def _capabilities(self):
        capabilities = self._capability_rows()
        totals = {
            "ok": len([item for item in capabilities if item["status"] == "ok"]),
            "partial": len([item for item in capabilities if item["status"] == "partial"]),
            "gap": len([item for item in capabilities if item["status"] == "gap"]),
        }
        lines = [
            "JARVIS capability audit:",
            f"Summary: ok={totals['ok']} partial={totals['partial']} gap={totals['gap']}",
        ]
        for item in capabilities:
            lines.append(f"- [{item['status']}] {item['name']}: {item['evidence']}")
            if item.get("next"):
                lines.append(f"  next: {item['next']}")
        return "\n".join(lines)

    def _verify(self):
        checks = self._verification_rows()
        totals = {
            "pass": len([item for item in checks if item["status"] == "pass"]),
            "warn": len([item for item in checks if item["status"] == "warn"]),
            "fail": len([item for item in checks if item["status"] == "fail"]),
        }
        lines = [
            "JARVIS runtime verification:",
            f"Summary: pass={totals['pass']} warn={totals['warn']} fail={totals['fail']}",
        ]
        for item in checks:
            lines.append(f"- [{item['status']}] {item['name']}: {item['evidence']}")
            if item.get("next"):
                lines.append(f"  next: {item['next']}")
        return "\n".join(lines)

    def _verification_rows(self):
        rows = [
            self._check(
                "Persistent memory API",
                "pass" if self._has_methods(self.memory, "all_facts", "recall_long", "remember") else "fail",
                "facts, long memory, and write API are callable"
                if self._has_methods(self.memory, "all_facts", "recall_long", "remember")
                else "memory API is missing required methods",
                "Restore MemoryManager all_facts/recall_long/remember."
                if not self._has_methods(self.memory, "all_facts", "recall_long", "remember")
                else None,
            ),
            self._check(
                "Learning proficiency gate",
                "pass"
                if self._has_methods(self.learning, "learn", "evaluate_responses", "approve", "promote")
                else "fail",
                "learning intake, eval, approval, and promotion methods are callable"
                if self._has_methods(self.learning, "learn", "evaluate_responses", "approve", "promote")
                else "learning manager is missing gate methods",
                "Restore LearningManager learn/evaluate_responses/approve/promote."
                if not self._has_methods(self.learning, "learn", "evaluate_responses", "approve", "promote")
                else None,
            ),
            self._verify_model_runtime(),
            self._verify_image_description_runtime(),
            self._verify_speech_runtime(),
            self._check(
                "Task and decision stores",
                "pass" if self._has_methods(self.actions, "create_task", "list_tasks", "record_decision") else "fail",
                "task and decision APIs are callable"
                if self._has_methods(self.actions, "create_task", "list_tasks", "record_decision")
                else "task or decision API is missing",
                "Restore ActionManager task and decision methods."
                if not self._has_methods(self.actions, "create_task", "list_tasks", "record_decision")
                else None,
            ),
            self._check(
                "Approval-gated system actions",
                "pass"
                if self._has_methods(self.system_actions, "propose", "approve", "execute")
                else "fail",
                "system actions require propose, approve, then execute"
                if self._has_methods(self.system_actions, "propose", "approve", "execute")
                else "system action approval gate is missing",
                "Restore SystemActionManager propose/approve/execute."
                if not self._has_methods(self.system_actions, "propose", "approve", "execute")
                else None,
            ),
            self._check(
                "Reminders",
                "pass" if self._has_methods(self.reminders, "create", "due", "list", "complete") else "fail",
                "reminder create/list/due/complete APIs are callable"
                if self._has_methods(self.reminders, "create", "due", "list", "complete")
                else "reminder API is missing",
                "Restore ReminderManager create/due/list/complete."
                if not self._has_methods(self.reminders, "create", "due", "list", "complete")
                else None,
            ),
            self._check(
                "Experience and reflection loop",
                "pass"
                if self._has_methods(self.experience, "record_exchange", "stats")
                and self._has_methods(self.reflections, "reflect", "stats")
                else "fail",
                "experience recording and reflection APIs are callable"
                if self._has_methods(self.experience, "record_exchange", "stats")
                and self._has_methods(self.reflections, "reflect", "stats")
                else "experience or reflection API is missing",
                "Restore ExperienceManager and ReflectionManager APIs."
                if not (
                    self._has_methods(self.experience, "record_exchange", "stats")
                    and self._has_methods(self.reflections, "reflect", "stats")
                )
                else None,
            ),
            self._check(
                "Transparent log",
                "pass" if (self._project_root() / "docs" / "JARVIS_TRANSPARENCY_LOG.md").exists() else "fail",
                "docs/JARVIS_TRANSPARENCY_LOG.md exists",
                "Create and maintain docs/JARVIS_TRANSPARENCY_LOG.md."
                if not (self._project_root() / "docs" / "JARVIS_TRANSPARENCY_LOG.md").exists()
                else None,
            ),
        ]
        return rows

    def _verify_model_runtime(self):
        if not self.language_module:
            return self._check(
                "Local model runtime",
                "warn",
                "language module is not configured for this session",
                "Enable use_language_fallback and run `model check` / `model smoke`.",
            )
        client = getattr(self.language_module, "client", None)
        if not client or not callable(getattr(client, "ensure_available", None)):
            return self._check(
                "Local model runtime",
                "fail",
                "language module has no usable client",
                "Wire a client with ensure_available().",
            )
        try:
            client.ensure_available()
        except Exception as error:
            self.language_module.available = False
            return self._check(
                "Local model runtime",
                "warn",
                f"configured but unavailable: {error}",
                "Start Ollama, install the configured model, then run `model check`.",
            )
        self.language_module.available = True
        return self._check(
            "Local model runtime",
            "pass",
            f"available model={getattr(client, 'model', 'unknown')}",
        )

    def _verify_image_description_runtime(self):
        client, source = self._vision_client()
        if client and callable(getattr(client, "generate_with_images", None)):
            model_name = getattr(client, "model", "unknown")
            if source == "language" and getattr(self.language_module, "available", False):
                return self._check(
                    "Model-backed image description",
                    "warn",
                    f"image payload API is present through language model={model_name}, but no image smoke was run",
                    "Run `image describe <path>` with a real local image and vision-capable model.",
                )
            if source == "vision":
                if not callable(getattr(client, "ensure_available", None)):
                    return self._check(
                        "Model-backed image description",
                        "warn",
                        f"vision client model={model_name} cannot be availability-checked",
                        "Use an Ollama client with ensure_available(), then run `image describe <path>`.",
                    )
                try:
                    client.ensure_available()
                except Exception as error:
                    return self._check(
                        "Model-backed image description",
                        "warn",
                        f"configured vision model={model_name} is unavailable: {error}",
                        "Start Ollama, install the configured vision model, then run `image describe <path>`.",
                    )
                return self._check(
                    "Model-backed image description",
                    "warn",
                    f"vision model runtime is available model={model_name}, but no image smoke was run",
                    "Run `image describe <path>` with a real local image before claiming visual understanding.",
                )
            return self._check(
                "Model-backed image description",
                "warn",
                f"image payload API is present through language model={model_name}, but local model runtime is not verified",
                "Run `model check`, then `image describe <path>` with a vision-capable model.",
            )
        return self._check(
            "Model-backed image description",
            "warn",
            "no vision-capable client is configured for this session",
            "Set use_vision_model=true with a vision-capable Ollama model, then run `image describe <path>`.",
        )

    def _verify_speech_runtime(self):
        if not self.speech or not callable(getattr(self.speech, "status", None)):
            return self._check(
                "Speech runtime",
                "fail",
                "speech adapter has no status API",
                "Restore SpeechManager.status().",
            )
        status = self.speech.status()
        tts = bool(status.get("text_to_speech"))
        stt = bool(status.get("speech_to_text"))
        passive = bool(status.get("passive_listening"))
        if tts and stt and not passive:
            return self._check(
                "Speech runtime",
                "pass",
                f"platform={status.get('platform')}; tts=true; stt=true; passive_listening=false",
            )
        return self._check(
            "Speech runtime",
            "warn",
            f"platform={status.get('platform')}; tts={str(tts).lower()}; stt={str(stt).lower()}; "
            f"passive_listening={str(passive).lower()}",
            "Use Windows System.Speech or provide a compatible speech adapter.",
        )

    def _capability_rows(self):
        facts = self.memory.all_facts() if self.memory else {}
        entries = self.memory.recall_long() if self.memory else []
        subjects = self.learning.list_subjects()
        promoted_subjects = [item for item in subjects if item.get("promoted")]
        promotion_ready = [item for item in subjects if item.get("promotion_ready")]
        model_configured = self.language_module is not None
        model_available = bool(model_configured and getattr(self.language_module, "available", False))
        vision_client, vision_source = self._vision_client()
        vision_configured = bool(
            vision_source == "vision"
            and vision_client
            and callable(getattr(vision_client, "generate_with_images", None))
        )
        vision_model = getattr(vision_client, "model", None) if vision_configured else "none"
        log_path = self._project_root() / "docs" / "JARVIS_TRANSPARENCY_LOG.md"

        rows = [
            self._capability(
                "Persistent memory",
                "ok" if self.memory else "gap",
                f"facts={len(facts)}, long_memory_entries={len(entries)}",
                "Create a MemoryManager and pass it into Brain." if not self.memory else None,
            ),
            self._capability(
                "Memory-aware model context",
                "ok" if self._module_has("memory.context_builder", "build_model_prompt") else "gap",
                "normal language fallback can enrich prompts from facts, notes, and learned memory",
                "Restore memory.context_builder.build_model_prompt." if not self._module_has("memory.context_builder", "build_model_prompt") else None,
            ),
            self._capability(
                "Source-backed learning",
                "ok" if self._has_methods(self.learning, "learn", "add_source", "list_subjects") else "gap",
                f"subjects={len(subjects)}; supports capture, distillation, and eval case generation",
                "Implement LearningManager.learn/add_source/list_subjects." if not self._has_methods(self.learning, "learn", "add_source", "list_subjects") else None,
            ),
            self._capability(
                "Proficiency learning gate",
                "ok" if self._has_methods(self.learning, "evaluate_responses", "approve", "promote") else "gap",
                f"promotion_ready={len(promotion_ready)}, promoted={len(promoted_subjects)}; promotion requires eval and approval",
                "Wire response evaluation, review approval, and promotion." if not self._has_methods(self.learning, "evaluate_responses", "approve", "promote") else None,
            ),
            self._capability(
                "Local model runtime",
                "ok" if model_available else ("partial" if model_configured else "partial"),
                self._model_evidence(model_configured, model_available),
                None if model_available else "Run `model check` and `model smoke` against the local Ollama runtime.",
            ),
            self._capability(
                "Structured experience memory",
                "ok" if self._has_methods(self.experience, "record_exchange", "recent", "stats") else "gap",
                f"structured_experiences={self.experience.stats()['total']}; chat exchanges can be recorded as evidence",
                "Restore ExperienceManager record_exchange/recent/stats." if not self._has_methods(self.experience, "record_exchange", "recent", "stats") else None,
            ),
            self._capability(
                "Reflection loop",
                "ok" if self._has_methods(self.reflections, "reflect", "stats") else "gap",
                f"reflections={self.reflections.stats()['total']}; findings can become tracked tasks",
                "Restore ReflectionManager.reflect/stats." if not self._has_methods(self.reflections, "reflect", "stats") else None,
            ),
            self._capability(
                "Tasks and decisions",
                "ok" if self._has_methods(self.actions, "create_task", "plan_goal", "record_decision") else "gap",
                f"open_tasks={len(self.actions.list_tasks(status='open'))}; decisions={len(self.actions.list_decisions())}",
                "Restore ActionManager task, plan, and decision methods." if not self._has_methods(self.actions, "create_task", "plan_goal", "record_decision") else None,
            ),
            self._capability(
                "Approval-gated system actions",
                "ok" if self._has_methods(self.system_actions, "propose", "approve", "execute") else "gap",
                f"pending={len(self.system_actions.list(status='pending'))}, approved={len(self.system_actions.list(status='approved'))}; execution requires approval",
                "Restore SystemActionManager propose/approve/execute." if not self._has_methods(self.system_actions, "propose", "approve", "execute") else None,
            ),
            self._capability(
                "Reminders and automation",
                "ok" if self._has_methods(self.reminders, "create", "due", "list", "complete") else "gap",
                f"open_reminders={len(self.reminders.list(status='open'))}, due={len(self.reminders.due())}",
                "Restore ReminderManager create/due/list/complete." if not self._has_methods(self.reminders, "create", "due", "list", "complete") else None,
            ),
            self._capability(
                "Explicit web fetch",
                "ok" if self._module_has("commands.web_command", "WebCommand") else "gap",
                "bounded http/https URL fetch command is available",
                "Restore commands.web_command.WebCommand." if not self._module_has("commands.web_command", "WebCommand") else None,
            ),
            self._capability(
                "Bounded web research",
                "ok"
                if (
                    self._module_has("commands.research_command", "ResearchCommand")
                    and self._module_has("research.web_researcher", "WebResearcher")
                )
                else "gap",
                "`research <topic>` and `research learn <topic>` can search, fetch limited sources, and feed learning",
                (
                    "Restore ResearchCommand and WebResearcher."
                    if not (
                        self._module_has("commands.research_command", "ResearchCommand")
                        and self._module_has("research.web_researcher", "WebResearcher")
                    )
                    else None
                ),
            ),
            self._capability(
                "Speech output",
                "ok" if self._module_has("commands.speech_command", "SpeechCommand") else "gap",
                "text-to-speech command is available; runtime depends on host speech support",
                "Restore commands.speech_command.SpeechCommand." if not self._module_has("commands.speech_command", "SpeechCommand") else None,
            ),
            self._capability(
                "Speech-to-text input",
                "ok"
                if (
                    self._module_has("commands.speech_command", "SpeechCommand")
                    and self._module_class_has("speech.speech_manager", "SpeechManager", "listen_once")
                )
                else "gap",
                "`listen` and `speech listen` explicitly transcribe one microphone utterance; passive listening is disabled",
                (
                    "Restore SpeechCommand and SpeechManager.listen_once."
                    if not (
                        self._module_has("commands.speech_command", "SpeechCommand")
                        and self._module_class_has("speech.speech_manager", "SpeechManager", "listen_once")
                    )
                    else None
                ),
            ),
            self._capability(
                "Image inspection",
                "ok" if self._module_has("commands.vision_command", "VisionCommand") else "gap",
                "image metadata inspection is available for explicit local PNG, JPEG, and GIF files",
                "Restore commands.vision_command.VisionCommand." if not self._module_has("commands.vision_command", "VisionCommand") else None,
            ),
            self._capability(
                "Model-backed image description",
                "partial"
                if (
                    self._module_class_has("vision.semantic_vision", "LocalVisionDescriber", "describe")
                    and self._module_class_has("utils.ollama_client", "OllamaClient", "generate_with_images")
                )
                else "gap",
                (
                    "`image describe <path>` can send explicit local images to a vision-capable "
                    f"Ollama model; configured={str(vision_configured).lower()}, model={vision_model}"
                ),
                (
                    "Restore LocalVisionDescriber and OllamaClient.generate_with_images."
                    if not (
                        self._module_class_has("vision.semantic_vision", "LocalVisionDescriber", "describe")
                        and self._module_class_has("utils.ollama_client", "OllamaClient", "generate_with_images")
                    )
                    else (
                        "Run `image describe <path>` with a real image before claiming runtime visual understanding."
                        if vision_configured
                        else "Set use_vision_model=true with a vision-capable Ollama model."
                    )
                ),
            ),
            self._capability(
                "Programming inspection",
                "ok" if self._module_has("commands.code_command", "CodeCommand") else "gap",
                "read-only Python code inspection command is available",
                "Restore commands.code_command.CodeCommand." if not self._module_has("commands.code_command", "CodeCommand") else None,
            ),
            self._capability(
                "Transparent project log",
                "ok" if log_path.exists() else "gap",
                f"log_path={log_path}",
                "Create docs/JARVIS_TRANSPARENCY_LOG.md and keep appending decisions." if not log_path.exists() else None,
            ),
        ]
        return rows

    def _model_evidence(self, configured, available):
        if not configured:
            return "model command exists, but no language module is configured for this Brain instance"
        model_client = getattr(self.language_module, "client", None)
        model_name = getattr(model_client, "model", None) or "unknown"
        if available:
            return f"configured=true, available=true, model={model_name}"
        return f"configured=true, available=false, model={model_name}"

    def _vision_client(self):
        client = getattr(self.vision_describer, "client", None)
        if client is not None:
            return client, "vision"
        if self.language_module:
            return getattr(self.language_module, "client", None), "language"
        return None, None

    def _capability(self, name, status, evidence, next=None):
        return {
            "name": name,
            "status": status,
            "evidence": evidence,
            "next": next,
        }

    def _check(self, name, status, evidence, next=None):
        return {
            "name": name,
            "status": status,
            "evidence": evidence,
            "next": next,
        }

    def _has_methods(self, target, *methods):
        return target is not None and all(callable(getattr(target, method, None)) for method in methods)

    def _module_has(self, module_name, attribute):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            return False
        return hasattr(module, attribute)

    def _module_class_has(self, module_name, class_name, method_name):
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            return False
        cls = getattr(module, class_name, None)
        return cls is not None and callable(getattr(cls, method_name, None))

    def _project_root(self):
        return Path(__file__).resolve().parents[2]
