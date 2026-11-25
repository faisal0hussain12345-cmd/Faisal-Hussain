from __future__ import annotations
import math, random, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
from .documentary_engine import _font

BLUE=(171,207,225); DARK=(19,32,47); ORANGE=(255,107,0); PALE=(220,233,240)

def frame(t,duration,title,size=(1920,1080)):
    w,h=size; phase=t/max(duration,.001)
    im=Image.new("RGB",size,BLUE); d=ImageDraw.Draw(im)
    if phase<.34:
        d.text((110,75),"MANHATTAN PROJECT / SECRET SITES",font=_font(34,mono=True),fill=DARK)
        d.polygon([(160,300),(420,220),(700,300),(1000,240),(1400,310),(1690,470),(1500,750),(1100,800),(700,700),(360,760)],fill=(130,170,195),outline=DARK)
        for x,y,name in [(450,440,"HANFORD"),(860,590,"LOS ALAMOS"),(1320,470,"OAK RIDGE")]:
            d.ellipse((x-18,y-18,x+18,y+18),fill=ORANGE,outline=DARK,width=3)
            d.text((x+25,y-28),name,font=_font(24,mono=True),fill=DARK)
        d.line((450,440,860,590,1320,470),fill=ORANGE,width=7)
        d.text((110,900),"UNITED STATES / 1942–1945",font=_font(28,mono=True),fill=DARK)
    elif phase<.76:
        d.rectangle((0,700,w,h),fill=(71,103,128))
        for yy in range(740,1040,55):
            d.line((0,yy,w,yy+int(8*math.sin(t*3+yy))),fill=(140,179,198),width=3)
        cx=960; cy=int(620-(phase-.34)*520)
        for r in (75,130,190,260):
            d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=ORANGE if r<200 else DARK,width=7)
        d.polygon([(cx,cy-310),(cx-90,cy-60),(cx-45,cy+80),(cx+45,cy+80),(cx+90,cy-60)],fill=(229,225,205),outline=DARK)
        d.text((110,80),"TRINITY / JULY 16, 1945",font=_font(38,mono=True),fill=DARK)
        d.text((110,145),"FIRST NUCLEAR DETONATION",font=_font(27,mono=True),fill=ORANGE)
    else:
        im=Image.new("RGB",size,DARK); d=ImageDraw.Draw(im)
        d.rectangle((140,120,w-140,h-120),outline=PALE,width=5)
        d.rectangle((165,145,w-165,h-145),outline=(95,145,170),width=2)
        for x,y in ((165,145),(w-165,145),(165,h-145),(w-165,h-145)):
            d.ellipse((x-13,y-13,x+13,y+13),fill=ORANGE)
        for txt,y,sz in ((title[:55],420,58),("THE WORLD WOULD NEVER BE THE SAME",555,31)):
            box=d.textbbox((0,0),txt,font=_font(sz,True))
            d.text(((w-(box[2]-box[0]))/2,y),txt,font=_font(sz,True),fill=BLUE)
        d.line((w//2-190,515,w//2+190,515),fill=ORANGE,width=5)
    rng=random.Random(int(t*12))
    for _ in range(180):
        x=rng.randrange(w); y=rng.randrange(h)
        d.point((x,y),fill=(rng.randrange(110,190),rng.randrange(150,215),rng.randrange(170,235)))
    if rng.random()<.16:
        x=rng.randrange(w); d.line((x,0,x+rng.randrange(-10,11),h),fill=PALE,width=1)
    if rng.random()<.25: im=ImageChops.offset(im,rng.choice((-1,1)),rng.choice((-1,1)))
    iris=min(1,max(0,t/.45),max(0,(duration-t)/.45))
    mask=Image.new("L",size,0); md=ImageDraw.Draw(mask); r=int(math.hypot(w/2,h/2)*iris)
    md.ellipse((w/2-r,h/2-r,w/2+r,h/2+r),fill=255)
    return Image.composite(im,Image.new("RGB",size,(4,8,14)),mask)

def render_manhattan_vintage(title,duration,output,fps=30,size=(1920,1080)):
    output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
    cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{size[0]}x{size[1]}","-r",str(fps),"-i","-","-an","-c:v","libx264","-preset","veryfast","-crf","22","-pix_fmt","yuv420p",str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for fi in range(max(1,round(duration*fps))): proc.stdin.write(frame(fi/fps,duration,title,size).tobytes())
        proc.stdin.close()
        if proc.wait()!=0: raise RuntimeError((proc.stderr.read().decode("utf-8","replace") if proc.stderr else "FFmpeg vintage render failed")[-3000:])
    finally:
        if proc.stderr: proc.stderr.close()
    return output
