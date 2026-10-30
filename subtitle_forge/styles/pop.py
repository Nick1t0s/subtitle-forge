"""Single-word captions with a quick scale and fade entrance."""
from ..ass import StyleConfig, escape_text
from ._common import event, word_groups

NAME = "pop"
DESCRIPTION = "One word at a time with a brief scale-up and fade-in animation."
CONFIG = StyleConfig(font_size=68, outline=4, shadow=2)
REQUIRES_WORDS = True


def generate(transcript, config=CONFIG):
    result = []
    for _segment, groups in word_groups(transcript):
        for group in groups:
            for word in group:
                # ASS transform times are milliseconds relative to the event.
                text = r"{\fscx65\fscy65\alpha&HFF&\t(0,110,\fscx100\fscy100\alpha&H00&)}" + escape_text(word.text.strip())
                item = event(word.start, word.end, text)
                if item:
                    result.append(item)
    return result
