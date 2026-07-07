from commands.base import Command
from utils.web_fetcher import WebFetchError, fetch_url


class WebCommand(Command):
    help_text = "- web fetch <url> - fetch and summarize an explicit http/https URL"

    def __init__(self, fetcher=fetch_url, logger=None):
        super().__init__(logger)
        self.fetcher = fetcher

    def handle(self, message, normalized):
        if normalized.startswith("web fetch "):
            return self._fetch(message.strip()[len("web fetch "):])
        if normalized.startswith("fetch url "):
            return self._fetch(message.strip()[len("fetch url "):])
        return None

    def _fetch(self, url):
        try:
            result = self.fetcher(url)
        except WebFetchError as error:
            return str(error)
        except Exception as error:
            if self.logger:
                self.logger.error(f"Web fetch failed unexpectedly: {type(error).__name__}: {error}")
            return "Something went wrong fetching that URL."
        text = result.get("text", "")
        if len(text) > 1200:
            text = text[:1197].rstrip() + "..."
        truncated = " (truncated)" if result.get("truncated") else ""
        return (
            f"Fetched {result.get('url', url)}{truncated}\n"
            f"Content type: {result.get('content_type', 'unknown')}\n"
            f"Summary:\n{text or '[no readable text]'}"
        )
