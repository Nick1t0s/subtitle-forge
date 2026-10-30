"""Burn generated ASS using ffmpeg without shell or filter-path interpolation."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def burn_subtitles(video: Path, subtitles: Path, output: Path, overwrite=False):
    if not video.is_file():
        raise ValueError(f"Video does not exist: {video}")
    if video.resolve() == output.resolve():
        raise ValueError("Input and output video paths must differ")
    if not shutil.which("ffmpeg"):
        raise ValueError("ffmpeg with libass is required to burn subtitles")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="subtitle-forge-") as temp:
        # A fixed simple name avoids ffmpeg's multiple levels of path escaping.
        shutil.copyfile(subtitles, Path(temp) / "captions.ass")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-y" if overwrite else "-n", "-i", str(video.resolve()),
                        "-vf", "ass=captions.ass", "-c:v", "libx264", "-crf", "18",
                        "-preset", "medium", "-c:a", "copy", str(output.resolve())],
                       cwd=temp, check=True)
