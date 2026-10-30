from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from subtitle_forge.ass import Event, StyleConfig, render_ass
from subtitle_forge.video import burn_subtitles


class BurnSubtitlesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.video = root / "input.mp4"
        self.video.write_bytes(b"video")
        self.subtitles = root / "captions.ass"
        self.subtitles.write_text("[Script Info]\n", encoding="utf-8")
        self.output = root / "output.mp4"

    def invoke_mocked(self, **kwargs):
        with patch("subtitle_forge.video.shutil.which", return_value="/usr/bin/ffmpeg"), \
                patch("subtitle_forge.video.subprocess.run") as run:
            burn_subtitles(self.video, self.subtitles, self.output, **kwargs)
        return run.call_args

    def test_pad_fit_uses_requested_output_dimensions(self):
        call = self.invoke_mocked(width=1080, height=1920, fit="pad")
        command = call.args[0]
        video_filter = command[command.index("-vf") + 1]
        self.assertIn("scale=1080:1920", video_filter)
        self.assertIn("pad=1080:1920", video_filter)

    def test_crop_fit_uses_requested_output_dimensions(self):
        call = self.invoke_mocked(width=720, height=1280, fit="crop")
        command = call.args[0]
        video_filter = command[command.index("-vf") + 1]
        self.assertIn("scale=720:1280", video_filter)
        self.assertIn("crop=720:1280", video_filter)

    def test_existing_output_is_protected_unless_overwrite_is_set(self):
        self.output.write_bytes(b"existing")
        with patch("subtitle_forge.video.shutil.which", return_value="/usr/bin/ffmpeg"), \
                patch("subtitle_forge.video.subprocess.run") as run:
            burn_subtitles(self.video, self.subtitles, self.output)
        self.assertIn("-n", run.call_args.args[0])

        call = self.invoke_mocked(overwrite=True)
        self.assertIn("-y", call.args[0])

    def test_missing_ffmpeg_is_reported(self):
        with patch("subtitle_forge.video.shutil.which", return_value=None):
            with self.assertRaisesRegex(ValueError, "ffmpeg"):
                burn_subtitles(self.video, self.subtitles, self.output)

    def test_input_and_output_must_differ(self):
        with patch("subtitle_forge.video.shutil.which", return_value="/usr/bin/ffmpeg"):
            with self.assertRaisesRegex(ValueError, "must differ"):
                burn_subtitles(self.video, self.subtitles, self.video)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "ffmpeg and ffprobe are required for media integration")
class VideoIntegrationTests(unittest.TestCase):
    def test_pad_and_crop_create_vertical_video_with_audio_and_decode_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            subtitles = root / "captions.ass"
            subtitles.write_text(
                render_ass([Event(0, 0.35, "Integration caption")], StyleConfig(),
                           width=180, height=320), encoding="utf-8")
            subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=blue:s=320x240:r=10:d=0.4",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=0.4",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-shortest", str(source),
            ], check=True)

            for fit in ("pad", "crop"):
                with self.subTest(fit=fit):
                    output = root / f"{fit}.mp4"
                    burn_subtitles(source, subtitles, output, width=180, height=320, fit=fit)
                    probe = subprocess.run([
                        "ffprobe", "-v", "error", "-show_entries",
                        "stream=codec_type,width,height", "-of", "json", str(output),
                    ], check=True, text=True, capture_output=True)
                    streams = json.loads(probe.stdout)["streams"]
                    video_stream = next(stream for stream in streams if stream["codec_type"] == "video")
                    self.assertEqual((video_stream["width"], video_stream["height"]), (180, 320))
                    self.assertTrue(any(stream["codec_type"] == "audio" for stream in streams))
                    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error",
                                    "-i", str(output), "-f", "null", "-"], check=True)


if __name__ == "__main__":
    unittest.main()
