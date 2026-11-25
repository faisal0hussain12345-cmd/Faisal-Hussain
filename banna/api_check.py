from __future__ import annotations

import os
import requests

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _gemini_models(key: str) -> list[str]:
    response = requests.get(
        f"{GEMINI_BASE}/models",
        params={"key": key, "pageSize": 1000},
        timeout=45,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Gemini model-list request failed (HTTP {response.status_code}); "
            "check the key and Gemini API access"
        )
    payload = response.json()
    candidates = []
    for item in payload.get("models", []):
        name = str(item.get("name", "")).removeprefix("models/")
        methods = item.get("supportedGenerationMethods") or []
        if name and "generateContent" in methods and "flash" in name.lower():
            candidates.append(name)
    # Prefer the smallest currently available free-tier Flash model first.
    priority = (
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.8-flash",
        "gemini-3.1-flash",
        "gemini-3-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
    )
    ordered = []
    for prefix in priority:
        ordered.extend(name for name in candidates if name == prefix and name not in ordered)
    ordered.extend(name for name in sorted(candidates) if name not in ordered)
    if not ordered:
        raise RuntimeError(
            "Gemini API key is accepted, but Models API returned no Flash model "
            "supporting generateContent. Check AI Studio project/model access."
        )
    return ordered


def _gemini_generate(key: str, model: str) -> tuple[bool, str]:
    response = requests.post(
        f"{GEMINI_BASE}/models/{model}:generateContent",
        params={"key": key},
        json={
            "contents": [{"parts": [{"text": "Reply with exactly: BANNA GEMINI OK"}]}],
            "generationConfig": {"maxOutputTokens": 64, "temperature": 0},
        },
        timeout=60,
    )
    if response.status_code >= 400:
        return False, f"HTTP {response.status_code}"
    data = response.json()
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            if isinstance(part.get("text"), str) and part["text"].strip():
                return True, ""
    return False, "empty model response"


def check_gemini() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY secret is missing")
    configured = os.getenv("GEMINI_TEXT_MODEL", "auto").strip()
    if configured and configured.lower() != "auto":
        models = [configured]
    else:
        models = _gemini_models(key)
    failures = []
    for model in models:
        ok, reason = _gemini_generate(key, model)
        if ok:
            return f"Gemini connection OK ({model})"
        failures.append(f"{model}: {reason}")
        if reason not in ("HTTP 404", "empty model response"):
            break
    raise RuntimeError(
        "Gemini could not generate text with the available Flash models. "
        + "; ".join(failures[:5])
    )


def _extract_openrouter_text(data: dict) -> str:
    choices = data.get("choices") or []
    if choices:
        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()
        if isinstance(content, list):
            parts = [
                str(part.get("text", ""))
                for part in content
                if isinstance(part, dict) and part.get("type") in ("text", "output_text")
            ]
            joined = "\n".join(part for part in parts if part.strip()).strip()
            if joined:
                return joined
        refusal = message.get("refusal")
        if refusal:
            return str(refusal)
    # Defensive support for OpenRouter's Responses-style output if a gateway returns it.
    for item in data.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") in ("output_text", "text") and part.get("text"):
                    return str(part["text"]).strip()
    return ""


def check_openrouter() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY secret is missing")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/faisal0hussain12345-cmd/Faisal-Hussain",
            "X-Title": "BANNA API connection check",
        },
        json={
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": "Reply with exactly: BANNA OPENROUTER OK"}],
            "max_tokens": 512,
            "temperature": 0,
        },
        timeout=120,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"OpenRouter API returned HTTP {response.status_code}; "
            "check key, free quota and provider availability"
        )
    data = response.json()
    answer = _extract_openrouter_text(data)
    if not answer:
        choice = (data.get("choices") or [{}])[0]
        finish = choice.get("finish_reason", "unknown")
        usage = data.get("usage") or {}
        raise RuntimeError(
            "OpenRouter accepted the request but returned no text "
            f"(finish_reason={finish}, completion_tokens={usage.get('completion_tokens', 'unknown')}). "
            "The free provider may be warming up or unavailable; run the test again."
        )
    return f"OpenRouter free connection OK (model: {data.get('model', 'free router')})"


def main() -> int:
    failed = False
    for check in (check_gemini, check_openrouter):
        try:
            print("[PASS] " + check())
        except Exception as exc:
            failed = True
            print("[FAIL] " + str(exc))
    print("API check completed. Secret values were not printed.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
