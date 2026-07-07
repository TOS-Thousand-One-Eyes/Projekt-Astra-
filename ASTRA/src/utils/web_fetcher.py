import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser


DEFAULT_TIMEOUT = 10
DEFAULT_MAX_BYTES = 200_000


class WebFetchError(Exception):
    pass


def fetch_url(url, opener=None, timeout=DEFAULT_TIMEOUT, max_bytes=DEFAULT_MAX_BYTES):
    parsed = urllib.parse.urlparse(str(url).strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise WebFetchError("Only full http:// or https:// URLs can be fetched.")

    request = urllib.request.Request(
        urllib.parse.urlunparse(parsed),
        headers={"User-Agent": "ASTRA local assistant"},
    )
    open_url = opener or urllib.request.urlopen
    try:
        response = open_url(request, timeout=timeout)
        raw = response.read(max_bytes + 1)
    except (OSError, urllib.error.URLError) as error:
        raise WebFetchError(f"Could not fetch URL: {error}") from error

    truncated = len(raw) > max_bytes
    raw = raw[:max_bytes]
    headers = getattr(response, "headers", None)
    content_type = get_header(headers, "Content-Type") or "unknown"
    charset = header_charset(headers) or "utf-8"
    text = raw.decode(charset, errors="replace")
    if "html" in content_type.lower() or looks_like_html(text):
        text = html_to_text(text)
    text = compact_text(text)
    return {
        "url": urllib.parse.urlunparse(parsed),
        "content_type": content_type,
        "text": text,
        "truncated": truncated,
    }


def get_header(headers, name):
    if not headers:
        return None
    if hasattr(headers, "get"):
        return headers.get(name)
    return None


def header_charset(headers):
    if headers and hasattr(headers, "get_content_charset"):
        return headers.get_content_charset()
    content_type = get_header(headers, "Content-Type") or ""
    match = re.search(r"charset=([^;\s]+)", content_type, re.I)
    return match.group(1) if match else None


def looks_like_html(text):
    return bool(re.search(r"<\s*(html|body|main|article|p|h1|title)\b", text, re.I))


def html_to_text(html):
    parser = TextExtractor()
    parser.feed(html)
    return parser.text()


def compact_text(text):
    return " ".join(str(text).split())


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []
        self._ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._ignored += 1
        if tag in {"p", "br", "li", "h1", "h2", "h3", "div", "section", "article"}:
            self._parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._ignored:
            self._ignored -= 1
        if tag in {"p", "li", "h1", "h2", "h3", "div", "section", "article"}:
            self._parts.append(" ")

    def handle_data(self, data):
        if not self._ignored:
            self._parts.append(data)

    def text(self):
        return compact_text(" ".join(self._parts))
