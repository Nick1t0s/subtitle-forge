"""Progressively reveals the phrase as words begin."""
from ..ass import StyleConfig, escape_text
from ._common import event, phrase, word_groups

NAME = "typewriter"
DESCRIPTION = "Reveals accumulated words at their start times, with no events during word gaps."
CONFIG = StyleConfig(font_size=52)
REQUIRES_WORDS = True


def generate(transcript, config=CONFIG):
    result = []
    for _segment, groups in word_groups(transcript):
        for group in groups:
            for index, word in enumerate(group):
                revealed = phrase(group[:index + 1])
                item = event(word.start, word.end, escape_text(revealed))
                if item:
                    result.append(item)
    return result
