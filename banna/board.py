from __future__ import annotations
import math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter

NAVY = (16, 26, 44)
PAPER = (232, 236, 240)
INK = (22, 30, 46)
ORANGE = (255, 107, 0)
BLUE = (48, 76, 106)

def font(size: int, bold: bool = False):
    candidates = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "C:/Windows/Fonts/arialbd.ttf"] if bold else
                  ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                   "C:/Windows/Fonts/arial.ttf"])
    for name in candidates:
        try: return ImageFont.truetype(name, size)
        except OSError: pass
    return ImageFont.load_default()

def make_scene_card(photo_path: Path, scene: dict, index: int, total: int, size=(1920,1080)) -> Path:
    w,h=size
    canvas=Image.new("RGB",size,NAVY)
    d=ImageDraw.Draw(canvas)
    # Subtle technical grid and vignette-like edge framing.
    for x in range(0,w,80): d.line((x,0,x,h),fill=(24,37,56),width=1)
    for y in range(0,h,80): d.line((0,y,w,y),fill=(24,37,56),width=1)
    photo=Image.open(photo_path).convert("RGB")
    photo=ImageOps.fit(photo,(w-180,690),method=Image.Resampling.LANCZOS,centering=(0.5,0.5))
    photo=ImageEnhance.Contrast(photo).enhance(1.08)
    photo=ImageEnhance.Color(photo).enhance(0.68)
    photo=photo.filter(ImageFilter.UnsharpMask(radius=1.2,percent=110,threshold=3))
    x,y=90,95
    canvas.paste(photo,(x,y))
    d.rectangle((x-4,y-4,x+photo.width+4,y+photo.height+4),outline=PAPER,width=5)
    d.rectangle((x-4,y-4,x+photo.width+4,y+photo.height+4),outline=ORANGE,width=2)
    # Evidence-board string and pin.
    d.ellipse((w//2-15,45,w//2+15,75),fill=ORANGE,outline=PAPER,width=3)
    d.line((w//2,75,w//2,95),fill=ORANGE,width=5)
    title=(scene.get("title") or scene.get("narration_cue") or f"EVIDENCE {index:02d}").upper()
    if len(title)>72: title=title[:69]+"..."
    d.text((100,825),title,font=font(42,True),fill=PAPER,stroke_width=1,stroke_fill=NAVY)
    d.line((100,895,760,895),fill=ORANGE,width=7)
    caption=scene.get("caption","")
    if caption:
        d.text((100,925),caption[:125],font=font(25),fill=(194,207,220))
    d.text((w-330,1000),f"CASE FILE  /  {index:02d} OF {total:02d}",font=font(20,True),fill=ORANGE)
    d.rectangle((50,45,w-50,h-45),outline=(77,97,120),width=2)
    return canvas

def render_scene(photo: Path, scene: dict, index: int, total: int, duration: float,
                 output: Path, width: int, height: int, fps: int) -> None:
    output.parent.mkdir(parents=True,exist_ok=True)
    still=output.with_suffix(".png")
    make_scene_card(photo,scene,index,total,(width,height)).save(still)
    frames=max(1,round(duration*fps))
    # Gentle Ken Burns push with very slight horizontal drift, preserving still-photo-only visual rule.
    vf=(f"zoompan=z='min(zoom+0.00045,1.12)':"
        f"x='iw/2-(iw/zoom/2)+on*0.08':y='ih/2-(ih/zoom/2)':"
        f"d=1:s={width}x{height}:fps={fps},format=yuv420p")
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-loop","1","-i",str(still),
         "-t",f"{duration:.3f}","-vf",vf,"-an","-c:v","libx264","-preset","veryfast",
         "-crf","20","-pix_fmt","yuv420p",str(output)]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr[-3000:])
    still.unlink(missing_ok=True)

def concat_and_mux(segments: list[Path], voice: Path, output: Path, duration: float) -> None:
    output.parent.mkdir(parents=True,exist_ok=True)
    listfile=output.parent/"segments.txt"
    listfile.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segments),encoding="utf-8")
    silent=output.parent/"visual_track.mp4"
    p=subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat","-safe","0",
                      "-i",str(listfile),"-c","copy","-an",str(silent)],capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr[-3000:])
    # Loop-safe audio bed: low-volume dark drone, ducked beneath narration.
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(silent),"-i",str(voice),
         "-filter_complex",
         "[1:a]aresample=48000,asplit=2[voice][side];"
         "sine=frequency=55:sample_rate=48000,volume=0.018,aloop=loop=-1:size=48000[drone];"
         "[drone][side]sidechaincompress=threshold=0.025:ratio=8:attack=25:release=500[duck];"
         "[voice][duck]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5[a]",
         "-map","0:v:0","-map","[a]","-t",f"{duration:.3f}","-c:v","libx264","-preset","veryfast",
         "-crf","24","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k","-movflags","+faststart",str(output)]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode: raise RuntimeError(p.stderr[-4000:])
    silent.unlink(missing_ok=True)
    listfile.unlink(missing_ok=True)
