"""Single-word captions, displayed only during the measured word interval."""
from ..ass import StyleConfig, escape_text
from ._common import event, word_groups

NAME = "word"
DESCRIPTION = "One word at a time, with event bounds taken from word timestamps."
CONFIG = StyleConfig(font_size=66, outline=4)
REQUIRES_WORDS = True


def generate(transcript, config=CONFIG):
    result = []
    for _segment, groups in word_groups(transcript):
        for group in groups:
            for word in group:
                item = event(word.start, word.end, escape_text(word.text.strip()))
                if item:
                    result.append(item)
    return result
