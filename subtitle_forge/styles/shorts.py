"""Large, timed captions for vertical short-form video."""
from __future__ import annotations

import re

from ..ass import Event, StyleConfig, escape_text

NAME = "shorts"
DESCRIPTION = "Large yellow captions in balanced groups of up to three words, with timed active-word scaling."
CONFIG = StyleConfig(
    font="DejaVu Sans",
    font_size=90,
    primary_color="&H0000E8FF",
    outline_color="&H00FFFFFF",
    outline=2.5,
    shadow=2,
    alignment=2,
    margin_v=470,
)
REQUIRES_WORDS = True

MAX_WORDS = 3
MAX_CHARS = 20
PAUSE_SPLIT_SECONDS = 0.45
ACTIVE_SCALE = 1.12
MAX_ANIMATION_MS = 70
_SENTENCE_END = re.compile(r"[.!?…][\"'”’\])}]*$")


def _split_groups(words):
    """Partition words on pauses/punctuation and into short, balanced cues."""
    batches = []
    current = []
    for word in words:
        if not word.text.strip():
            continue
        if current and (word.start - current[-1].end > PAUSE_SPLIT_SECONDS
                        or _SENTENCE_END.search(current[-1].text.strip())):
            batches.append(current)
            current = []
        current.append(word)
    if current:
        batches.append(current)

    for batch in batches:
        # Greedy short groups; if this leaves one word, move one word from
        # the previous group when that produces a more balanced 2+2 split.
        groups = []
        i = 0
        while i < len(batch):
            group = [batch[i]]
            chars = len(batch[i].text.strip())
            while i + len(group) < len(batch) and len(group) < MAX_WORDS:
                nxt = batch[i + len(group)]
                candidate = chars + 1 + len(nxt.text.strip())
                if candidate > MAX_CHARS and len(group) >= 2:
                    break
                if candidate > MAX_CHARS and len(group) == 1:
                    # Two long words are still a useful, wrapped cue.
                    group.append(nxt)
                    break
                group.append(nxt)
                chars = candidate
            groups.append(group)
            i += len(group)
        if len(groups) > 1 and len(groups[-1]) == 1 and len(groups[-2]) == 3:
            prior = groups[-2]
            moved = prior.pop()
            groups[-1].insert(0, moved)
        yield from groups


def _word_text(word, group_start, active, font_size):
    text = escape_text(word.text.strip())
    # Every token sets its own base size and bold state, so scaling one word
    # cannot change the size or weight of a neighbor.
    rendered = rf"{{\b1\fs{font_size}"
    if word is active:
        duration = max(0.0, word.end - word.start)
        rise = min(MAX_ANIMATION_MS, duration * 250.0)
        fall = rise
        offset = max(0, round((word.start - group_start) * 1000))
        span = max(1, round(duration * 1000))
        rise_end = min(span, round(rise))
        fall_start = max(rise_end, span - round(fall))
        target = round(font_size * ACTIVE_SCALE)
        rendered += (rf"\t({offset},{offset + rise_end},\fs{target})"
                     rf"\t({offset + fall_start},{offset + span},\fs{font_size})")
    # Put the transforms in the token's opening override block, then reset
    # immediately after its text so no animation can affect the next token.
    return rendered + "}" + text + r"{\r}"


def generate(transcript, config=CONFIG) -> list[Event]:
    result = []
    for segment in transcript.segments:
        if not segment.words:
            raise ValueError("This style requires word-level timestamps; transcript segment has no words")
        for group in _split_groups(segment.words):
            start = min(float(word.start) for word in group)
            end = max(float(word.end) for word in group)
            if end <= start:
                continue
            # Wrap at whitespace in the short-cue range; a pair of long words
            # may exceed the target and is left to ASS wrapping.
            lines = []
            line = []
            line_chars = 0
            for word in group:
                token = word.text.strip()
                added = len(token) + (1 if line else 0)
                if line and line_chars + added > MAX_CHARS:
                    lines.append(line)
                    line, line_chars = [], 0
                    added = len(token)
                line.append(word)
                line_chars += added
            if line:
                lines.append(line)

            rows = []
            for line_words in lines:
                parts = []
                for word in line_words:
                    parts.append(_word_text(word, start, word, config.font_size))
                rows.append(" ".join(parts))
            text = r"\N".join(rows)
            result.append(Event(start, end, text))
    return result
