"""
Thin wrapper around Google's Gemini API.

If no GEMINI_API_KEY is configured, the service falls back to canned
"demo mode" responses so the rest of the app (routes, frontend, UX)
can be built and tested without a live key. Once a key is added to
.env, real Gemini calls take over automatically -- no code changes
needed.
"""

import json
import os
import re
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

_demo_mode = not API_KEY

if not _demo_mode:
    from google import genai
    from google.genai import types as genai_types

    _client = genai.Client(api_key=API_KEY)


def is_demo_mode() -> bool:
    return _demo_mode


def _extract_json(raw_text: str) -> Dict[str, Any]:
    """Gemini sometimes wraps JSON in markdown fences, adds stray trailing
    characters, or (occasionally) cuts off the very last closing brace.
    Strip fences, try parsing as-is, and if that fails, attempt to repair
    by balancing any unclosed brackets/braces before parsing again."""
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    decoder = json.JSONDecoder()
    try:
        obj, _ = decoder.raw_decode(cleaned)
        return obj
    except json.JSONDecodeError:
        open_brackets = cleaned.count("[") - cleaned.count("]")
        open_braces = cleaned.count("{") - cleaned.count("}")
        repaired = cleaned + ("]" * max(open_brackets, 0)) + ("}" * max(open_braces, 0))
        obj, _ = decoder.raw_decode(repaired)
        return obj

def generate_json(system_prompt: str, user_prompt: str, demo_fallback: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ask Gemini to respond with a single JSON object and parse it.
    Falls back to demo_fallback if no API key is configured or the call fails.
    """
    if _demo_mode:
        return demo_fallback

    try:
        full_prompt = (
            f"{system_prompt}\n\n"
            "Respond with ONLY a valid JSON object. No markdown fences, no preamble, no commentary. "
            "Keep every explanation or context field to 1-2 concise sentences.\n\n"
            f"{user_prompt}"
        )
        response = _client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.4,
                response_mime_type="application/json",
                max_output_tokens=8192,
            ),
        )
        print("RAW GEMINI OUTPUT:", response.text)
        return _extract_json(response.text)
    except Exception as exc:  # noqa: BLE001 - surface a clean fallback instead of a 500
        print(f"GEMINI ERROR: {exc}")
        fallback = dict(demo_fallback)
        fallback["_warning"] = f"Live AI call failed, showing demo content instead ({exc})"
        return fallback