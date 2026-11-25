from __future__ import annotations
import json, subprocess, os
from pathlib import Path
from .config import Settings, find_voiceover
from .audio import probe_audio
from .timing import narration_timeline, align_scenes_to_words
from .transcription import transcribe_word_timestamps
from .images import resolve_scene_images
from .board import concat_and_mux
from .documentary_engine import render_continuous_board
from .sound import synthesize_bed
from .qc import validate_final_video, extract_contact_sheet, extract_photo_contact_sheet
from .vintage import render_vintage_clip

def load_storyboard(path: Path) -> dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("scenes"),list) or not data["scenes"]:
        raise ValueError("storyboard.json must contain a non-empty scenes array.")
    if len(data["scenes"]) > 60:
        raise ValueError("A storyboard may contain at most 60 visual beats.")
    for i,s in enumerate(data["scenes"],1):
        if not isinstance(s,dict) or not (s.get("image") or s.get("image_prompt") or s.get("map_image") or s.get("map_locations") or s.get("graphic_type")):
            raise ValueError(f"Scene {i} must contain image or image_prompt.")
    return data

def validate_voiceover_topic(transcript: str, project: dict) -> None:
    expected = project.get("expected_topic_keywords") or []
    if not expected or not transcript.strip():
        return
    normalized = transcript.casefold()
    matches = [str(term) for term in expected if str(term).casefold() in normalized]
    minimum = int(project.get("minimum_topic_keyword_matches", min(2, len(expected))))
    if len(matches) < minimum:
        topic = str(project.get("expected_topic") or "the selected documentary topic")
        raise ValueError(
            f"Voice-over topic mismatch: this storyboard expects '{topic}', "
            f"but the supplied recording did not contain enough matching topic terms "
            f"({len(matches)}/{minimum}). Refusing to render unrelated audio against this story."
        )


def render(storyboard_path: Path | None = None) -> Path:
    settings=Settings.from_env()
    if (settings.width,settings.height)!=(1920,1080):
        raise ValueError("The skill delivery profile is fixed at 1920x1080.")
    if settings.fps != 30:
        raise ValueError("The skill delivery profile is fixed at 30 fps.")
    voice=find_voiceover(settings)
    # Optional short-preview mode: render only the first N seconds of the original narration.
    max_duration=float(os.getenv("BANNA_MAX_DURATION_SECONDS","0") or 0)
    if max_duration>0:
        preview_voice=Path("work/render/preview_voiceover.mp3")
        preview_voice.parent.mkdir(parents=True,exist_ok=True)
        result=subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-i",str(voice),
                               "-t",str(max_duration),"-vn","-c:a","libmp3lame","-q:a","3",str(preview_voice)],
                              capture_output=True,text=True)
        if result.returncode:
            raise RuntimeError(f"Could not trim preview narration: {result.stderr[-2000:]}")
        voice=preview_voice
    storyboard_path=storyboard_path or Path("storyboard.json")
    if not storyboard_path.is_file():
        raise FileNotFoundError("storyboard.json is missing. Prepare a story-specific visual plan before rendering.")
    storyboard=load_storyboard(storyboard_path)
    max_scenes=int(os.getenv("BANNA_MAX_SCENES","0") or 0)
    if max_scenes>0:
        storyboard["scenes"]=storyboard["scenes"][:max_scenes]
        if not storyboard["scenes"]:
            raise ValueError("Preview mode requires at least one storyboard scene.")
    duration=probe_audio(voice)["duration"]
    print(f"[BANNA] Original voice-over duration: {duration:.2f}s ({duration/60:.2f} min)",flush=True)
    if not 60.0 <= duration <= 1200.0:
        raise ValueError(f"The documentary skill supports 60 seconds to 20 minutes; voice-over is {duration:.2f} seconds.")
    timeline=narration_timeline(voice,len(storyboard["scenes"]))
    try:
        word_times,detected_language=transcribe_word_timestamps(voice)
    except Exception as exc:
        word_times,detected_language=[], "fallback"
        print(f"[BANNA] Whisper failed; using silence-based timing: {exc}",flush=True)
    transcript_path=Path("work/render/voiceover_transcript.txt")
    if word_times:
        transcript_text=" ".join(str(item.get("word","")).strip() for item in word_times if item.get("word")).strip()
        transcript_path=Path("work/render/voiceover_transcript.txt")
        transcript_path.parent.mkdir(parents=True,exist_ok=True)
        transcript_path.write_text(transcript_text,encoding="utf-8")
        print("[BANNA] Voice-over transcript (first 2200 chars): "+transcript_text[:2200],flush=True)
        validate_voiceover_topic(transcript_text,storyboard.get("project") or {})
        timeline["boundaries"]=align_scenes_to_words(word_times,storyboard["scenes"],duration,timeline["boundaries"])
        timeline["scene_durations"]=[b-a for a,b in zip(timeline["boundaries"],timeline["boundaries"][1:])]
        print(f"[BANNA] Whisper word alignment active ({detected_language}, {len(word_times)} words)",flush=True)
    else:
        detected_language="unknown"
        print("[BANNA] Whisper unavailable; using FFmpeg silence-based scene timing",flush=True)
    photos=resolve_scene_images(storyboard,settings.photos_dir,settings.generated_dir,settings.image_model,settings.image_generation_enabled)
    if len(photos)!=len(storyboard["scenes"]):
        raise RuntimeError("Every scene must resolve to exactly one still image.")
    expected_photos = int((storyboard.get("project") or {}).get("minimum_unique_archival_photos", 0))
    photo_manifest = settings.generated_dir / "BANNA_photo_sources.json"
    photo_records = json.loads(photo_manifest.read_text(encoding="utf-8")) if photo_manifest.is_file() else []
    if expected_photos:
        if len(photos) < expected_photos or len(photo_records) < expected_photos:
            raise RuntimeError(
                f"Archival-photo QC failed: expected at least {expected_photos} source photographs, "
                f"but resolved {len(photos)} images and {len(photo_records)} source records."
            )
        source_pages = [str(item.get("source_page") or "") for item in photo_records]
        image_urls = [str(item.get("image_url") or "") for item in photo_records]
        if len(set(image_urls)) != len(image_urls):
            raise RuntimeError("Archival-photo QC failed: duplicate image URLs were detected.")
        if any(not item for item in source_pages + image_urls):
            raise RuntimeError("Archival-photo QC failed: every photograph must have a traceable source and image URL.")
    if min(timeline["scene_durations"]) < 8.0:
        raise RuntimeError("Narration timing QC failed: a visual beat is shorter than eight seconds.")
    work=Path("work/render"); work.mkdir(parents=True,exist_ok=True)
    photo_contact=extract_photo_contact_sheet(photos,storyboard["scenes"],settings.output_dir/"BANNA_Photo_Assets_Contact_Sheet.jpg")
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
            if str((storyboard.get("project") or {}).get("expected_topic", "")).casefold() == "manhattan project":
                from .manhattan_vintage import render_manhattan_vintage
                render_manhattan_vintage(str(storyboard["scenes"][insert_idx].get("vintage_title") or "TRINITY"),
                                         insert_duration,insert,settings.fps,(settings.width,settings.height))
            else:
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
    # Cue sheet follows the narration-aligned scene starts and marked visual beats.
    sound_cues=[]
    for i, scene in enumerate(storyboard["scenes"]):
        at=float(timeline["boundaries"][i])
        if i>0:
            sound_cues.append({"time":at,"type":"transition_whoosh","scene":scene.get("id")})
            sound_cues.append({"time":at+0.08,"type":"typing","scene":scene.get("id")})
        if scene.get("stamp"):
            sound_cues.append({"time":at+0.9,"type":"stamp","scene":scene.get("id")})
        if scene.get("vintage_insert"):
            sound_cues.append({"time":at+0.2,"type":"impact","scene":scene.get("id")})
        if scene.get("wireless_sfx"):
            sound_cues.append({"time":at+0.25,"type":"wireless","scene":scene.get("id")})
        if scene.get("highlight_sfx"):
            sound_cues.append({"time":at+0.5,"type":"circle","scene":scene.get("id")})
    cue_path=work/"cues.json"
    cue_path.write_text(json.dumps(sound_cues,indent=2),encoding="utf-8")
    bed=work/"sound_bed.wav"
    synthesize_bed(duration,timeline["boundaries"][:-1],bed,film_ranges=film_ranges,cues=sound_cues)
    output=settings.output_dir/"BANNA_documentary_1080p.mp4"
    concat_and_mux([board],voice,bed,output,duration)
    qc=validate_final_video(output,duration)
    contact=extract_contact_sheet(output,settings.output_dir/"BANNA_QC_contact_sheet.jpg",samples=24)
    report={"voiceover":str(voice),"duration_seconds":duration,"resolution":f'{qc["width"]}x{qc["height"]}',
            "video_codec":qc["codec"],"fps":qc["fps"],"audio_codec":qc["audio_codec"],"audio_duration":qc["audio_duration"],"audio_channels":qc["audio_channels"],"scene_count":len(photos),"scene_durations":timeline["scene_durations"],
            "silence_ranges":timeline["silences"],"map_grid_inspections":[str(x) for x in sorted(settings.generated_dir.glob("*_map_grid.jpg"))],"word_alignment_language":detected_language,"word_alignment_count":len(word_times),"contact_sheet":str(contact),"photo_contact_sheet":str(photo_contact),"unique_archival_photo_count":len(photo_records),"visual_source":"distinct archival still photographs with brief bespoke cyanotype insert"}
    (settings.output_dir/"BANNA_word_timing.json").write_text(json.dumps({"language":detected_language,"words":word_times},indent=2),encoding="utf-8")
    (settings.output_dir/"BANNA_sound_cues.json").write_text(json.dumps(sound_cues,indent=2),encoding="utf-8")
    if transcript_path.is_file():
        (settings.output_dir/"BANNA_voiceover_transcript.txt").write_text(transcript_path.read_text(encoding="utf-8"),encoding="utf-8")
    (settings.output_dir/"BANNA_QC_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(f"[BANNA] QC passed: {qc['width']}x{qc['height']} / {qc['duration']:.2f}s",flush=True)
    print(f"[BANNA] Contact sheet: {contact}",flush=True)
    return output
