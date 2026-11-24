from __future__ import annotations
import json, math, wave
from pathlib import Path
import numpy as np

SAMPLE_RATE = 48000

def synthesize_bed(duration: float, scene_starts: list[float], output: Path, film_ranges: list[tuple[float,float]] | None = None) -> Path:
    """Stream a royalty-free synthetic suspense bed and synced editorial SFX."""
    output.parent.mkdir(parents=True, exist_ok=True)
    total = int(math.ceil(duration * SAMPLE_RATE))
    rng = np.random.default_rng(2026)
    whoosh_len = int(0.55 * SAMPLE_RATE)
    whoosh_noise = rng.normal(0, 1, whoosh_len).astype(np.float32)
    kernel = np.ones(80, dtype=np.float32) / 80
    whoosh = np.convolve(whoosh_noise, kernel, mode="same")
    env = np.sin(np.linspace(0, math.pi, whoosh_len, dtype=np.float32)) ** 2
    whoosh *= env / (np.max(np.abs(whoosh)) + 1e-8)
    thud_len = int(0.7 * SAMPLE_RATE)
    tt = np.arange(thud_len, dtype=np.float32) / SAMPLE_RATE
    thud = (np.sin(2 * np.pi * (72 * np.exp(-tt * 5) + 38) * tt) * np.exp(-tt * 6)).astype(np.float32)
    click = (rng.normal(0, 1, 1100) * np.exp(-np.arange(1100) / 180)).astype(np.float32)
    click_events = []
    for start in scene_starts[1:]:
        for j in range(10):
            click_events.append((int((start + j / 22) * SAMPLE_RATE), click))
    whoosh_events = [(int(t * SAMPLE_RATE), whoosh) for t in scene_starts[1:]]
    thud_events = [(int(t * SAMPLE_RATE), thud) for t in scene_starts[1:]]
    film_click = (rng.normal(0,1,576) * np.exp(-np.arange(576)/180)).astype(np.float32)
    film_hiss = (rng.normal(0,1,int(SAMPLE_RATE*0.08))).astype(np.float32)
    for start,end in (film_ranges or []):
        at=start
        while at<end:
            events.append((int(at*SAMPLE_RATE),film_click,0.045))
            at += 1/24
        events.append((int(start*SAMPLE_RATE),film_hiss,0.018))
    events = sorted([(i, a, 0.16) for i, a in whoosh_events] +
                    [(i, a, 0.08) for i, a in click_events] +
                    [(i, a, 0.24) for i, a in thud_events], key=lambda x: x[0])
    with wave.open(str(output), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        chunk_size = SAMPLE_RATE * 8
        for offset in range(0, total, chunk_size):
            end = min(total, offset + chunk_size)
            t = np.arange(offset, end, dtype=np.float32) / SAMPLE_RATE
            pad = (0.10 * np.sin(2*np.pi*55*t + np.sin(2*np.pi*0.07*t)*1.5)
                   + 0.045 * np.sin(2*np.pi*65.4*t)
                   + 0.025 * np.sin(2*np.pi*82.4*t))
            pad *= (0.55 + 0.45*np.sin(2*np.pi*t/23)**2)
            pad *= np.clip(t/2.5, 0, 1) * np.clip((duration-t)/2.0, 0, 1)
            # A restrained low pulse gives scene transitions a documentary rhythm.
            pulse = 0.025 * np.sin(2*np.pi*48*t) * (np.sin(2*np.pi*0.8*t) > 0)
            chunk = (pad + pulse).astype(np.float32)
            for pos, samples, gain in events:
                if pos >= end:
                    break
                if pos + len(samples) <= offset:
                    continue
                left = max(0, pos - offset)
                src_left = max(0, offset - pos)
                count = min(len(samples) - src_left, len(chunk) - left)
                if count > 0:
                    chunk[left:left+count] += samples[src_left:src_left+count] * gain
            wav.writeframes((np.clip(chunk, -0.95, 0.95) * 32767).astype("<i2").tobytes())
    return output
