from __future__ import annotations

import os
from pathlib import Path
import requests

from .api_check import _extract_openrouter_text


def review_script(script: str, model: str | None = None) -> tuple[str, str]:
    """Review a narration using OpenRouter's zero-cost free-model router only."""
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Add it to GitHub Actions secrets.")
    if not script.strip():
        raise ValueError("The script is empty.")
    selected = (model or os.getenv("OPENROUTER_FREE_MODEL", "openrouter/free")).strip()
    if not (selected == "openrouter/free" or selected.endswith(":free")):
        raise ValueError("BANNA free mode accepts only openrouter/free or a model ID ending in :free.")
    prompt = (
        "You are an editorial reviewer for a factual documentary narration. Review clarity, "
        "chronology, repetition, unsupported certainty, and audience suitability. Do not invent "
        "facts, dates, quotations, sources, or events. Do not claim claims are verified. Return "
        "a concise issue list, lines requiring external source verification, and a polished "
        "version preserving the original meaning. Label uncertain claims clearly.\n\nSCRIPT:\n"
        + script
    )
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/faisal0hussain12345-cmd/Faisal-Hussain",
            "X-Title": "BANNA Documentary Studio",
        },
        json={
            "model": selected,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.2,
        },
        timeout=240,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"OpenRouter free-model request failed ({response.status_code}): {response.text[:1000]}"
        )
    data = response.json()
    result = _extract_openrouter_text(data)
    if not result:
        choice = (data.get("choices") or [{}])[0]
        finish = choice.get("finish_reason", "unknown")
        raise RuntimeError(
            f"OpenRouter returned no review text (finish_reason={finish}). "
            "Retry later or choose a currently available model ending in :free."
        )
    actual_model = str(data.get("model") or selected)
    return result, actual_model


def review_file(source: Path, destination: Path, model: str | None = None) -> Path:
    result, actual_model = review_script(source.read_text(encoding="utf-8"), model=model)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        f"<!-- OpenRouter model: {actual_model} -->\n\n{result}\n", encoding="utf-8"
    )
    return destination
