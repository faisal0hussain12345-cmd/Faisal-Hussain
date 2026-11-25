from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAVY = (16, 26, 44)
PAPER = (232, 236, 240)
INK = (22, 30, 46)
ORANGE = (255, 107, 0)
CYAN = (105, 153, 184)
SEA = (39, 68, 92)


def _font(size: int, bold: bool = False, mono: bool = False):
    names = []
    if mono:
        names = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"]
    else:
        names = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else
                 "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default()


def _base(title: str, size: tuple[int, int]) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    w, h = size
    im = Image.new("RGB", size, NAVY)
    d = ImageDraw.Draw(im)
    for x in range(0, w, 80):
        d.line((x, 0, x, h), fill=(23, 38, 58), width=1)
    for y in range(0, h, 80):
        d.line((0, y, w, y), fill=(23, 38, 58), width=1)
    d.rectangle((35, 35, w - 35, h - 35), outline=(96, 116, 136), width=2)
    d.text((70, 55), title.upper(), font=_font(32, mono=True), fill=PAPER)
    d.line((70, 112, w - 70, 112), fill=ORANGE, width=4)
    return im, d


def _ship(d: ImageDraw.ImageDraw, x: int, y: int, scale: float = 1.0,
          pitch: float = 0.0, color=INK) -> None:
    # Side-view reconstruction; deliberately schematic, not presented as a photograph.
    def p(points):
        return [(int(x + px * scale), int(y + py * scale + px * pitch)) for px, py in points]
    hull = [(-600, 0), (520, 0), (610, 45), (540, 120), (-470, 120), (-590, 55)]
    d.polygon(p(hull), fill=color, outline=PAPER)
    d.line(p([(-520, 18), (555, 18)]), fill=PAPER, width=max(2, int(5 * scale)))
    d.rectangle((int(x-390*scale), int(y-145*scale), int(x+430*scale), int(y-4*scale)),
                fill=(205, 216, 224), outline=INK, width=max(2, int(4*scale)))
    for fx in (-280, -70, 140, 350):
        xx=int(x+fx*scale); yy=int(y-145*scale+fx*pitch)
        d.rectangle((xx, yy-int(130*scale), xx+int(62*scale), yy),
                    fill=(160, 82, 49), outline=INK, width=max(2, int(3*scale)))
        d.rectangle((xx-int(5*scale), yy-int(138*scale), xx+int(67*scale), yy-int(124*scale)),
                    fill=INK)
    for px in range(-360, 450, 58):
        xx=int(x+px*scale); yy=int(y-85*scale+px*pitch)
        r=max(2,int(6*scale))
        d.ellipse((xx-r,yy-r,xx+r,yy+r),fill=(255,196,104))


def render_titanic_graphic(kind: str, title: str, output: Path,
                           size: tuple[int, int] = (1600, 900)) -> Path:
    w, h = size
    im, d = _base(title, size)

    if kind == "atlantic_route_map":
        # Schematic Atlantic route, with a restrained landmass outline.
        d.polygon([(90,190),(230,150),(360,200),(400,300),(360,430),(260,520),(150,440),(90,310)],
                  fill=(68,96,116), outline=PAPER)
        d.polygon([(w-390,520),(w-300,440),(w-190,500),(w-130,660),(w-230,760),(w-350,700)],
                  fill=(68,96,116), outline=PAPER)
        route=[(350,310),(500,360),(610,405),(930,510),(1260,620)]
        labels=["SOUTHAMPTON","CHERBOURG","QUEENSTOWN","LAST POSITION","NEW YORK"]
        for i in range(len(route)-1):
            d.line((route[i],route[i+1]),fill=ORANGE,width=7)
        for point,label in zip(route,labels):
            x,y=point
            d.ellipse((x-13,y-13,x+13,y+13),fill=ORANGE,outline=PAPER,width=3)
            d.text((x+18,y-28),label,font=_font(19,mono=True),fill=PAPER)
        d.text((95,h-100),"NORTH ATLANTIC / APRIL 1912",font=_font(26,True),fill=ORANGE)

    elif kind == "ship_launch":
        # Shipyard launch-day reconstruction with slipway, cranes and crowd silhouettes.
        d.rectangle((0,690,w,h-40),fill=(52,83,105))
        d.polygon([(0,610),(w,610),(w,690),(0,690)],fill=(102,124,139))
        _ship(d,790,650,0.72,pitch=0.0)
        for cx in (180,340,1280,1450):
            d.line((cx,155,cx,620),fill=(172,185,195),width=9)
            d.line((cx,180,cx+150,290),fill=(172,185,195),width=7)
            d.line((cx,290,cx+150,290),fill=ORANGE,width=4)
        for px in range(80,w-50,38):
            d.ellipse((px,735,px+13,748),fill=PAPER)
            d.line((px+6,748,px+6,790),fill=PAPER,width=4)
        d.text((95,220),"BELFAST / MAY 31, 1911",font=_font(29,mono=True),fill=ORANGE)

    elif kind == "passenger_deck":
        # Non-identifiable silhouettes represent the many lives aboard.
        d.rectangle((90,620,w-90,700),fill=(188,202,214),outline=PAPER,width=4)
        d.rectangle((140,400,w-140,620),fill=(75,100,120),outline=PAPER,width=4)
        for i in range(22):
            x=190+(i%11)*112
            y=520+(i//11)*65
            d.ellipse((x,y-52,x+24,y-28),fill=INK)
            d.polygon([(x-7,y-28),(x+31,y-28),(x+42,y+42),(x-17,y+42)],fill=INK)
        d.text((125,230),"MORE THAN 2,200 PEOPLE ABOARD",font=_font(32,True),fill=PAPER)
        d.text((125,285),"PASSENGERS / CREW / FAMILIES / IMMIGRANTS",font=_font(22,mono=True),fill=ORANGE)

    elif kind == "lookout_night":
        # Crow's-nest silhouette and two anonymous lookouts scanning a calm sea.
        d.rectangle((0,650,w,h-40),fill=(30,54,77))
        for i in range(80):
            x=(i*97)%w; y=150+(i*53)%430
            d.ellipse((x,y,x+3,y+3),fill=(165,190,205))
        d.line((w//2,130,w//2,600),fill=(175,190,201),width=18)
        d.line((w//2-360,300,w//2+360,300),fill=(175,190,201),width=15)
        d.rectangle((w//2-250,250,w//2+250,330),outline=ORANGE,width=6)
        for x in (w//2-120,w//2+120):
            d.ellipse((x-22,180,x+22,224),fill=INK)
            d.polygon([(x-34,225),(x+34,225),(x+54,295),(x-54,295)],fill=INK)
        d.text((105,720),"CROW'S NEST / LOOKOUTS ON WATCH",font=_font(27,mono=True),fill=PAPER)
        d.text((105,775),"DARK SKY / CALM SEA / LIMITED VISIBILITY",font=_font(22,mono=True),fill=ORANGE)

    elif kind == "iceberg_collision":
        # Non-graphic reconstruction of the collision moment.
        for i in range(70):
            sx=(i*137)%w; sy=145+(i*71)%(h-330)
            d.ellipse((sx,sy,sx+3,sy+3),fill=(166,190,205))
        d.polygon([(1110,630),(1210,330),(1300,445),(1390,270),(1490,620),(1430,720),(1190,710)],
                  fill=(210,228,236),outline=PAPER)
        d.polygon([(0,700),(w,700),(w,h-40),(0,h-40)],fill=SEA)
        for yy in range(735, h-65, 42):
            pts=[(xx, yy+int(8*math.sin(xx*.018+yy))) for xx in range(0,w,24)]
            d.line(pts,fill=CYAN,width=2)
        _ship(d,650,630,0.70,pitch=0.015)
        d.ellipse((1015,575,1125,685),outline=ORANGE,width=7)
        d.line((1070,630,1175,560),fill=ORANGE,width=5)
        d.text((1080,520),"ICEBERG",font=_font(22,mono=True),fill=ORANGE)

    elif kind == "ship_cross_section":
        # Simplified watertight-compartment cutaway showing progressive flooding.
        top=360; bottom=690
        hull=[(150,top),(1430,top),(1500,470),(1400,bottom),(250,bottom),(140,480)]
        d.polygon(hull,fill=(190,204,214),outline=PAPER)
        for x in (390,620,850,1080,1300):
            d.line((x,top+5,x,bottom-5),fill=INK,width=8)
        d.rectangle((165,555,680,685),fill=(46,106,144))
        d.rectangle((685,610,835,685),fill=(46,106,144))
        for x in (390,620,850,1080,1300):
            d.ellipse((x-8,top-8,x+8,top+8),fill=ORANGE)
        d.text((180,735),"FLOODED COMPARTMENTS",font=_font(25,mono=True),fill=ORANGE)
        d.text((900,735),"WATER OVER TOP OF BULKHEADS",font=_font(22,mono=True),fill=PAPER)
        d.line((680,545,680,490),fill=ORANGE,width=5)
        d.line((835,600,835,510),fill=ORANGE,width=5)
        d.text((190,230),"WATERTIGHT COMPARTMENTS",font=_font(32,True),fill=PAPER)
        d.text((190,275),"A system with limits — not an unsinkable hull",font=_font(23),fill=CYAN)

    elif kind == "sinking_ship":
        d.rectangle((0,690,w,h-40),fill=SEA)
        for yy in range(720,h-60,42):
            pts=[(xx, yy+int(9*math.sin(xx*.014+yy))) for xx in range(0,w,24)]
            d.line(pts,fill=CYAN,width=3)
        _ship(d,810,650,0.72,pitch=0.20)
        # Lifeboat silhouettes and distant horizon lights.
        for bx,by in ((210,670),(430,740),(1190,760),(1370,690)):
            d.polygon([(bx,by),(bx+145,by),(bx+125,by+27),(bx+20,by+27)],fill=(220,228,232),outline=INK)
            for px in (bx+38,bx+105):
                d.line((px,by+12,px-6,by+55),fill=INK,width=4)
        d.text((90,220),"APRIL 15 / 2:20 A.M.",font=_font(30,mono=True),fill=ORANGE)
        d.text((90,270),"THE SHIP DISAPPEARS BENEATH THE ATLANTIC",font=_font(25),fill=PAPER)

    else:
        raise ValueError(f"Unsupported Titanic graphic type: {kind}")

    output.parent.mkdir(parents=True, exist_ok=True)
    im.save(output, quality=94)
    return output
