"""
OpenRouter client using plain `requests` — deliberately NOT using the `openai`
Python package, to avoid the dependency/environment issues that came up
before. OpenRouter's API is just a normal REST endpoint.

Model: "openrouter/free" — OpenRouter's own auto-router, picks a currently
working free model. This is why you might see different underlying models
(e.g. "inclusionai/ling-3.0-flash-fin:free") across different calls — that's
expected, not a bug.

Free tier: 50 requests/day, 20/min (1,000/day after the account has ever
purchased $10 of credit). Be mindful of this while testing.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "openrouter/free"


def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """One LLM call via OpenRouter. Returns the raw text content of the reply."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key "
            "from https://openrouter.ai/keys"
        )

    body: dict = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    response = requests.post(
        url=OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    # Some free models include a "reasoning" field alongside "content" (e.g.
    # reasoning-capable models routed via OpenRouter's auto-router) - we only
    # ever want the actual answer, never the reasoning trace.
    return data["choices"][0]["message"]["content"] or ""
