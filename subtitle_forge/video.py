"""Burn generated ASS using ffmpeg without shell or filter-path interpolation."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def burn_subtitles(video: Path, subtitles: Path, output: Path, overwrite=False,
                   width=1080, height=1920, fit="pad"):
    for dimension in (width, height):
        if isinstance(dimension, bool) or not isinstance(dimension, int) or dimension <= 0 or dimension % 2:
            raise ValueError("Video width and height must be positive even integers for H.264 yuv420p")
    if fit not in ("pad", "crop"):
        raise ValueError("Video fit must be pad or crop")
    if not video.is_file():
        raise ValueError(f"Video does not exist: {video}")
    if video.resolve() == output.resolve():
        raise ValueError("Input and output video paths must differ")
    if subtitles.resolve() == output.resolve():
        raise ValueError("Subtitle and output video paths must differ")
    if not shutil.which("ffmpeg"):
        raise ValueError("ffmpeg with libass is required to burn subtitles")
    output.parent.mkdir(parents=True, exist_ok=True)
    if fit == "pad":
        layout = (f"scale={width}:{height}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
                  f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
    else:
        layout = (f"scale={width}:{height}:force_original_aspect_ratio=increase:force_divisible_by=2,"
                  f"crop={width}:{height}")
    with tempfile.TemporaryDirectory(prefix="subtitle-forge-") as temp:
        # A fixed simple name avoids ffmpeg's multiple levels of path escaping.
        shutil.copyfile(subtitles, Path(temp) / "captions.ass")
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                        "-y" if overwrite else "-n", "-i", str(video.resolve()),
                        "-vf", f"{layout},setsar=1,ass=captions.ass", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                        "-preset", "medium", "-c:a", "copy", str(output.resolve())],
                       cwd=temp, check=True)
