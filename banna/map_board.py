from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from .documentary_engine import NAVY, PAPER, ORANGE, _font

def draw_coordinate_grid(image: Image.Image, divisions: int=10) -> Image.Image:
    """Return a numbered inspection grid; use this to verify pins before rendering."""
    out=image.convert("RGB").copy(); d=ImageDraw.Draw(out); w,h=out.size
    for i in range(divisions+1):
        x=round(i*w/divisions); y=round(i*h/divisions)
        d.line((x,0,x,h),fill=(255,107,0),width=1)
        d.line((0,y,w,y),fill=(255,107,0),width=1)
        d.text((x+3,3),str(i),font=_font(16,mono=True),fill=(255,107,0))
        d.text((3,y+3),str(i),font=_font(16,mono=True),fill=(255,107,0))
    return out

def render_map_panel(title: str, locations: list[dict], size=(1600,900)) -> Image.Image:
    """Stylized schematic map panel; locations require normalized x/y in [0,1]."""
    im=Image.new("RGB",size,NAVY); d=ImageDraw.Draw(im); w,h=size
    for x in range(0,w,50): d.line((x,0,x,h),fill=(24,40,60),width=1)
    for y in range(0,h,50): d.line((0,y,w,y),fill=(24,40,60),width=1)
    d.text((65,45),title.upper(),font=_font(38,True),fill=PAPER)
    prev=None
    for i,p in enumerate(locations,1):
        x,y=float(p["x"]),float(p["y"])
        if not (0<=x<=1 and 0<=y<=1): raise ValueError("Map x/y must be normalized to [0,1]")
        pt=(round(x*w),round(y*h))
        if prev: d.line((prev,pt),fill=ORANGE,width=4)
        d.ellipse((pt[0]-13,pt[1]-13,pt[0]+13,pt[1]+13),fill=ORANGE,outline=PAPER,width=3)
        label=str(p.get("label",f"POINT {i}"))
        d.text((pt[0]+20,pt[1]-12),label[:36],font=_font(23,mono=True),fill=PAPER)
        prev=pt
    return im

def annotate_map_image(base: Image.Image, title: str, locations: list[dict]) -> Image.Image:
    """Pin verified normalized map coordinates and connect them with orange evidence routes."""
    im=base.convert("RGB").copy(); d=ImageDraw.Draw(im); w,h=im.size
    prev=None
    for i,p in enumerate(locations,1):
        x,y=float(p["x"]),float(p["y"])
        if not (0<=x<=1 and 0<=y<=1): raise ValueError("Map x/y must be normalized to [0,1]")
        pt=(round(x*w),round(y*h))
        if prev: d.line((prev,pt),fill=ORANGE,width=max(3,w//500))
        r=max(8,w//120)
        d.ellipse((pt[0]-r,pt[1]-r,pt[0]+r,pt[1]+r),fill=ORANGE,outline=PAPER,width=3)
        d.text((pt[0]+r+5,pt[1]-r-5),str(p.get("label",f"POINT {i}"))[:40],font=_font(max(16,w//70),mono=True),fill=PAPER,stroke_width=2,stroke_fill=NAVY)
        prev=pt
    if title:
        d.rounded_rectangle((20,20,min(w-20, min(w-20, 20+len(title)*20)),85),fill=NAVY,outline=ORANGE,width=3)
        d.text((38,34),title[:60],font=_font(max(18,w//65),True),fill=PAPER)
    return im
