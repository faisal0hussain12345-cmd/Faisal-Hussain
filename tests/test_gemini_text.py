import os
import unittest
from unittest.mock import Mock, patch

from banna.gemini_text import generate_script


class GeminiTextTests(unittest.TestCase):
    def test_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                generate_script("History", "US", "English", 5)

    def test_generates_with_discovered_free_text_model(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Draft [VERIFY SOURCE]"}]}}]
        }
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}, clear=True), patch(
            "banna.gemini_text._gemini_models", return_value=["gemini-test-flash"]
        ), patch("banna.gemini_text.requests.post", return_value=response) as post:
            result = generate_script("A historical topic", "USA", "English", 8)
        self.assertIn("[VERIFY SOURCE]", result)
        self.assertIn("gemini-test-flash:generateContent", post.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
