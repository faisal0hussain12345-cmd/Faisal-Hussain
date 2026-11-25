from __future__ import annotations

import os
from pathlib import Path
import requests


def review_script(script: str, model: str | None = None) -> str:
    """Opt-in editorial review via OpenAI Responses API; one request may be billable."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it as a GitHub Actions secret.")
    if not script.strip():
        raise ValueError("The script is empty.")
    selected_model = (model or os.getenv("OPENAI_MODEL", "gpt-6-luna")).strip()
    prompt = (
        "Review this factual documentary narration for clarity, chronology, repetition, "
        "unsupported certainty, and audience suitability. Do not invent facts, dates, quotes, "
        "sources, or events. Do not claim facts are verified. Return a concise issue list, "
        "lines needing external source verification, and a polished version preserving meaning. "
        "Clearly label uncertain claims.\n\nSCRIPT:\n" + script
    )
    response = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": selected_model, "input": prompt},
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI script review failed ({response.status_code}): {response.text[:1200]}")
    data = response.json()
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"].strip()
    chunks = []
    for item in data.get("output", []):
        for part in item.get("content", []):
            if part.get("type") in {"output_text", "text"} and part.get("text"):
                chunks.append(part["text"])
    result = "\n".join(chunks).strip()
    if not result:
        raise RuntimeError("OpenAI returned no review text.")
    return result


def review_file(source: Path, destination: Path, model: str | None = None) -> Path:
    result = review_script(source.read_text(encoding="utf-8"), model=model)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result + "\n", encoding="utf-8")
    return destination
