from __future__ import annotations
import os
from pathlib import Path

def transcribe_word_timestamps(audio: Path) -> tuple[list[dict], str]:
    """Optional local CPU Whisper alignment. Returns word timestamps and detected language."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return [], "unavailable"
    model_name=os.getenv("BANNA_WHISPER_MODEL","tiny")
    model=WhisperModel(model_name,device="cpu",compute_type="int8")
    segments, info=model.transcribe(str(audio),beam_size=1,word_timestamps=True,vad_filter=True)
    words=[]
    for segment in segments:
        for item in (segment.words or []):
            if item.word and item.start is not None and item.end is not None:
                words.append({"word":item.word.strip(),"start":float(item.start),"end":float(item.end)})
    return words, str(getattr(info,"language","unknown"))
