from commands.registry import build_default_registry
from commands.research_command import ResearchCommand
from learning.learning_manager import LearningManager
from memory.memory_manager import MemoryManager
from research.web_researcher import ResearchError, WebResearcher, search_wikipedia, search_wikipedia_fulltext


def test_web_researcher_fetches_bounded_sources_and_records_failures():
    def searcher(query, max_results):
        assert query == "line balancing"
        assert max_results == 2
        return [
            {"url": "https://example.com/a", "title": "A", "snippet": "First"},
            {"url": "https://example.com/b", "title": "B", "snippet": "Second"},
            {"url": "https://example.com/c", "title": "C", "snippet": "Third"},
        ]

    def fetcher(url):
        if url.endswith("/b"):
            raise ResearchError("blocked")
        return {
            "url": url,
            "content_type": "text/html",
            "text": f"Readable source text from {url}.",
            "truncated": False,
        }

    report = WebResearcher(searcher=searcher, fetcher=fetcher).research("line balancing", max_results=2)

    assert report["fetched"] == 2
    assert [source["status"] for source in report["sources"]] == ["fetched", "failed", "fetched"]
    assert report["sources"][1]["error"] == "blocked"


def test_search_wikipedia_parses_opensearch_response():
    class StubResponse:
        def read(self, limit):
            return (
                b'["line balancing",["Line balancing"],'
                b'["Balancing production work across stations."],'
                b'["https://en.wikipedia.org/wiki/Assembly_line"]]'
            )

    def opener(request, timeout):
        assert "w/api.php" in request.full_url
        assert timeout == 10
        return StubResponse()

    results = search_wikipedia("line balancing", max_results=1, opener=opener)

    assert results == [
        {
            "url": "https://en.wikipedia.org/wiki/Assembly_line",
            "title": "Line balancing",
            "snippet": "Balancing production work across stations.",
        }
    ]


def test_search_wikipedia_fulltext_parses_query_search_response():
    class StubResponse:
        def read(self, limit):
            return (
                b'{"query":{"search":[{"title":"Assembly line",'
                b'"snippet":"A <span class=\\"searchmatch\\">manufacturing</span> process."}]}}'
            )

    def opener(request, timeout):
        assert "list=search" in request.full_url
        assert timeout == 10
        return StubResponse()

    results = search_wikipedia_fulltext("line balancing manufacturing", max_results=1, opener=opener)

    assert results == [
        {
            "url": "https://en.wikipedia.org/wiki/Assembly_line",
            "title": "Assembly line",
            "snippet": "A manufacturing process.",
        }
    ]


def test_research_command_summarizes_stubbed_sources():
    class StubResearcher:
        def research(self, topic, max_results=None):
            assert topic == "maintenance"
            assert max_results is None
            return {
                "topic": topic,
                "candidates": 1,
                "max_results": 3,
                "fetched": 1,
                "sources": [
                    {
                        "status": "fetched",
                        "title": "Maintenance guide",
                        "url": "https://example.com/maintenance",
                        "snippet": "Practical maintenance source.",
                        "text": "Use evidence, record uncertainty, and cite sources.",
                    }
                ],
            }

    response = ResearchCommand(researcher=StubResearcher()).handle("research maintenance", "research maintenance")

    assert "Research results for maintenance:" in response
    assert "- fetched: 1/3" in response
    assert "Maintenance guide" in response
    assert "Use evidence" in response


def test_research_learn_creates_proficient_subject_from_fetched_sources(tmp_path):
    learning = LearningManager(data_dir=tmp_path)

    class StubResearcher:
        def research(self, topic, max_results=None):
            return {
                "topic": topic,
                "candidates": 1,
                "max_results": 3,
                "fetched": 1,
                "sources": [
                    {
                        "status": "fetched",
                        "title": "Line balancing source",
                        "url": "https://example.com/line-balancing",
                        "snippet": "Takt and station balancing.",
                        "text": "Line balancing uses takt time, work content, and station constraints.",
                    }
                ],
            }

    command = ResearchCommand(learning=learning, researcher=StubResearcher())

    response = command.handle("research learn line balancing", "research learn line balancing")
    payload = learning.get("line balancing")

    assert "Research learning subject created: line balancing" in response
    assert payload["target_level"] == "proficient"
    assert len(payload["sources"]) == 1
    assert payload["sources"][0]["source"] == "web:https://example.com/line-balancing"
    assert len(payload["eval_cases"]) == 13


def test_default_registry_dispatches_research_and_shares_learning(tmp_path, config):
    memory = MemoryManager(data_dir=tmp_path / "memory")
    learning = LearningManager(data_dir=tmp_path / "runtime")

    class StubResearcher:
        def research(self, topic, max_results=None):
            return {
                "topic": topic,
                "candidates": 1,
                "max_results": 3,
                "fetched": 1,
                "sources": [
                    {
                        "status": "fetched",
                        "title": "Hydraulics",
                        "url": "https://example.com/hydraulics",
                        "snippet": "Hydraulic maintenance.",
                        "text": "Hydraulic systems need pressure checks and safe lockout.",
                    }
                ],
            }

    registry = build_default_registry(config, memory, learning=learning, researcher=StubResearcher())

    result = registry.dispatch("research learn hydraulics")
    status = registry.dispatch("learning status hydraulics").response

    assert result.command_name == "ResearchCommand"
    assert "Research learning subject created: hydraulics" in result.response
    assert "- sources: 1" in status
    assert "- eval cases: 13" in status
