from __future__ import annotations
import json, subprocess
from pathlib import Path
from .config import Settings, find_voiceover
from .audio import probe_audio
from .timing import narration_timeline, align_scenes_to_words
from .transcription import transcribe_word_timestamps
from .images import resolve_scene_images
from .board import concat_and_mux
from .documentary_engine import render_continuous_board
from .sound import synthesize_bed
from .qc import validate_final_video, extract_contact_sheet
from .vintage import render_vintage_clip

def load_storyboard(path: Path) -> dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("scenes"),list) or not data["scenes"]:
        raise ValueError("storyboard.json must contain a non-empty scenes array.")
    if len(data["scenes"]) > 60:
        raise ValueError("A storyboard may contain at most 60 visual beats.")
    for i,s in enumerate(data["scenes"],1):
        if not isinstance(s,dict) or not (s.get("image") or s.get("image_prompt") or s.get("map_image") or s.get("map_locations")):
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
    if not 60.0 <= duration <= 1200.0:
        raise ValueError(f"The documentary skill supports 60 seconds to 20 minutes; voice-over is {duration:.2f} seconds.")
    timeline=narration_timeline(voice,len(storyboard["scenes"]))
    try:
        word_times,detected_language=transcribe_word_timestamps(voice)
    except Exception as exc:
        word_times,detected_language=[], "fallback"
        print(f"[BANNA] Whisper failed; using silence-based timing: {exc}",flush=True)
    if word_times:
        timeline["boundaries"]=align_scenes_to_words(word_times,storyboard["scenes"],duration,timeline["boundaries"])
        timeline["scene_durations"]=[b-a for a,b in zip(timeline["boundaries"],timeline["boundaries"][1:])]
        print(f"[BANNA] Whisper word alignment active ({detected_language}, {len(word_times)} words)",flush=True)
    else:
        detected_language="unknown"
        print("[BANNA] Whisper unavailable; using FFmpeg silence-based scene timing",flush=True)
    photos=resolve_scene_images(storyboard,settings.photos_dir,settings.generated_dir,settings.image_model,settings.image_generation_enabled)
    if len(photos)!=len(storyboard["scenes"]):
        raise RuntimeError("Every scene must resolve to exactly one still image.")
    work=Path("work/render"); work.mkdir(parents=True,exist_ok=True)
    board=work/"continuous_evidence_board.mp4"
    print(f"[BANNA] Building one continuous evidence-board world ({len(photos)} stills)",flush=True)
    render_continuous_board(photos,storyboard["scenes"],timeline["scene_durations"],board,
                            settings.width,settings.height,settings.fps,quality=20,workers=2,surface=(storyboard.get("project") or {}).get("surface","map_board"))
    # Insert one bespoke cyanotype 2D sequence at the marked dramatic beat.
    film_ranges=[]
    insert_idx=next((i for i,scene in enumerate(storyboard["scenes"]) if scene.get("vintage_insert")),None)
    if insert_idx is not None:
        scene_duration=timeline["scene_durations"][insert_idx]
        insert_duration=min(5.0,scene_duration*0.55)
        if insert_duration>=2.0:
            insert_start=sum(timeline["scene_durations"][:insert_idx])+(scene_duration-insert_duration)/2
            film_ranges.append((insert_start,insert_start+insert_duration))
            insert=work/"vintage_2d_insert.mp4"
            render_vintage_clip(str(storyboard["scenes"][insert_idx].get("vintage_title") or storyboard["scenes"][insert_idx].get("title") or "THE TURNING POINT"),
                                insert_duration,insert,settings.fps,(settings.width,settings.height))
            spliced=work/"board_with_vintage_insert.mp4"
            post=insert_start+insert_duration
            cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(board),"-i",str(insert),
                 "-filter_complex",
                 f"[0:v]trim=start=0:duration={insert_start:.6f},setpts=PTS-STARTPTS[pre];"
                 f"[1:v]trim=duration={insert_duration:.6f},setpts=PTS-STARTPTS[ins];"
                 f"[0:v]trim=start={post:.6f},setpts=PTS-STARTPTS[post];"
                 "[pre][ins][post]concat=n=3:v=1:a=0[v]",
                 "-map","[v]","-an","-c:v","libx264","-preset","veryfast","-crf","20",
                 "-pix_fmt","yuv420p",str(spliced)]
            result=subprocess.run(cmd,capture_output=True,text=True)
            if result.returncode: raise RuntimeError(f"Vintage insert splice failed: {result.stderr[-3000:]}")
            board=spliced
            print(f"[BANNA] Inserted cyanotype 2D sequence at {insert_start:.2f}s",flush=True)
    bed=work/"sound_bed.wav"
    synthesize_bed(duration,timeline["boundaries"][:-1],bed,film_ranges=film_ranges)
    output=settings.output_dir/"BANNA_documentary_1080p.mp4"
    concat_and_mux([board],voice,bed,output,duration)
    qc=validate_final_video(output,duration)
    contact=extract_contact_sheet(output,settings.output_dir/"BANNA_QC_contact_sheet.jpg",samples=12)
    report={"voiceover":str(voice),"duration_seconds":duration,"resolution":f'{qc["width"]}x{qc["height"]}',
            "video_codec":qc["codec"],"scene_count":len(photos),"scene_durations":timeline["scene_durations"],
            "silence_ranges":timeline["silences"],"map_grid_inspections":[str(x) for x in sorted(settings.generated_dir.glob("*_map_grid.jpg"))],"word_alignment_language":detected_language,"word_alignment_count":len(word_times),"contact_sheet":str(contact),"visual_source":"still photographs and generated still illustrations only"}
    (settings.output_dir/"BANNA_word_timing.json").write_text(json.dumps({"language":detected_language,"words":word_times},indent=2),encoding="utf-8")
    (settings.output_dir/"BANNA_QC_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(f"[BANNA] QC passed: {qc['width']}x{qc['height']} / {qc['duration']:.2f}s",flush=True)
    print(f"[BANNA] Contact sheet: {contact}",flush=True)
    return output
