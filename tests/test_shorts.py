import re
import unittest

from subtitle_forge.ass import render_ass
from subtitle_forge.models import Segment, Transcript, Word
from subtitle_forge.styles import load_style


class ShortsStyleTests(unittest.TestCase):
    def test_multiword_tokens_cannot_exceed_three_visible_words(self):
        module = load_style("shorts")
        transcript = Transcript((Segment(0, 2, "two word token next", (
            Word(0, .5, "two word"), Word(.6, 1, "token"), Word(1.1, 2, "next"),
        )),))
        events = module.generate(transcript, module.CONFIG)
        for time in (.2, .8, 1.5):
            visible = [event for event in events if event.start <= time < event.end]
            tokens = [re.sub(r"\{[^}]*\}", "", event.text).split() for event in visible]
            self.assertLessEqual(sum(map(len, tokens)), 3)

    @staticmethod
    def visible(events, time):
        return [event for event in events if event.start <= time < event.end]

    @staticmethod
    def label(event):
        return re.sub(r"\{[^}]*\}", "", event.text)

    def test_each_active_state_shows_one_to_three_words_with_exactly_one_enlarged(self):
        module = load_style("shorts")
        words = tuple(Word(i * 0.4, i * 0.4 + 0.3, word)
                      for i, word in enumerate(("one", "two", "three", "four")))
        transcript = Transcript((Segment(0, 2, "ignored segment phrase", words),), "en")
        events = module.generate(transcript, module.CONFIG)

        self.assertEqual(len(events), 8)  # two groups, two active states each, two visible words
        self.assertTrue(all(event.end > event.start for event in events))
        boundaries = sorted({event.start for event in events} | {event.end for event in events})
        for start, end in zip(boundaries, boundaries[1:]):
            if end <= start:
                continue
            visible = self.visible(events, (start + end) / 2)
            self.assertGreaterEqual(len(visible), 1)
            self.assertLessEqual(len(visible), 3)
            active = [event for event in visible if r"\fscx135\fscy135" in event.text]
            self.assertEqual(len(active), 1)
            self.assertNotIn("ignored segment phrase", " ".join(self.label(event) for event in visible))

    def test_four_words_are_balanced_into_two_pairs_with_fixed_word_positions(self):
        module = load_style("shorts")
        words = tuple(Word(i * 0.4, i * 0.4 + 0.3, word)
                      for i, word in enumerate(("one", "two", "three", "four")))
        events = module.generate(Transcript((Segment(0, 2, "", words),), "en"), module.CONFIG)
        states = [self.visible(events, time) for time in (0.1, 0.5, 0.9, 1.3)]
        self.assertEqual([[self.label(event) for event in state] for state in states], [
            ["one", "two"], ["one", "two"], ["three", "four"], ["three", "four"],
        ])
        for word in ("one", "two", "three", "four"):
            positions = {
                re.search(r"\\pos\(([^)]+)\)", event.text).group(1)
                for event in events if self.label(event) == word
            }
            self.assertEqual(len(positions), 1, f"{word} should stay in its slot across active states")

    def test_previous_group_is_held_through_a_pause_until_next_group_starts(self):
        module = load_style("shorts")
        words = (Word(0.1, 0.3, "first"), Word(1.2, 1.4, "second"))
        events = module.generate(Transcript((Segment(0, 2, "", words),), "en"), module.CONFIG)
        during_pause = self.visible(events, 0.8)
        self.assertEqual([self.label(event) for event in during_pause], ["first"])
        self.assertTrue(all(event.end == 1.2 for event in during_pause))
        self.assertEqual([self.label(event) for event in self.visible(events, 1.3)], ["second"])

    def test_requires_word_timestamps_and_uses_vertical_canvas_and_short_style(self):
        module = load_style("shorts")
        with self.assertRaisesRegex(ValueError, "word-level timestamps"):
            module.generate(Transcript((Segment(0, 2, "no word timing here"),), "en"), module.CONFIG)
        self.assertEqual(module.CONFIG.font_size, 90)
        self.assertEqual(module.CONFIG.primary_color, "&H0000E8FF")
        self.assertEqual(module.CONFIG.outline_color, "&H00FFFFFF")
        self.assertEqual((module.CONFIG.canvas_width, module.CONFIG.canvas_height), (1080, 1920))
        transcript = Transcript((Segment(0, 1, "hello", (Word(0, 1, "hello"),)),), "en")
        rendered = render_ass(module.generate(transcript, module.CONFIG), module.CONFIG)
        self.assertIn("PlayResX: 1080", rendered)
        self.assertIn("PlayResY: 1920", rendered)


if __name__ == "__main__":
    unittest.main()
