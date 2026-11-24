from __future__ import annotations
import json
import os
import subprocess
import tempfile
import wave
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from banna.config import Settings
from banna.pipeline import render


class PipelineIntegrationTests(unittest.TestCase):
    def test_full_audio_to_mp4_pipeline_without_external_image_api(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            voice=root/"voice.wav"
            with wave.open(str(voice),"wb") as wav:
                wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(48000)
                wav.writeframes(b"\x00\x00"*(48000*60))
            photos=[]
            for i,color in enumerate(((70,80,90),(90,80,70),(80,90,70))):
                photo=root/f"still_{i}.png"
                Image.new("RGB",(320,180),color).save(photo)
                photos.append(photo)
            storyboard={
                "project":{"surface":"map_board"},
                "scenes":[
                    {"id":"one","title":"OPENING","image":str(photos[0]),"narration_cue":"Opening"},
                    {"id":"two","title":"THE DISCOVERY","image":str(photos[1]),"narration_cue":"Discovery"},
                    {"id":"three","title":"THE TURNING POINT","image":str(photos[2]),"narration_cue":"Turning point","vintage_insert":True}
                ]
            }
            board_file=root/"storyboard.json"
            board_file.write_text(json.dumps(storyboard),encoding="utf-8")
            settings=Settings(width=1920,height=1080,fps=30,output_dir=root/"output",
                              photos_dir=root/"photos",generated_dir=root/"generated",
                              image_model="test",image_provider="gemini",voiceover=voice)

            def fake_board(_photos,_scenes,durations,output,width,height,fps,quality=20,workers=1,surface="map_board"):
                duration=sum(durations)
                cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","lavfi","-i",
                     f"color=c=0x102030:s={width}x{height}:r={fps}:d={duration:.3f}",
                     "-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",str(output)]
                subprocess.run(cmd,check=True,capture_output=True)
                return output

            def fake_vintage(_title,duration,output,fps,size):
                cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","lavfi","-i",
                     f"color=c=0xff6b00:s={size[0]}x{size[1]}:r={fps}:d={duration:.3f}",
                     "-an","-c:v","libx264","-preset","ultrafast","-pix_fmt","yuv420p",str(output)]
                subprocess.run(cmd,check=True,capture_output=True)
                return output

            previous=Path.cwd()
            os.chdir(root)
            try:
                with patch("banna.pipeline.Settings.from_env",return_value=settings), \
                     patch("banna.pipeline.find_voiceover",return_value=voice), \
                     patch("banna.pipeline.transcribe_word_timestamps",return_value=([],"unavailable")), \
                     patch("banna.pipeline.render_continuous_board",side_effect=fake_board), \
                     patch("banna.pipeline.render_vintage_clip",side_effect=fake_vintage):
                    result=render(board_file)
                self.assertTrue(result.is_file())
                self.assertTrue((root/"output"/"BANNA_QC_contact_sheet.jpg").is_file())
                self.assertTrue((root/"output"/"BANNA_QC_report.json").is_file())
                report=json.loads((root/"output"/"BANNA_QC_report.json").read_text(encoding="utf-8"))
                self.assertEqual(report["resolution"],"1920x1080")
                self.assertAlmostEqual(report["duration_seconds"],60.0,delta=0.2)
                self.assertEqual(report["scene_count"],3)
            finally:
                os.chdir(previous)


if __name__=="__main__":
    unittest.main()
