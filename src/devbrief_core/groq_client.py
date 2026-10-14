from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()


def create_groq_client() -> AsyncOpenAI:
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env (see .env.example).")
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    return AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
    )
