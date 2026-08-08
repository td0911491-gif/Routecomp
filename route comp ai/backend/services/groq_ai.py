"""
groq_ai.py
Two jobs, both via Groq's free/fast inference API (OpenAI-compatible endpoint):

1. parse_query(text)   -> pulls {"origin": ..., "destination": ...} out of a
                           free-text sentence like "cheapest way from Kolkata
                           to Delhi". Falls back to a plain regex first, and
                           only calls Groq if the regex can't confidently
                           parse it — keeps the app usable even with a bad/
                           missing key, and saves API calls for the easy case.

2. generate_summary(...) -> writes a short, plain-English recommendation
                             once the route + mode comparison is computed.

Set GROQ_API_KEY as an environment variable (see .env.example).
"""

import os
import re
import json
import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

FROM_TO_RE = re.compile(
    r"from\s+(?P<origin>.+?)\s+to\s+(?P<destination>.+?)(?:[.!?]|$)",
    re.IGNORECASE,
)


def _api_key() -> str | None:
    return os.environ.get("GROQ_API_KEY")


def _call_groq(messages, temperature=0.3, max_tokens=400) -> str | None:
    key = _api_key()
    if not key:
        return None
    try:
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError):
        return None


def parse_query(text: str) -> dict | None:
    """Returns {"origin": str, "destination": str} or None if it can't be parsed."""
    match = FROM_TO_RE.search(text)
    if match:
        return {
            "origin": match.group("origin").strip(),
            "destination": match.group("destination").strip(),
        }

    # Regex missed it (e.g. "Kolkata to Delhi, cheapest option please") — ask Groq.
    raw = _call_groq(
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the origin and destination place names from the user's "
                    "travel query. Reply with ONLY a JSON object like "
                    '{"origin": "...", "destination": "..."} and nothing else. '
                    'If you cannot find both, reply with {"origin": null, "destination": null}.'
                ),
            },
            {"role": "user", "content": text},
        ],
        temperature=0,
        max_tokens=100,
    )
    if not raw:
        return None

    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        parsed = json.loads(cleaned)
        if parsed.get("origin") and parsed.get("destination"):
            return {"origin": parsed["origin"], "destination": parsed["destination"]}
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def generate_summary(origin: str, destination: str, options: list[dict], badges: dict) -> str:
    """Short natural-language recommendation. Falls back to a templated
    sentence if no Groq key is set or the call fails, so the app still works."""
    fallback = (
        f"From {origin} to {destination}: {badges.get('cheapest', 'N/A')} is cheapest, "
        f"{badges.get('fastest', 'N/A')} is fastest, and {badges.get('most_luxurious', 'N/A')} "
        f"is the most comfortable option."
    )

    table = "\n".join(
        f"- {o['mode']}: {o['duration_hours']}h, ${o['cost_usd']} (₹{o['cost_inr']}), comfort {o['comfort']}/5"
        for o in options
    )
    raw = _call_groq(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise travel assistant. Given a list of transport "
                    "options with time, cost, and comfort, write a 2-3 sentence "
                    "plain-English recommendation. Mention the cheapest, fastest, "
                    "and most comfortable picks by name, and add one practical tip. "
                    "No markdown, no headers."
                ),
            },
            {
                "role": "user",
                "content": f"Trip: {origin} to {destination}\n\nOptions:\n{table}",
            },
        ],
        temperature=0.6,
        max_tokens=200,
    )
    return raw.strip() if raw else fallback
