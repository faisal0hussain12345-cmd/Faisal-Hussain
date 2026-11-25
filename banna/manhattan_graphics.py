from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

NAVY=(16,26,44); PAPER=(232,236,240); INK=(22,30,46); ORANGE=(255,107,0)
STEEL=(85,111,137); CYAN=(117,164,190); RED=(166,72,49)

def font(n,bold=False,mono=False):
    names=(["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"] if mono else
           ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"] if bold else
           ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"])
    for p in names:
        try: return ImageFont.truetype(p,n)
        except OSError: pass
    return ImageFont.load_default()

def base(title,size):
    w,h=size; im=Image.new("RGB",size,NAVY); d=ImageDraw.Draw(im)
    for x in range(0,w,80): d.line((x,0,x,h),fill=(23,38,58),width=1)
    for y in range(0,h,80): d.line((0,y,w,y),fill=(23,38,58),width=1)
    d.rectangle((35,35,w-35,h-35),outline=(96,116,136),width=2)
    d.text((75,55),title.upper(),font=font(31,mono=True),fill=PAPER)
    d.line((75,112,w-75,112),fill=ORANGE,width=4)
    return im,d

def render_manhattan_graphic(kind:str,title:str,output:Path,size=(1600,900)):
    w,h=size; im,d=base(title,size)
    def label(a,b,sub=""):
        d.text((95,205),a,font=font(39,True),fill=PAPER)
        if sub: d.text((98,270),sub,font=font(23,mono=True),fill=ORANGE)
    if kind=="mp_fission":
        label("THE ATOM / A NEW SOURCE OF ENERGY","1938 — NUCLEAR FISSION")
        d.ellipse((570,300,1030,760),outline=CYAN,width=8)
        cx,cy=800,530
        for a in range(0,360,45):
            r=math.radians(a); x=cx+190*math.cos(r); y=cy+190*math.sin(r)
            d.line((cx,cy,x,y),fill=STEEL,width=5); d.ellipse((x-25,y-25,x+25,y+25),fill=ORANGE,outline=PAPER,width=2)
        d.ellipse((cx-65,cy-65,cx+65,cy+65),fill=PAPER,outline=ORANGE,width=5)
        d.text((650,790),"CONTROLLED CHAIN REACTION / SCHEMATIC",font=font(20,mono=True),fill=CYAN)
    elif kind=="mp_letter":
        d.rectangle((280,185,1320,770),fill=(224,218,198),outline=PAPER,width=5)
        d.text((355,235),"A LETTER TO THE PRESIDENT",font=font(29,mono=True),fill=INK)
        d.text((355,300),"AUGUST 2, 1939",font=font(24,mono=True),fill=ORANGE)
        for i in range(10):
            y=385+i*32; d.line((355,y,1230-(i%3)*70,y),fill=(95,91,80),width=4)
        d.text((355,720),"HISTORICAL DOCUMENT / VISUAL RECONSTRUCTION",font=font(17,mono=True),fill=INK)
    elif kind=="mp_wartime":
        label("A WORLD AT WAR","PEARL HARBOR / DECEMBER 1941")
        for x,y,s in [(250,480,1),(620,580,.8),(1030,430,1.1)]:
            d.polygon([(x,y),(x+180*s,y-35*s),(x+300*s,y),(x+180*s,y+35*s)],fill=STEEL,outline=PAPER)
            for k in range(4): d.ellipse((x+35+k*35,y-7,x+47+k*35,y+5),fill=ORANGE)
        d.text((95,760),"MOBILIZATION / INDUSTRY / SCIENCE / MILITARY",font=font(23,mono=True),fill=CYAN)
    elif kind=="mp_map":
        label("THREE SECRET CENTERS","A NATIONAL INDUSTRIAL AND SCIENTIFIC EFFORT")
        # Schematic continental US, not a navigational map.
        d.polygon([(230,390),(390,320),(650,345),(840,300),(1110,350),(1320,440),(1260,620),(1050,690),(780,650),(570,710),(350,620)],fill=(52,78,101),outline=PAPER)
        for x,y,t in [(430,470,"HANFORD / WA"),(770,550,"LOS ALAMOS / NM"),(1110,485,"OAK RIDGE / TN")]:
            d.ellipse((x-18,y-18,x+18,y+18),fill=ORANGE,outline=PAPER,width=3)
            d.text((x+25,y-25),t,font=font(20,mono=True),fill=PAPER)
        d.text((95,790),"SCHEMATIC UNITED STATES / NOT TO SCALE",font=font(18,mono=True),fill=CYAN)
    elif kind=="mp_chicago":
        label("CHICAGO PILE-1","DECEMBER 2, 1942 / FIRST CONTROLLED SELF-SUSTAINING CHAIN REACTION")
        d.rectangle((390,360,1210,700),fill=(95,104,109),outline=PAPER,width=5)
        for row in range(5):
            for col in range(10):
                x=430+col*74; y=400+row*55
                d.rectangle((x,y,x+55,y+34),fill=(43,55,67),outline=CYAN,width=2)
        d.text((500,745),"GRAPHITE / URANIUM LATTICE — SCHEMATIC",font=font(22,mono=True),fill=ORANGE)
    elif kind=="mp_oakridge":
        label("OAK RIDGE / TENNESSEE","URANIUM ENRICHMENT AT INDUSTRIAL SCALE")
        d.rectangle((180,500,1420,700),fill=(63,79,91),outline=PAPER,width=4)
        for x in range(230,1390,145):
            d.rectangle((x,340,x+100,500),fill=(155,171,181),outline=PAPER,width=3)
            d.rectangle((x+25,300,x+75,340),fill=ORANGE)
        d.text((205,750),"Y-12 / K-25 / X-10 FACILITIES",font=font(24,mono=True),fill=CYAN)
    elif kind=="mp_hanford":
        label("HANFORD / WASHINGTON","PLUTONIUM PRODUCTION")
        d.rectangle((200,420,1400,690),fill=(74,91,104),outline=PAPER,width=4)
        for x in (330,650,970,1230):
            d.rectangle((x,280,x+145,420),fill=(145,160,171),outline=PAPER,width=3)
            d.rectangle((x+45,220,x+100,280),fill=RED,outline=PAPER,width=2)
        d.line((220,710,1380,710),fill=CYAN,width=7)
        d.text((220,765),"REACTORS / CHEMICAL SEPARATION / INDUSTRIAL COMPLEX",font=font(19,mono=True),fill=ORANGE)
    elif kind=="mp_losalamos":
        label("LOS ALAMOS / NEW MEXICO","SITE Y / WEAPONS DESIGN LABORATORY")
        d.polygon([(110,670),(330,450),(560,590),(760,350),(990,570),(1210,400),(1490,660)],fill=(77,95,112),outline=PAPER)
        d.rectangle((500,430,1120,650),fill=(125,139,148),outline=PAPER,width=4)
        for x in (570,740,910): d.rectangle((x,500,x+110,650),fill=(55,68,82),outline=CYAN,width=2)
        d.text((540,730),"SCIENTIFIC DESIGN / ENGINEERING / TESTING",font=font(21,mono=True),fill=ORANGE)
    elif kind=="mp_leadership":
        label("SCIENCE MEETS MILITARY COMMAND","J. ROBERT OPPENHEIMER / GENERAL LESLIE GROVES")
        d.ellipse((410,330,650,570),fill=(45,58,73),outline=PAPER,width=5)
        d.rectangle((360,580,700,760),fill=(45,58,73),outline=PAPER,width=4)
        d.ellipse((960,330,1200,570),fill=(45,58,73),outline=PAPER,width=5)
        d.rectangle((910,580,1250,760),fill=(45,58,73),outline=PAPER,width=4)
        d.text((385,790),"SCIENTIFIC DIRECTOR",font=font(19,mono=True),fill=CYAN)
        d.text((1000,790),"MILITARY DIRECTOR",font=font(19,mono=True),fill=ORANGE)
    elif kind=="mp_trinity":
        label("TRINITY TEST / JULY 16, 1945","THE FIRST NUCLEAR DETONATION")
        d.rectangle((0,660,w,h-35),fill=(95,82,65))
        d.rectangle((780,420,820,670),fill=(72,77,80),outline=PAPER,width=2)
        for r in (80,145,215,290):
            d.ellipse((800-r,380-r,800+r,380+r),outline=ORANGE if r<220 else CYAN,width=8)
        d.polygon([(800,140),(740,365),(770,470),(830,470),(860,365)],fill=(226,219,193),outline=PAPER)
        d.text((105,770),"NEW MEXICO DESERT / NON-PHOTOREALISTIC DIAGRAM",font=font(20,mono=True),fill=CYAN)
    elif kind=="mp_hiroshima":
        label("HIROSHIMA / AUGUST 6, 1945","LITTLE BOY / URANIUM BOMB")
        for x,y in [(260,570),(520,520),(830,600),(1110,540),(1350,600)]:
            d.rectangle((x,y-100,x+150,y),fill=(62,72,83),outline=PAPER,width=2)
            d.polygon([(x-20,y-100),(x+70,y-180),(x+170,y-100)],fill=(95,106,115),outline=PAPER)
        d.text((100,760),"CITY DESTRUCTION / SYMBOLIC, NON-GRAPHIC RECONSTRUCTION",font=font(18,mono=True),fill=ORANGE)
    elif kind=="mp_nagasaki":
        label("NAGASAKI / AUGUST 9, 1945","FAT MAN / PLUTONIUM IMPLOSION DESIGN")
        for x,y in [(250,580),(560,510),(900,590),(1210,520)]:
            d.rectangle((x,y-115,x+175,y),fill=(61,74,86),outline=PAPER,width=3)
            d.line((x+20,y-90,x+150,y-20),fill=CYAN,width=3)
        d.text((100,760),"SECOND ATOMIC BOMBING / NON-GRAPHIC RECONSTRUCTION",font=font(19,mono=True),fill=ORANGE)
    elif kind=="mp_legacy":
        label("THE NUCLEAR AGE BEGINS","A SECRET WARTIME PROGRAM / A WORLDWIDE CONSEQUENCE")
        d.ellipse((560,260,1040,740),outline=ORANGE,width=8)
        for a in range(0,360,60):
            r=math.radians(a); x=800+210*math.cos(r); y=500+210*math.sin(r)
            d.line((800,500,x,y),fill=CYAN,width=8)
            d.ellipse((x-20,y-20,x+20,y+20),fill=PAPER)
        d.text((95,790),"SCIENCE / POWER / ETHICS / MEMORY",font=font(24,mono=True),fill=ORANGE)
    else:
        raise ValueError(f"Unknown Manhattan Project graphic type: {kind}")
    output.parent.mkdir(parents=True,exist_ok=True); im.save(output,quality=94)
    return output
