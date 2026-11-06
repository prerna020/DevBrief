"""Per-review metrics for the LLM call: latency, tokens, estimated cost, outcome.

`track_llm_call` wraps the model call in `nodes/review.py`. It never changes
what the call returns or raises, and a failure to record metrics is logged and
swallowed, so metrics can never break a review. Rows are written to the
`review_metrics` table (see `packages/db/src/schema.ts`) on a background thread
so the review response is not delayed by the extra database round trip.
"""

import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from langchain_core.callbacks import get_usage_metadata_callback

load_dotenv()

logger = logging.getLogger(__name__)

# USD per 1,000,000 tokens: (input, output). List prices, so the estimated
# cost is what the review would cost without a free tier. A model that is not
# listed gets cost = NULL (shown as "unpriced" in the report), never a guess.
# Sources: Groq model page (gpt-oss, qwen), Google AI Studio list prices as
# tracked by models.litellm.ai (Gemini flash-lite), checked 2026-11-04.
# Edit this table when you add models or prices change.
PRICING_USD_PER_1M_TOKENS: dict[tuple[str, str], tuple[float, float]] = {
    ("groq", "openai/gpt-oss-20b"): (0.075, 0.30),
    ("groq", "openai/gpt-oss-120b"): (0.15, 0.60),
    ("groq", "qwen/qwen3.8-27b"): (0.80, 4.00),
    ("gemini", "gemini-flash-lite-latest"): (0.30, 2.50),
    ("gemini", "gemini-3.5-flash-lite"): (0.30, 2.50),
    ("gemini", "gemini-3.1-flash-lite"): (0.25, 1.50),
}


def estimate_cost_usd(
    provider: str, model: str, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    """Estimated list-price cost, or None if tokens or the model's price are unknown."""
    if input_tokens is None or output_tokens is None:
        return None
    if provider == "openrouter" and model.endswith(":free"):
        return 0.0
    price = PRICING_USD_PER_1M_TOKENS.get((provider, model))
    if price is None:
        return None
    input_price, output_price = price
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


@dataclass
class LlmCallMetrics:
    provider: str
    model: str
    repo_id: str | None
    latency_ms: int
    input_tokens: int | None
    output_tokens: int | None
    cost_usd: float | None
    success: bool
    error_type: str | None
    attempts: int = 1


@dataclass
class LlmCallTracker:
    """Set by the code inside `track_llm_call`: how many model calls it made."""

    attempts: int = 0


def _insert(m: LlmCallMetrics) -> None:
    url = os.getenv("DATABASE_URL")
    if not url:
        return
    try:
        with psycopg.connect(url, connect_timeout=10) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO review_metrics
                    (repo_id, provider, model, latency_ms, input_tokens,
                     output_tokens, cost_usd, success, error_type, attempts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    m.repo_id,
                    m.provider,
                    m.model,
                    m.latency_ms,
                    m.input_tokens,
                    m.output_tokens,
                    m.cost_usd,
                    m.success,
                    m.error_type,
                    m.attempts,
                ),
            )
    except Exception:  # noqa: BLE001 - metrics must never break a review
        logger.warning("could not record review metrics", exc_info=True)


def record(m: LlmCallMetrics) -> None:
    """Writes one metrics row without blocking the caller."""
    threading.Thread(target=_insert, args=(m,), daemon=True).start()


def _error_label(exc: BaseException) -> str:
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__
    return f"{name}:{status}" if status else name


@contextmanager
def track_llm_call(
    provider: str,
    model: str,
    repo_id: str | None,
    tracker: LlmCallTracker | None = None,
) -> Iterator[LlmCallTracker]:
    """Times everything inside the block and records one metrics row.

    Token counts come from the provider's usage report, collected by
    LangChain for every model call made inside the block, so they add up
    across retries. Latency covers the whole block, including waits between
    retries. The block should set `tracker.attempts` to the number of model
    calls it made. Exceptions raised inside the block are re-raised unchanged
    after being recorded.
    """
    tracker = tracker or LlmCallTracker()
    started = time.perf_counter()
    error_type: str | None = None
    with get_usage_metadata_callback() as usage:
        try:
            yield tracker
        except BaseException as exc:
            error_type = _error_label(exc)
            raise
        finally:
            try:
                latency_ms = round((time.perf_counter() - started) * 1000)
                calls = list(usage.usage_metadata.values())
                input_tokens = sum(c.get("input_tokens", 0) for c in calls) if calls else None
                output_tokens = sum(c.get("output_tokens", 0) for c in calls) if calls else None
                record(
                    LlmCallMetrics(
                        provider=provider,
                        model=model,
                        repo_id=repo_id,
                        latency_ms=latency_ms,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=estimate_cost_usd(provider, model, input_tokens, output_tokens),
                        success=error_type is None,
                        error_type=error_type,
                        attempts=max(tracker.attempts, 1),
                    )
                )
            except Exception:  # noqa: BLE001 - never mask the real result or error
                logger.warning("could not build review metrics", exc_info=True)
