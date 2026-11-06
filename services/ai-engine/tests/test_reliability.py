"""Retry, validation and fallback behavior of the model call (app/nodes/review.py)."""

import importlib

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

from app.errors import InvalidModelOutputError, ProviderCredentialError
from app.nodes import FindingsResponse, review
from app.state import LlmCredential, ReviewState
from devbrief_core.models import Finding

review_mod = importlib.import_module("app.nodes.review")

CRED = LlmCredential(provider="groq", api_key="sk-test", model="openai/gpt-oss-20b")
GOOD = FindingsResponse(
    findings=[Finding(file="f.py", line=2, severity="critical", message="bug", rationale="why")]
)


def status_error(code: int, headers: dict | None = None, body=None) -> APIStatusError:
    request = httpx.Request("POST", "http://example.com")
    response = httpx.Response(code, request=request, headers=headers or {})
    return APIStatusError("provider boom", response=response, body=body)


def timeout_error() -> APITimeoutError:
    return APITimeoutError(request=httpx.Request("POST", "http://example.com"))


class SequenceLLM:
    """Plays back a list of outcomes (exceptions are raised, anything else is
    returned). The last outcome repeats if the list runs out."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def with_structured_output(self, schema, method="function_calling"):
        return self

    def invoke(self, messages):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


@pytest.fixture
def run(monkeypatch):
    """run(outcomes) -> (result_or_exception, llm). Never raises."""

    def _run(*outcomes):
        llm = SequenceLLM(outcomes)
        monkeypatch.setattr(review_mod, "build_llm", lambda cred: llm)
        state = ReviewState(
            diff="diff --git a/f.py b/f.py\n--- a/f.py\n+++ b/f.py\n@@ -1 +1,2 @@\n x\n+y\n",
            llm_credential=CRED,
        )
        try:
            return review(state), llm
        except Exception as exc:  # noqa: BLE001
            return exc, llm

    return _run


class TestTransientRetries:
    def test_recovers_after_two_rate_limits(self, run, slept):
        result, llm = run(status_error(429), status_error(429), GOOD)
        assert [f.message for f in result["findings"]] == ["bug"]
        assert llm.calls == 3
        assert slept == [1.0, 2.0]  # exponential backoff

    def test_gives_up_after_three_retries_with_clear_error(self, run, slept):
        result, llm = run(status_error(429))
        assert isinstance(result, ProviderCredentialError)
        assert "status 429" in str(result)
        assert "4 attempt" in str(result)
        assert llm.calls == 4  # first call + 3 retries
        assert slept == [1.0, 2.0, 4.0]

    @pytest.mark.parametrize("code", [500, 502, 503, 529])
    def test_server_errors_are_retried(self, run, slept, code):
        result, llm = run(status_error(code), GOOD)
        assert result["findings"]
        assert llm.calls == 2

    def test_server_error_message_after_retries(self, run):
        result, _ = run(status_error(503))
        assert isinstance(result, ProviderCredentialError)
        assert "server error (status 503)" in str(result)

    def test_timeouts_are_retried(self, run, slept):
        result, llm = run(timeout_error(), GOOD)
        assert result["findings"]
        assert llm.calls == 2

    def test_timeout_message_after_retries(self, run):
        result, llm = run(timeout_error())
        assert isinstance(result, ProviderCredentialError)
        assert "did not answer within 60 seconds" in str(result)
        assert llm.calls == 4

    def test_connection_errors_are_retried(self, run):
        request = httpx.Request("POST", "http://example.com")
        result, llm = run(APIConnectionError(request=request), GOOD)
        assert result["findings"]
        assert llm.calls == 2

    def test_retry_after_header_is_respected(self, run, slept):
        result, _ = run(status_error(429, {"retry-after": "7"}), GOOD)
        assert result["findings"]
        assert slept == [7.0]

    def test_retry_after_longer_than_we_will_wait_stops_retrying(self, run, slept):
        result, llm = run(status_error(429, {"retry-after": "3600"}))
        assert isinstance(result, ProviderCredentialError)
        assert llm.calls == 1
        assert slept == []

    @pytest.mark.parametrize("code", [400, 401, 403, 404])
    def test_client_errors_are_not_retried(self, run, slept, code):
        result, llm = run(status_error(code))
        assert isinstance(result, ProviderCredentialError)
        assert llm.calls == 1
        assert slept == []


class TestInvalidOutput:
    def test_one_retry_then_success(self, run, slept):
        result, llm = run(ValueError("bad json"), GOOD)
        assert result["findings"]
        assert llm.calls == 2
        assert slept == []  # invalid output is retried immediately

    def test_retries_once_then_falls_back_to_a_safe_error(self, run):
        result, llm = run(ValueError("bad json"))
        assert isinstance(result, InvalidModelOutputError)
        assert isinstance(result, ProviderCredentialError)  # same 422 path as before
        assert llm.calls == 2  # first call + exactly one retry
        assert "could not be parsed" in str(result)
        assert "2 attempt" in str(result)

    def test_missing_tool_call_returns_none_is_treated_as_invalid(self, run):
        # LangChain returns None when the model makes no tool call.
        result, llm = run(None)
        assert isinstance(result, InvalidModelOutputError)
        assert llm.calls == 2

    def test_provider_400_for_malformed_tool_call_counts_as_invalid_output(self, run):
        body = {"code": "tool_use_failed", "message": "Failed to call a function."}
        result, llm = run(status_error(400, body=body), GOOD)
        assert result["findings"]
        assert llm.calls == 2

    def test_provider_400_malformed_tool_call_twice_gives_safe_error(self, run):
        body = {"code": "tool_use_failed", "message": "Failed to call a function."}
        result, llm = run(status_error(400, body=body))
        assert isinstance(result, InvalidModelOutputError)
        assert llm.calls == 2

    def test_fallback_message_never_contains_raw_model_output(self, run):
        result, _ = run(ValueError("SECRET-MODEL-TEXT <script>"))
        assert "SECRET-MODEL-TEXT" not in str(result)


class TestMixedFailures:
    def test_transient_then_invalid_then_success(self, run):
        result, llm = run(status_error(503), ValueError("bad"), GOOD)
        assert result["findings"]
        assert llm.calls == 3


class TestMetricsAttempts:
    def test_attempts_are_recorded(self, run, recorded_metrics):
        run(status_error(429), status_error(429), GOOD)
        (row,) = recorded_metrics
        assert row.success is True
        assert row.attempts == 3

    def test_failure_records_every_attempt(self, run, recorded_metrics):
        run(status_error(503))
        (row,) = recorded_metrics
        assert row.success is False
        assert row.attempts == 4
        assert row.error_type == "APIStatusError:503"

    def test_no_retry_means_one_attempt(self, run, recorded_metrics):
        run(GOOD)
        assert recorded_metrics[0].attempts == 1


class TestBuildLlmSettings:
    def test_client_has_a_timeout_and_no_hidden_retries(self):
        llm = review_mod.build_llm(CRED)
        assert llm.max_retries == 0
        assert llm.request_timeout == review_mod.REQUEST_TIMEOUT_SECONDS


def test_unexpected_errors_in_the_graph_are_logged_and_do_not_stop_the_server(monkeypatch, caplog):
    """An unexpected exception becomes a 500 for that one request; the app keeps serving."""
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from app import main as m

    def boom(state):
        raise RuntimeError("something nobody planned for")

    monkeypatch.setattr(m, "review_graph", SimpleNamespace(invoke=boom))
    monkeypatch.setattr(m, "get_user_llm_credential", lambda uid: CRED)
    m.app.dependency_overrides[m.get_current_user] = lambda: "u-1"
    try:
        client = TestClient(m.app, raise_server_exceptions=False)
        with caplog.at_level("ERROR"):
            first = client.post("/v1/review", json={"diff": "x"})
            second = client.get("/v1/health")
    finally:
        m.app.dependency_overrides.clear()

    assert first.status_code == 500
    assert second.status_code == 200  # still alive
    assert "unexpected error while reviewing" in caplog.text
