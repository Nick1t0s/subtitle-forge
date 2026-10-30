import re
import unittest

from subtitle_forge.ass import render_ass
from subtitle_forge.models import Segment, Transcript, Word
from subtitle_forge.styles import load_style


class ShortsStyleTests(unittest.TestCase):
    def test_groups_word_times_and_keeps_pauses_and_sentence_boundaries(self):
        module = load_style("shorts")
        transcript = Transcript((Segment(0, 6, "ignored segment text", (
            Word(0.2, 0.4, "One."),
            Word(0.5, 0.7, "Next"),
            Word(0.8, 1.0, "two"),
            Word(1.1, 1.3, "three"),
            Word(2.0, 2.2, "after"),
            Word(2.3, 2.5, "pause"),
        )),), "en")

        events = module.generate(transcript, module.CONFIG)

        self.assertEqual([(event.start, event.end) for event in events], [
            (0.2, 0.4), (0.5, 1.3), (2.0, 2.5),
        ])
        self.assertEqual(len(events), 3)
        self.assertNotIn("ignored segment text", " ".join(event.text for event in events))
        self.assertIn("One.", events[0].text)
        self.assertNotIn("Next", events[0].text)
        self.assertIn("Next", events[1].text)
        self.assertNotIn("after", events[1].text)
        self.assertIn("after", events[2].text)

    def test_four_words_are_balanced_into_two_pairs_and_active_word_animated(self):
        module = load_style("shorts")
        transcript = Transcript((Segment(0, 2, "one two three four", tuple(
            Word(index * 0.4, index * 0.4 + 0.3, word)
            for index, word in enumerate(("one", "two", "three", "four"))
        )),), "en")

        events = module.generate(transcript, module.CONFIG)

        self.assertEqual(len(events), 2)
        for event, words in zip(events, (("one", "two"), ("three", "four"))):
            for word in words:
                self.assertIn(word, event.text)
            self.assertEqual(len(re.findall(r"\\b1\\fs90", event.text)), 2)
            # Each active word has an ease-up and return transform.
            self.assertEqual(len(re.findall(r"\\t\(", event.text)), 4)

    def test_requires_word_timestamps(self):
        module = load_style("shorts")
        transcript = Transcript((Segment(0, 2, "no word timing here"),), "en")
        with self.assertRaisesRegex(ValueError, "word-level timestamps"):
            module.generate(transcript, module.CONFIG)

    def test_config_is_yellow_white_outlined_and_ass_has_vertical_dimensions(self):
        module = load_style("shorts")
        self.assertEqual(module.CONFIG.font_size, 90)
        self.assertEqual(module.CONFIG.primary_color, "&H0000E8FF")
        self.assertEqual(module.CONFIG.outline_color, "&H00FFFFFF")
        transcript = Transcript((Segment(0, 1, "hello", (Word(0, 1, "hello"),)),), "en")
        rendered = render_ass(module.generate(transcript, module.CONFIG), module.CONFIG,
                              width=1080, height=1920)
        self.assertIn("PlayResX: 1080", rendered)
        self.assertIn("PlayResY: 1920", rendered)

    def test_active_word_animation_is_attached_before_its_word_and_reset_for_next(self):
        module = load_style("shorts")
        transcript = Transcript((Segment(0, 1, "alpha beta", (
            Word(0, 0.4, "alpha"), Word(0.5, 1, "beta"),
        )),), "en")
        caption = module.generate(transcript, module.CONFIG)[0].text

        alpha = caption.index("alpha")
        beta = caption.index("beta")
        alpha_animation = caption.index(r"\t(")
        beta_animation = caption.index(r"\t(", alpha_animation + 1)
        self.assertLess(alpha_animation, alpha)
        self.assertLess(beta_animation, beta)
        # A fresh base size tag after alpha's transforms keeps beta independent.
        self.assertRegex(caption[alpha:beta], r"\\fs90.*\\fs90")


if __name__ == "__main__":
    unittest.main()
