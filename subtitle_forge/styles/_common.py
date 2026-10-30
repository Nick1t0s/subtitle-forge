"""Shared helpers for built-in subtitle styles."""
from __future__ import annotations

import re

from ..ass import Event, StyleConfig, escape_text


def chunks(words, max_words: int = 7, max_chars: int = 42):
    """Yield contiguous word groups, keeping their measured time bounds."""
    result = []
    size = 0
    for word in words:
        text = word.text.strip()
        if not text:
            continue
        added = len(text) + (1 if result else 0)
        if result and (len(result) >= max_words or size + added > max_chars):
            yield result
            result, size = [], 0
            added = len(text)
        result.append(word)
        size += added
    if result:
        yield result


def wrap_phrase(text: str, max_words: int = 7, max_chars: int = 42) -> str:
    """Wrap a complete phrase with ASS line breaks, without changing its timing."""
    tokens = re.findall(r"\S+", text)
    lines = []
    current = []
    size = 0
    for token in tokens:
        added = len(token) + (1 if current else 0)
        if current and (len(current) >= max_words or size + added > max_chars):
            lines.append(" ".join(current))
            current, size = [], 0
            added = len(token)
        current.append(token)
        size += added
    if current:
        lines.append(" ".join(current))
    return r"\N".join(escape_text(line) for line in lines)


def phrase(items) -> str:
    return " ".join(item.text.strip() if hasattr(item, "text") else item for item in items)


def event(start, end, text):
    if end <= start:
        return None
    return Event(float(start), float(end), text)


def classic_groups(segment):
    """Yield the complete cue phrase for its original measured interval."""
    text = wrap_phrase(segment.text.strip())
    if text:
        yield segment.start, segment.end, text


def word_groups(transcript):
    for segment in transcript.segments:
        if not segment.words:
            raise ValueError("This style requires word-level timestamps; transcript segment has no words")
        yield segment, list(chunks(segment.words))


def color(color_value: str) -> str:
    # StyleConfig stores &HAABBGGRR; ASS override tags need their closing '&'.
    return "{\\1c" + color_value + "&}"
