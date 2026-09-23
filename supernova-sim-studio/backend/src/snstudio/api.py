from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, get_settings
from .database import Database, get_database
from .engines import EngineRegistry
from .schemas import (
    TERMINAL_STATUSES,
    DoctorReport,
    Engine,
    ParameterSchema,
    ProfilePair,
    Project,
    ProjectCreate,
    Run,
    RunSpec,
    Sweep,
    SweepPreview,
    SweepSpec,
)
from .service import StudioService
from .storage import (
    all_profiles,
    move_run_to_trash,
    safe_artifact,
    store_profile_pair,
)


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
    registry: EngineRegistry | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    database = database or get_database()
    registry = registry or EngineRegistry(settings)
    service = StudioService(settings, database, registry)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        settings.ensure_directories()
        database.init()
        yield

    app = FastAPI(
        title="Supernova Simulation Studio API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.registry = registry
    app.state.service = service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        engines = [adapter.doctor() for adapter in registry.all()]
        return {
            "status": "ok",
            "version": app.version,
            "worker_required": True,
            "enabled_engines": [engine.id for engine in engines if engine.enabled],
        }

    @app.get("/api/v1/doctor", response_model=DoctorReport)
    def doctor() -> DoctorReport:
        engines = [adapter.doctor() for adapter in registry.all()]
        checks = [
            {"name": "data_dir", "ok": settings.data_dir.is_dir(), "value": str(settings.data_dir)},
            {
                "name": "database",
                "ok": settings.database_path.is_file(),
                "value": str(settings.database_path),
            },
            {
                "name": "worker_concurrency",
                "ok": settings.worker_concurrency > 0,
                "value": settings.worker_concurrency,
            },
        ]
        return DoctorReport(
            ok=all(check["ok"] for check in checks) and any(engine.enabled for engine in engines),
            data_dir=str(settings.data_dir),
            database=str(settings.database_path),
            engines=engines,
            checks=checks,
        )

    @app.get("/api/v1/engines", response_model=list[Engine])
    def engines() -> list[Engine]:
        return [adapter.doctor() for adapter in registry.all()]

    @app.get("/api/v1/engines/{engine_id}/parameters", response_model=ParameterSchema)
    def parameter_schema(engine_id: str) -> ParameterSchema:
        try:
            adapter = registry.get(engine_id)
        except KeyError as exc:
            raise HTTPException(404, str(exc)) from exc
        return ParameterSchema(
            engine_id=engine_id,
            fields=adapter.parameter_fields(),
            template=adapter.template_text(),
        )

    @app.get("/api/v1/projects", response_model=list[Project])
    def projects() -> list[dict[str, Any]]:
        return database.list_projects()

    @app.post("/api/v1/projects", response_model=Project, status_code=201)
    def create_project(payload: ProjectCreate) -> dict[str, Any]:
        return database.create_project(payload.name, payload.description)

    @app.get("/api/v1/profiles", response_model=list[ProfilePair])
    def profiles() -> list[dict[str, Any]]:
        return all_profiles(database, registry)

    @app.post("/api/v1/profiles", response_model=ProfilePair, status_code=201)
    async def upload_profile(
        name: Annotated[str, Form()],
        structure: Annotated[UploadFile, File()],
        composition: Annotated[UploadFile, File()],
    ) -> dict[str, Any]:
        try:
            return store_profile_pair(
                settings,
                database,
                name=name,
                structure_filename=structure.filename or "",
                structure_data=await structure.read(),
                composition_filename=composition.filename or "",
                composition_data=await composition.read(),
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/runs/preview")
    def preview_run(payload: RunSpec):
        try:
            return service.preview_run(payload)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/runs", response_model=Run, status_code=202)
    def submit_run(payload: RunSpec):
        try:
            return service.submit_run(payload)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/runs", response_model=list[Run])
    def list_runs(
        project_id: str | None = None,
        sweep_id: str | None = None,
        limit: int = Query(default=200, ge=1, le=1000),
    ):
        return database.list_runs(project_id=project_id, sweep_id=sweep_id, limit=limit)

    @app.get("/api/v1/runs/{run_id}", response_model=Run)
    def get_run(run_id: str):
        run = database.get_run(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        return run

    @app.post("/api/v1/runs/{run_id}/cancel", response_model=Run)
    def cancel_run(run_id: str):
        run = database.request_cancel(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        return run

    @app.post("/api/v1/runs/{run_id}/retry", response_model=Run, status_code=202)
    def retry_run(run_id: str):
        try:
            return service.retry_run(run_id)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.delete("/api/v1/runs/{run_id}")
    def delete_run(run_id: str):
        run = database.get_run(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        if run["status"] not in {status.value for status in TERMINAL_STATUSES}:
            raise HTTPException(409, "只能删除已结束任务")
        trash_path = move_run_to_trash(settings, run)
        database.delete_run_record(run_id)
        return {"deleted": True, "recoverable_path": str(trash_path) if trash_path else None}

    @app.get("/api/v1/runs/{run_id}/logs")
    def logs(run_id: str, offset: int = Query(default=0, ge=0)):
        run = database.get_run(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        path = Path(run["run_dir"]) / "run.log"
        text = path.read_text(errors="replace") if path.is_file() else ""
        return {"offset": len(text), "text": text[offset:]}

    @app.get("/api/v1/runs/{run_id}/events")
    async def events(run_id: str) -> StreamingResponse:
        if database.get_run(run_id) is None:
            raise HTTPException(404, "任务不存在")

        async def stream() -> AsyncIterator[str]:
            offset = 0
            while True:
                run = database.get_run(run_id)
                if run is None:
                    break
                path = Path(run["run_dir"]) / "run.log"
                text = path.read_text(errors="replace") if path.is_file() else ""
                payload = {
                    "run": run,
                    "log": text[offset:],
                    "offset": len(text),
                }
                offset = len(text)
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if run["status"] in {status.value for status in TERMINAL_STATUSES}:
                    break
                await asyncio.sleep(1)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @app.get("/api/v1/runs/{run_id}/series")
    def series(run_id: str):
        run = database.get_run(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        try:
            adapter = registry.get(run["engine_id"])
        except KeyError as exc:
            raise HTTPException(422, str(exc)) from exc
        return adapter.parse_series(Path(run["run_dir"]))

    @app.get("/api/v1/compare")
    def compare(run_ids: Annotated[list[str], Query()]):
        result: list[dict[str, Any]] = []
        for run_id in run_ids:
            run = database.get_run(run_id)
            if run is None:
                raise HTTPException(404, f"任务不存在：{run_id}")
            adapter = registry.get(run["engine_id"])
            result.append(
                {
                    "run": run,
                    "series": [
                        item.model_dump(mode="json")
                        for item in adapter.parse_series(Path(run["run_dir"]))
                    ],
                }
            )
        return result

    @app.get("/api/v1/runs/{run_id}/artifacts")
    def artifacts(run_id: str):
        run = database.get_run(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        return (run.get("manifest") or {}).get("artifacts", [])

    @app.get("/api/v1/runs/{run_id}/artifacts/{artifact_path:path}")
    def download_artifact(run_id: str, artifact_path: str) -> FileResponse:
        run = database.get_run(run_id)
        if run is None:
            raise HTTPException(404, "任务不存在")
        try:
            path = safe_artifact(Path(run["run_dir"]), artifact_path)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
        return FileResponse(path, filename=path.name)

    @app.post("/api/v1/sweeps/preview", response_model=SweepPreview)
    def preview_sweep(payload: SweepSpec):
        try:
            return service.preview_sweep(payload)
        except (KeyError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.post("/api/v1/sweeps", status_code=202)
    def submit_sweep(payload: SweepSpec):
        try:
            sweep, runs = service.submit_sweep(payload)
            return {"sweep": sweep, "runs": runs}
        except (KeyError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/api/v1/sweeps", response_model=list[Sweep])
    def list_sweeps():
        return database.list_sweeps()

    @app.get("/api/v1/sweeps/{sweep_id}")
    def get_sweep(sweep_id: str):
        sweep = database.get_sweep(sweep_id)
        if sweep is None:
            raise HTTPException(404, "扫描不存在")
        return sweep

    frontend = settings.frontend_dist
    if frontend.is_dir() and (frontend / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

        @app.get("/{full_path:path}", response_class=HTMLResponse)
        def spa(full_path: str):
            candidate = frontend / full_path
            if (
                full_path
                and candidate.is_file()
                and candidate.resolve().is_relative_to(frontend.resolve())
            ):
                return FileResponse(candidate)
            return (frontend / "index.html").read_text()
    else:

        @app.get("/", response_class=HTMLResponse)
        def no_frontend() -> str:
            return "<h1>Supernova Simulation Studio API</h1><p>Frontend 尚未构建；API 文档位于 <a href='/docs'>/docs</a>。</p>"

    return app
