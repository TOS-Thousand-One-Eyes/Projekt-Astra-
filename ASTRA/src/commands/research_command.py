import re

from commands.base import Command
from learning.learning_manager import LearningManager
from research.web_researcher import ResearchError, WebResearcher


class ResearchCommand(Command):
    help_text = (
        "- research <topic> - search the web and summarize bounded source candidates\n"
        "- research learn <topic> - research a topic and add fetched web sources to a proficient learning subject"
    )

    def __init__(self, learning=None, researcher=None, logger=None):
        super().__init__(logger)
        self.learning = learning or LearningManager()
        self.researcher = researcher or WebResearcher()

    def handle(self, message, normalized):
        if normalized.startswith("research learn proficient "):
            return self._research_learn(message.strip()[len("research learn proficient "):], target_level="proficient")
        if normalized.startswith("research learn "):
            return self._research_learn(message.strip()[len("research learn "):], target_level="proficient")
        if normalized.startswith("web research "):
            return self._research(message.strip()[len("web research "):])
        if normalized.startswith("research "):
            return self._research(message.strip()[len("research "):])
        return None

    def _research(self, topic):
        topic, max_results = parse_limit(topic)
        if not topic:
            return "Use: research <topic>"
        try:
            report = self.researcher.research(topic, max_results=max_results)
        except ResearchError as error:
            return f"Research failed: {error}"
        except Exception as error:
            if self.logger:
                self.logger.error(f"Research failed unexpectedly: {type(error).__name__}: {error}")
            return "Something went wrong researching that topic."
        return format_research_report(report)

    def _research_learn(self, topic, target_level="proficient"):
        topic, max_results = parse_limit(topic)
        if not topic:
            return "Use: research learn <topic>"
        try:
            report = self.researcher.research(topic, max_results=max_results)
        except ResearchError as error:
            return f"Research failed: {error}"
        except Exception as error:
            if self.logger:
                self.logger.error(f"Research learning failed unexpectedly: {type(error).__name__}: {error}")
            return "Something went wrong researching that learning subject."

        source_candidates = [
            {
                "source": f"web:{source['url']}",
                "content": compose_learning_source(source),
                "confidence": "medium",
            }
            for source in fetched_sources(report)
        ]
        if not source_candidates:
            return format_research_report(report) + "\nNo fetched sources were usable for learning."

        payload = self.learning.learn(
            topic,
            target_use="answer future ASTRA questions with cited web evidence",
            target_level=target_level,
            source_candidates=source_candidates,
        )
        return (
            f"Research learning subject created: {payload['subject']} ({payload['slug']}).\n"
            f"Fetched sources added: {len(source_candidates)}.\n"
            f"Total sources: {len(payload.get('sources', []))}; eval cases: {len(payload.get('eval_cases', []))}.\n"
            "Next: run `learning run-eval <topic>`, then review with `learning approve <topic>` before promotion."
        )


def parse_limit(topic):
    text = " ".join(str(topic).split())
    match = re.search(r"\s+with\s+(\d+)\s+sources?$", text, re.I)
    if not match:
        return text, None
    return text[: match.start()].strip(), int(match.group(1))


def fetched_sources(report):
    return [source for source in report.get("sources", []) if source.get("status") == "fetched"]


def compose_learning_source(source):
    parts = [
        f"Title: {source.get('title', '')}",
        f"URL: {source.get('url', '')}",
    ]
    if source.get("snippet"):
        parts.append(f"Search snippet: {source['snippet']}")
    parts.append(f"Content: {source.get('text', '')}")
    return "\n".join(parts)


def format_research_report(report):
    lines = [
        f"Research results for {report['topic']}:",
        f"- candidates: {report.get('candidates', 0)}",
        f"- fetched: {report.get('fetched', 0)}/{report.get('max_results', 0)}",
    ]
    for source in report.get("sources", []):
        status = source.get("status", "unknown")
        title = source.get("title") or source.get("url", "unknown")
        lines.append(f"- [{status}] {title} - {source.get('url', '')}")
        if source.get("snippet"):
            lines.append(f"  snippet: {shorten(source['snippet'], 180)}")
        if status == "fetched" and source.get("text"):
            lines.append(f"  text: {shorten(source['text'], 240)}")
        if source.get("error"):
            lines.append(f"  error: {source['error']}")
    return "\n".join(lines)


def shorten(text, limit):
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."
