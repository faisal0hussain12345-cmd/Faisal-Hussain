import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from banna.openrouter_review import review_script, review_file


class OpenRouterReviewTests(unittest.TestCase):
    def test_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                review_script("A script")

    def test_rejects_paid_model_id(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test"}):
            with self.assertRaises(ValueError):
                review_script("A script", "openai/gpt-4o")

    def test_uses_free_router(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "model": "provider/example-free",
            "choices": [{"message": {"content": "Review output"}}],
        }
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test"}, clear=True), patch(
            "banna.openrouter_review.requests.post", return_value=response
        ) as post:
            result, model = review_script("Narration")
        self.assertEqual(result, "Review output")
        self.assertEqual(model, "provider/example-free")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "openrouter/free")

    def test_saves_review(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "model": "provider/free",
            "choices": [{"message": {"content": "Review output"}}],
        }
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            os.environ, {"OPENROUTER_API_KEY": "test"}
        ), patch("banna.openrouter_review.requests.post", return_value=response):
            src = Path(temp) / "script.txt"
            dst = Path(temp) / "review.md"
            src.write_text("Narration", encoding="utf-8")
            review_file(src, dst)
            self.assertIn("Review output", dst.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
