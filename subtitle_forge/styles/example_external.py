"""Minimal example of an explicitly loaded external style plugin.

Load with ``load_style('/path/to/example_external.py')``. Python style files
execute at import time, so only load files from trusted sources.
"""
from subtitle_forge.ass import Event, StyleConfig, escape_text

NAME = "example_external"
DESCRIPTION = "A minimal external style that uses one event per original cue."
CONFIG = StyleConfig(font_size=48)
REQUIRES_WORDS = False


def generate(transcript, config=CONFIG) -> list[Event]:
    events = []
    for segment in transcript.segments:
        text = " ".join(segment.text.split())
        if text:
            events.append(Event(segment.start, segment.end, escape_text(text)))
    return events
