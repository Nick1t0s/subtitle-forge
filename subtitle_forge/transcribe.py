"""Run transcription in the user's existing Whisper environment."""
from pathlib import Path
import subprocess


def transcribe(media: Path, output: Path, language: str | None = None) -> None:
    if not media.is_file():
        raise ValueError(f"Media file does not exist: {media}")
    python = Path.home() / "whisper-venv/bin/python"
    if not python.is_file():
        raise ValueError("Transcription requires the existing ~/whisper-venv environment.")
    worker = Path(__file__).with_name("whisper_worker.py")
    command = [str(python), str(worker), str(media.resolve()), str(output.resolve())]
    if language:
        command.extend(["--language", language])
    subprocess.run(command, check=True)
