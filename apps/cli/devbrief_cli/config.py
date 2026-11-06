import os

import platformdirs
import tomllib

from devbrief_cli.utils import _fail

DEFAULT_AI_ENGINE_URL = os.environ.get(
    "DEVBRIEF_API_URL", "http://localhost:8000"
)
CONFIG_PATH = platformdirs.user_config_path("devbrief") / "config.toml"

def get_ai_engine_url() -> str:
    if not CONFIG_PATH.exists():
        return DEFAULT_AI_ENGINE_URL

    try:
        with CONFIG_PATH.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        _fail(f"Error : invalid config file at {CONFIG_PATH} : {e}")

    url = data.get("api", {}).get("url")
    if not url:
        _fail(f"Error : {CONFIG_PATH} exists but has no [api] url set.")

    return url

def get_api_key() -> str | None:
    if not CONFIG_PATH.exists():
        return None

    try:
        with CONFIG_PATH.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        _fail(f"Error : invalid config file at {CONFIG_PATH} : {e}")

    api_key = data.get("api" , {}).get("api_key")
    if api_key is None:
        return None

    return api_key
