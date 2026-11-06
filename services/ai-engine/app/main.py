import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from app.auth import (
    get_current_user,
    get_user_llm_credential,
    require_current_user,
    verify_internal_service_token,
)
from app.errors import DiffTooLargeError, ProviderCredentialError
from app.graph import review_graph
from app.indexing import IndexingNotConfiguredError, index_knowledge, index_repo
from app.mcp_server import mcp
from app.state import IndexKnowledgeRequest, IndexRepoRequest, ReviewState


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app : FastAPI) -> AsyncIterator[None]:
    async with mcp.session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)
app.mount("/mcp-server" , mcp.streamable_http_app())

@app.get("/v1/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/v1/me")
def me_endpoint(user_id: str = Depends(require_current_user)) -> dict:
    """Validates a DevBrief API key. Used by `devbrief auth` to catch a bad paste
    immediately, instead of failing later on the first `devbrief review`."""
    return {"user_id": user_id}


@app.post("/v1/review")
def review_endpoint(
    state: ReviewState,
    user_id: str | None = Depends(get_current_user),
    is_internal_service: bool = Depends(verify_internal_service_token),
) -> ReviewState:
    # Two distinct trust boundaries, see `app.auth.verify_internal_service_token`:
    #   1. CLI path — caller authenticates as a real DevBrief user via Bearer key.
    #   2. Worker/GitHub App path — caller is our own trusted worker, which
    #      has already resolved the owning DevBrief user for this installation
    #      itself and asserts it via `on_behalf_of_user_id`.
    if is_internal_service and state.on_behalf_of_user_id:
        resolved_user_id = state.on_behalf_of_user_id
    elif user_id is not None:
        resolved_user_id = user_id
    else:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    credential = get_user_llm_credential(resolved_user_id)
    if credential is None:
        # Fail closed: no shared/self-hosted key runs on a stranger's behalf.
        raise HTTPException(
            status_code=412,
            detail=(
                "No LLM provider configured for this account. Connect a Gemini, Groq, or "
                "OpenRouter key in the DevBrief dashboard settings before running a review."
            ),
        )
    state.llm_credential = credential
    state.on_behalf_of_user_id = None

    try:
        result = review_graph.invoke(state)
    except (ProviderCredentialError, DiffTooLargeError) as exc:
        # ProviderCredentialError: the credential exists but the provider
        # rejected it (bad model name, revoked key, rate limit, etc.).
        # DiffTooLargeError: the diff exceeds MAX_DIFF_CHARS. Both are
        # distinct from 412 (no credential configured at all) — 422: request
        # was well-formed and authenticated, but couldn't be processed as
        # specified.
        logger.warning("review could not be completed: %s", exc)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        # Anything unexpected: log it with the traceback, then let FastAPI
        # answer 500 exactly as it did before. The server keeps running and
        # the worker posts a failure comment for this one review.
        logger.exception("unexpected error while reviewing")
        raise
    # check what shape `result` actually comes back as once you run this —
    # langgraph may hand back a plain dict of the final state rather than a
    # ReviewState instance; adjust this line if FastAPI complains.
    result_state = ReviewState(**result)
    # Never echo the provider credential back to the caller.
    result_state.llm_credential = None
    return result_state

@app.post("/v1/index/repo")
def index_endpoint(repo: IndexRepoRequest) -> dict:
    try:
        count = index_repo([(f.path, f.content) for f in repo.files], repo.repo_id)
    except IndexingNotConfiguredError as exc:
        # Indexing is optional; reviews work without it.
        return {"status": "skipped", "reason": str(exc)}
    return {"status": "ok", "chunks_indexed": count}


@app.post("/v1/index/knowledge")
def index_knowledge_endpoint(body: IndexKnowledgeRequest) -> dict:
    try:
        count = index_knowledge(body.repo_id, body.documents)
    except IndexingNotConfiguredError as exc:
        return {"status": "skipped", "reason": str(exc)}
    return {"status": "ok", "documents_indexed": count}