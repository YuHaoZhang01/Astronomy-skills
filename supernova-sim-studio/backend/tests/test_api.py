from __future__ import annotations

from fastapi.testclient import TestClient

from snstudio.api import create_app


def test_api_run_lifecycle(studio) -> None:
    settings, database, registry = studio
    with TestClient(create_app(settings, database, registry)) as client:
        project = client.post(
            "/api/v1/projects",
            json={"name": "SN 2026abc", "description": "project isolation test"},
        )
        assert project.status_code == 201
        assert any(
            item["id"] == project.json()["id"] for item in client.get("/api/v1/projects").json()
        )
        health = client.get("/api/health")
        assert health.status_code == 200
        assert "supersnec" in health.json()["enabled_engines"]
        profiles = client.get("/api/v1/profiles").json()
        assert any(item["id"] == "builtin:supersnec:stripped_star" for item in profiles)
        payload = {
            "engine_id": "supersnec",
            "profile_id": "builtin:supersnec:stripped_star",
            "parameters": {"Ni_mass": 0.04},
        }
        preview = client.post("/api/v1/runs/preview", json=payload)
        assert preview.status_code == 200
        assert preview.json()["valid"] is True
        submitted = client.post("/api/v1/runs", json=payload)
        assert submitted.status_code == 202
        run_id = submitted.json()["id"]
        assert client.get(f"/api/v1/runs/{run_id}").json()["status"] == "queued"
        cancelled = client.post(f"/api/v1/runs/{run_id}/cancel")
        assert cancelled.json()["status"] == "cancelled"


def test_profile_upload_rejects_unsafe_name(studio) -> None:
    settings, database, registry = studio
    with TestClient(create_app(settings, database, registry)) as client:
        response = client.post(
            "/api/v1/profiles",
            data={"name": "bad"},
            files={
                "structure": ("../bad.short", b"1\n2\n3\n", "text/plain"),
                "composition": ("bad.iso.dat", b"1\n2\n3\n", "text/plain"),
            },
        )
        assert response.status_code == 422
