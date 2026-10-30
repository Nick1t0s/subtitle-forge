"""Heavy, single-word captions centered in the frame."""
from dataclasses import replace

from ..ass import StyleConfig
from .impact_bottom import CONFIG as BOTTOM_CONFIG, _generate

NAME = "impact-center"
DESCRIPTION = "One heavy outlined word at a time, centered in the frame without animation."
CONFIG = replace(BOTTOM_CONFIG, alignment=5, margin_v=0)
REQUIRES_WORDS = True


def generate(transcript, config=CONFIG):
    return _generate(transcript, config, centered=True)
