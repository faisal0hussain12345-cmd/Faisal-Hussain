import os
import unittest
from unittest.mock import Mock, patch

from banna.api_check import _extract_openrouter_text, _gemini_models, check_gemini, check_openrouter


class ApiCheckTests(unittest.TestCase):
    def test_gemini_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                check_gemini()

    def test_gemini_discovers_models_and_skips_old_25_model(self):
        response = Mock(status_code=200)
        response.json.return_value = {"models": [
            {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
        ]}
        with patch("banna.api_check.requests.get", return_value=response):
            self.assertEqual(_gemini_models("test")[0], "gemini-3.5-flash-lite")

    def test_openrouter_requires_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                check_openrouter()

    def test_extracts_text_content(self):
        self.assertEqual(
            _extract_openrouter_text({"choices": [{"message": {"content": [{"type": "text", "text": "Hello"}]}}]}),
            "Hello",
        )

    def test_extracts_responses_api_style_text(self):
        self.assertEqual(
            _extract_openrouter_text({"output": [{"type": "message", "content": [{"type": "output_text", "text": "Hello"}]}]}),
            "Hello",
        )

    def test_openrouter_uses_free_router_and_more_output_tokens(self):
        response = Mock(status_code=200)
        response.json.return_value = {
            "model": "provider/free",
            "choices": [{"message": {"content": "BANNA OPENROUTER OK"}, "finish_reason": "stop"}],
        }
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test"}, clear=True), patch(
            "banna.api_check.requests.post", return_value=response
        ) as post:
            result = check_openrouter()
        self.assertIn("connection OK", result)
        self.assertEqual(post.call_args.kwargs["json"]["model"], "openrouter/free")
        self.assertEqual(post.call_args.kwargs["json"]["max_tokens"], 512)


if __name__ == "__main__":
    unittest.main()
