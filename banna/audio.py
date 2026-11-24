from __future__ import annotations
import json, re, subprocess
from pathlib import Path

def _run(args: list[str]) -> str:
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise RuntimeError(p.stderr[-4000:])
    return p.stdout

def probe_audio(path: Path) -> dict:
    raw = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration:format_name",
                "-of", "json", str(path)])
    data = json.loads(raw)
    duration = float(data["format"]["duration"])
    if duration <= 0:
        raise ValueError("Voice-over duration is empty or invalid.")
    return {"duration": duration, "format": data["format"].get("format_name", "unknown")}

def silence_ranges(path: Path, noise_db: str = "-35dB", min_silence: float = 0.25) -> list[tuple[float,float]]:
    p = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
                        f"silencedetect=noise={noise_db}:d={min_silence}", "-f", "null", "-"],
                       capture_output=True, text=True)
    log = p.stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", log)]
    ranges = []
    for i, start in enumerate(starts):
        end = ends[i] if i < len(ends) else start
        ranges.append((start, end))
    return ranges

def scene_boundaries(duration: float, count: int, silences: list[tuple[float,float]]) -> list[float]:
    if count < 1:
        raise ValueError("At least one scene is required.")
    boundaries = [0.0]
    for i in range(1, count):
        target = duration * i / count
        candidates = [b for a,b in silences if 0.4 < b < duration - 0.4]
        nearby = [b for b in candidates if abs(b-target) <= min(3.0, duration/count*0.35)]
        boundaries.append(min(nearby, key=lambda b: abs(b-target)) if nearby else target)
    boundaries.append(duration)
    boundaries = sorted(boundaries)
    # Enforce positive scene durations after snapping to silence.
    clean = [boundaries[0]]
    for value in boundaries[1:-1]:
        if value - clean[-1] >= 1.0 and duration - value >= 1.0:
            clean.append(value)
    clean.append(duration)
    return clean
