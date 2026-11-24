from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
from .documentary_engine import NAVY, ORANGE, _font

CYAN=(172,208,226)
INK=(26,38,52)
PALE=(210,228,238)

def vintage_frame(t: float, duration: float, title: str, size=(1920,1080)) -> Image.Image:
    """Cyanotype silent-film insert: schematic route, side-view action, intertitle and iris wipes."""
    w,h=size
    # Animate on twos (12 fps), retaining full-rate motion for the impact flash.
    impact_at=duration*0.62
    tq=t if abs(t-impact_at)<0.16 else math.floor(t*12)/12
    phase=tq/max(duration,0.001)
    im=Image.new("RGB",size,CYAN)
    d=ImageDraw.Draw(im)
    if phase<0.28:
        # Schematic map with a dashed orange route and a target circle.
        for x in range(80,w,150): d.line((x,100,x-45,h-100),fill=(130,170,195),width=2)
        for y in range(130,h,115): d.line((70,y,w-70,y+25),fill=(130,170,195),width=2)
        route=[(180,720),(440,590),(760,640),(1040,430),(1370,500),(1690,300)]
        for i in range(len(route)-1):
            a,b=route[i],route[i+1]
            for k in range(0,12,2):
                p0=(a[0]+(b[0]-a[0])*k/12,a[1]+(b[1]-a[1])*k/12)
                p1=(a[0]+(b[0]-a[0])*(k+1)/12,a[1]+(b[1]-a[1])*(k+1)/12)
                d.line((p0,p1),fill=ORANGE,width=8)
        for i,p in enumerate(route):
            d.ellipse((p[0]-13,p[1]-13,p[0]+13,p[1]+13),fill=ORANGE,outline=INK,width=3)
            if i in (0,3,5): d.text((p[0]+22,p[1]-25),f"POINT {i+1}",font=_font(22,mono=True),fill=INK)
        pulse=1+0.08*math.sin(tq*8)
        cx,cy=route[3]; rx,ry=115*pulse,82*pulse
        d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),outline=ORANGE,width=6)
        d.text((100,65),"FIELD MAP / ROUTE RECONSTRUCTION",font=_font(34,mono=True),fill=INK)
    elif phase<0.75:
        # Side-view, non-graphic action sequence with flat silhouettes.
        d.rectangle((0,0,w,620),fill=(188,216,230))
        for i,x in enumerate(range(-80,w+200,260)):
            top=180+(i%3)*65
            d.rectangle((x,top,x+220,770),fill=(105,145,170),outline=INK,width=4)
            for yy in range(top+55,680,120):
                for xx in range(x+30,x+190,75):
                    d.rectangle((xx,yy,xx+36,yy+58),fill=(48,76,100),outline=INK,width=2)
        d.rectangle((0,760,w,840),fill=(105,140,160))
        d.rectangle((0,840,w,h),fill=(130,166,184))
        for x in range(0,w,170): d.line((x,955,x+75,955),fill=PALE,width=7)
        local=(phase-0.28)/0.47
        car_x=int(w+450-local*(w+950))
        car_y=820
        d.polygon([(car_x-230,car_y-65),(car_x+170,car_y-65),(car_x+240,car_y-5),(car_x+260,car_y+30),(car_x-270,car_y+30)],fill=INK)
        d.polygon([(car_x-90,car_y-65),(car_x+110,car_y-65),(car_x+55,car_y-135),(car_x-40,car_y-135)],fill=(70,105,130))
        for wx in (car_x-150,car_x+155):
            d.ellipse((wx-48,car_y,wx+48,car_y+96),fill=(12,20,30),outline=PALE,width=4)
            d.ellipse((wx-22,car_y+27,wx+22,car_y+71),fill=(120,155,176))
        for i in range(8):
            x=150+i*230+int(local*70)
            bob=math.sin(tq*5+i)*5
            d.ellipse((x-23,650+bob,x+23,700+bob),fill=INK)
            d.polygon([(x-28,700+bob),(x+28,700+bob),(x+62,850),(x-62,850)],fill=INK)
        d.text((95,70),"RECONSTRUCTED SEQUENCE",font=_font(32,mono=True),fill=INK)
        if abs(t-impact_at)<0.16:
            flash=Image.new("RGB",size,(245,248,250))
            im=Image.blend(im,flash,0.82)
            d=ImageDraw.Draw(im)
            d.text((w//2-130,h//2-45),"IMPACT",font=_font(58,True),fill=ORANGE)
    else:
        # Silent-film intertitle, double border and orange corner pins.
        im=Image.new("RGB",size,(10,14,20)); d=ImageDraw.Draw(im)
        d.rectangle((150,120,w-150,h-120),outline=PALE,width=5)
        d.rectangle((172,142,w-172,h-142),outline=(105,145,170),width=2)
        for x,y in ((172,142),(w-172,142),(172,h-142),(w-172,h-142)):
            d.ellipse((x-13,y-13,x+13,y+13),fill=ORANGE)
        lines=[title[:58],"THE EVIDENCE CHANGES EVERYTHING"]
        for text,y,font_size in ((lines[0],430,58),(lines[1],560,32)):
            f=_font(font_size,True); box=d.textbbox((0,0),text,font=f)
            d.text(((w-(box[2]-box[0]))/2,y),text,font=f,fill=CYAN)
        d.line((w//2-180,520,w//2+180,520),fill=ORANGE,width=5)
    # Film grain, occasional scratch, flicker and gate weave.
    import random
    rng=random.Random(int(t*12))
    for _ in range(180):
        x=rng.randrange(w); y=rng.randrange(h)
        col=(rng.randrange(100,180),rng.randrange(140,210),rng.randrange(160,230))
        d.point((x,y),fill=col)
    if rng.random()<0.18:
        x=rng.randrange(w); d.line((x,0,x+rng.randrange(-12,13),h),fill=PALE,width=1)
    if rng.random()<0.35:
        im=ImageChops.offset(im,rng.choice((-2,-1,1,2)),rng.choice((-2,-1,1,2)))
    # Iris in/out, matching the bundled silent-film style.
    iris_in=min(1.0,max(0.0,t/0.45))
    iris_out=min(1.0,max(0.0,(duration-t)/0.45))
    radius=int(math.hypot(w/2,h/2)*min(iris_in,iris_out))
    mask=Image.new("L",size,0); md=ImageDraw.Draw(mask)
    md.ellipse((w/2-radius,h/2-radius,w/2+radius,h/2+radius),fill=255)
    black=Image.new("RGB",size,(5,8,13))
    return Image.composite(im,black,mask)

def render_vintage_clip(title: str, duration: float, output, fps: int=30, size=(1920,1080)):
    """Render the vintage illustrated sequence to a temporary silent video."""
    import subprocess
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{size[0]}x{size[1]}","-r",str(fps),"-i","-","-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for fi in range(max(1,round(duration*fps))):
            proc.stdin.write(vintage_frame(fi/fps,duration,title,size).tobytes())
    except BrokenPipeError as exc:
        proc.stdin.close(); proc.wait()
        if proc.stderr: proc.stderr.close()
        raise RuntimeError("FFmpeg stopped during vintage insert rendering.") from exc
    except Exception:
        proc.stdin.close(); proc.wait()
        if proc.stderr: proc.stderr.close()
        raise
    finally:
        if not proc.stdin.closed: proc.stdin.close()
    err=proc.stderr.read().decode("utf-8","replace") if proc.stderr else ""
    if proc.stderr: proc.stderr.close()
    code=proc.wait()
    if code: raise RuntimeError(f"Vintage insert encoding failed: {err[-3000:]}")
    return output
