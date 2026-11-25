from __future__ import annotations

import os
import requests


def check_gemini() -> str:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY secret is missing")
    model = os.getenv("GEMINI_TEXT_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = requests.post(
        url,
        params={"key": key},
        json={"contents": [{"parts": [{"text": "Reply with exactly: BANNA GEMINI OK"}]}],
              "generationConfig": {"maxOutputTokens": 20, "temperature": 0}},
        timeout=60,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"Gemini API returned HTTP {response.status_code}; check key, quota and model access")
    data = response.json()
    if not data.get("candidates"):
        raise RuntimeError("Gemini API responded but returned no candidate")
    return f"Gemini connection OK ({model})"


def check_openrouter() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY secret is missing")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "HTTP-Referer": "https://github.com/faisal0hussain12345-cmd/Faisal-Hussain",
                 "X-Title": "BANNA API connection check"},
        json={"model": "openrouter/free",
              "messages": [{"role": "user", "content": "Reply with exactly: BANNA OPENROUTER OK"}],
              "max_tokens": 20, "temperature": 0},
        timeout=90,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenRouter API returned HTTP {response.status_code}; check key, free quota and provider availability")
    data = response.json()
    choices = data.get("choices") or []
    if not choices or not choices[0].get("message", {}).get("content"):
        raise RuntimeError("OpenRouter responded but returned no text")
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
