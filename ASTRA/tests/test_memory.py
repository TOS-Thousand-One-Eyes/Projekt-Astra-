from memory.facts import Facts
from memory.long_memory import LongMemory
from memory.short_memory import ShortMemory


def test_short_memory_remember_and_clear():
    memory = ShortMemory()
    memory.remember("hello")
    memory.remember("world")
    assert memory.recall() == ["hello", "world"]
    memory.clear()
    assert memory.recall() == []


def test_long_memory_persists_between_instances(tmp_path):
    path = tmp_path / "long_memory.json"
    memory = LongMemory(path)
    memory.remember("first entry")

    reloaded = LongMemory(path)
    entries = reloaded.recall()
    assert len(entries) == 1
    assert entries[0]["entry"] == "first entry"
    assert "timestamp" in entries[0]


def test_long_memory_starts_empty_without_file(tmp_path):
    memory = LongMemory(tmp_path / "missing.json")
    assert memory.recall() == []


def test_facts_learn_and_get_is_case_insensitive(tmp_path):
    facts = Facts(tmp_path / "facts.json")
    facts.learn("  Name ", " Erik ")
    assert facts.get("name") == "Erik"
    assert facts.get("NAME") == "Erik"
    assert facts.get("age") is None


def test_facts_persist_between_instances(tmp_path):
    path = tmp_path / "facts.json"
    Facts(path).learn("color", "blue")

    reloaded = Facts(path)
    assert reloaded.all() == {"color": "blue"}


def test_memory_manager_routes_to_both_memories(memory):
    memory.remember("a message")
    assert memory.recall() == ["a message"]
    assert memory.recall_long()[0]["entry"] == "a message"


def test_memory_manager_facts(memory):
    memory.learn("name", "Erik")
    assert memory.get_fact("name") == "Erik"
    assert memory.all_facts() == {"name": "Erik"}
