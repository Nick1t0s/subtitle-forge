"""Large, timed captions for vertical short-form video."""
from __future__ import annotations

import re

from ..ass import Event, StyleConfig, escape_text
from ..font_metrics import measure_text

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
ACTIVE_SCALE = 1.35
WORD_GAP = 22
SIDE_MARGIN = 65
_SENTENCE_END = re.compile(r"[.!?…][\"'”’\])}]*$")


def _split_groups(words):
    """Partition words on pauses/punctuation and into short, balanced cues."""
    batches = []
    current = []
    for word in words:
        if not word.text.strip():
            continue
        if len(word.text.split()) > MAX_WORDS:
            raise ValueError("A word timestamp contains more than three words; provide word-level timestamps")
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
            while i + len(group) < len(batch):
                nxt = batch[i + len(group)]
                if sum(len(item.text.split()) for item in group) + len(nxt.text.split()) > MAX_WORDS:
                    break
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
        if (len(groups) > 1 and len(groups[-1]) == 1 and len(groups[-2]) == 3
                and all(len(word.text.split()) == 1 for word in groups[-2] + groups[-1])):
            prior = groups[-2]
            moved = prior.pop()
            groups[-1].insert(0, moved)
        yield from groups


def _layout(group, config):
    """Reserve maximum-size word slots once; emphasis never moves neighbors."""
    labels = [escape_text(word.text.strip()) for word in group]
    font_size = config.font_size
    advances = [measure_text(label, config.font, font_size) for label in labels]
    gap = WORD_GAP * config.font_size / CONFIG.font_size
    available = max(1, config.canvas_width - 2 * SIDE_MARGIN)
    full_width = sum(advance * ACTIVE_SCALE for advance in advances) + gap * (len(group) - 1)
    ratio = min(1.0, available / max(1, full_width))
    font_size = max(1, int(font_size * ratio))
    slots = [advance * font_size / config.font_size * ACTIVE_SCALE for advance in advances]
    gap *= ratio
    cursor = (config.canvas_width - sum(slots) - gap * (len(group) - 1)) / 2
    centers = []
    for slot in slots:
        centers.append(cursor + slot / 2)
        cursor += slot + gap
    # The caption center corresponds to its configured baseline safe zone.
    y = max(font_size * ACTIVE_SCALE / 2, config.canvas_height - config.margin_v - font_size / 2)
    y = min(y, config.canvas_height - font_size * ACTIVE_SCALE / 2)
    return labels, font_size, centers, y


def generate(transcript, config=CONFIG) -> list[Event]:
    groups = []
    for segment in transcript.segments:
        if not segment.words:
            raise ValueError("This style requires word-level timestamps; transcript segment has no words")
        for group in _split_groups(segment.words):
            groups.append((group, max(segment.end, group[-1].end)))
    result = []
    for group_index, (group, segment_end) in enumerate(groups):
        # Keep the previous caption and its active word through silence until
        # the next group starts. Before first speech and after the final cue,
        # nothing is displayed.
        display_end = groups[group_index + 1][0][0].start if group_index + 1 < len(groups) else segment_end
        if display_end < group[-1].end:
            raise ValueError("Shorts captions require globally ordered, non-overlapping word timestamps")
        labels, size, centers, y = _layout(group, config)
        for active_index, active in enumerate(group):
            start = active.start
            end = group[active_index + 1].start if active_index + 1 < len(group) else display_end
            if end <= start:
                continue
            for index, label in enumerate(labels):
                scale = round(ACTIVE_SCALE * 100) if index == active_index else 100
                tags = (rf"{{\an5\pos({centers[index]:.2f},{y:.2f})\b1\fs{size}"
                        rf"\fscx{scale}\fscy{scale}\q2}}")
                result.append(Event(start, end, tags + label))
    return result
