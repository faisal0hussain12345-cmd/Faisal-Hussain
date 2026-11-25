from __future__ import annotations

import os
from pathlib import Path
import requests

from .api_check import _gemini_models

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _generate_with_model(key: str, model: str, prompt: str) -> str:
    response = requests.post(
        f"{GEMINI_BASE}/models/{model}:generateContent",
        params={"key": key},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.55, "maxOutputTokens": 8192},
        },
        timeout=240,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:600]}")
    data = response.json()
    chunks = []
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if isinstance(part.get("text"), str):
                chunks.append(part["text"])
    result = "\n".join(chunks).strip()
    if not result:
        raise RuntimeError("Gemini returned no narration text")
    return result


def generate_script(topic: str, audience: str, language: str, duration_minutes: int) -> str:
    """Create a narration draft with a currently available Gemini Flash model."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to GitHub Actions secrets.")
    if not topic.strip():
        raise ValueError("A documentary topic is required.")
    if not 1 <= duration_minutes <= 60:
        raise ValueError("Duration must be between 1 and 60 minutes.")
    configured = os.getenv("GEMINI_TEXT_MODEL", "auto").strip()
    models = [configured] if configured and configured.lower() != "auto" else _gemini_models(key)
    prompt = (
        "Write a documentary narration draft. Do not invent facts, dates, quotations, statistics, "
        "or named sources. Mark every claim that needs research with [VERIFY SOURCE]. Separate "
        "known background from claims needing verification. Do not pretend that this draft is "
        "fact-checked. Use a compelling but responsible documentary voice.\n"
        f"Target audience: {audience}\nLanguage: {language}\n"
        f"Topic: {topic}\nTarget duration: {duration_minutes} minutes\n"
        "Return: working title, short synopsis, chapter outline, then the complete narration."
    )
    errors = []
    for model in models:
        try:
            return _generate_with_model(key, model, prompt)
        except RuntimeError as exc:
            errors.append(f"{model}: {exc}")
            if "HTTP 404" not in str(exc):
                break
    raise RuntimeError("No available Gemini Flash model completed generation. " + "; ".join(errors[:4]))


def generate_script_file(topic: str, audience: str, language: str,
                         duration_minutes: int, destination: Path) -> Path:
    result = generate_script(topic, audience, language, duration_minutes)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result + "\n", encoding="utf-8")
    return destination
