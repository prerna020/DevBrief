from __future__ import annotations

import os

from dotenv import load_dotenv
from groq import AsyncGroq

load_dotenv()


def create_groq_client() -> AsyncGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to .env (see .env.example).")
    return AsyncGroq(api_key=api_key)

