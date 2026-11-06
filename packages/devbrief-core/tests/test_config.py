from devbrief_core.config import SEVERITY_RANK, DevBriefConfig


def test_devbrief_config_defaults():
    cfg = DevBriefConfig()
    assert cfg.ignore_paths == []
    assert cfg.min_severity == "info"
    assert cfg.max_comments_per_pr == 10
    assert cfg.require_check is False
    assert cfg.guidelines == []


def test_devbrief_config_accepts_custom_values():
    cfg = DevBriefConfig(
        ignore_paths=["generated/*", "*.lock"],
        min_severity="warning",
        max_comments_per_pr=3,
        require_check=True,
    )
    assert cfg.ignore_paths == ["generated/*", "*.lock"]
    assert cfg.min_severity == "warning"
    assert cfg.max_comments_per_pr == 3
    assert cfg.require_check is True


def test_devbrief_config_rejects_invalid_severity():
    from pydantic import ValidationError

    try:
        DevBriefConfig(min_severity="fatal")  # type: ignore[arg-type]
    except ValidationError as exc:
        assert "min_severity" in str(exc)
    else:
        raise AssertionError("expected validation error for invalid severity")


def test_severity_rank_ordering():
    assert SEVERITY_RANK["info"] < SEVERITY_RANK["warning"] < SEVERITY_RANK["critical"]