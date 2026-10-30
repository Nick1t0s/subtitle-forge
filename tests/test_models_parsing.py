import json
from pathlib import Path
import tempfile
import unittest

from subtitle_forge.models import Segment, Transcript, Word
from subtitle_forge.parsing import load_transcript, save_transcript


class ModelTests(unittest.TestCase):
    def test_models_are_immutable_and_normalize_collections(self):
        word = Word(0, 0.5, "hi")
        segment = Segment(0, 1, "hi", [word])
        transcript = Transcript([segment], "en")
        self.assertEqual(transcript.segments, (segment,))
        self.assertEqual(segment.words, (word,))
        with self.assertRaises((AttributeError, TypeError)):
            word.text = "changed"

    def test_invalid_intervals_are_rejected(self):
        for start, end in ((-1, 1), (1, 1), (2, 1), (0, float("inf")), (float("nan"), 1)):
            with self.subTest(start=start, end=end), self.assertRaises((ValueError, TypeError)):
                Word(start, end, "x")
        with self.assertRaises((ValueError, TypeError)):
            Segment(0, 0, "empty")

    def test_words_must_be_ordered_without_overlap(self):
        with self.assertRaises(ValueError):
            Segment(0, 2, "x y", (Word(0, 1, "x"), Word(0.9, 1.5, "y")))


class ParsingTests(unittest.TestCase):
    def test_json_round_trip_and_word_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "transcript.json"
            path.write_text(json.dumps({
                "language": "en",
                "segments": [{"start": 0, "end": 2, "text": "one two", "words": [
                    {"start": 0, "end": 0.8, "word": "one"},
                    {"start": 1, "end": 2, "text": "two"},
                ]}],
            }), encoding="utf-8")
            loaded = load_transcript(path)
            self.assertEqual([w.text for w in loaded.segments[0].words], ["one", "two"])
            saved = Path(directory) / "saved.json"
            save_transcript(loaded, saved)
            self.assertEqual(load_transcript(saved), loaded)

    def test_srt_cues_do_not_get_fake_word_timestamps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "captions.srt"
            path.write_text("1\n00:00:01,200 --> 00:00:02,450\nHello there\n", encoding="utf-8")
            transcript = load_transcript(path)
            self.assertEqual(len(transcript.segments), 1)
            self.assertEqual(transcript.segments[0].text, "Hello there")
            self.assertEqual(transcript.segments[0].start, 1.2)
            self.assertEqual(transcript.segments[0].end, 2.45)
            self.assertEqual(transcript.segments[0].words, ())

    def test_example_is_a_loadable_transcript(self):
        transcript = load_transcript(Path(__file__).parents[1] / "examples" / "transcript.json")
        self.assertEqual(transcript.language, "ru")
        self.assertEqual(len(transcript.segments), 2)
        self.assertEqual(len(transcript.segments[0].words), 2)


if __name__ == "__main__":
    unittest.main()
