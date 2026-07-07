import re


def build_model_prompt(message, memory, max_items=6):
    """Build a memory-aware prompt for the local language fallback."""
    context_items = _fact_items(memory) + _memory_items(message, memory, max_items=max_items)
    if not context_items:
        return message

    lines = [
        "You are ASTRA, a local-first personal assistant.",
        "Use the provided memory context only when it is relevant.",
        "If the context is insufficient, say what is missing instead of inventing facts.",
        "When using a memory item, cite its bracketed id.",
        "",
        "Memory context:",
    ]
    lines.extend(f"- [{item['id']}] {item['text']}" for item in context_items[:max_items])
    lines.extend(["", f"User message: {message}"])
    return "\n".join(lines)


def _fact_items(memory):
    items = []
    for key, value in sorted(memory.all_facts().items()):
        if key:
            items.append({"id": f"fact:{key}", "text": f"{key}: {value}"})
    return items


def _memory_items(message, memory, max_items=6):
    query_tokens = set(_tokens(message))
    candidates = []
    for index, entry in enumerate(memory.recall_long()):
        entry_type = entry.get("type")
        if entry_type not in {"learned", "note"}:
            continue
        text = " ".join(str(entry.get("entry", "")).split())
        if not text:
            continue
        score = len(query_tokens & set(_tokens(text)))
        if entry_type == "learned":
            score += 2
        if entry_type == "note":
            score += 1
        if score <= 0:
            continue
        timestamp = entry.get("timestamp", "unknown")
        candidates.append(
            {
                "score": score,
                "index": index,
                "id": f"{entry_type}:{timestamp}",
                "text": text,
            }
        )
    candidates.sort(key=lambda item: (item["score"], item["index"]), reverse=True)
    return [{"id": item["id"], "text": item["text"]} for item in candidates[:max_items]]


def _tokens(value):
    return re.findall(r"[a-z0-9]{3,}", str(value).lower())
