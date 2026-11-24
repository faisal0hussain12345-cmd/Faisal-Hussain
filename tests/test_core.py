import json
import tempfile
import unittest
from pathlib import Path

from banna.audio import scene_boundaries, probe_audio
from banna.pipeline import load_storyboard
from banna.images import generate_gemini_image
from banna.sound import synthesize_bed
import wave


class AudioProbeTests(unittest.TestCase):
    def test_probe_audio_reads_duration_and_format(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"probe.wav"
            with wave.open(str(path),"wb") as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000)
                wav.writeframes(b"\x00\x00"*8000)
            info=probe_audio(path)
            self.assertAlmostEqual(info["duration"],1.0,delta=0.02)
            self.assertIn("wav",info["format"])


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
            synthesize_bed(1.2, [0.0, 0.6], path, film_ranges=[(0.2,0.8)])
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


class GeminiImageAdapterTests(unittest.TestCase):
    def test_extracts_generated_image_bytes_from_gemini_response(self):
        import base64
        from unittest.mock import Mock, patch
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)/"still.png"
            payload={"candidates":[{"content":{"parts":[{"inlineData":{"mimeType":"image/png","data":base64.b64encode(b"png-test").decode()}}]}}]}
            response=Mock(status_code=200)
            response.json.return_value=payload
            with patch.dict("os.environ",{"GEMINI_API_KEY":"test-key"}), patch("banna.images.requests.post",return_value=response) as post:
                result=generate_gemini_image("archival train station",target,"gemini-2.5-flash-image")
            self.assertEqual(result.read_bytes(),b"png-test")
            self.assertEqual(post.call_args.kwargs["params"],{"key":"test-key"})

    def test_gemini_adapter_requires_api_key(self):
        from unittest.mock import patch
        with patch.dict("os.environ",{},clear=True):
            with self.assertRaises(RuntimeError):
                generate_gemini_image("test",Path("missing.png"),"gemini-2.5-flash-image")


if __name__ == "__main__":
    unittest.main()
