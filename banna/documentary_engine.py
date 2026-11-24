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
    d.text((pad + 18, pad + photo_h + 20), title[:68], font=_font(32, True), fill=INK)
    caption = str(scene.get("caption") or f"CASE FILE / {number:02d} OF {total:02d}")
    d.text((pad + 18, pad + photo_h + 78), caption[:90], font=_font(20, mono=True), fill=STEEL)
    d.line((pad + 18, pad + photo_h + 116, pad + min(card_w - 18, 360), pad + photo_h + 116),
           fill=ORANGE, width=7)
    # Paper pin is fixed to the top-center of the card body.
    d.ellipse((layer.width // 2 - 15, 8, layer.width // 2 + 15, 38),
              fill=ORANGE, outline=PAPER, width=4)
    return layer


def _build_world(photos: list[Path], scenes: list[dict]) -> tuple[Image.Image, list[dict]]:
    world_h = max(2160, 500 + ((len(scenes) + 2) // 3) * 900)\n    world = Image.new("RGB", (WORLD_W, world_h), NAVY)
    d = ImageDraw.Draw(world)
    for x in range(0, WORLD_W, 100):
        d.line((x, 0, x, WORLD_H), fill=(23, 37, 57), width=1)
    for y in range(0, WORLD_H, 100):
        d.line((0, y, WORLD_W, y), fill=(23, 37, 57), width=1)
    d.text((150, 90), "DOCUMENTARY / EVIDENCE ARCHIVE", font=_font(38, mono=True), fill=(158, 176, 196))
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
    # Connect card-edge pins, not photo faces, with orange evidence strings.
    for i in range(len(cards) - 1):
        a = card_anchor(cards[i], 0.0, -0.46)
        b = card_anchor(cards[i + 1], 0.0, -0.46)
        d.line((a, b), fill=ORANGE, width=5)
        for px, py in (a, b):
            d.ellipse((px - 9, py - 9, px + 9, py + 9), fill=ORANGE, outline=PAPER, width=2)
    return world, cards


def _camera_center(index: int, total: int) -> tuple[float, float]:
    cols = 3
    row, col = divmod(index, cols)
    return (620 + col * 1120, 570 + row * 900)


def _draw_overlay(frame: Image.Image, scene: dict, elapsed: float, scene_duration: float,
                  index: int, total: int) -> None:
    d = ImageDraw.Draw(frame, "RGBA")
    w, h = frame.size
    # Typed mono label, orange underline and a hand-drawn target circle.
    label = str(scene.get("board_label") or scene.get("title") or f"CASE FILE {index + 1:02d}").upper()[:48]
    reveal = min(1.0, max(0.0, elapsed / 0.75))
    label = label[:max(1, int(len(label) * reveal))]
    d.rounded_rectangle((72, 64, min(w - 72, 820), 142), radius=8, fill=(7, 12, 20, 205),
                        outline=(255, 107, 0, 230), width=2)
    d.text((96, 82), label, font=_font(30, mono=True), fill=(245, 241, 230, 255))
    underline_w = int(min(600, 18 * elapsed * 30))
    d.line((96, 151, 96 + underline_w, 151), fill=ORANGE + (255,), width=5)
    if elapsed > min(1.2, scene_duration * 0.25):
        pulse = 1 + 0.035 * math.sin(elapsed * 5)
        rx, ry = int(100 * pulse), int(64 * pulse)
        cx, cy = w - 220, 190
        d.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), outline=ORANGE + (240,), width=5)
    if index == total - 1 and elapsed > scene_duration - 1.5:
        title = "THE EVIDENCE CONNECTS"
        f = _font(42, True)
        d.text((w - 760, h - 110), title, font=f, fill=ORANGE + (255,))


def render_continuous_board(photos: list[Path], scenes: list[dict], durations: list[float],
                            output: Path, width: int = 1920, height: int = 1080,
                            fps: int = 30, quality: int = 22) -> Path:
    if not photos or len(photos) != len(scenes) or len(scenes) != len(durations):
        raise ValueError("Photos, scenes and durations must have the same non-zero length.")
    if any(d <= 0 for d in durations):
        raise ValueError("Every scene duration must be positive.")
    world, _ = _build_world(photos, scenes)
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "-",
           "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(quality),
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    total_duration = sum(durations)
    starts = []
    cursor = 0.0
    for duration in durations:
        starts.append(cursor)
        cursor += duration
    try:
        frame_count = int(math.ceil(total_duration * fps))
        for fi in range(frame_count):
            t = min(total_duration - 1 / fps, fi / fps)
            idx = max(i for i, start in enumerate(starts) if start <= t)
            local = t - starts[idx]
            cx, cy = _camera_center(idx, len(scenes))
            # Ease from the previous scene's camera position, then drift gently.
            if idx > 0 and local < 1.2:
                px, py = _camera_center(idx - 1, len(scenes))
                q = min(1.0, local / 1.2)
                q = q * q * (3 - 2 * q)
                cx, cy = px + (cx - px) * q, py + (cy - py) * q
            zoom = 0.92 + 0.045 * min(1.0, local / max(2.0, durations[idx]))
            cx += math.sin(local * 0.19) * 16
            cy += math.cos(local * 0.15) * 12
            world_w, world_h = world.size\n            crop_w, crop_h = int(world_w / zoom), int(world_h / zoom)
            left = max(0, min(WORLD_W - crop_w, int(cx - crop_w / 2)))
            top = max(0, min(WORLD_H - crop_h, int(cy - crop_h / 2)))
            frame = world.crop((left, top, left + crop_w, top + crop_h)).resize(
                (width, height), Image.Resampling.LANCZOS)
            _draw_overlay(frame, scenes[idx], local, durations[idx], idx, len(scenes))
            proc.stdin.write(frame.tobytes())
    except BrokenPipeError as exc:
        raise RuntimeError("FFmpeg stopped while rendering the continuous board.") from exc
    finally:
        proc.stdin.close()
    stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
    code = proc.wait()
    if code:
        raise RuntimeError(f"FFmpeg board render failed: {stderr[-4000:]}")
    return output
