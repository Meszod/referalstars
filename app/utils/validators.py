from __future__ import annotations


def parse_positive_int(text: str | None, max_digits: int = 9) -> int | None:
    """Faqat butun musbat son. '12.5', '-3', '1e3', 'abc', '0' -> None."""
    if text is None:
        return None
    text = text.strip()
    if not text.isascii() or not text.isdigit() or len(text) > max_digits:
        return None
    value = int(text)
    return value if value > 0 else None


def parse_milestones(text: str) -> dict[int, int] | None:
    """'10:5, 20:10' -> {10: 5, 20: 10}. Xato bo'lsa None. '0' yoki 'off' -> {}."""
    text = text.strip().lower()
    if text in {"0", "off", "yo‘q", "yoq"}:
        return {}
    result: dict[int, int] = {}
    for part in text.replace(";", ",").split(","):
        if ":" not in part:
            return None
        k, v = (p.strip() for p in part.split(":", 1))
        key, val = parse_positive_int(k), parse_positive_int(v)
        if key is None or val is None:
            return None
        result[key] = val
    return result or None
