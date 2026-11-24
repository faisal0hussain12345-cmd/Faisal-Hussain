from __future__ import annotations
import math
from PIL import Image, ImageDraw
from .documentary_engine import NAVY, ORANGE, _font

CYAN=(172,208,226); INK=(26,38,52)

def vintage_frame(t: float, duration: float, title: str, size=(1920,1080)) -> Image.Image:
    """Generate a non-graphic cyanotype silent-film still; animate by varying t."""
    w,h=size; im=Image.new("RGB",size,CYAN); d=ImageDraw.Draw(im)
    # blueprint map lines and a dashed route
    for x in range(100,w,180): d.line((x,180,x-60,h-160),fill=(130,170,195),width=3)
    for y in range(220,h,150): d.line((80,y,w-80,y+35),fill=(130,170,195),width=2)
    route=[(220,700),(520,580),(850,620),(1120,420),(1500,500),(1720,330)]
    for i in range(len(route)-1):
        a,b=route[i],route[i+1]
        for k in range(0,10,2):
            p0=(a[0]+(b[0]-a[0])*k/10,a[1]+(b[1]-a[1])*k/10)
            p1=(a[0]+(b[0]-a[0])*(k+1)/10,a[1]+(b[1]-a[1])*(k+1)/10)
            d.line((p0,p1),fill=ORANGE,width=8)
    for i,p in enumerate(route):
        d.ellipse((p[0]-14,p[1]-14,p[0]+14,p[1]+14),fill=ORANGE,outline=INK,width=3)
    # moving flat silhouette procession
    shift=int((t/max(duration,0.01))*w*0.35)
    for i in range(7):
        x=(180+i*260+shift)%(w+200)-100; bob=math.sin(t*5+i)*7
        d.ellipse((x-25,650+bob,x+25,700+bob),fill=INK)
        d.polygon([(x-30,700+bob),(x+30,700+bob),(x+65,900),(x-65,900)],fill=INK)
    d.rectangle((110,100,w-110,h-100),outline=INK,width=5)
    d.rectangle((125,115,w-125,h-115),outline=INK,width=2)
    if t>duration*0.72:
        d.rectangle((220,390,w-220,690),fill=(10,14,20),outline=ORANGE,width=5)
        text=title[:70]; f=_font(52,True)
        box=d.textbbox((0,0),text,font=f)
        d.text(((w-(box[2]-box[0]))/2,510),text,font=f,fill=CYAN)
    # grain and flicker
    import random
    rng=random.Random(int(t*12))
    for _ in range(140):
        x=rng.randrange(w); y=rng.randrange(h); d.point((x,y),fill=(rng.randrange(100,180),rng.randrange(140,210),rng.randrange(160,230)))
    return im
