from memory.facts import Facts
from memory.long_memory import LongMemory
from memory.memory_manager import MemoryManager
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


def test_long_memory_corrupt_file_sets_a_load_warning(tmp_path):
    path = tmp_path / "long_memory.json"
    path.write_text("{not valid json", encoding="utf-8")
    memory = LongMemory(path)
    assert memory.load_warning is not None
    assert "long_memory.json" in memory.load_warning


def test_long_memory_missing_file_sets_no_load_warning(tmp_path):
    memory = LongMemory(tmp_path / "missing.json")
    assert memory.load_warning is None


def test_long_memory_falls_back_to_empty_on_wrong_shape_json(tmp_path):
    path = tmp_path / "long_memory.json"
    path.write_text('{"oops": 1}', encoding="utf-8")
    memory = LongMemory(path)
    assert memory.recall() == []


def test_long_memory_wrong_shape_json_sets_a_load_warning(tmp_path):
    path = tmp_path / "long_memory.json"
    path.write_text('{"oops": 1}', encoding="utf-8")
    memory = LongMemory(path)
    assert memory.load_warning is not None
    assert "long_memory.json" in memory.load_warning


def test_long_memory_falls_back_to_empty_on_wrong_element_shape_json(tmp_path):
    path = tmp_path / "long_memory.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    memory = LongMemory(path)
    assert memory.recall() == []
    assert memory.load_warning is not None
    assert "long_memory.json" in memory.load_warning


def test_long_memory_save_uses_temp_file_then_replaces_target(tmp_path):
    path = tmp_path / "long_memory.json"
    memory = LongMemory(path)
    memory.remember("first entry")
    # No temp file of any name may remain after a save (the temp name is
    # PID-suffixed now, so match by pattern, not the old fixed name).
    assert list(tmp_path.glob("*.tmp")) == []
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


def test_long_memory_search_does_not_crash_on_entry_missing_entry_key(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.entries.append({"timestamp": "2020-01-01T00:00:00", "type": "note"})
    assert memory.search("anything") == []


def test_long_memory_forget_does_not_crash_on_entry_missing_entry_key(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.entries.append({"timestamp": "2020-01-01T00:00:00", "type": "note"})
    assert memory.forget("anything") == 0


def test_long_memory_search_does_not_crash_on_non_string_entry_value(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.entries.append({"timestamp": "2020-01-01T00:00:00", "entry": 42, "type": "note"})
    assert memory.search("42") == [memory.entries[0]]


def test_long_memory_forget_does_not_crash_on_non_string_entry_value(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.entries.append({"timestamp": "2020-01-01T00:00:00", "entry": 42, "type": "note"})
    assert memory.forget("42") == 1


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


def test_long_memory_forget_with_type_only_removes_matching_type(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("test", entry_type="chat")
    memory.remember("test", entry_type="note")
    removed = memory.forget("test", entry_type="note")
    assert removed == 1
    remaining = memory.recall()
    assert len(remaining) == 1
    assert remaining[0]["type"] == "chat"


def test_long_memory_forget_without_type_removes_all_matching_text(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("test", entry_type="chat")
    memory.remember("test", entry_type="note")
    removed = memory.forget("test")
    assert removed == 2
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


def test_facts_corrupt_file_sets_a_load_warning(tmp_path):
    path = tmp_path / "facts.json"
    path.write_text("{not valid json", encoding="utf-8")
    facts = Facts(path)
    assert facts.load_warning is not None
    assert "facts.json" in facts.load_warning


def test_facts_falls_back_to_empty_on_wrong_shape_json(tmp_path):
    path = tmp_path / "facts.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    facts = Facts(path)
    assert facts.all() == {}


def test_facts_wrong_shape_json_sets_a_load_warning(tmp_path):
    path = tmp_path / "facts.json"
    path.write_text("[1, 2, 3]", encoding="utf-8")
    facts = Facts(path)
    assert facts.load_warning is not None
    assert "facts.json" in facts.load_warning


def test_memory_manager_routes_to_both_memories(memory):
    memory.remember("a message")
    assert memory.recall() == ["a message"]
    assert memory.recall_long()[0]["entry"] == "a message"


def test_memory_manager_load_warnings_empty_when_clean(memory):
    assert memory.load_warnings() == []


def test_memory_manager_aggregates_load_warnings_from_both_stores(tmp_path):
    (tmp_path / "long_memory.json").write_text("{not valid json", encoding="utf-8")
    (tmp_path / "facts.json").write_text("{not valid json", encoding="utf-8")
    manager = MemoryManager(data_dir=tmp_path)
    assert len(manager.load_warnings()) == 2


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
    memory.remember("buy milk", entry_type="note")
    assert memory.forget("buy milk") == 1
    assert memory.recall_long() == []


def test_memory_manager_forget_also_clears_short_memory(memory):
    memory.remember("buy milk", entry_type="note")
    memory.forget("buy milk")
    assert memory.recall() == []


def test_memory_manager_forget_does_not_remove_a_chat_entry_with_the_same_text(memory):
    memory.remember("buy milk", entry_type="chat")
    memory.remember("buy milk", entry_type="note")
    removed = memory.forget("buy milk")
    assert removed == 1
    remaining_types = [item["type"] for item in memory.recall_long()]
    assert remaining_types == ["chat"]


def test_memory_manager_forget_with_no_matching_note_leaves_short_memory_untouched(memory):
    memory.remember("test", entry_type="chat")
    removed = memory.forget("test")
    assert removed == 0
    assert memory.recall() == ["test"]


def test_long_memory_save_uses_a_process_unique_tmp_path(tmp_path, monkeypatch):
    import os

    captured = {}
    real_replace = os.replace

    def capturing_replace(src, dst):
        captured["src"] = str(src)
        real_replace(src, dst)

    monkeypatch.setattr("memory.long_memory.os.replace", capturing_replace)
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("entry")

    assert str(os.getpid()) in captured["src"]


def test_facts_save_uses_a_process_unique_tmp_path(tmp_path, monkeypatch):
    import os

    captured = {}
    real_replace = os.replace

    def capturing_replace(src, dst):
        captured["src"] = str(src)
        real_replace(src, dst)

    monkeypatch.setattr("memory.facts.os.replace", capturing_replace)
    facts = Facts(tmp_path / "facts.json")
    facts.learn("name", "Erik")

    assert str(os.getpid()) in captured["src"]


def test_save_leaves_no_tmp_files_behind(tmp_path):
    memory = LongMemory(tmp_path / "long_memory.json")
    memory.remember("entry")
    facts = Facts(tmp_path / "facts.json")
    facts.learn("name", "Erik")

    leftovers = [item.name for item in tmp_path.iterdir() if ".tmp" in item.name]
    assert leftovers == []


def test_facts_load_normalizes_hand_edited_keys(tmp_path):
    import json

    path = tmp_path / "facts.json"
    path.write_text(json.dumps({"Name": "Erik"}), encoding="utf-8")
    facts = Facts(path)

    assert facts.get("name") == "Erik"
    assert facts.load_warning is not None
    assert "Name" in facts.load_warning


def test_facts_load_with_already_normalized_keys_sets_no_warning(tmp_path):
    import json

    path = tmp_path / "facts.json"
    path.write_text(json.dumps({"name": "Erik"}), encoding="utf-8")
    facts = Facts(path)

    assert facts.get("name") == "Erik"
    assert facts.load_warning is None


def test_facts_load_tolerates_a_utf8_bom(tmp_path):
    import json

    path = tmp_path / "facts.json"
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps({"name": "Erik"}).encode("utf-8"))
    facts = Facts(path)

    assert facts.get("name") == "Erik"
    assert facts.load_warning is None


def test_long_memory_load_tolerates_a_utf8_bom(tmp_path):
    import json

    path = tmp_path / "long_memory.json"
    entries = [{"timestamp": "2026-01-01T00:00:00", "entry": "hi", "type": "chat"}]
    path.write_bytes(b"\xef\xbb\xbf" + json.dumps(entries).encode("utf-8"))
    memory = LongMemory(path)

    assert len(memory.recall()) == 1
    assert memory.load_warning is None
