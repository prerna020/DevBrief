import logging
import time

from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIStatusError, APITimeoutError
from pydantic import BaseModel
from devbrief_core.config import SEVERITY_RANK
from devbrief_core.models import Finding

from app.errors import InvalidModelOutputError, ProviderCredentialError
from app.knowledge.pack import format_pack
from app.metrics import LlmCallTracker, track_llm_call
from app.state import LlmCredential, ReviewState

logger = logging.getLogger(__name__)

PROVIDER_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    # Gemini's OpenAI-compatible endpoint (Google AI Studio API key).
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
}

PROVIDER_DISPLAY_NAMES = {
    "groq": "Groq",
    "openrouter": "OpenRouter",
    "gemini": "Gemini",
}

# Gemini's OpenAI-compatible layer documents structured output via
# `response_format` (JSON schema); forced tool calls are less reliable there.
# Groq/OpenRouter keep the original function-calling path.
STRUCTURED_OUTPUT_METHOD = {
    "groq": "function_calling",
    "openrouter": "function_calling",
    "gemini": "json_schema",
}


# Reliability settings for the model call (see `_invoke_with_retries`).
REQUEST_TIMEOUT_SECONDS = 60
MAX_TRANSIENT_RETRIES = 3  # timeouts, 429, 5xx, network errors
MAX_INVALID_OUTPUT_RETRIES = 1  # malformed / missing structured output
BACKOFF_BASE_SECONDS = 1.0  # waits 1s, 2s, 4s between retries
BACKOFF_MAX_SECONDS = 30.0  # also the longest Retry-After we are willing to wait for
_sleep = time.sleep  # replaced in tests so they do not really wait


class FindingsResponse(BaseModel):
    findings: list[Finding]


def build_llm(credential: LlmCredential) -> ChatOpenAI:
    """Builds a fresh, per-request LLM client from the caller's BYOK
    provider credential. Both Groq and OpenRouter expose OpenAI-compatible
    chat endpoints, so one `ChatOpenAI` class covers both — only the
    base_url, api_key, and model name differ per provider. No client is ever
    cached or shared across requests/users."""
    return ChatOpenAI(
        base_url=PROVIDER_BASE_URLS[credential.provider],
        api_key=credential.api_key,
        model=credential.model,
        temperature=0,
        # `_invoke_with_retries` is the only retry layer. The OpenAI client's
        # own default (2 hidden retries) would multiply with ours and hide
        # attempts from the metrics. The timeout is what turns a hung
        # provider into a retryable failure instead of a ten-minute wait.
        max_retries=0,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


REVIEW_SYSTEM_PROMPT = """You are DevBrief, an automated code reviewer. You are given a unified diff \
of a pull request and must find real, actionable issues introduced by the changes.

Only comment on lines that are added or modified in this diff — never on unchanged \
context lines, and never invent a file or line number that isn't present in the diff. \
Use the line number from the new (target) version of the file, as shown in the diff's \
hunk headers (the `+` side of `@@ -a,b +c,d @@`).

You may also be given retrieved context from elsewhere in the repository, clearly \
labeled as such. Use it only to inform your understanding of the diff — never cite a  \
file or line number from the retrieved context, and never report issues that exist \
only in the retrieved context and not in the diff itself.

For each issue, assign a severity:
- "critical": bugs, security vulnerabilities, data loss, or correctness errors that \
will cause incorrect behavior in production.
- "warning": design or maintainability problems that aren't outright bugs — poor \
error handling, missing edge cases, unclear naming, code likely to cause a bug later.
- "info": minor style or clarity suggestions worth mentioning but not blocking.

Be selective. A diff with no real issues should return an empty findings list — do not \
invent minor nitpicks just to have something to say. Prioritize signal over volume; a \
reviewer who comments on everything is as useless as one who comments on nothing.

For each finding, give:
- file: the file path as it appears in the diff
- line: the target-file line number
- severity: one of "critical", "warning", "info"
- message: a one-sentence description of the issue
- rationale: a short explanation of why it matters and, where useful, how to fix it

Respond with ONLY a single valid JSON object matching the FindingsResponse schema \
({"findings": [...]}) — no markdown code fences (no ```json blocks), no surrounding \
text or explanation.
"""


class _InvalidModelOutput(ValueError):
    """The model answered, but not with a usable FindingsResponse (e.g. it made
    no tool call at all, so LangChain returned None)."""


def _transient_reason(exc: Exception) -> str | None:
    """Why this failure is worth retrying (timeout, rate limit, 5xx, network), else None."""
    if isinstance(exc, APITimeoutError):
        return "timeout"
    if isinstance(exc, APIConnectionError):
        return "connection error"
    if isinstance(exc, APIStatusError):
        if exc.status_code == 429:
            return "rate limited (429)"
        if exc.status_code == 408:
            return "timeout (408)"
        if exc.status_code >= 500:
            return f"server error ({exc.status_code})"
    return None


def _is_invalid_output(exc: Exception) -> bool:
    """True when the model produced output we cannot use. Providers report a
    malformed tool call either as a parse error on our side (ValueError) or as
    a 400 on theirs (Groq: code `tool_use_failed`)."""
    if isinstance(exc, APIStatusError):
        if exc.status_code != 400:
            return False
        text = f"{getattr(exc, 'code', '')} {exc.message} {exc.body}".lower()
        return any(
            marker in text
            for marker in ("tool_use_failed", "failed_generation", "tool call validation failed")
        )
    return isinstance(exc, ValueError)


def _retry_delay(exc: Exception, retry_number: int) -> float | None:
    """Seconds to wait before retry number `retry_number` (1-based): exponential
    backoff, or the provider's Retry-After if that is longer. None means the
    provider asked for a wait longer than we are willing to hold a review for,
    so retrying would only waste time."""
    delay = min(BACKOFF_BASE_SECONDS * (2 ** (retry_number - 1)), BACKOFF_MAX_SECONDS)
    response = getattr(exc, "response", None)
    retry_after = response.headers.get("retry-after") if response is not None else None
    if retry_after:
        try:
            requested = float(retry_after)
        except ValueError:
            requested = 0.0
        if requested > BACKOFF_MAX_SECONDS:
            return None
        delay = max(delay, requested)
    return delay


def _invoke_with_retries(structured_llm, messages, tracker: LlmCallTracker) -> FindingsResponse:
    """Calls the model, retrying what is worth retrying:

    - timeouts, 429, 5xx and network errors: up to MAX_TRANSIENT_RETRIES retries
      with exponential backoff;
    - invalid output (bad structure, no tool call): MAX_INVALID_OUTPUT_RETRIES
      retry, immediately.

    Anything else (bad key, unknown model, ...) is raised at once, unchanged.
    The last error is re-raised when retries run out, so the caller's error
    mapping decides what the user sees.
    """
    transient_retries = 0
    invalid_retries = 0
    while True:
        tracker.attempts += 1
        try:
            response = structured_llm.invoke(messages)
            if not isinstance(response, FindingsResponse):
                raise _InvalidModelOutput("model returned no structured review")
            return response
        except Exception as exc:  # noqa: BLE001 - classified below, otherwise re-raised
            reason = _transient_reason(exc)
            if reason and transient_retries < MAX_TRANSIENT_RETRIES:
                delay = _retry_delay(exc, transient_retries + 1)
                if delay is not None:
                    transient_retries += 1
                    logger.warning(
                        "model call failed (%s); retry %d/%d in %.1fs",
                        reason, transient_retries, MAX_TRANSIENT_RETRIES, delay,
                    )
                    _sleep(delay)
                    continue
            elif not reason and _is_invalid_output(exc) and invalid_retries < MAX_INVALID_OUTPUT_RETRIES:
                invalid_retries += 1
                logger.warning(
                    "model returned invalid output (%s); retry %d/%d",
                    type(exc).__name__, invalid_retries, MAX_INVALID_OUTPUT_RETRIES,
                )
                continue
            raise


def _invalid_output_message(provider_name: str, model_name: str, tracker: LlmCallTracker) -> str:
    return (
        f"{provider_name} returned a response that could not be parsed as a "
        f"review (model '{model_name}') after {tracker.attempts} attempt(s). "
        "This is usually transient; try again."
    )


def review(state: ReviewState) -> dict:
    if state.llm_credential is None:
        # Fail closed — no shared/self-hosted fallback. Reaching this node
        # without a resolved BYOK credential means `review_endpoint` didn't
        # do its job; surfacing that as a clear error here is a second line
        # of defense, not the primary check (that's `require_current_user` +
        # the DB lookup in main.py, which should reject the request before
        # the graph ever runs).
        raise ValueError(
            "No LLM provider credential configured for this account. "
            "Connect a Gemini, Groq, or OpenRouter key in the DevBrief dashboard settings."
        )

    llm = build_llm(state.llm_credential)
    # Function calling, not free-form JSON: the provider constrains the model
    # to emit a tool call against the FindingsResponse schema, so it can't
    # write prose or a fenced JSON block. langchain parses the tool arguments
    # (fence-tolerant via parse_json_markdown) and validates them into the
    # pydantic model. A missing/broken tool call surfaces as
    # OutputParserException (a ValueError) or ValidationError below.
    structured_llm = llm.with_structured_output(
        FindingsResponse,
        method=STRUCTURED_OUTPUT_METHOD[state.llm_credential.provider],
    )

    human_message = f"""## Retrieved context from the repository
{format_pack(state.context)}
## Diff to review
{state.diff}"""
    provider_name = PROVIDER_DISPLAY_NAMES[state.llm_credential.provider]
    model_name = state.llm_credential.model
    messages = [
        ("system", REVIEW_SYSTEM_PROMPT),
        ("human", human_message),
    ]
    tracker = LlmCallTracker()
    try:
        with track_llm_call(
            state.llm_credential.provider, model_name, state.repo_id, tracker
        ):
            response: FindingsResponse = _invoke_with_retries(structured_llm, messages, tracker)
    except InvalidModelOutputError:
        raise
    except APIStatusError as exc:
        # Covers a bad/nonexistent model name (404), a malformed request
        # (400), a revoked/invalid provider key (401), and rate limits (429)
        # — all surfaced with the provider's own message rather than a raw
        # traceback, so the user can tell *what* to fix in their settings.
        # Rate limits and 5xx only get here after the retries ran out.
        if _is_invalid_output(exc):
            logger.warning("provider rejected the model's tool call (%s)", exc)
            raise InvalidModelOutputError(_invalid_output_message(provider_name, model_name, tracker)) from exc
        if exc.status_code in (401, 403):
            raise ProviderCredentialError(
                f"{provider_name} rejected the configured API key "
                f"(status {exc.status_code}). It may be invalid or revoked — "
                "reconnect your key in the DevBrief dashboard settings."
            ) from exc
        if exc.status_code == 404:
            raise ProviderCredentialError(
                f"{provider_name} could not find the model '{model_name}'. "
                "Check the model name in your DevBrief dashboard settings."
            ) from exc
        if exc.status_code == 429:
            raise ProviderCredentialError(
                f"{provider_name} is rate limiting requests (status 429) and was still "
                f"limiting after {tracker.attempts} attempt(s). Wait a minute or two and "
                "push a new commit, or pick another model in your DevBrief dashboard settings."
            ) from exc
        if exc.status_code >= 500:
            raise ProviderCredentialError(
                f"{provider_name} had a server error (status {exc.status_code}) and was "
                f"still failing after {tracker.attempts} attempt(s). This is usually "
                "temporary; try again in a few minutes."
            ) from exc
        raise ProviderCredentialError(
            f"{provider_name} rejected the request (status {exc.status_code}): "
            f"{exc.message}"
        ) from exc
    except APITimeoutError as exc:
        raise ProviderCredentialError(
            f"{provider_name} did not answer within {REQUEST_TIMEOUT_SECONDS} seconds "
            f"({tracker.attempts} attempt(s)). The provider may be overloaded; try again later."
        ) from exc
    except APIConnectionError as exc:
        raise ProviderCredentialError(
            f"Could not reach {provider_name} — the provider may be down, or there's "
            "a network issue between DevBrief and the provider."
        ) from exc
    except ValueError as exc:
        # Covers langchain's OutputParserException (missing/broken tool call)
        # and pydantic ValidationError (malformed args) — both ValueError
        # subclasses — so an unparseable model response is a clean 4xx, not a 500.
        # Reaching here means the one retry also returned invalid output.
        logger.warning(
            "unparseable model response (%s: %s)", type(exc).__name__, exc
        )
        raise InvalidModelOutputError(_invalid_output_message(provider_name, model_name, tracker)) from exc

    min_rank = SEVERITY_RANK[state.config.min_severity]
    filtered = [f for f in response.findings if SEVERITY_RANK[f.severity] >= min_rank]

    filtered.sort(key=lambda f: SEVERITY_RANK[f.severity], reverse=True)
    capped = filtered[: state.config.max_comments_per_pr]
    return {"findings": capped}
