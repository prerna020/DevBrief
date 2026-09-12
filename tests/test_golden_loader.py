from __future__ import annotations

import pytest

# pyrefly: ignore [missing-import]
from eval.load_golden import load_golden_cases


def test_malformed_golden_file_names_the_file(tmp_path) -> None:
    (tmp_path / "bad-case.json").write_text('{"id": 42}', encoding="utf-8")

    with pytest.raises(ValueError, match="bad-case.json"):
        load_golden_cases(tmp_path)

