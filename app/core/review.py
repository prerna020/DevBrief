from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from .groq_client import create_groq_client
from .prompts.learning_mode_v1 import build_learning_mode_prompt
from .schema import REVIEW_JSON_SCHEMA, Review

RETRY_DELAYS_SECONDS = (0.5, 1.5, 4.0)


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


@dataclass(frozen=True)
class ReviewResult:
    review: Review
    usage: TokenUsage
    latency_ms: float
    attempts: int


class ReviewError(RuntimeError):
    def __init__(self, message: str, diff: str, last_error: Exception | None, attempts: int) -> None:
        super().__init__(message)
        self.diff_excerpt, self.last_error, self.attempts = diff[:1000], last_error, attempts


def _is_retriable(error: Exception) -> bool:
    return isinstance(error, (json.JSONDecodeError, ValidationError, ConnectionError, TimeoutError, OSError))


async def review_diff(diff: str, file_path: str, team_rules: list[str] = []) -> ReviewResult:
    client = create_groq_client()
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    last_error: Exception | None = None
    for attempt, delay in enumerate(RETRY_DELAYS_SECONDS, start=1):
        started_at = time.perf_counter()
        try:
            completion = await client.chat.completions.create(
                model=model, temperature=0.2,
                response_format={"type": "json_schema", "json_schema": {"name": "review", "strict": True, "schema": REVIEW_JSON_SCHEMA}},
                messages=[{"role": "system", "content": build_learning_mode_prompt(team_rules)}, {"role": "user", "content": f"File path: {file_path}\n\nDiff:\n<UNTRUSTED_DIFF_CONTENT>\n{diff}\n</UNTRUSTED_DIFF_CONTENT>"}],
            )
            content = completion.choices[0].message.content if completion.choices else None
            if not content:
                raise ValueError("Groq returned an empty response.")
            review = Review.model_validate(json.loads(content))
            usage: Any = completion.usage
            return ReviewResult(review, TokenUsage(getattr(usage, "prompt_tokens", None), getattr(usage, "completion_tokens", None), getattr(usage, "total_tokens", None)), (time.perf_counter() - started_at) * 1000, attempt)
        except Exception as error:
            last_error = error
            if not _is_retriable(error) or attempt == len(RETRY_DELAYS_SECONDS):
                break
            await asyncio.sleep(delay)
    raise ReviewError("Unable to generate a valid review after 3 attempts.", diff, last_error, len(RETRY_DELAYS_SECONDS))
