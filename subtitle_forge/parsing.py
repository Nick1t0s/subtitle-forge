"""Load and save transcript data."""

import json
from pathlib import Path
import re
from typing import Any

from .models import Segment, Transcript, Word


_SRT_TIME = re.compile(
    r"^(\d{1,}):(\d{2}):(\d{2})[,.](\d{1,3})$"
)


def _seconds(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number")
    return float(value)


def _parse_json(path: Path) -> Transcript:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid transcript JSON: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("segments"), list):
        raise ValueError("JSON transcript must contain a segments array")
    segments = []
    for index, item in enumerate(data["segments"], 1):
        if not isinstance(item, dict):
            raise ValueError(f"segment {index} must be an object")
        words_data = item.get("words", [])
        if not isinstance(words_data, list):
            raise ValueError(f"segment {index} words must be an array")
        words = []
        for word_index, wd in enumerate(words_data, 1):
            if not isinstance(wd, dict):
                raise ValueError(f"word {word_index} in segment {index} must be an object")
            word_text = wd.get("word", wd.get("text"))
            if word_text is None:
                raise ValueError(f"word {word_index} in segment {index} needs word or text")
            words.append(Word(
                _seconds(wd.get("start"), "word start"),
                _seconds(wd.get("end"), "word end"),
                word_text,
            ))
        segments.append(Segment(
            _seconds(item.get("start"), "segment start"),
            _seconds(item.get("end"), "segment end"),
            item.get("text"),
            tuple(words),
        ))
    language = data.get("language")
    return Transcript(tuple(segments), language)


def _srt_seconds(value: str) -> float:
    match = _SRT_TIME.fullmatch(value.strip())
    if not match:
        raise ValueError(f"invalid SRT timestamp: {value!r}")
    hours, minutes, seconds, fraction = match.groups()
    if int(minutes) >= 60 or int(seconds) >= 60:
        raise ValueError(f"invalid SRT timestamp: {value!r}")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(fraction) / (10 ** len(fraction))


def _parse_srt(path: Path) -> Transcript:
    content = path.read_text(encoding="utf-8-sig")
    blocks = re.split(r"\r?\n\s*\r?\n", content.strip()) if content.strip() else []
    segments = []
    for number, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if lines and lines[0].strip().isdigit():
            lines = lines[1:]
        if not lines:
            continue
        timing = re.fullmatch(r"\s*(\S+)\s*-->\s*(\S+)(?:\s+.*)?", lines[0])
        if not timing:
            raise ValueError(f"invalid SRT cue {number}: missing timing line")
        start, end = map(_srt_seconds, timing.groups())
        # A cue remains one timed segment; word timings are never inferred.
        segments.append(Segment(start, end, "\n".join(lines[1:]), ()))
    return Transcript(tuple(segments))


def load_transcript(path: Path) -> Transcript:
    """Load a JSON transcript or an SRT file, selected by suffix."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".srt":
        return _parse_srt(path)
    if suffix == ".json":
        return _parse_json(path)
    raise ValueError(f"unsupported transcript format: {path.suffix or '(no extension)'}")


def save_transcript(transcript: Transcript, path: Path) -> None:
    """Write a transcript as UTF-8 JSON."""
    if not isinstance(transcript, Transcript):
        raise TypeError("transcript must be a Transcript")
    path = Path(path)
    data = {
        "language": transcript.language,
        "segments": [
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "words": [
                    {"start": word.start, "end": word.end, "word": word.text}
                    for word in segment.words
                ],
            }
            for segment in transcript.segments
        ],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
