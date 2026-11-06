import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.language_models.chat_models import BaseChatModel

from app import metrics
from app.metrics import estimate_cost_usd, track_llm_call


class TestEstimateCost:
    def test_known_model(self):
        # 1M input at $0.075 + 1M output at $0.30
        assert estimate_cost_usd("groq", "openai/gpt-oss-20b", 1_000_000, 1_000_000) == pytest.approx(0.375)

    def test_small_review(self):
        # 2,000 in / 500 out on gemini-flash-lite-latest ($0.30 / $2.50 per 1M)
        cost = estimate_cost_usd("gemini", "gemini-flash-lite-latest", 2000, 500)
        assert cost == pytest.approx((2000 * 0.30 + 500 * 2.50) / 1_000_000)

    def test_unknown_model_is_none_not_a_guess(self):
        assert estimate_cost_usd("groq", "some/unlisted-model", 1000, 1000) is None

    def test_missing_tokens_is_none(self):
        assert estimate_cost_usd("groq", "openai/gpt-oss-20b", None, None) is None

    def test_openrouter_free_models_cost_zero(self):
        assert estimate_cost_usd("openrouter", "google/gemma:free", 500, 500) == 0.0


class _UsageModel(BaseChatModel):
    """A real LangChain chat model that reports token usage like a provider does."""

    @property
    def _llm_type(self) -> str:
        return "usage-test"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = AIMessage(
            content="ok",
            usage_metadata={"input_tokens": 120, "output_tokens": 30, "total_tokens": 150},
            response_metadata={"model_name": "test-model"},
        )
        return ChatResult(generations=[ChatGeneration(message=message)])


class TestTrackLlmCall:
    def test_records_latency_tokens_and_cost_on_success(self, recorded_metrics):
        with track_llm_call("groq", "openai/gpt-oss-20b", "repo-1"):
            _UsageModel().invoke("hello")

        (row,) = recorded_metrics
        assert row.success is True
        assert row.error_type is None
        assert row.repo_id == "repo-1"
        assert row.input_tokens == 120
        assert row.output_tokens == 30
        assert row.latency_ms >= 0
        assert row.cost_usd == pytest.approx((120 * 0.075 + 30 * 0.30) / 1_000_000)

    def test_records_failure_and_reraises_the_original_error(self, recorded_metrics):
        class Boom(Exception):
            status_code = 429

        with pytest.raises(Boom):
            with track_llm_call("groq", "openai/gpt-oss-20b", None):
                raise Boom("rate limited")

        (row,) = recorded_metrics
        assert row.success is False
        assert row.error_type == "Boom:429"
        assert row.input_tokens is None
        assert row.cost_usd is None

    def test_no_usage_reported_means_null_tokens(self, recorded_metrics):
        with track_llm_call("gemini", "gemini-flash-lite-latest", None):
            pass
        (row,) = recorded_metrics
        assert row.input_tokens is None and row.output_tokens is None and row.cost_usd is None

    def test_a_metrics_failure_never_breaks_the_call(self, monkeypatch):
        def explode(_):
            raise RuntimeError("db down")

        monkeypatch.setattr(metrics, "record", explode)
        with track_llm_call("groq", "openai/gpt-oss-20b", None):
            result = 42
        assert result == 42


def test_insert_swallows_database_errors(monkeypatch):
    def refuse(*args, **kwargs):
        raise metrics.psycopg.OperationalError("connection refused")

    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@db.invalid/none")
    monkeypatch.setattr(metrics.psycopg, "connect", refuse)
    metrics._insert(
        metrics.LlmCallMetrics("groq", "m", None, 10, None, None, None, True, None)
    )  # must not raise