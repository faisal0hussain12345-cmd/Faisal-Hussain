from __future__ import annotations
from PIL import Image, ImageDraw, ImageFont
from .documentary_engine import card_anchor, _font

def make_paper_tracked(lines: list[str], width: int=1000, height: int=600):
    """Create a paper note and exact per-line pixel bounding boxes."""
    im=Image.new("RGBA",(width,height),(232,236,240,255)); d=ImageDraw.Draw(im)
    font=_font(30,mono=True); boxes=[]
    y=55
    for line in lines:
        box=d.textbbox((55,y),line,font=font)
        d.text((55,y),line,font=font,fill=(22,30,46,255))
        boxes.append((box[0],box[1],box[2],box[3])); y += 58
    return im, {"lines":boxes}

def text_underline_world(card: dict, meta: dict, line_idx: int, y_pad: int=6):
    x0,y0,x1,y1=meta["lines"][line_idx]
    return (card_anchor(card,(x0-500)/1000,(y1+y_pad-300)/600),
            card_anchor(card,(x1-500)/1000,(y1+y_pad-300)/600))

def text_circle_world(card: dict, meta: dict, line_idx: int, pad_x: int=18, pad_y: int=12):
    x0,y0,x1,y1=meta["lines"][line_idx]
    cx,cy=card_anchor(card,((x0+x1)/2-500)/1000,((y0+y1)/2-300)/600)
    return (cx,cy,(x1-x0)/2+pad_x,(y1-y0)/2+pad_y)

def draw_wobble_circle(draw: ImageDraw.ImageDraw, box, color=(255,107,0), width=5, steps=96):
    import math
    x0,y0,x1,y1=box; cx=(x0+x1)/2; cy=(y0+y1)/2; rx=(x1-x0)/2; ry=(y1-y0)/2
    pts=[]
    for i in range(steps+1):
        a=2*math.pi*i/steps; wobble=1+0.018*math.sin(7*a)+0.012*math.sin(13*a)
        pts.append((cx+rx*wobble*math.cos(a),cy+ry*wobble*math.sin(a)))
    draw.line(pts,fill=color,width=width)
