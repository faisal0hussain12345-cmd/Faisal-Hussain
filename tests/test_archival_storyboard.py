import json
import unittest
from pathlib import Path

from banna.free_photos import _query_candidates, _query_for_scene
from banna.timing import align_scenes_to_words


class ArchivalStoryboardTests(unittest.TestCase):
    def test_manhattan_storyboard_requires_distinct_photo_beats(self):
        data = json.loads(Path("storyboard.manhattan.json").read_text(encoding="utf-8"))
        scenes = data["scenes"]
        self.assertGreaterEqual(len(scenes), 24)
        self.assertGreaterEqual(data["project"]["minimum_unique_archival_photos"], 24)
        self.assertEqual(len({scene["photo_search"] for scene in scenes}), len(scenes))
        self.assertTrue(all("graphic_type" not in scene for scene in scenes))

    def test_photo_search_never_injects_titanic_as_default(self):
        queries = _query_candidates({
            "title": "Oak Ridge Calutron Operators",
            "caption": "Women operating uranium enrichment equipment",
            "photo_search": "Y-12 calutron operators Oak Ridge 1944",
        })
        self.assertTrue(queries)
        self.assertTrue(all("titanic" not in query.casefold() for query in queries))
        self.assertNotIn("RMS Titanic 1912", _query_for_scene({}))

    def test_word_alignment_never_creates_flash_length_scenes(self):
        words = [
            {"word": word, "start": i * 2.0, "end": i * 2.0 + 1.0}
            for i, word in enumerate("the secret project began in december nineteen thirty eight and changed history".split())
        ]
        scenes = [{"id": f"scene-{i}"} for i in range(5)]
        bounds = [0.0, 10.0, 20.0, 30.0, 40.0, 50.0]
        result = align_scenes_to_words(words, scenes, 50.0, bounds)
        self.assertEqual(len(result), 6)
        self.assertTrue(all((b - a) >= 8.0 for a, b in zip(result, result[1:])))


if __name__ == "__main__":
    unittest.main()
