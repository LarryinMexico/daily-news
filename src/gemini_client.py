from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Tuple


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def load_genai_modules() -> Tuple[Any, Any]:
    from google import genai
    from google.genai import types

    return genai, types


def extract_json_block(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in Gemini response")
    return json.loads(candidate[start : end + 1])


def call_gemini_json(prompt: str) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    genai, types = load_genai_modules()
    model_name = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
    last_error: Exception | None = None

    for attempt in range(1, 4):
        client = None
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                ),
            )
            print(f"[Gemini] model={model_name} attempt={attempt} success")
            return extract_json_block(response.text or "")
        except Exception as exc:
            last_error = exc
            print(f"[Gemini] model={model_name} attempt={attempt} failed: {exc}")
            time.sleep(5)
        finally:
            if client is not None:
                client.close()

    raise RuntimeError(f"Gemini request failed after retries: {last_error}")
