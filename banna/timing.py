from __future__ import annotations
import re
from pathlib import Path
from .audio import probe_audio, silence_ranges

def narration_timeline(audio: Path, scene_count: int) -> dict:
    """Estimate scene starts from media duration, snapping safely to distinct pauses."""
    if scene_count < 1: raise ValueError("scene_count must be positive")
    duration = probe_audio(audio)["duration"]
    if duration < scene_count * 0.5:
        raise ValueError("Too many storyboard scenes for the voice-over duration; each scene needs at least 0.5 seconds.")
    silences = silence_ranges(audio)
    boundaries = [0.0]
    for i in range(1, scene_count):
        target = duration * i / scene_count
        low = boundaries[-1] + 0.5
        high = duration - (scene_count-i)*0.5
        candidates = [end for _, end in silences if low <= end <= high and abs(end-target) <= 2.5]
        chosen = min(candidates, key=lambda x: abs(x-target)) if candidates else target
        chosen = min(high, max(low, chosen))
        boundaries.append(chosen)
    boundaries.append(duration)
    return {"duration": duration, "silences": silences, "boundaries": boundaries,
            "scene_durations": [b-a for a,b in zip(boundaries,boundaries[1:])]}

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

def align_scenes_to_words(words: list[dict], scenes: list[dict], duration: float,
                          fallback_boundaries: list[float]) -> list[float]:
    """Use spoken cue phrases when available; otherwise preserve pause-based boundaries."""
    if len(fallback_boundaries) != len(scenes)+1:
        raise ValueError("Fallback boundaries must bracket every scene.")
    if not words:
        return fallback_boundaries
    tokens=[re.sub(r"[^a-z0-9]+","",w.get("word","").lower()) for w in words]
    starts=[float(w["start"]) for w in words]
    result=[0.0]
    cursor=0
    for i in range(1,len(scenes)):
        scene=scenes[i]
        cue=str(scene.get("trigger_words") or scene.get("narration_cue") or "").lower()
        phrase=[re.sub(r"[^a-z0-9]+","",x) for x in cue.split()]
        phrase=[x for x in phrase if x]
        if len(phrase)>6: phrase=phrase[:6]
        found=None
        if phrase:
            for j in range(cursor,max(cursor,len(tokens)-len(phrase)+1)):
                if tokens[j:j+len(phrase)]==phrase:
                    found=starts[j]; cursor=j+len(phrase); break
        target=float(found if found is not None else fallback_boundaries[i])
        low=result[-1]+0.5
        high=duration-(len(scenes)-i)*0.5
        result.append(min(high,max(low,target)))
    result.append(duration)
    return result
