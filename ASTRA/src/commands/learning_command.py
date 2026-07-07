import json
import re

from commands.base import Command
from learning.learning_manager import LearningManager, slugify, tokenize
from utils.web_fetcher import WebFetchError, fetch_url


class LearningCommand(Command):

    help_text = (
        "- learn about <topic> / nauč se <téma> - create or update a learning subject\n"
        "- learn deeply about <topic> - create a proficient-level learning subject\n"
        "- teach <topic>: <source text> - add source material to a learning subject\n"
        "- learn source <topic>: <url> - add an explicit web source to a subject\n"
        "- learning status [topic] - show learning subjects or one subject state\n"
        "- learning eval <topic> - show eval prompts for a subject\n"
        "- learning run-eval <topic> - run eval prompts through the local language module\n"
        "- learning promote <topic> - promote approved, eval-passing learning into long memory"
    )

    def __init__(self, memory, learning=None, language_module=None, web_fetcher=None, logger=None):
        super().__init__(logger)
        self.memory = memory
        self.learning = learning or LearningManager()
        self.language_module = language_module
        self.web_fetcher = web_fetcher or fetch_url

    def handle(self, message, normalized):
        if normalized.startswith("learn deeply about "):
            return self._learn(message.strip()[len("learn deeply about "):], target_level="proficient")
        if normalized.startswith("learn proficient about "):
            return self._learn(message.strip()[len("learn proficient about "):], target_level="proficient")
        if normalized.startswith("learn about "):
            return self._learn(message.strip()[len("learn about "):])
        if normalized.startswith("learn source "):
            return self._learn_source(message.strip()[len("learn source "):])
        if normalized.startswith("learn "):
            return self._learn(message.strip()[len("learn "):])
        if normalized.startswith("nauč se "):
            return self._learn(message.strip()[len("nauč se "):])
        if normalized.startswith("nauc se "):
            return self._learn(message.strip()[len("nauc se "):])
        if normalized.startswith("teach "):
            return self._teach(message.strip()[len("teach "):])
        if normalized.startswith("zdroj pro "):
            return self._teach_czech(message.strip()[len("zdroj pro "):])
        if normalized == "learning status":
            return self._list_subjects()
        if normalized.startswith("learning status "):
            return self._status(message.strip()[len("learning status "):])
        if normalized.startswith("learning eval "):
            return self._eval_prompts(message.strip()[len("learning eval "):])
        if normalized.startswith("learning run-eval "):
            return self._run_eval(message.strip()[len("learning run-eval "):])
        if normalized.startswith("learning approve "):
            return self._approve(message.strip()[len("learning approve "):])
        if normalized.startswith("learning promote "):
            return self._promote(message.strip()[len("learning promote "):])
        return None

    def _learn(self, subject, target_level="working"):
        subject = subject.strip()
        if not subject:
            return "Tell me what subject to learn."
        candidates = self._memory_candidates(subject)
        payload = self.learning.learn(
            subject,
            target_use="answer future ASTRA questions with cited memory",
            target_level=target_level,
            source_candidates=candidates,
        )
        source_count = len(payload.get("sources", []))
        if source_count:
            return (
                f"Learning subject created: {payload['subject']} ({payload['slug']}).\n"
                f"Captured {source_count} source candidate(s) from memory and generated "
                f"{len(payload['eval_cases'])} eval cases for {payload.get('target_level')} level.\n"
                "Next: add stronger source text with `teach <topic>: <source text>` or run `learning eval <topic>`."
            )
        return (
            f"Learning subject created: {payload['subject']} ({payload['slug']}).\n"
            "I did not find usable source material in memory yet. Add evidence with "
            "`teach <topic>: <source text>` before trusting this subject."
        )

    def _learn_source(self, text):
        subject, url = self._split_subject_and_source(text)
        if not subject or not url:
            return "Use: learn source <topic>: <url>"
        try:
            fetched = self.web_fetcher(url)
        except WebFetchError as error:
            return f"I couldn't fetch that source: {error}"
        except Exception as error:
            if self.logger:
                self.logger.error(f"Learning source fetch failed: {type(error).__name__}: {error}")
            return "Something went wrong fetching that source."
        content = str(fetched.get("text", "")).strip()
        if not content:
            return f"I fetched {fetched.get('url', url)}, but found no readable text."
        source = f"web:{fetched.get('url', url)}"
        payload = self.learning.add_source(subject, content, source=source, confidence="medium")
        return (
            f"Added web source to {payload['subject']}.\n"
            f"Source: {source}\n"
            f"Sources: {len(payload['sources'])}; eval cases: {len(payload['eval_cases'])}."
        )

    def _teach(self, text):
        subject, source_text = self._split_subject_and_source(text)
        if not subject or not source_text:
            return "Use: teach <topic>: <source text>"
        payload = self.learning.add_source(subject, source_text, source="user:teach", confidence="high")
        return (
            f"Added source material to {payload['subject']}.\n"
            f"Sources: {len(payload['sources'])}; eval cases: {len(payload['eval_cases'])}.\n"
            "Use `learning eval <topic>` to test proficiency prompts."
        )

    def _teach_czech(self, text):
        subject, source_text = self._split_subject_and_source(text)
        if not subject or not source_text:
            return "Použij: zdroj pro <téma>: <text zdroje>"
        payload = self.learning.add_source(subject, source_text, source="user:zdroj", confidence="high")
        return (
            f"Přidal jsem zdroj k tématu {payload['subject']}.\n"
            f"Zdroje: {len(payload['sources'])}; eval cases: {len(payload['eval_cases'])}."
        )

    def _status(self, subject):
        payload = self.learning.get(subject)
        if not payload:
            return f"I don't have a learning subject for: {subject}"
        report = payload.get("eval_report") or {}
        return (
            f"Learning status for {payload['subject']}:\n"
            f"- status: {payload.get('status')}\n"
            f"- sources: {len(payload.get('sources', []))}\n"
            f"- eval cases: {len(payload.get('eval_cases', []))}\n"
            f"- eval passed: {report.get('passed_gate', False)}\n"
            f"- review: {payload.get('review_status')}\n"
            f"- promotion ready: {payload.get('promotion_ready', False)}"
        )

    def _list_subjects(self):
        subjects = self.learning.list_subjects()
        if not subjects:
            return "No learning subjects yet."
        lines = [
            f"- {item['subject']} ({item['slug']}): {item['status']}, "
            f"{item['sources']} source(s), promotion ready: {item['promotion_ready']}"
            for item in subjects
        ]
        return "Learning subjects:\n" + "\n".join(lines)

    def _eval_prompts(self, subject):
        try:
            cases = self.learning.eval_prompts(subject)
        except FileNotFoundError:
            return f"I don't have a learning subject for: {subject}"
        lines = [f"- {case['id']}: {case['query']}" for case in cases]
        return "Eval prompts:\n" + "\n".join(lines)

    def _approve(self, subject):
        try:
            payload = self.learning.approve(subject)
        except FileNotFoundError:
            return f"I don't have a learning subject for: {subject}"
        if payload.get("promotion_ready"):
            return f"{payload['subject']} is approved and promotion-ready."
        return f"{payload['subject']} is approved, but it still needs a passing eval report before promotion."

    def _promote(self, subject):
        existing = self.learning.get(subject)
        if not existing:
            return f"I don't have a learning subject for: {subject}"
        if existing.get("promoted_at"):
            return f"{existing['subject']} is already promoted to long memory."
        try:
            payload = self.learning.promote(subject)
        except ValueError as error:
            return str(error)
        note = payload.get("promotion_note") or ""
        self.memory.remember(note, entry_type="learned")
        return (
            f"Promoted learning subject to long memory: {payload['subject']}.\n"
            f"Stored as learned memory with {len(payload.get('sources', []))} source(s)."
        )

    def _run_eval(self, subject):
        if not self.language_module or not getattr(self.language_module, "available", False):
            return (
                "No local language module is available for run-eval. "
                "Start ASTRA with the language fallback enabled, or use `learning eval <topic>` "
                "and provide answers manually."
            )
        try:
            cases = self.learning.eval_prompts(subject)
        except FileNotFoundError:
            return f"I don't have a learning subject for: {subject}"
        responses = []
        for case in cases:
            prompt = self._eval_prompt(case)
            answer = self.language_module.respond(prompt)
            if not answer:
                return f"Local language module did not return an answer for {case['id']}."
            responses.append({"case_id": case["id"], "answer": answer})
        report = self.learning.evaluate_responses(subject, responses)
        return (
            f"Learning eval complete for {subject}: "
            f"{report['passed_cases']}/{report['total_cases']} passed "
            f"({report['pass_percent']}%). Gate passed: {report['passed_gate']}."
        )

    def _eval_prompt(self, case):
        expected_sources = ", ".join(case.get("expected_sources", [])) or "none"
        return (
            f"Learning eval case: {case['id']}\n"
            f"Question: {case['query']}\n"
            f"Expected behavior: {case['behavior']}\n"
            f"Expected source ids: {expected_sources}\n"
            "Answer directly. If you use evidence, cite the exact source id."
        )

    def _memory_candidates(self, subject):
        terms = set(tokenize(subject))
        if not terms:
            return []
        candidates = []
        for entry in self.memory.recall_long():
            text = str(entry.get("entry", ""))
            if not text:
                continue
            score = len(terms & set(tokenize(text)))
            if score:
                candidates.append({
                    "score": score,
                    "source": f"memory:{entry.get('timestamp', 'unknown')}",
                    "content": text,
                    "confidence": "medium",
                })
        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:5]

    def _split_subject_and_source(self, text):
        match = re.match(r"(.+?)\s*:\s*(.+)", text, re.S)
        if not match:
            return "", ""
        return match.group(1).strip(), match.group(2).strip()

    def to_json(self, subject):
        payload = self.learning.get(slugify(subject))
        return json.dumps(payload, ensure_ascii=False, indent=2) if payload else None
