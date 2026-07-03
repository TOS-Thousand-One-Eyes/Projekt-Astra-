from memory.facts import Facts
from memory.long_memory import LongMemory
from memory.short_memory import ShortMemory


def test_short_memory_remember_and_recall():
    memory = ShortMemory()
    memory.remember("hello")
    memory.remember("world")
    assert memory.recall() == ["hello", "world"]


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


def test_long_memory_falls_back_to_empty_on_corrupt_file(tmp_path):
    path = tmp_path / "long_memory.json"
    path.write_text("{not valid json", encoding="utf-8")
    memory = LongMemory(path)
    assert memory.recall() == []


def test_long_memory_save_uses_temp_file_then_replaces_target(tmp_path):
    path = tmp_path / "long_memory.json"
    memory = LongMemory(path)
    memory.remember("first entry")
    assert not (tmp_path / "long_memory.json.tmp").exists()
    assert path.exists()


def test_long_memory_entry_type_defaults_to_chat(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("hi")
    assert memory.recall()[0]["type"] == "chat"


def test_long_memory_entry_type_can_be_set_to_note(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("buy milk", entry_type="note")
    assert memory.recall()[0]["type"] == "note"


def test_long_memory_search_is_case_insensitive_substring(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("buy milk")
    memory.remember("walk the dog")
    results = memory.search("MILK")
    assert len(results) == 1
    assert results[0]["entry"] == "buy milk"


def test_long_memory_search_returns_empty_list_when_no_match(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("buy milk")
    assert memory.search("bicycle") == []


def test_long_memory_forget_removes_matching_entry_and_returns_count(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("buy milk")
    memory.remember("buy milk")
    memory.remember("walk the dog")
    removed = memory.forget("buy milk")
    assert removed == 2
    remaining = [item["entry"] for item in memory.recall()]
    assert remaining == ["walk the dog"]

    reloaded = LongMemory(tmp_path / "long_memory.json")
    assert [item["entry"] for item in reloaded.recall()] == ["walk the dog"]


def test_long_memory_forget_returns_zero_when_no_match(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("buy milk")
    assert memory.forget("bicycle") == 0
    assert len(memory.recall()) == 1


def test_long_memory_forget_is_case_insensitive(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("Buy Milk")
    assert memory.forget("buy milk") == 1
    assert memory.recall() == []


def test_short_memory_forget_removes_matching_entry_case_insensitively():
    memory = ShortMemory()
    memory.remember("Buy Milk")
    memory.remember("walk the dog")
    removed = memory.forget("buy milk")
    assert removed == 1
    assert memory.recall() == ["walk the dog"]


def test_short_memory_forget_returns_zero_when_no_match():
    memory = ShortMemory()
    memory.remember("buy milk")
    assert memory.forget("bicycle") == 0
    assert memory.recall() == ["buy milk"]


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


def test_facts_falls_back_to_empty_on_corrupt_file(tmp_path):
    path = tmp_path / "facts.json"
    path.write_text("{not valid json", encoding="utf-8")
    facts = Facts(path)
    assert facts.all() == {}


def test_memory_manager_routes_to_both_memories(memory):
    memory.remember("a message")
    assert memory.recall() == ["a message"]
    assert memory.recall_long()[0]["entry"] == "a message"


def test_memory_manager_facts(memory):
    memory.learn("name", "Erik")
    assert memory.get_fact("name") == "Erik"
    assert memory.all_facts() == {"name": "Erik"}


def test_memory_manager_search_long_delegates(memory):
    memory.remember("buy milk")
    memory.remember("walk the dog")
    results = memory.search_long("milk")
    assert len(results) == 1
    assert results[0]["entry"] == "buy milk"


def test_memory_manager_forget_delegates(memory):
    memory.remember("buy milk")
    assert memory.forget("buy milk") == 1
    assert memory.recall_long() == []


def test_memory_manager_forget_also_clears_short_memory(memory):
    memory.remember("buy milk")
    memory.forget("buy milk")
    assert memory.recall() == []
