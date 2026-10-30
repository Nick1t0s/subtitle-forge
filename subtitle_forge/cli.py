"""The command-line interface; rendering needs only the Python standard library."""
import argparse
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

from .ass import render_ass
from .parsing import load_transcript
from .styles import list_styles, load_style
from .transcribe import transcribe
from .video import burn_subtitles


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def parser():
    root = argparse.ArgumentParser(description="Generate styled, word-timed ASS subtitles")
    root.add_argument("--version", action="version", version="subtitle-forge 0.1.0")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("styles", help="List built-in styles")
    generate = commands.add_parser("generate", help="Render a JSON/SRT transcript to ASS")
    generate.add_argument("input", type=Path)
    generate.add_argument("-o", "--output", required=True, type=Path)
    generate.add_argument("--style", default="karaoke", help="Built-in name or trusted .py plugin")
    generate.add_argument("--width", type=positive, default=1920)
    generate.add_argument("--height", type=positive, default=1080)
    generate.add_argument("--font")
    generate.add_argument("--font-size", type=positive)
    generate.add_argument("--margin-v", type=int)
    generate.add_argument("--burn", type=Path, metavar="VIDEO")
    generate.add_argument("--video-output", type=Path)
    generate.add_argument("--overwrite", action="store_true")
    speech = commands.add_parser("transcribe", help="Use existing local faster-whisper with word timestamps")
    speech.add_argument("input", type=Path)
    speech.add_argument("-o", "--output", required=True, type=Path)
    speech.add_argument("--language")
    speech.add_argument("--overwrite", action="store_true")
    return root


def main(argv=None):
    root = parser()
    args = root.parse_args(argv)
    try:
        if args.command == "styles":
            for style in list_styles():
                print(f"{style.NAME:12} {style.DESCRIPTION}")
            return 0
        if args.input.resolve() == args.output.resolve():
            raise ValueError("Input and output paths must differ")
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Output already exists: {args.output}; use --overwrite")
        if args.command == "transcribe":
            transcribe(args.input, args.output, args.language)
        else:
            if bool(args.burn) != bool(args.video_output):
                raise ValueError("--burn and --video-output must be used together")
            if args.burn:
                paths = [args.input, args.output, args.burn, args.video_output]
                if args.output.resolve() == args.burn.resolve():
                    raise ValueError("Subtitle output must differ from source video")
                if args.video_output.resolve() in {p.resolve() for p in paths[:3]}:
                    raise ValueError("Video output must differ from all input and subtitle paths")
                if not args.burn.is_file():
                    raise ValueError(f"Video does not exist: {args.burn}")
                if args.video_output.exists() and not args.overwrite:
                    raise ValueError("Video output already exists; use --overwrite")
            transcript = load_transcript(args.input)
            if not transcript.segments:
                raise ValueError("Transcript contains no segments")
            style = load_style(args.style)
            options = {key: getattr(args, key) for key in ("font", "font_size", "margin_v")
                       if getattr(args, key) is not None}
            config = replace(style.CONFIG, **options)
            events = style.generate(transcript, config)
            content = render_ass(events, config, width=args.width, height=args.height)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content, encoding="utf-8")
            if args.burn:
                burn_subtitles(args.burn, args.output, args.video_output, args.overwrite)
        print(args.output)
        return 0
    except (ValueError, TypeError, OSError, subprocess.CalledProcessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
