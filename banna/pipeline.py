from __future__ import annotations
import json, subprocess
from pathlib import Path
from .config import Settings, find_voiceover
from .audio import probe_audio
from .timing import narration_timeline
from .images import resolve_scene_images
from .board import concat_and_mux
from .documentary_engine import render_continuous_board
from .sound import synthesize_bed
from .qc import validate_final_video, extract_contact_sheet

def load_storyboard(path: Path) -> dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("scenes"),list) or not data["scenes"]:
        raise ValueError("storyboard.json must contain a non-empty scenes array.")
    if len(data["scenes"]) > 60:
        raise ValueError("A storyboard may contain at most 60 visual beats.")
    for i,s in enumerate(data["scenes"],1):
        if not isinstance(s,dict) or not (s.get("image") or s.get("image_prompt")):
            raise ValueError(f"Scene {i} must contain image or image_prompt.")
    return data

def render(storyboard_path: Path | None = None) -> Path:
    settings=Settings.from_env()
    if (settings.width,settings.height)!=(1920,1080):
        raise ValueError("The skill delivery profile is fixed at 1920x1080.")
    if settings.fps != 30:
        raise ValueError("The skill delivery profile is fixed at 30 fps.")
    voice=find_voiceover(settings)
    storyboard_path=storyboard_path or Path("storyboard.json")
    if not storyboard_path.is_file():
        raise FileNotFoundError("storyboard.json is missing. Prepare a story-specific visual plan before rendering.")
    storyboard=load_storyboard(storyboard_path)
    duration=probe_audio(voice)["duration"]
    timeline=narration_timeline(voice,len(storyboard["scenes"]))
    photos=resolve_scene_images(storyboard,settings.photos_dir,settings.generated_dir,settings.image_model)
    if len(photos)!=len(storyboard["scenes"]):
        raise RuntimeError("Every scene must resolve to exactly one still image.")
    work=Path("work/render"); work.mkdir(parents=True,exist_ok=True)
    board=work/"continuous_evidence_board.mp4"
    print(f"[BANNA] Building one continuous evidence-board world ({len(photos)} stills)",flush=True)
    render_continuous_board(photos,storyboard["scenes"],timeline["scene_durations"],board,
                            settings.width,settings.height,settings.fps,quality=20)
    bed=work/"sound_bed.wav"
    synthesize_bed(duration,timeline["boundaries"][:-1],bed)
    output=settings.output_dir/"BANNA_documentary_1080p.mp4"
    concat_and_mux([board],voice,bed,output,duration)
    qc=validate_final_video(output,duration)
    contact=extract_contact_sheet(output,settings.output_dir/"BANNA_QC_contact_sheet.jpg",samples=12)
    report={"voiceover":str(voice),"duration_seconds":duration,"resolution":f'{qc["width"]}x{qc["height"]}',
            "video_codec":qc["codec"],"scene_count":len(photos),"scene_durations":timeline["scene_durations"],
            "silence_ranges":timeline["silences"],"contact_sheet":str(contact),"visual_source":"still photographs and generated still illustrations only"}
    (settings.output_dir/"BANNA_QC_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(f"[BANNA] QC passed: {qc['width']}x{qc['height']} / {qc['duration']:.2f}s",flush=True)
    print(f"[BANNA] Contact sheet: {contact}",flush=True)
    return output
