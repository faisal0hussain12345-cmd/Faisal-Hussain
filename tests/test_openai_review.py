import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from banna.openai_review import review_script, review_file


class OpenAIReviewTests(unittest.TestCase):
    def test_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                review_script("A documentary script.")

    def test_responses_api_output_and_model(self):
        response = Mock(status_code=200)
        response.json.return_value = {"output_text": "Review text"}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-key"}, clear=True), patch(
            "banna.openai_review.requests.post", return_value=response
        ) as post:
            result = review_script("Narration", model="test-model")
        self.assertEqual(result, "Review text")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "test-model")
        self.assertEqual(post.call_args.kwargs["headers"]["Authorization"], "Bearer unit-test-key")

    def test_rejects_empty_script(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "unit-test-key"}):
            with self.assertRaises(ValueError):
                review_script(" ")

    def test_writes_review_file(self):
        response = Mock(status_code=200)
        response.json.return_value = {"output_text": "Review text"}
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            os.environ, {"OPENAI_API_KEY": "unit-test-key"}
        ), patch("banna.openai_review.requests.post", return_value=response):
            source = Path(temp) / "script.txt"
            target = Path(temp) / "out" / "review.md"
            source.write_text("Narration", encoding="utf-8")
            self.assertEqual(review_file(source, target), target)
            self.assertEqual(target.read_text(encoding="utf-8").strip(), "Review text")


if __name__ == "__main__":
    unittest.main()
