from __future__ import annotations
import re
from pathlib import Path
from .audio import probe_audio, silence_ranges

def narration_timeline(audio: Path, scene_count: int) -> dict:
    """Estimate scene starts from exact media duration, then snap to detected pauses."""
    if scene_count < 1: raise ValueError("scene_count must be positive")
    duration = probe_audio(audio)["duration"]
    silences = silence_ranges(audio)
    boundaries = [0.0]
    for i in range(1, scene_count):
        target = duration * i / scene_count
        candidates = [end for _, end in silences if 0.35 < end < duration - 0.35 and abs(end-target) <= 2.5]
        boundaries.append(min(candidates, key=lambda x: abs(x-target)) if candidates else target)
    boundaries.append(duration)
    clean = [boundaries[0]]
    for t in sorted(boundaries[1:-1]):
        if t-clean[-1] >= 0.75 and duration-t >= 0.75: clean.append(t)
    clean.append(duration)
    return {"duration": duration, "silences": silences, "boundaries": clean,
            "scene_durations": [b-a for a,b in zip(clean,clean[1:])]}

def estimate_word_times(text: str, duration: float) -> list[dict]:
    """Fallback word timing estimate; explicitly marked approximate, never presented as forced alignment."""
    words = re.findall(r"\S+", text)
    if not words: return []
    weights = [max(1, len(re.findall(r"[aeiouy]+", w.lower()))) for w in words]
    total = sum(weights); cursor = 0.0; out=[]
    for word, weight in zip(words, weights):
        start=cursor; cursor += duration*weight/total
        out.append({"word":word,"start":start,"end":cursor,"estimated":True})
    return out
