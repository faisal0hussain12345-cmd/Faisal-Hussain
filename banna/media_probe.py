from __future__ import annotations

import re
import subprocess
from pathlib import Path


def probe_media(path: Path) -> dict:
    """Read container/stream metadata from FFmpeg's own input inspection output."""
    result = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(path)],
        capture_output=True, text=True,
    )
    output = result.stderr or result.stdout
    duration_match = re.search(
        r"Duration:\s*(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)", output
    )
    if not duration_match:
        raise RuntimeError(f"FFmpeg could not read media metadata for {path}: {output[-2000:]}")
    hours, minutes, seconds = duration_match.groups()
    duration = int(hours) * 3600 + int(minutes) * 60 + float(seconds)

    format_match = re.search(r"Input #\d+,\s*([^,\r\n]+)", output)
    format_name = format_match.group(1).strip() if format_match else "unknown"

    video = None
    video_match = re.search(
        r"Video:\s*([A-Za-z0-9_]+).*?(\d{3,5})x(\d{3,5}).*?(\d+(?:\.\d+)?)\s*fps",
        output, re.S,
    )
    if video_match:
        codec, width, height, fps = video_match.groups()
        video = {
            "codec": codec.lower(),
            "width": int(width),
            "height": int(height),
            "fps": float(fps),
        }

    audio = None
    audio_match = re.search(
        r"Audio:\s*([A-Za-z0-9_]+).*?(\d{4,6})\s*Hz.*?(mono|stereo|[1-9](?:\.\d)?)",
        output, re.S | re.I,
    )
    if audio_match:
        codec, sample_rate, channel_label = audio_match.groups()
        channel_label = channel_label.lower()
        channels = {"mono": 1, "stereo": 2}.get(channel_label)
        if channels is None:
            channels = int(float(channel_label) * 2) if "." in channel_label else int(channel_label)
        audio = {
            "codec": codec.lower(),
            "sample_rate": int(sample_rate),
            "channels": channels,
            "duration": duration,
        }

    return {
        "duration": duration,
        "format": format_name,
        "video": video,
        "audio": audio,
    }
