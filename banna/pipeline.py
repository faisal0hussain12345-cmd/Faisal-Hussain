from __future__ import annotations
import json, os, subprocess
from pathlib import Path
from .config import Settings, find_voiceover
from .audio import probe_audio, silence_ranges, scene_boundaries
from .images import resolve_scene_images
from .board import render_scene, concat_and_mux

def load_storyboard(path: Path) -> dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("scenes"),list) or not data["scenes"]:
        raise ValueError("storyboard.json must contain a non-empty scenes array.")
    for i,s in enumerate(data["scenes"],1):
        if not (s.get("image") or s.get("image_prompt")):
            raise ValueError(f"Scene {i} must contain image or image_prompt.")
    return data

def render(storyboard_path: Path | None = None) -> Path:
    settings=Settings.from_env()
    voice=find_voiceover(settings)
    storyboard_path=storyboard_path or Path("storyboard.json")
    if not storyboard_path.is_file() and Path("storyboard.example.json").is_file():
        storyboard_path=Path("storyboard.example.json")
    if not storyboard_path.is_file():
        raise FileNotFoundError("No storyboard found. Create storyboard.json from storyboard.example.json.")
    storyboard=load_storyboard(storyboard_path)
    info=probe_audio(voice); duration=info["duration"]
    silences=silence_ranges(voice)
    photos=resolve_scene_images(storyboard,settings.photos_dir,settings.generated_dir,settings.image_model)
    bounds=scene_boundaries(duration,len(photos),silences)
    work=Path("work/render"); work.mkdir(parents=True,exist_ok=True)
    segments=[]
    for i,(photo,scene) in enumerate(zip(photos,storyboard["scenes"]),1):
        start,end=bounds[i-1],bounds[i]
        if end-start < 0.5: continue
        target=work/f"scene_{i:03d}.mp4"
        print(f"[BANNA] Rendering scene {i}/{len(photos)} ({end-start:.2f}s)",flush=True)
        render_scene(photo,scene,i,len(photos),end-start,target,settings.width,settings.height,settings.fps)
        segments.append(target)
    if not segments: raise RuntimeError("No valid visual scenes were rendered.")
    output=settings.output_dir/"BANNA_documentary_1080p.mp4"
    concat_and_mux(segments,voice,output,duration)
    print(f"[BANNA] Finished: {output} | voice-over {duration:.2f}s",flush=True)
    return output
