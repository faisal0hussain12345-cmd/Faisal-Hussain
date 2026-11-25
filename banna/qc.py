from __future__ import annotations
import json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from .documentary_engine import _font

def probe_video(path: Path) -> dict:
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,codec_name,width,height,duration,r_frame_rate,sample_rate,channels","-of","json",str(path)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr[-2000:])
    data=json.loads(p.stdout)
    streams=data.get("streams",[])
    video=next((s for s in streams if s.get("codec_type")=="video"),None)
    audio=next((s for s in streams if s.get("codec_type")=="audio"),None)
    if not video: raise ValueError("Output has no video stream")
    fps_text=str(video.get("r_frame_rate","0/1"))
    try:
        numerator,denominator=map(int,fps_text.split("/"))
        fps=numerator/denominator if denominator else 0.0
    except Exception:
        fps=0.0
    return {
        "duration":float(data["format"]["duration"]),
        "width":video["width"],"height":video["height"],"codec":video.get("codec_name"),
        "fps":fps,"audio_codec":audio.get("codec_name") if audio else None,
        "audio_duration":float(audio.get("duration",data["format"]["duration"])) if audio else None,
        "audio_channels":audio.get("channels") if audio else None,
    }

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


def extract_photo_contact_sheet(photos: list[Path], scenes: list[dict], output: Path,
                                columns: int = 4) -> Path:
    """Create a review sheet proving each narration beat has its own source photograph."""
    output.parent.mkdir(parents=True, exist_ok=True)
    cell_w, cell_h, label_h = 480, 300, 66
    rows = (len(photos) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), (16, 26, 44))
    draw = ImageDraw.Draw(sheet)
    for i, (photo_path, scene) in enumerate(zip(photos, scenes)):
        image = Image.open(photo_path).convert("RGB")
        image = ImageOps.fit(image, (cell_w - 16, cell_h - 16), method=Image.Resampling.LANCZOS)
        x = (i % columns) * cell_w + 8
        y = (i // columns) * (cell_h + label_h) + 8
        sheet.paste(image, (x, y))
        title = str(scene.get("title") or scene.get("id") or f"BEAT {i+1:02d}")[:52]
        draw.text((x + 4, y + cell_h + 4), f"{i+1:02d}  {title}", font=_font(18, mono=True), fill=(245, 241, 230))
    sheet.save(output, quality=92)
    return output

def validate_final_video(video: Path, expected_duration: float, tolerance: float=0.35) -> dict:
    info=probe_video(video)
    if info["width"]!=1920 or info["height"]!=1080: raise ValueError(f"Expected 1920x1080, got {info['width']}x{info['height']}")
    if info["codec"]!="h264": raise ValueError(f"Expected H.264 video, got {info['codec']}")
    if abs(info["fps"]-30.0)>0.05: raise ValueError(f"Expected 30 fps, got {info['fps']:.3f}")
    if abs(info["duration"]-expected_duration)>tolerance:
        raise ValueError(f"Voiceover/video duration mismatch: {expected_duration:.2f}s vs {info['duration']:.2f}s")
    if not info["audio_codec"]: raise ValueError("Output is missing the narration/audio stream")
    if info["audio_codec"]!="aac": raise ValueError(f"Expected AAC audio, got {info['audio_codec']}")
    if info["audio_duration"] is not None and abs(info["audio_duration"]-expected_duration)>tolerance:
        raise ValueError(f"Voiceover/audio duration mismatch: {expected_duration:.2f}s vs {info['audio_duration']:.2f}s")
    return info
