import unittest
from banna.pipeline import validate_voiceover_topic


class VoiceoverTopicTests(unittest.TestCase):
    def test_accepts_matching_titanic_narration(self):
        validate_voiceover_topic(
            "The Titanic struck an iceberg. The Carpathia rescued survivors.",
            {"expected_topic": "Titanic", "expected_topic_keywords": ["Titanic", "iceberg", "Carpathia"]},
        )

    def test_rejects_unrelated_manhattan_project_audio(self):
        with self.assertRaisesRegex(ValueError, "topic mismatch"):
            validate_voiceover_topic(
                "The Manhattan Project began during World War Two and developed the atomic bomb.",
                {"expected_topic": "Titanic", "expected_topic_keywords": ["Titanic", "iceberg", "Carpathia"]},
            )

    def test_does_not_block_projects_without_topic_guard(self):
        validate_voiceover_topic("Any narration text.", {})


if __name__ == "__main__":
    unittest.main()
