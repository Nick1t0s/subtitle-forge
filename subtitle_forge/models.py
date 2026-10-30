"""Validated transcript data structures."""

from dataclasses import dataclass
import math


def _validate_interval(start: float, end: float, label: str) -> None:
    if not isinstance(start, (int, float)) or isinstance(start, bool) or not math.isfinite(start):
        raise ValueError(f"{label} start must be a finite number")
    if not isinstance(end, (int, float)) or isinstance(end, bool) or not math.isfinite(end):
        raise ValueError(f"{label} end must be a finite number")
    if start < 0 or end <= start:
        raise ValueError(f"{label} must have 0 <= start < end")


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str

    def __post_init__(self) -> None:
        _validate_interval(self.start, self.end, "word")
        if not isinstance(self.text, str):
            raise TypeError("word text must be a string")


@dataclass(frozen=True)
class Segment:
    start: float
    end: float
    text: str
    words: tuple[Word, ...] = ()

    def __post_init__(self) -> None:
        _validate_interval(self.start, self.end, "segment")
        if not isinstance(self.text, str):
            raise TypeError("segment text must be a string")
        words = tuple(self.words)
        object.__setattr__(self, "words", words)
        previous_end = -1.0
        for word in words:
            if not isinstance(word, Word):
                raise TypeError("segment words must contain Word instances")
            if word.start < previous_end:
                raise ValueError("words must be ordered and must not overlap")
            previous_end = word.end


@dataclass(frozen=True)
class Transcript:
    segments: tuple[Segment, ...]
    language: str | None = None

    def __post_init__(self) -> None:
        segments = tuple(self.segments)
        if any(not isinstance(segment, Segment) for segment in segments):
            raise TypeError("transcript segments must contain Segment instances")
        object.__setattr__(self, "segments", segments)
        if self.language is not None and not isinstance(self.language, str):
            raise TypeError("language must be a string or None")
