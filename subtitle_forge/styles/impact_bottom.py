"""Heavy, single-word captions anchored near the bottom of the frame."""
from __future__ import annotations

from ..ass import Event, StyleConfig, escape_text
from ..font_metrics import measure_text

NAME = "impact-bottom"
DESCRIPTION = "One heavy outlined word at a time, centered near the bottom without animation."
CONFIG = StyleConfig(
    font="Oswald",
    font_size=128,
    primary_color="&H00FFFFFF",
    outline_color="&H00000000",
    outline=8,
    shadow=2,
    alignment=2,
    margin_v=260,
)
REQUIRES_WORDS = True

PAUSE_SPLIT_SECONDS = 0.45
SIDE_MARGIN = 60


def _ordered_words(transcript):
    words = []
    for segment in transcript.segments:
        if not segment.words:
            raise ValueError("This style requires word-level timestamps; transcript segment has no words")
        words.extend(word for word in segment.words if word.text.strip())
    words.sort(key=lambda word: (word.start, word.end))
    previous = None
    for word in words:
        if previous is not None and word.start < previous.end:
            raise ValueError("Impact captions require globally ordered, non-overlapping word timestamps")
        previous = word
    return words


def _generate(transcript, config, centered=False) -> list[Event]:
    """Create a stable-position cue per word, extending only across short pauses."""
    words = _ordered_words(transcript)
    result = []
    x = config.canvas_width / 2
    y = (config.canvas_height / 2 if centered else
         config.canvas_height - config.margin_v - config.font_size / 2)
    available = max(1, config.canvas_width - 2 * SIDE_MARGIN)

    for index, word in enumerate(words):
        text = word.text.strip()
        size = config.font_size
        advance = measure_text(text, config.font, size)
        if advance > available:
            size = max(1, int(size * available / advance))

        end = word.end
        if index + 1 < len(words):
            next_word = words[index + 1]
            if next_word.start - word.end <= PAUSE_SPLIT_SECONDS:
                end = next_word.start

        if end <= word.start:
            continue
        tags = (rf"{{\an5\pos({x:.2f},{y:.2f})\b700\fs{size}"
                rf"\q2\fscx100\fscy100}}")
        result.append(Event(float(word.start), float(end), tags + escape_text(text)))
    return result


def generate(transcript, config=CONFIG) -> list[Event]:
    return _generate(transcript, config)
