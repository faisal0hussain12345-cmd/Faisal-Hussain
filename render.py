from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
AUDIO = ROOT / "assets" / "voiceover.mp3"
WORK = ROOT / "work"
OUTPUT = ROOT / "output" / "manhattan_project_documentary_draft.mp4"
WIDTH, HEIGHT, FPS = 1920, 1080, 30

SCENES = [
    ("THE SECRET PROJECT", "A wartime race to unlock the power hidden inside the atom.", "1939–1942  /  THE WARNING"),
    ("A LETTER THAT CHANGED HISTORY", "Scientists warn that nuclear fission could lead to a weapon of unprecedented power.", "EINSTEIN–SZILARD LETTER  /  1939"),
    ("THE MANHATTAN PROJECT", "A secret American-led effort brings together scientists, engineers, soldiers, and industry.", "MANHATTAN ENGINEER DISTRICT  /  1942"),
    ("A CITY BUILT IN SECRET", "Oak Ridge, Hanford, and Los Alamos become the hidden engines of the project.", "TENNESSEE  /  WASHINGTON  /  NEW MEXICO"),
    ("THE SCIENCE BECOMES REAL", "At Chicago Pile-1, a controlled chain reaction demonstrates that the process can work.", "CHICAGO  /  DECEMBER 2, 1942"),
    ("THE HUMAN COST OF SECRECY", "Thousands work behind fences and checkpoints, often unaware of the full purpose of their work.", "SECURITY  /  LABOR  /  INDUSTRY"),
    ("TRINITY", "In the New Mexico desert, the first nuclear device is detonated.", "JULY 16, 1945  /  NEW MEXICO"),
    ("A WEAPON USED IN WAR", "Atomic bombs are dropped on Hiroshima and Nagasaki, killing and injuring civilians on a vast scale.", "HIROSHIMA  /  AUGUST 6  •  NAGASAKI  /  AUGUST 9"),
    ("SURRENDER AND ITS DEBATE", "Japan announces surrender. Historians continue to debate the roles of the atomic bombings, Soviet entry into the war, and other factors.", "AUGUST 1945  /  HISTORICAL DEBATE"),
    ("THE NUCLEAR AGE", "The project ends as a wartime program, but the nuclear age it helped create continues.", "SCIENCE  /  POWER  /  RESPONSIBILITY"),
]


def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def duration_seconds(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        check=True, capture_output=True, text=True
    )
    return float(result.stdout.strip())


def font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def wrap_text(draw, text: str, face, max_width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=face)[2] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def make_card(index: int, title: str, description: str, stamp: str, path: Path) -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), (18, 23, 29))
    draw = ImageDraw.Draw(image)
    for x in range(0, WIDTH, 80):
        draw.line((x, 0, x, HEIGHT), fill=(27, 33, 39), width=1)
    for y in range(0, HEIGHT, 80):
        draw.line((0, y, WIDTH, y), fill=(27, 33, 39), width=1)
    draw.rounded_rectangle((105, 95, 1815, 985), radius=18,
                           fill=(231, 222, 199), outline=(170, 155, 126), width=5)
    draw.rectangle((105, 95, 1815, 125), fill=(211, 111, 45))
    draw.text((165, 175), f"CASE FILE  /  MP-{index:02d}", font=font(28, True), fill=(93, 82, 65))
    draw.line((165, 235, 1750, 235), fill=(167, 151, 122), width=3)
    y = 315
    for line in wrap_text(draw, title, font(76, True), 1450):
        draw.text((165, y), line, font=font(76, True), fill=(31, 37, 41))
        y += 96
    y += 35
    for line in wrap_text(draw, description, font(39), 1430):
        draw.text((170, y), line, font=font(39), fill=(65, 66, 62))
        y += 58
    draw.ellipse((1540, 680, 1695, 835), outline=(190, 76, 37), width=10)
    draw.line((1560, 758, 1675, 758), fill=(190, 76, 37), width=8)
    draw.line((1618, 700, 1618, 815), fill=(190, 76, 37), width=8)
    draw.text((165, 875), stamp, font=font(25, True), fill=(145, 72, 40))
    draw.text((1650, 905), f"FILE {index:02d} / 10", font=font(22, True), fill=(93, 82, 65))
    image.save(path, quality=94)


def main() -> None:
    if not AUDIO.is_file():
        raise SystemExit("Narration not found. Upload it to assets/voiceover.mp3.")
    for binary in ("ffmpeg", "ffprobe"):
        if shutil.which(binary) is None:
            raise SystemExit(f"{binary} is required but was not found.")

    WORK.mkdir(parents=True, exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    total = duration_seconds(AUDIO)
    segment_duration = total / len(SCENES)
    segment_files = []

    for i, (title, description, stamp) in enumerate(SCENES, start=1):
        still = WORK / f"scene_{i:02d}.jpg"
        segment = WORK / f"scene_{i:02d}.mp4"
        make_card(i, title, description, stamp, still)
        frames = max(1, round(segment_duration * FPS))
        zoom_filter = (
            f"zoompan=z='min(1.0+0.00012*on,1.035)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s={WIDTH}x{HEIGHT}:fps={FPS},format=yuv420p"
        )
        run(["ffmpeg", "-y", "-loop", "1", "-i", str(still),
             "-t", f"{segment_duration:.3f}", "-vf", zoom_filter, "-an",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
             "-pix_fmt", "yuv420p", str(segment)])
        segment_files.append(segment)

    concat_file = WORK / "concat.txt"
    concat_file.write_text("".join(f"file '{p.as_posix()}'\n" for p in segment_files), encoding="utf-8")
    silent_video = WORK / "silent_video.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
         "-c", "copy", str(silent_video)])
    run(["ffmpeg", "-y", "-i", str(silent_video), "-i", str(AUDIO),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags",
         "+faststart", str(OUTPUT)])

    metadata = {
        "voiceover_seconds": round(total, 2),
        "scene_count": len(SCENES),
        "resolution": f"{WIDTH}x{HEIGHT}",
        "fps": FPS,
        "output": str(OUTPUT.relative_to(ROOT)),
        "note": "Evidence-board visual draft; archival footage and verified source imagery are not yet integrated."
    }
    (OUTPUT.parent / "render_report.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
