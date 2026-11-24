import json
import tempfile
import unittest
from pathlib import Path

from banna.audio import scene_boundaries
from banna.pipeline import load_storyboard
from banna.sound import synthesize_bed
import wave


class SceneTimingTests(unittest.TestCase):
    def test_boundaries_cover_full_voiceover(self):
        result = scene_boundaries(100.0, 4, [(23.0, 24.0), (49.0, 50.0), (74.0, 75.0)])
        self.assertEqual(result[0], 0.0)
        self.assertEqual(result[-1], 100.0)
        self.assertEqual(len(result), 5)
        self.assertTrue(all(b > a for a, b in zip(result, result[1:])))

    def test_single_scene(self):
        self.assertEqual(scene_boundaries(42.0, 1, []), [0.0, 42.0])


class SoundBedTests(unittest.TestCase):
    def test_sound_bed_duration_and_format(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bed.wav"
            synthesize_bed(1.2, [0.0, 0.6], path)
            with wave.open(str(path), "rb") as audio:
                self.assertEqual(audio.getframerate(), 48000)
                self.assertEqual(audio.getnchannels(), 1)
                self.assertAlmostEqual(audio.getnframes() / audio.getframerate(), 1.2, places=2)


class StoryboardTests(unittest.TestCase):
    def test_rejects_empty_scene_list(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "storyboard.json"
            path.write_text(json.dumps({"scenes": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_storyboard(path)

    def test_rejects_scene_without_image_source(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "storyboard.json"
            path.write_text(json.dumps({"scenes": [{"id": "one"}]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_storyboard(path)

    def test_accepts_image_prompt(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "storyboard.json"
            path.write_text(json.dumps({"scenes": [{"id": "one", "image_prompt": "A historical archive photo"}]}), encoding="utf-8")
            self.assertEqual(len(load_storyboard(path)["scenes"]), 1)


if __name__ == "__main__":
    unittest.main()
