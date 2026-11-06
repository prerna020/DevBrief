import subprocess
from pathlib import Path

import yaml
from devbrief_core.config import DevBriefConfig


def _get_repo_root() -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def load_devbrief_config() -> DevBriefConfig:
    repo_root = _get_repo_root()
    if repo_root is None:
        return DevBriefConfig()

    config_path = repo_root / ".devbrief.yml"
    if not config_path.exists():
        return DevBriefConfig()

    try:
        data = yaml.safe_load(config_path.read_text())
    except yaml.YAMLError:
        return DevBriefConfig()

    return DevBriefConfig(**(data or {}))