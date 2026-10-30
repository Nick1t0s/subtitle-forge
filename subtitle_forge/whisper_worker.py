"""Standalone worker: only run using ~/whisper-venv/bin/python."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("media")
    parser.add_argument("output", type=Path)
    parser.add_argument("--language")
    args = parser.parse_args()

    # CUDA wheel libraries must be visible before CTranslate2 is imported.
    import nvidia.cublas.lib
    import nvidia.cudnn.lib
    libs = list(nvidia.cublas.lib.__path__) + list(nvidia.cudnn.lib.__path__)
    current = os.environ.get("LD_LIBRARY_PATH", "").split(":")
    if any(lib not in current for lib in libs):
        os.environ["LD_LIBRARY_PATH"] = ":".join(libs + current)
        os.execv(sys.executable, [sys.executable, *sys.argv])

    from faster_whisper import WhisperModel
    model = WhisperModel("large-v3-turbo", device="cuda", compute_type="float16",
                         local_files_only=True)
    segments, info = model.transcribe(args.media, language=args.language,
                                     word_timestamps=True, vad_filter=True, beam_size=5)
    data = {"language": info.language, "segments": []}
    for segment in segments:
        # Whisper can emit zero-length tokens; those cannot be visible events.
        words = [{"start": word.start, "end": word.end, "word": word.word}
                 for word in (segment.words or ()) if word.end > word.start]
        if segment.end > segment.start and segment.text.strip():
            data["segments"].append({"start": segment.start, "end": segment.end,
                                     "text": segment.text.strip(), "words": words})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=args.output.parent, delete=False) as handle:
            temp_name = handle.name
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, args.output)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


if __name__ == "__main__":
    main()
