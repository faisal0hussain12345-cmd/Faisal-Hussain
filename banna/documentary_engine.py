from __future__ import annotations

"""Single-world documentary board renderer inspired by the bundled skill.

The whole evidence board is rendered as one large world surface. The camera
moves continuously over that surface; there are no per-scene stock-video cuts.
All source visuals are still images. Motion is generated from camera transforms,
draw-on annotations, tags, stamps and transitions.
"""
import math
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

NAVY = (16, 26, 44)
PAPER = (232, 236, 240)
INK = (22, 30, 46)
ORANGE = (255, 107, 0)
STEEL = (62, 84, 110)
WORLD_W = 3840


def _font(size: int, bold: bool = False, mono: bool = False):
    names = []
    if mono:
        names += ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]
    elif bold:
        names += ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    else:
        names += ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    names += ["C:/Windows/Fonts/consola.ttf" if mono else "C:/Windows/Fonts/arial.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def card_anchor(card: dict[str, Any], u: float, v: float) -> tuple[float, float]:
    """Exact rotated point on a card; u/v range from -0.5 to +0.5."""
    if not (-0.5 <= u <= 0.5 and -0.5 <= v <= 0.5):
        raise ValueError("Card anchor u and v must be in [-0.5, 0.5].")
    angle = math.radians(float(card.get("rotation", 0)))
    x = float(card["x"]) + u * float(card["w"])
    y = float(card["y"]) + v * float(card["h"])
    dx, dy = x - float(card["x"]), y - float(card["y"])
    return (float(card["x"]) + dx * math.cos(angle) - dy * math.sin(angle),
            float(card["y"]) + dx * math.sin(angle) + dy * math.cos(angle))


def _fit_photo(path: Path, size: tuple[int, int]) -> Image.Image:
    im = Image.open(path).convert("RGB")
    im = ImageOps.fit(im, size, method=Image.Resampling.LANCZOS)
    im = ImageEnhance.Color(im).enhance(0.62)
    im = ImageEnhance.Contrast(im).enhance(1.12)
    return im.filter(ImageFilter.UnsharpMask(radius=1.1, percent=105, threshold=3))


def _card_layer(photo: Path, scene: dict, number: int, total: int, card_w: int = 760) -> Image.Image:
    ratio = 16 / 9
    photo_h = int(card_w / ratio)
    pad = 34
    label_h = 150
    layer = Image.new("RGBA", (card_w + pad * 2, photo_h + label_h + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((pad + 12, pad + 16, pad + card_w + 12, pad + photo_h + label_h + 16),
                         radius=8, fill=(0, 0, 0, 145))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    layer.alpha_composite(shadow)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((pad, pad, pad + card_w, pad + photo_h + label_h),
                        radius=5, fill=PAPER, outline=(255, 255, 255), width=5)
    im = _fit_photo(photo, (card_w - 28, photo_h - 28))
    layer.paste(im, (pad + 14, pad + 14))
    d = ImageDraw.Draw(layer)
    title = str(scene.get("title") or scene.get("narration_cue") or f"EVIDENCE {number:02d}")
    title_text=title[:68]
    title_font=_font(32,True)
    title_pos=(pad+18,pad+photo_h+20)
    title_box=d.textbbox(title_pos,title_text,font=title_font)
    d.text(title_pos,title_text,font=title_font,fill=INK)
    caption = str(scene.get("caption") or f"CASE FILE / {number:02d} OF {total:02d}")
    d.text((pad + 18, pad + photo_h + 78), caption[:90], font=_font(20, mono=True), fill=STEEL)
    # Pixel-anchored underline hugs the exact rendered title baseline.
    d.line((title_box[0],title_box[3]+9,title_box[2],title_box[3]+9),fill=ORANGE,width=7)
    # Paper pin is fixed to the top-center of the card body.
    d.ellipse((layer.width // 2 - 15, 8, layer.width // 2 + 15, 38),
              fill=ORANGE, outline=PAPER, width=4)
    return layer


def _build_world(photos: list[Path], scenes: list[dict], surface: str="map_board") -> tuple[Image.Image, list[dict]]:
    palette={
        "map_board":((16,26,44),(23,37,57),(158,176,196)),
        "paper_press":((232,236,240),(210,218,226),(45,55,68)),
        "scrapbook_dossier":((29,30,36),(45,46,54),(205,205,198)),
        "chalk_case_board":((17,39,32),(28,58,48),(205,220,210)),
        "digital_coda":((5,8,13),(16,24,38),(150,178,210))
    }
    if surface not in palette: raise ValueError(f"Unknown documentary surface: {surface}")
    bg,grid,header=palette[surface]
    world_h = max(2160, 500 + ((len(scenes) + 2) // 3) * 900)
    world = Image.new("RGB", (WORLD_W, world_h), bg)
    d = ImageDraw.Draw(world)
    for x in range(0, WORLD_W, 100):
        d.line((x, 0, x, world_h), fill=grid, width=1)
    for y in range(0, world_h, 100):
        d.line((0, y, WORLD_W, y), fill=grid, width=1)
    d.text((150, 90), "DOCUMENTARY / EVIDENCE ARCHIVE", font=_font(38, mono=True), fill=header)
    d.line((150, 155, WORLD_W - 150, 155), fill=ORANGE, width=4)
    cards = []
    cols = 3
    cell_w, cell_h = 1120, 900
    for i, (photo, scene) in enumerate(zip(photos, scenes)):
        row, col = divmod(i, cols)
        cx = 620 + col * cell_w
        cy = 570 + row * cell_h
        rotation = [-2.2, 1.4, -1.0, 2.0, -1.6, 1.0][i % 6]
        card = {"x": cx, "y": cy, "w": 828, "h": 640, "rotation": rotation,
                "scene": scene, "index": i}
        layer = _card_layer(photo, scene, i + 1, len(photos))
        rotated = layer.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
        world.paste(rotated, (int(cx - rotated.width / 2), int(cy - rotated.height / 2)), rotated)
        cards.append(card)
    # Connect exact card-edge pins; row-wrap strings travel only through the empty gutter.
    for i in range(len(cards)-1):
        current,next_card=cards[i],cards[i+1]
        if i//cols==(i+1)//cols:
            a=card_anchor(current,0.48,0.0)
            b=card_anchor(next_card,-0.48,0.0)
            d.line((a,b),fill=ORANGE,width=5)
        else:
            a=card_anchor(current,0.0,0.46)
            b=card_anchor(next_card,0.0,-0.46)
            gutter_y=(a[1]+b[1])/2
            d.line((a,(a[0],gutter_y),(b[0],gutter_y),b),fill=ORANGE,width=5)
        for px,py in (a,b):
            d.ellipse((px-9,py-9,px+9,py+9),fill=ORANGE,outline=PAPER,width=2)
    return world, cards


def _camera_center(index: int, total: int) -> tuple[float, float]:
    cols = 3
    row, col = divmod(index, cols)
    return (620 + col * 1120, 570 + row * 900)


def _draw_wobble(draw: ImageDraw.ImageDraw, box, color=(255,107,0,245), width=5):
    x0,y0,x1,y1=box; cx=(x0+x1)/2; cy=(y0+y1)/2
    rx=max(8,(x1-x0)/2); ry=max(8,(y1-y0)/2); pts=[]
    for i in range(97):
        a=2*math.pi*i/96
        wobble=1+0.018*math.sin(7*a)+0.012*math.sin(13*a)
        pts.append((cx+rx*wobble*math.cos(a),cy+ry*wobble*math.sin(a)))
    draw.line(pts,fill=color,width=width)


def _draw_overlay(frame: Image.Image, scene: dict, elapsed: float, scene_duration: float,
                  index: int, total: int) -> None:
    d=ImageDraw.Draw(frame,"RGBA"); w,h=frame.size
    full_label=str(scene.get("board_label") or scene.get("title") or f"CASE FILE {index+1:02d}").upper()[:40]
    # Skill guide typewriter speed: 22 characters per second.
    shown=max(0,min(len(full_label),int(elapsed*22)))
    label=full_label[:shown]
    f=_font(30,mono=True); pos=(96,82)
    d.rounded_rectangle((72,64,min(w-72,900),158),radius=8,fill=(7,12,20,205),
                        outline=(255,107,0,230),width=2)
    d.text(pos,label,font=f,fill=(245,241,230,255))
    bbox=d.textbbox(pos,label or " ",font=f)
    underline_target=max(0,bbox[2]-bbox[0])
    underline_w=int(underline_target*min(1.0,elapsed/0.65))
    d.line((bbox[0],166,bbox[0]+underline_w,166),fill=ORANGE+(255,),width=5)
    # Draw-on wobble circle frames the exact typed label, not a guessed screen point.
    if elapsed>0.8 and label:
        _draw_wobble(d,(bbox[0]-18,69,bbox[2]+18,125),ORANGE+(240,),5)
    # Typed evidence tags.
    tags=scene.get("tags",[])
    for i,tag in enumerate(tags[:3]):
        if elapsed>1.0+i*0.25:
            y=190+i*54; text=str(tag)[:30]
            d.rounded_rectangle((76,y,500,y+40),radius=4,fill=(8,14,22,220),outline=ORANGE+(230,),width=2)
            d.text((92,y+7),text,font=_font(21,mono=True),fill=PAPER+(255,))
    # Optional year card with serif typography and animated orange rules.
    if scene.get("year") and elapsed>0.35:
        year=str(scene["year"])[:12]
        card=(w//2-250,h//2-130,w//2+250,h//2+130)
        d.rounded_rectangle(card,radius=6,fill=(8,14,22,235),outline=ORANGE+(255,),width=3)
        d.line((card[0]+35,card[1]+48,card[2]-35,card[1]+48),fill=ORANGE+(255,),width=4)
        d.text((w//2-115,h//2-48),year,font=_font(76,True),fill=PAPER+(255,))
        d.line((card[0]+35,card[3]-48,card[2]-35,card[3]-48),fill=ORANGE+(255,),width=4)
    # Optional dossier stamp: slam-in with overshoot and a brief shake.
    if scene.get("stamp") and elapsed>1.0:
        stamp=str(scene["stamp"]).upper()[:22]
        sf=_font(42,True,mono=True); bb=sf.getbbox(stamp)
        sw,sh=bb[2]-bb[0]+44,bb[3]-bb[1]+34
        stamp_layer=Image.new("RGBA",(sw+30,sh+30),(0,0,0,0))
        sd=ImageDraw.Draw(stamp_layer)
        sd.rectangle((12,12,sw+12,sh+12),outline=ORANGE+(255,),width=5)
        sd.text((34,25),stamp,font=sf,fill=ORANGE+(255,))
        stamp_layer=stamp_layer.rotate(7,resample=Image.Resampling.BICUBIC,expand=True)
        sx=w-stamp_layer.width-110+int(math.sin(elapsed*34)*5)
        rgba=frame.convert("RGBA")
        rgba.alpha_composite(stamp_layer,(sx,230))
        frame.paste(rgba.convert("RGB"))
    if scene.get("thesis") and elapsed>scene_duration*0.55:
        thesis=str(scene["thesis"])[:55]
        d.rounded_rectangle((w//2-500,h-210,w//2+500,h-100),radius=5,fill=(8,14,22,230),outline=ORANGE+(240,),width=2)
        d.text((w//2-465,h-178),thesis,font=_font(28,True),fill=PAPER+(255,))
    # Finale: return all cards to view and glitch the closing title.
    if index==total-1 and elapsed>scene_duration-1.5:
        title="THE EVIDENCE CONNECTS"; f2=_font(42,True); x=w-760; y=h-110
        d.text((x+4,y),title,font=f2,fill=(255,107,0,120))
        d.text((x-3,y+2),title,font=f2,fill=(220,235,245,255))
        d.text((x,y),title,font=f2,fill=ORANGE+(255,))


def _render_chunk(photos: list[Path], scenes: list[dict], durations: list[float],
                  start_frame: int, end_frame: int, output: Path,
                  width: int, height: int, fps: int, quality: int, surface: str) -> str:
    world, _ = _build_world(photos, scenes, surface)
    starts=[]; cursor=0.0
    for duration in durations:
        starts.append(cursor); cursor += duration
    total_duration=cursor
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","rawvideo",
         "-pix_fmt","rgb24","-s",f"{width}x{height}","-r",str(fps),"-i","-",
         "-an","-c:v","libx264","-preset","veryfast","-crf",str(quality),
         "-pix_fmt","yuv420p","-g",str(fps*2),"-keyint_min",str(fps*2),
         "-sc_threshold","0",str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for fi in range(start_frame,end_frame):
            t=min(total_duration-1/fps,fi/fps)
            idx=max(i for i,start in enumerate(starts) if start<=t)
            local=t-starts[idx]
            cx,cy=_camera_center(idx,len(scenes))
            if idx>0 and local<1.2:
                px,py=_camera_center(idx-1,len(scenes))
                q=min(1.0,local/1.2); q=q*q*(3-2*q)
                cx,cy=px+(cx-px)*q,py+(cy-py)*q
            progress=min(1.0,local/max(2.0,durations[idx]))
            zoom=1.85+0.08*progress
            if idx==len(scenes)-1 and local>max(0.0,durations[idx]-2.5):
                reveal=min(1.0,(local-max(0.0,durations[idx]-2.5))/2.5)
                reveal=reveal*reveal*(3-2*reveal)
                cx=cx+(WORLD_W/2-cx)*reveal
                cy=cy+(world.size[1]/2-cy)*reveal
                zoom=zoom+(1.0-zoom)*reveal
            cx+=math.sin(local*0.19)*16
            cy+=math.cos(local*0.15)*12
            world_w,world_h=world.size
            crop_w,crop_h=int(world_w/zoom),int(world_h/zoom)
            left=max(0,min(world_w-crop_w,int(cx-crop_w/2)))
            top=max(0,min(world_h-crop_h,int(cy-crop_h/2)))
            frame=world.crop((left,top,left+crop_w,top+crop_h)).resize((width,height),Image.Resampling.LANCZOS)
            _draw_overlay(frame,scenes[idx],local,durations[idx],idx,len(scenes))
            proc.stdin.write(frame.tobytes())
    except BrokenPipeError as exc:
        raise RuntimeError("FFmpeg stopped while rendering the continuous board.") from exc
    finally:
        proc.stdin.close()
    stderr=proc.stderr.read().decode("utf-8","replace") if proc.stderr else ""
    if proc.stderr: proc.stderr.close()
    code=proc.wait()
    if code: raise RuntimeError(f"FFmpeg board render failed: {stderr[-4000:]}")
    return str(output)


def render_continuous_board(photos: list[Path], scenes: list[dict], durations: list[float],
                            output: Path, width: int=1920, height: int=1080,
                            fps: int=30, quality: int=22, workers: int=1, surface: str="map_board") -> Path:
    if not photos or len(photos)!=len(scenes) or len(scenes)!=len(durations):
        raise ValueError("Photos, scenes and durations must have the same non-zero length.")
    if any(d<=0 for d in durations):
        raise ValueError("Every scene duration must be positive.")
    if workers<1: raise ValueError("workers must be at least one.")
    output.parent.mkdir(parents=True,exist_ok=True)
    frame_count=int(math.ceil(sum(durations)*fps))
    workers=min(workers,frame_count)
    if workers==1:
        _render_chunk(photos,scenes,durations,0,frame_count,output,width,height,fps,quality,surface)
        return output
    from concurrent.futures import ProcessPoolExecutor
    import tempfile
    with tempfile.TemporaryDirectory(prefix="banna_chunks_",dir=str(output.parent)) as temp:
        root=Path(temp); jobs=[]
        for i in range(workers):
            start=frame_count*i//workers
            end=frame_count*(i+1)//workers
            target=root/f"chunk_{i:03d}.mp4"
            jobs.append((start,end,target))
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures=[pool.submit(_render_chunk,photos,scenes,durations,start,end,target,
                                 width,height,fps,quality,surface) for start,end,target in jobs]
            for future in futures: future.result()
        listing=root/"concat.txt"
        listing.write_text("".join(f"file '{target.resolve().as_posix()}'\n" for _,_,target in jobs),encoding="utf-8")
        cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","concat","-safe","0",
             "-i",str(listing),"-c","copy","-an",str(output)]
        result=subprocess.run(cmd,capture_output=True,text=True)
        if result.returncode: raise RuntimeError(f"Parallel render assembly failed: {result.stderr[-4000:]}")
    return output
