"""Phrase captions with an accurately timed per-word highlight."""
from ..ass import StyleConfig, escape_text
from ._common import color, event, phrase, word_groups

NAME = "karaoke"
DESCRIPTION = "Chunked phrase captions; the active word is highlighted for its measured interval."
CONFIG = StyleConfig(highlight_color="&H0000FFFF")
REQUIRES_WORDS = True


def generate(transcript, config=CONFIG):
    result = []
    for _segment, groups in word_groups(transcript):
        for group in groups:
            for active in group:
                pieces = []
                for word in group:
                    if word is active:
                        pieces.append(color(config.highlight_color) + escape_text(word.text.strip()) + r"{\r}")
                    else:
                        pieces.append(escape_text(word.text.strip()))
                item = event(active.start, active.end, " ".join(pieces))
                if item:
                    result.append(item)
    return result
