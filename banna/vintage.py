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
        # North Atlantic route reconstruction: Southampton -> Cherbourg ->
        # Queenstown -> Titanic's final position, with New York as destination.
        d.text((100,65),"NORTH ATLANTIC / APRIL 1912",font=_font(34,mono=True),fill=INK)
        d.text((110,125),"EUROPE",font=_font(24,True),fill=INK)
        d.text((w-330,h-160),"NORTH AMERICA",font=_font(24,True),fill=INK)
        # Simplified coast silhouettes and graticule.
        for x in range(120,w,180): d.line((x,180,x-30,h-160),fill=(130,170,195),width=2)
        for y in range(210,h-140,130): d.line((80,y,w-80,y+18),fill=(130,170,195),width=2)
        d.polygon([(120,220),(270,190),(390,270),(420,390),(350,510),(260,580),(180,480),(130,350)],fill=(130,170,195),outline=INK)
        d.polygon([(w-330,550),(w-250,500),(w-170,570),(w-140,710),(w-220,830),(w-300,780)],fill=(130,170,195),outline=INK)
        route=[(360,360),(540,405),(690,470),(1030,560),(1460,630)]
        for i in range(len(route)-1):
            a,b=route[i],route[i+1]
            for k in range(0,16,2):
                p0=(a[0]+(b[0]-a[0])*k/16,a[1]+(b[1]-a[1])*k/16)
                p1=(a[0]+(b[0]-a[0])*(k+1)/16,a[1]+(b[1]-a[1])*(k+1)/16)
                d.line((p0,p1),fill=ORANGE,width=7)
        labels=["SOUTHAMPTON","CHERBOURG","QUEENSTOWN","LAST POSITION","NEW YORK"]
        for i,p in enumerate(route):
            d.ellipse((p[0]-13,p[1]-13,p[0]+13,p[1]+13),fill=ORANGE,outline=INK,width=3)
            if i in (0,1,2,3,4):
                d.text((p[0]+20,p[1]-25),labels[i],font=_font(20,mono=True),fill=INK)
        pulse=1+0.08*math.sin(tq*8)
        cx,cy=route[3]; rx,ry=115*pulse,82*pulse
        d.ellipse((cx-rx,cy-ry,cx+rx,cy+ry),outline=ORANGE,width=6)
    elif phase<0.75:
        # Titanic side profile, iceberg, lifeboats and rising water.
        d.rectangle((0,0,w,570),fill=(188,216,230))
        # Distant ice field.
        d.polygon([(1380,560),(1480,390),(1570,470),(1660,300),(1750,470),(1840,400),(1920,570)],fill=(225,239,245),outline=INK)
        d.polygon([(1430,570),(1520,470),(1620,550),(1720,440),(1820,570)],fill=(206,226,236),outline=INK)
        # Sea with animated horizontal wave lines.
        d.rectangle((0,650,w,h),fill=(55,91,119))
        for yy in range(690,1050,52):
            pts=[]
            for xx in range(0,w+20,40):
                pts.append((xx,yy+int(7*math.sin(xx*0.018+tq*3+yy))))
            d.line(pts,fill=(150,184,202),width=3)
        # Ship moves slowly down and pitches forward as flooding worsens.
        local=(phase-0.28)/0.47
        ship_x=220
        bow_y=int(625+local*155)
        stern_y=int(600+local*15)
        hull=[(ship_x,stern_y),(1500,stern_y-10),(1780,bow_y+5),(1690,bow_y+95),(520,bow_y+120),(280,bow_y+70)]
        d.polygon(hull,fill=(18,30,44),outline=INK)
        d.line((300,bow_y+25,1700,bow_y+20),fill=(220,228,232),width=8)
        # Deckhouses and four funnels, smoke.
        d.rectangle((460,stern_y-160,1480,stern_y-10),fill=(218,226,230),outline=INK,width=5)
        for fx in (610,850,1090,1330):
            d.rectangle((fx,stern_y-285,fx+92,stern_y-150),fill=(180,78,38),outline=INK,width=5)
            d.rectangle((fx-8,stern_y-295,fx+100,stern_y-270),fill=INK)
            for puff in range(3):
                sx=fx+35+puff*34-int(local*18)
                sy=stern_y-330-puff*34
                d.ellipse((sx-32,sy-22,sx+32,sy+22),fill=(145,169,183),outline=(90,120,140),width=2)
        # Lit portholes and tiny lifeboat silhouettes.
        for xx in range(520,1600,75):
            d.ellipse((xx,stern_y-95,xx+18,stern_y-77),fill=(255,205,112),outline=INK,width=1)
        for bx in (360,760,1160,1510):
            by=int(785+local*25)
            d.polygon([(bx,by),(bx+180,by),(bx+155,by+36),(bx+25,by+36)],fill=(218,226,230),outline=INK)
            for px in (bx+35,bx+145): d.line((px,by+10,px-12,by+78),fill=INK,width=4)
        d.text((95,70),"THE FINAL HOURS / NORTH ATLANTIC",font=_font(32,mono=True),fill=INK)
        if abs(t-impact_at)<0.16:
            flash=Image.new("RGB",size,(245,248,250))
            im=Image.blend(im,flash,0.82)
            d=ImageDraw.Draw(im)
            d.text((w//2-175,h//2-45),"ICEBERG IMPACT",font=_font(58,True),fill=ORANGE)
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
