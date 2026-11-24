from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    image_model: str = "gemini-2.5-flash-image"
    image_provider: str = "gemini"
    output_dir: Path = ROOT / "output"
    photos_dir: Path = ROOT / "media" / "photos"
    generated_dir: Path = ROOT / "work" / "generated"
    voiceover: Path | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        voice = os.getenv("BANNA_VOICEOVER", "").strip()
        return cls(
            width=int(os.getenv("BANNA_WIDTH", "1920")),
            height=int(os.getenv("BANNA_HEIGHT", "1080")),
            fps=int(os.getenv("BANNA_FPS", "30")),
            image_model=os.getenv("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image"),
            image_provider=os.getenv("BANNA_IMAGE_PROVIDER", "gemini").lower(),
            output_dir=Path(os.getenv("BANNA_OUTPUT_DIR", str(ROOT / "output"))),
            photos_dir=Path(os.getenv("BANNA_PHOTOS_DIR", str(ROOT / "media" / "photos"))),
            generated_dir=Path(os.getenv("BANNA_GENERATED_DIR", str(ROOT / "work" / "generated"))),
            voiceover=Path(voice) if voice else None,
        )

def find_voiceover(settings: Settings) -> Path:
    if settings.voiceover and settings.voiceover.is_file():
        return settings.voiceover
    candidates = []
    for pattern in ("*.mp3", "*.wav", "*.m4a", "*.aac"):
        candidates.extend(p for p in ROOT.glob(pattern) if p.is_file())
    candidates = [p for p in candidates if p.name.lower() not in {"sample.mp3"}]
    if not candidates:
        raise FileNotFoundError(
            "No voice-over found. Add an MP3/WAV to the repository root or set BANNA_VOICEOVER."
        )
    return max(candidates, key=lambda p: p.stat().st_mtime)
