import httpx
from devbrief_core.diff import parse_diff
from devbrief_core.models import Finding
from unidiff.errors import UnidiffParseError

from devbrief_cli.config import get_ai_engine_url, get_api_key
from devbrief_cli.devbrief_config import _get_repo_root, load_devbrief_config
from devbrief_cli.utils import _fail


def _file_snapshots(diff_text: str) -> list[dict[str, str]]:
    root = _get_repo_root()
    if root is None:
        return []
    snapshots: list[dict[str, str]] = []
    try:
        parsed = parse_diff(diff_text)
    except (UnidiffParseError, ValueError):
        return []
    for pf in parsed:
        path = root / pf.path
        try:
            snapshots.append({"path": pf.path, "content": path.read_text(encoding="utf-8")})
        except OSError:
            continue
    return snapshots


def _post_review(diff_text : str) -> list[Finding]:
    api_key = get_api_key()
    if not api_key:
        _fail("Error: not authenticated. Run `devbrief auth` first.")

    headers = {"Authorization": f"Bearer {api_key}"}

    devbrief_config = load_devbrief_config()
    ai_engine_url = get_ai_engine_url()
    try:
        response = httpx.post(
            f"{ai_engine_url}/v1/review",
            json={
                "diff": diff_text,
                "config": devbrief_config.model_dump(),
                "file_snapshots": _file_snapshots(diff_text),
            },
            headers=headers,
            timeout=120.0
        )
    except httpx.ConnectError:
        _fail(f"Error : could not connect to ai-engine at {ai_engine_url}.")
    
    except httpx.TimeoutException:
        _fail("Error: ai-engine request timed out.")

    if response.status_code == 401:
        _fail("Error: not authenticated. Run `devbrief auth` first.")
    if response.status_code == 412:
        _fail(f"Error: {response.json().get('detail', response.text)}")
    if response.status_code == 422:
        _fail(f"Error: {response.json().get('detail', response.text)}")
    if response.status_code != 200:
        _fail(f"Error: ai-engine returned {response.status_code}: {response.text}")
    
    data = response.json()
    return [Finding(**f) for f in data["findings"]]

