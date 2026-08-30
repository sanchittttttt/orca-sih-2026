"""
Thin wrapper around OpenRouter (free tier). OpenRouter mimics OpenAI's API format,
so we reuse the `openai` SDK and just point it at a different base_url.

Free tier constraints: 50 requests/day, 20/min (1,000/day if the account has ever
purchased $10 of credit). Keep this in mind while testing.

Model: "openrouter/free" — OpenRouter's own auto-router, chosen because
OpenRouter's free model catalogue rotates/gets delisted often; this avoids
hardcoding a specific model ID that might vanish mid-hackathon.
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client: OpenAI | None = None
MODEL = "openrouter/free"


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY not set. Copy .env.example to .env and add your key "
                "from https://openrouter.ai/keys"
            )
        _client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    return _client


def call_llm(system_prompt: str, user_prompt: str, json_mode: bool = False) -> str:
    """One LLM call. Returns the raw text content of the response."""
    client = get_client()
    kwargs: dict = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **kwargs,
    )
    return response.choices[0].message.content or ""
