import os
import unittest
from unittest.mock import Mock, patch

from banna.api_check import check_gemini, check_openrouter


class ApiCheckTests(unittest.TestCase):
    def test_gemini_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                check_gemini()

    def test_openrouter_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                check_openrouter()

    def test_openrouter_uses_free_router(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "model": "provider/free",
            "choices": [{"message": {"content": "BANNA OPENROUTER OK"}}],
        }
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test"}, clear=True), patch(
            "banna.api_check.requests.post", return_value=response
        ) as post:
            result = check_openrouter()
        self.assertIn("connection OK", result)
        self.assertEqual(post.call_args.kwargs["json"]["model"], "openrouter/free")


if __name__ == "__main__":
    unittest.main()
