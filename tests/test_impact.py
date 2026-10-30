import re
import unittest
from dataclasses import replace
from unittest.mock import patch

from subtitle_forge.models import Segment, Transcript, Word
from subtitle_forge.styles import load_style


class ImpactStyleTests(unittest.TestCase):
    @staticmethod
    def transcript(words):
        return Transcript((Segment(0, max(word.end for word in words), "segment text must not leak", tuple(words)),))

    @staticmethod
    def label(event):
        return re.sub(r"\{[^}]*\}", "", event.text)

    @staticmethod
    def visible(events, time):
        return [event for event in events if event.start <= time < event.end]

    def test_registry_exposes_separate_bottom_and_center_styles(self):
        bottom = load_style("impact-bottom")
        center = load_style("impact-center")
        self.assertEqual(bottom.NAME, "impact-bottom")
        self.assertEqual(center.NAME, "impact-center")
        self.assertEqual((bottom.CONFIG.alignment, bottom.CONFIG.margin_v), (2, 260))
        self.assertEqual((center.CONFIG.alignment, center.CONFIG.margin_v), (5, 0))

    def test_one_word_visible_at_a_time_with_hard_changes_and_no_phrase_leak(self):
        module = load_style("impact-bottom")
        words = (Word(0, .4, "MiXeD"), Word(.4, .8, "Case"), Word(1.5, 1.9, "Again"))
        events = module.generate(self.transcript(words))
        self.assertEqual([self.label(event) for event in events], ["MiXeD", "Case", "Again"])
        self.assertEqual([(event.start, event.end) for event in events], [(0, .4), (.4, .8), (1.5, 1.9)])
        for moment in (.1, .4, .7, 1.6):
            visible = self.visible(events, moment)
            self.assertEqual(len(visible), 1)
            self.assertNotIn("segment text", visible[0].text)

    def test_short_pause_holds_word_but_long_pause_does_not(self):
        module = load_style("impact-bottom")
        words = (Word(0, .3, "short"), Word(.6, .9, "next"), Word(2, 2.3, "long"), Word(2.8, 3, "last"))
        events = module.generate(self.transcript(words))
        self.assertEqual([(e.start, e.end) for e in events], [(0, .6), (.6, .9), (2, 2.3), (2.8, 3)])
        self.assertEqual([self.label(e) for e in self.visible(events, .45)], ["short"])
        self.assertEqual(self.visible(events, 1.5), [])

    def test_variants_keep_same_words_and_timings_but_use_different_vertical_positions(self):
        words = (Word(.2, .7, "Center"), Word(.7, 1.1, "Bottom"))
        transcript = self.transcript(words)
        bottom = load_style("impact-bottom").generate(transcript)
        center = load_style("impact-center").generate(transcript)
        self.assertEqual([(e.start, e.end, self.label(e)) for e in bottom],
                         [(e.start, e.end, self.label(e)) for e in center])
        bottom_y = re.search(r"\\pos\(([^,]+),([^)]+)\)", bottom[0].text).group(2)
        center_y = re.search(r"\\pos\(([^,]+),([^)]+)\)", center[0].text).group(2)
        self.assertNotEqual(bottom_y, center_y)
        self.assertEqual(center_y, "960.00")

    def test_positions_scale_with_custom_canvas_dimensions(self):
        transcript = self.transcript((Word(0, 1, "scale"),))
        for name, y in (("impact-bottom", 720 - 260 - 128 / 2), ("impact-center", 360)):
            module = load_style(name)
            config = replace(module.CONFIG, canvas_width=640, canvas_height=720)
            event = module.generate(transcript, config)[0]
            match = re.search(r"\\pos\(([^,]+),([^)]+)\)", event.text)
            self.assertEqual(match.groups(), ("320.00", f"{y:.2f}"))

    def test_long_word_is_shrunk_to_fit_canvas_width(self):
        module = load_style("impact-bottom")
        transcript = self.transcript((Word(0, 1, "oversized"),))
        with patch("subtitle_forge.styles.impact_bottom.measure_text", side_effect=lambda text, font, size: size * 10):
            event = module.generate(transcript, module.CONFIG)[0]
        size = int(re.search(r"\\fs(\d+)", event.text).group(1))
        self.assertLess(size, module.CONFIG.font_size)
        self.assertGreater(size, 0)

    def test_rejects_transcripts_without_word_timestamps(self):
        module = load_style("impact-bottom")
        transcript = Transcript((Segment(0, 2, "plain SRT style segment"),))
        with self.assertRaisesRegex(ValueError, "word-level timestamps"):
            module.generate(transcript)


if __name__ == "__main__":
    unittest.main()
