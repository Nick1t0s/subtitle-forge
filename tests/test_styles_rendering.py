from pathlib import Path
import tempfile
import unittest

from subtitle_forge.ass import Event, StyleConfig, escape_text, render_ass
from subtitle_forge.models import Segment, Transcript, Word
from subtitle_forge.styles import list_styles, load_style


class AssTests(unittest.TestCase):
    def test_rendered_ass_contains_script_and_event_text(self):
        rendered = render_ass([Event(0, 1.25, "Hello, world!")], StyleConfig())
        self.assertIn("[Script Info]", rendered)
        self.assertIn("[Events]", rendered)
        self.assertIn("Hello, world!", rendered)

    def test_ass_markup_is_escaped(self):
        escaped = escape_text("{\\b1}Hello\nworld")
        self.assertNotIn("{\\b1}", escaped)
        self.assertEqual(escaped, "｛＼b1｝Hello world")
        self.assertIn("world", escaped)
        self.assertNotIn("\n", escaped)


class StyleTests(unittest.TestCase):
    def test_builtin_styles_are_discoverable_and_generatable(self):
        names = {module.NAME for module in list_styles()}
        expected = {"classic", "word", "karaoke", "typewriter", "pop"}
        self.assertTrue(expected.issubset(names))
        transcript = Transcript((Segment(
            0, 1.5, "hello world", (Word(0, 0.6, "hello"), Word(0.7, 1.5, "world"))
        ),), "en")
        for name in expected:
            with self.subTest(style=name):
                module = load_style(name)
                self.assertTrue(module.DESCRIPTION)
                self.assertTrue(isinstance(module.REQUIRES_WORDS, bool))
                events = module.generate(transcript, module.CONFIG)
                self.assertTrue(events)
                self.assertTrue(all(isinstance(event, Event) for event in events))

    def test_all_but_classic_reject_srt_without_word_times(self):
        transcript = Transcript((Segment(12.25, 15.75, "a sufficiently long caption"),), None)
        for name in ("word", "karaoke", "typewriter", "pop"):
            with self.subTest(style=name), self.assertRaisesRegex(ValueError, "word-level timestamps"):
                load_style(name).generate(transcript, load_style(name).CONFIG)

    def test_karaoke_events_follow_word_times_and_leave_pauses(self):
        transcript = Transcript((Segment(
            0, 4, "one two", (Word(0.5, 1.0, "one"), Word(2.25, 3.0, "two"))
        ),), "en")
        module = load_style("karaoke")
        events = module.generate(transcript, module.CONFIG)
        self.assertEqual([(event.start, event.end) for event in events], [(0.5, 1.0), (2.25, 3.0)])
        self.assertLess(events[0].end, events[1].start)
        # Karaoke's generated override tag must survive ASS rendering as one tag.
        rendered = render_ass(events, module.CONFIG)
        self.assertIn(r"{\1c" + module.CONFIG.highlight_color + "&}", rendered)
        self.assertNotIn(r"{\\1c", rendered)

    def test_classic_srt_events_keep_the_cue_interval(self):
        from subtitle_forge.parsing import load_transcript

        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "long.srt"
            source.write_text(
                "1\n12:00:12,250 --> 12:00:15,750\n"
                "This is a deliberately long subtitle cue with enough words to exceed the usual line chunk limit.\n",
                encoding="utf-8",
            )
            transcript = load_transcript(source)
        module = load_style("classic")
        events = module.generate(transcript, module.CONFIG)
        self.assertTrue(events)
        self.assertTrue(all((event.start, event.end) == (43212.25, 43215.75) for event in events))


if __name__ == "__main__":
    unittest.main()
