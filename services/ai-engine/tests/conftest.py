import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Ensure `app.*` is importable regardless of how pytest is invoked.
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load real env vars (DATABASE_URL, PINECONE_*, ENCRYPTION_KEY, ...) from the
# repo root so module-level clients (Pinecone, OllamaEmbeddings) construct
# without crashing. Tests that must not touch external services mock them.
load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

# In CI there is no `.env`; the module graph still constructs a Pinecone
# client at import time (app.indexing), which only needs *some* key string.
# Real calls are mocked in the tests, so a placeholder keeps imports working.
os.environ.setdefault("PINECONE_API_KEY", "ci-fake-pinecone-key")
os.environ.setdefault("PINECONE_INDEX_NAME", "ci-fake-index")


@pytest.fixture(autouse=True)
def _unset_internal_token(monkeypatch: pytest.MonkeyPatch):
    """`verify_internal_service_token` reads an env var — each test that cares
    sets it explicitly; default to absent so accidental matches don't happen."""
    monkeypatch.delenv("INTERNAL_SERVICE_TOKEN", raising=False)
    yield


@pytest.fixture(autouse=True)
def recorded_metrics(monkeypatch: pytest.MonkeyPatch):
    """Metrics rows would otherwise be written to the real DATABASE_URL from
    .env. Capture them in a list instead; tests can assert on it."""
    rows: list = []
    monkeypatch.setattr("app.metrics.record", rows.append)
    return rows


@pytest.fixture(autouse=True)
def slept(monkeypatch: pytest.MonkeyPatch):
    """Retries back off by sleeping; tests must not really wait. The list
    records each requested wait so tests can assert on the backoff schedule.
    (`app.nodes.review` is imported by name because `app.nodes` re-exports a
    function called `review`, which shadows the submodule attribute.)"""
    import importlib

    waits: list[float] = []
    monkeypatch.setattr(importlib.import_module("app.nodes.review"), "_sleep", waits.append)
    return waits
