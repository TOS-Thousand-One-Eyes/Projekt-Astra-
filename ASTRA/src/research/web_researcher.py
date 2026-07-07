import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from utils.web_fetcher import WebFetchError, compact_text, fetch_url


DEFAULT_MAX_RESULTS = 3
MAX_RESULTS_LIMIT = 5
SEARCH_URL = "https://duckduckgo.com/html/"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "ASTRA local assistant research"


class ResearchError(Exception):
    pass


class WebResearcher:
    """Bounded web research workflow with injectable search and fetch steps."""

    def __init__(self, searcher=None, fetcher=fetch_url, max_results=DEFAULT_MAX_RESULTS):
        self.searcher = searcher or search_web
        self.fetcher = fetcher
        self.max_results = clamp_results(max_results)

    def research(self, topic, max_results=None):
        topic = compact_text(topic)
        if not topic:
            raise ResearchError("Research topic cannot be empty.")
        limit = clamp_results(max_results or self.max_results)
        try:
            candidates = self.searcher(topic, max_results=limit)
        except ResearchError:
            raise
        except Exception as error:
            raise ResearchError(f"Search failed: {error}") from error

        sources = []
        seen = set()
        for candidate in candidates:
            url = normalize_url(candidate.get("url", ""))
            if not url or url in seen:
                continue
            seen.add(url)
            try:
                fetched = self.fetcher(url)
            except (WebFetchError, ResearchError) as error:
                sources.append(failed_source(candidate, url, str(error)))
                continue
            except Exception as error:
                sources.append(failed_source(candidate, url, f"fetch failed: {error}"))
                continue

            text = compact_text(fetched.get("text", ""))
            if not text:
                sources.append(failed_source(candidate, url, "no readable text"))
                continue
            sources.append({
                "url": fetched.get("url", url),
                "title": compact_text(candidate.get("title", "")) or fetched.get("url", url),
                "snippet": compact_text(candidate.get("snippet", "")),
                "text": trim_text(text, 4000),
                "content_type": fetched.get("content_type", "unknown"),
                "truncated": bool(fetched.get("truncated")) or len(text) > 4000,
                "status": "fetched",
            })
            if len([item for item in sources if item["status"] == "fetched"]) >= limit:
                break

        return {
            "topic": topic,
            "query": topic,
            "max_results": limit,
            "candidates": len(candidates),
            "sources": sources,
            "fetched": len([item for item in sources if item["status"] == "fetched"]),
        }


def search_web(query, max_results=DEFAULT_MAX_RESULTS, opener=None):
    query = compact_text(query)
    if not query:
        raise ResearchError("Search query cannot be empty.")
    limit = clamp_results(max_results)
    url = SEARCH_URL + "?" + urllib.parse.urlencode({"q": query})
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    open_url = opener or urllib.request.urlopen
    try:
        with open_url(request, timeout=10) as response:
            raw = response.read(200_000)
    except Exception as error:
        raise ResearchError(f"Could not search the web: {error}") from error

    html = raw.decode("utf-8", errors="replace")
    results = SearchResultParser().parse(html)
    deduped = []
    seen = set()
    for result in results:
        normalized = normalize_url(result.get("url", ""))
        if not normalized or normalized in seen:
            continue
        result["url"] = normalized
        seen.add(normalized)
        deduped.append(result)
        if len(deduped) >= limit:
            break
    return deduped or search_wikipedia(query, max_results=limit, opener=opener)


def search_wikipedia(query, max_results=DEFAULT_MAX_RESULTS, opener=None):
    limit = clamp_results(max_results)
    params = {
        "action": "opensearch",
        "namespace": "0",
        "search": compact_text(query),
        "limit": str(limit),
        "format": "json",
    }
    url = WIKIPEDIA_SEARCH_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    open_url = opener or urllib.request.urlopen
    try:
        response = open_url(request, timeout=10)
        raw = response.read(100_000)
    except Exception as error:
        raise ResearchError(f"Could not search Wikipedia fallback: {error}") from error
    try:
        loaded = json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as error:
        raise ResearchError(f"Wikipedia fallback returned invalid JSON: {error}") from error
    if not isinstance(loaded, list) or len(loaded) < 4:
        return search_wikipedia_fulltext(query, max_results=limit, opener=opener)
    titles = loaded[1] if isinstance(loaded[1], list) else []
    snippets = loaded[2] if isinstance(loaded[2], list) else []
    urls = loaded[3] if isinstance(loaded[3], list) else []
    results = []
    for title, snippet, url in zip(titles, snippets, urls):
        normalized = normalize_url(url)
        if normalized:
            results.append({
                "url": normalized,
                "title": compact_text(title),
                "snippet": compact_text(snippet),
            })
        if len(results) >= limit:
            break
    return results or search_wikipedia_fulltext(query, max_results=limit, opener=opener)


def search_wikipedia_fulltext(query, max_results=DEFAULT_MAX_RESULTS, opener=None):
    limit = clamp_results(max_results)
    open_url = opener or urllib.request.urlopen
    results = {}
    for search_query in query_variants(query):
        params = {
            "action": "query",
            "list": "search",
            "srsearch": search_query,
            "srlimit": str(MAX_RESULTS_LIMIT),
            "format": "json",
        }
        url = WIKIPEDIA_SEARCH_URL + "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            response = open_url(request, timeout=10)
            raw = response.read(100_000)
        except Exception as error:
            raise ResearchError(f"Could not search Wikipedia full-text fallback: {error}") from error
        try:
            loaded = json.loads(raw.decode("utf-8", errors="replace"))
        except json.JSONDecodeError as error:
            raise ResearchError(f"Wikipedia full-text fallback returned invalid JSON: {error}") from error
        items = ((loaded.get("query") or {}).get("search") or []) if isinstance(loaded, dict) else []
        for item in items:
            title = compact_text(item.get("title", ""))
            if not title:
                continue
            url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"))
            current = {
                "url": url,
                "title": title,
                "snippet": strip_html(item.get("snippet", "")),
            }
            score = relevance_score(query, current)
            if url not in results or score > results[url]["score"]:
                current["score"] = score
                results[url] = current
    ranked = sorted(results.values(), key=lambda item: (-item.pop("score"), item["title"]))
    return ranked[:limit]


class SearchResultParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.results = []
        self._current = None
        self._field = None
        self._parts = []

    def parse(self, html):
        self.feed(html)
        return self.results

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(str(attrs.get("class", "")).split())
        if tag == "a" and "result__a" in classes:
            self._current = {"url": decode_duckduckgo_url(attrs.get("href", "")), "title": "", "snippet": ""}
            self._field = "title"
            self._parts = []
        elif self._current and "result__snippet" in classes:
            self._field = "snippet"
            self._parts = []

    def handle_endtag(self, tag):
        if not self._current:
            return
        if tag == "a" and self._field == "title":
            self._current["title"] = compact_text(" ".join(self._parts))
            self._field = None
            self._parts = []
        elif tag in {"a", "div"} and self._field == "snippet":
            self._current["snippet"] = compact_text(" ".join(self._parts))
            self._field = None
            self._parts = []
            if self._current.get("url"):
                self.results.append(self._current)
            self._current = None

    def handle_data(self, data):
        if self._current and self._field:
            self._parts.append(data)


def decode_duckduckgo_url(value):
    if not value:
        return ""
    parsed = urllib.parse.urlparse(value)
    params = urllib.parse.parse_qs(parsed.query)
    if "uddg" in params and params["uddg"]:
        return params["uddg"][0]
    return value


def normalize_url(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("//"):
        text = "https:" + text
    parsed = urllib.parse.urlparse(text)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return urllib.parse.urlunparse(parsed._replace(fragment=""))


def failed_source(candidate, url, error):
    return {
        "url": url,
        "title": compact_text(candidate.get("title", "")) or url,
        "snippet": compact_text(candidate.get("snippet", "")),
        "text": "",
        "content_type": "unknown",
        "truncated": False,
        "status": "failed",
        "error": error,
    }


def trim_text(text, limit):
    cleaned = compact_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def strip_html(value):
    return compact_text(re.sub(r"<[^>]+>", "", str(value)))


def query_variants(query):
    cleaned = compact_text(query)
    tokens = [token for token in re.findall(r"[A-Za-z0-9]+", cleaned) if len(token) > 2]
    variants = []
    if len(tokens) >= 2:
        variants.append(f"\"{tokens[0]} {tokens[1]}\" " + " ".join(tokens[2:]))
    variants.append(cleaned)
    return [variant.strip() for variant in variants if variant.strip()]


def relevance_score(query, result):
    terms = {stem(token) for token in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(token) > 2}
    text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
    result_terms = {stem(token) for token in re.findall(r"[A-Za-z0-9]+", text) if len(token) > 2}
    score = len(terms & result_terms)
    query_tokens = [token for token in re.findall(r"[A-Za-z0-9]+", query.lower()) if len(token) > 2]
    if len(query_tokens) >= 2 and " ".join(query_tokens[:2]) in text:
        score += 3
    return score


def stem(token):
    token = token.lower()
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            return token[: -len(suffix)]
    return token


def clamp_results(value):
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = DEFAULT_MAX_RESULTS
    return max(1, min(count, MAX_RESULTS_LIMIT))
