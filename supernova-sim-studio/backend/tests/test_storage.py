from __future__ import annotations

from pathlib import Path

import pytest

from snstudio.storage import safe_artifact


def test_artifact_path_cannot_escape_run_directory(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "result.dat").write_text("ok")
    outside = tmp_path / "secret.dat"
    outside.write_text("no")

    assert safe_artifact(run_dir, "result.dat") == run_dir / "result.dat"
    with pytest.raises(ValueError, match="不安全"):
        safe_artifact(run_dir, "../secret.dat")
