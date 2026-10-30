"""Conventional phrase captions."""
from ..ass import StyleConfig, escape_text
from ._common import classic_groups, event

NAME = "classic"
DESCRIPTION = "Whole phrase captions with readable seven-word/42-character chunks."
CONFIG = StyleConfig()
REQUIRES_WORDS = False


def generate(transcript, config=CONFIG):
    result = []
    for segment in transcript.segments:
        for start, end, text in classic_groups(segment):
            item = event(start, end, text)
            if item:
                result.append(item)
    return result
