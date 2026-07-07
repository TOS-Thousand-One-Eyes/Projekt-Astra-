import pytest

from commands.web_command import WebCommand
from utils.web_fetcher import WebFetchError, fetch_url


class StubHeaders(dict):
    def get_content_charset(self):
        return "utf-8"


class StubResponse:
    def __init__(self, body, content_type="text/html; charset=utf-8"):
        self.body = body
        self.headers = StubHeaders({"Content-Type": content_type})

    def read(self, limit):
        return self.body[:limit]


def test_fetch_url_accepts_http_and_extracts_html_text():
    def opener(request, timeout):
        assert request.full_url == "https://example.com/page"
        assert timeout == 10
        return StubResponse(
            b"<html><head><script>secret()</script></head><body><h1>Title</h1><p>Hello web.</p></body></html>"
        )

    result = fetch_url("https://example.com/page", opener=opener)

    assert result["url"] == "https://example.com/page"
    assert result["content_type"].startswith("text/html")
    assert result["text"] == "Title Hello web."
    assert "secret" not in result["text"]


def test_fetch_url_rejects_non_http_urls():
    with pytest.raises(WebFetchError, match="http"):
        fetch_url("file:///etc/passwd", opener=lambda request, timeout: None)


def test_web_command_uses_injected_fetcher():
    def fetcher(url):
        return {
            "url": url,
            "content_type": "text/plain",
            "text": "Fetched content for tests.",
            "truncated": False,
        }

    command = WebCommand(fetcher=fetcher)

    response = command.handle("web fetch https://example.com", "web fetch https://example.com")

    assert "Fetched https://example.com" in response
    assert "Fetched content for tests." in response


def test_web_command_reports_fetch_errors():
    command = WebCommand(fetcher=lambda url: (_ for _ in ()).throw(WebFetchError("blocked")))

    response = command.handle("web fetch https://example.com", "web fetch https://example.com")

    assert response == "blocked"
