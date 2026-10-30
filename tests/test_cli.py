from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "subtitle_forge", *map(str, arguments)],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )

    def test_styles_command_lists_builtins(self):
        result = self.run_cli("styles")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("shorts", "classic", "word", "karaoke", "typewriter", "pop"):
            self.assertIn(name, result.stdout)

    def test_generate_writes_ass_and_protects_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "captions.ass"
            source = ROOT / "examples" / "transcript.json"
            result = self.run_cli("generate", source, "-o", output, "--style", "karaoke")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("[Events]", output.read_text(encoding="utf-8"))
            second = self.run_cli("generate", source, "-o", output, "--style", "classic")
            self.assertNotEqual(second.returncode, 0)
            self.assertIn("already exists", second.stderr)

    def test_burn_options_must_be_given_as_a_pair(self):
        source = ROOT / "examples" / "transcript.json"
        with tempfile.TemporaryDirectory() as directory:
            subtitle = Path(directory) / "captions.ass"
            video = Path(directory) / "out.mp4"
            only_burn = self.run_cli("generate", source, "-o", subtitle,
                                     "--style", "classic", "--burn", "input.mp4")
            self.assertNotEqual(only_burn.returncode, 0)
            self.assertIn("--burn and --video-output", only_burn.stderr)
            only_output = self.run_cli("generate", source, "-o", subtitle,
                                       "--style", "classic", "--video-output", video)
            self.assertNotEqual(only_output.returncode, 0)
            self.assertIn("--burn and --video-output", only_output.stderr)

    def test_default_output_uses_portrait_shorts_style(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "default.ass"
            result = self.run_cli("generate", ROOT / "examples/transcript.json", "-o", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            content = output.read_text(encoding="utf-8")
            self.assertIn("PlayResX: 1080", content)
            self.assertIn("PlayResY: 1920", content)
            self.assertIn("&H0000E8FF", content)
            self.assertIn(r"\t(", content)


if __name__ == "__main__":
    unittest.main()
