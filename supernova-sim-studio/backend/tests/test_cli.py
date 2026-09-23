from __future__ import annotations

import json

from typer.testing import CliRunner

from snstudio.cli import ClientContext, ctl_app


def test_status_accepts_optional_positional_run_id(monkeypatch) -> None:
    requested: list[tuple[str, str]] = []

    def fake_request(self, method: str, path: str, **_kwargs):
        requested.append((method, path))
        return {"id": "run-123", "status": "succeeded"}

    monkeypatch.setattr(ClientContext, "request", fake_request)
    result = CliRunner().invoke(ctl_app, ["--json", "status", "run-123"])

    assert result.exit_code == 0
    assert requested == [("GET", "/api/v1/runs/run-123")]
    assert json.loads(result.stdout)["id"] == "run-123"
