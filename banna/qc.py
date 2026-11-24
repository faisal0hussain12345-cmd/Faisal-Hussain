from __future__ import annotations
import json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from .documentary_engine import _font

def probe_video(path: Path) -> dict:
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=width,height,codec_name","-of","json",str(path)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr[-2000:])
    data=json.loads(p.stdout); video=next((s for s in data.get("streams",[]) if s.get("width")),None)
    if not video: raise ValueError("Output has no video stream")
    return {"duration":float(data["format"]["duration"]),"width":video["width"],"height":video["height"],"codec":video.get("codec_name")}

def extract_contact_sheet(video: Path, output: Path, samples: int=8) -> Path:
    info=probe_video(video); output.parent.mkdir(parents=True,exist_ok=True)
    thumbs=[]
    for i in range(samples):
        t=max(0.0,min(info["duration"]-0.05,info["duration"]*(i+0.5)/samples))
        tmp=output.parent/f".qc_{i}.jpg"
        p=subprocess.run(["ffmpeg","-y","-loglevel","error","-ss",str(t),"-i",str(video),"-frames:v","1","-vf","scale=480:270",str(tmp)],capture_output=True,text=True)
        if p.returncode: raise RuntimeError(p.stderr[-2000:])
        from PIL import Image
        thumbs.append(Image.open(tmp).convert("RGB").copy()); tmp.unlink(missing_ok=True)
    sheet=Image.new("RGB",(960,((len(thumbs)+1)//2)*300),(16,26,44)); d=ImageDraw.Draw(sheet)
    for i,im in enumerate(thumbs):
        x=(i%2)*480; y=(i//2)*300; sheet.paste(im,(x,y))
        d.text((x+10,y+273),f"QC FRAME {i+1}",font=_font(18,mono=True),fill=(255,107,0))
    sheet.save(output,quality=92); return output

def validate_final_video(video: Path, expected_duration: float, tolerance: float=0.35) -> dict:
    info=probe_video(video)
    if info["width"]!=1920 or info["height"]!=1080: raise ValueError(f"Expected 1920x1080, got {info['width']}x{info['height']}")
    if abs(info["duration"]-expected_duration)>tolerance:
        raise ValueError(f"Voiceover/video duration mismatch: {expected_duration:.2f}s vs {info['duration']:.2f}s")
    return info
