import pytest
from devbrief_cli.output import render_findings
from devbrief_cli.devbrief_config import load_devbrief_config


class TestRenderFindings:
    def test_empty_findings_shows_clean_message(self, capsys):
        render_findings([])
        assert "No findings" in capsys.readouterr().out

    def test_groups_by_severity_and_orders(self, capsys):
        from devbrief_core.models import Finding

        findings = [
            Finding(file="a.py", line=1, severity="info", message="info msg", rationale="r"),
            Finding(file="b.py", line=2, severity="critical", message="crit msg", rationale="r"),
        ]
        render_findings(findings)
        out = capsys.readouterr().out
        assert "CRITICAL (1)" in out
        assert "INFO (1)" in out
        # critical renders before info.
        assert out.index("CRITICAL") < out.index("INFO")


class TestLoadDevBriefConfig:
    def test_returns_defaults_outside_git_repo(self, monkeypatch, tmp_path):
        monkeypatch.setattr("devbrief_cli.devbrief_config._get_repo_root", lambda: None)
        cfg = load_devbrief_config()
        assert cfg.max_comments_per_pr == 10

    def test_returns_defaults_without_config_file(self, monkeypatch, tmp_path):
        repo = tmp_path / "r"
        repo.mkdir()
        monkeypatch.setattr("devbrief_cli.devbrief_config._get_repo_root", lambda: repo)
        cfg = load_devbrief_config()
        assert cfg.ignore_paths == []

    def test_loads_yaml_config(self, monkeypatch, tmp_path):
        repo = tmp_path / "r"
        repo.mkdir()
        (repo / ".devbrief.yml").write_text("min_severity: warning\nmax_comments_per_pr: 3\n")
        monkeypatch.setattr("devbrief_cli.devbrief_config._get_repo_root", lambda: repo)
        cfg = load_devbrief_config()
        assert cfg.min_severity == "warning"
        assert cfg.max_comments_per_pr == 3

    def test_bad_yaml_falls_back_to_defaults(self, monkeypatch, tmp_path):
        repo = tmp_path / "r"
        repo.mkdir()
        (repo / ".devbrief.yml").write_text(": : not yaml : :")
        monkeypatch.setattr("devbrief_cli.devbrief_config._get_repo_root", lambda: repo)
        assert load_devbrief_config().max_comments_per_pr == 10


class TestFail:
    def test_fail_prints_to_stderr_and_exits(self, capsys):
        import typer
        from devbrief_cli.utils import _fail

        with pytest.raises(typer.Exit) as e:
            _fail("boom")
        assert e.value.exit_code == 1
        assert "boom" in capsys.readouterr().err