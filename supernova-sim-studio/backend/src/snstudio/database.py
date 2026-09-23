from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .schemas import RunStatus


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            yield connection
        finally:
            connection.close()

    def init(self) -> None:
        with self.connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    structure_path TEXT NOT NULL,
                    composition_path TEXT NOT NULL,
                    structure_filename TEXT NOT NULL,
                    composition_filename TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    source TEXT NOT NULL,
                    engine_id TEXT,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sweeps (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    engine_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    axes_json TEXT NOT NULL,
                    base_parameters_json TEXT NOT NULL,
                    raw_parameters TEXT,
                    output_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_runs INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    sweep_id TEXT,
                    engine_id TEXT NOT NULL,
                    profile_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    raw_parameters TEXT,
                    rendered_parameters TEXT,
                    output_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    current_time REAL,
                    tend REAL,
                    error TEXT,
                    run_dir TEXT NOT NULL,
                    pid INTEGER,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    engine_version TEXT,
                    manifest_json TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    FOREIGN KEY(sweep_id) REFERENCES sweeps(id)
                );
                CREATE INDEX IF NOT EXISTS idx_runs_status_created
                    ON runs(status, created_at);
                CREATE INDEX IF NOT EXISTS idx_runs_sweep ON runs(sweep_id);
                """
            )
            connection.execute(
                "INSERT OR IGNORE INTO projects(id,name,description,created_at) VALUES(?,?,?,?)",
                ("default", "默认项目", "本机与服务器共享的默认计算项目", utcnow()),
            )

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        item = dict(row)
        for source, target in (
            ("parameters_json", "parameters"),
            ("manifest_json", "manifest"),
            ("metadata_json", "metadata"),
            ("axes_json", "axes"),
            ("base_parameters_json", "base_parameters"),
        ):
            if source in item:
                raw = item.pop(source)
                item[target] = json.loads(raw) if raw else None
        return item

    def list_projects(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [
                self._row(row)
                for row in connection.execute(
                    "SELECT * FROM projects ORDER BY created_at"
                ).fetchall()
            ]

    def create_project(self, name: str, description: str) -> dict[str, Any]:
        project_id = uuid.uuid4().hex
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO projects VALUES(?,?,?,?)",
                (project_id, name, description, utcnow()),
            )
        return self.get_project(project_id)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            return self._row(
                connection.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            )

    def create_profile(self, values: dict[str, Any]) -> dict[str, Any]:
        profile_id = values.get("id") or uuid.uuid4().hex
        created_at = values.get("created_at") or utcnow()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO profiles(
                    id,name,structure_path,composition_path,structure_filename,
                    composition_filename,sha256,source,engine_id,size_bytes,
                    metadata_json,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    profile_id,
                    values["name"],
                    values["structure_path"],
                    values["composition_path"],
                    values["structure_filename"],
                    values["composition_filename"],
                    values["sha256"],
                    values.get("source", "upload"),
                    values.get("engine_id"),
                    values.get("size_bytes", 0),
                    json.dumps(values.get("metadata", {}), ensure_ascii=False),
                    created_at,
                ),
            )
        return self.get_profile(profile_id)

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            return self._row(
                connection.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
            )

    def list_profiles(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            return [
                self._row(row)
                for row in connection.execute(
                    "SELECT * FROM profiles ORDER BY created_at DESC"
                ).fetchall()
            ]

    def create_sweep(self, values: dict[str, Any]) -> dict[str, Any]:
        sweep_id = values.get("id") or uuid.uuid4().hex
        created_at = utcnow()
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO sweeps(
                    id,project_id,engine_id,profile_id,name,axes_json,
                    base_parameters_json,raw_parameters,output_mode,status,total_runs,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    sweep_id,
                    values["project_id"],
                    values["engine_id"],
                    values["profile_id"],
                    values["name"],
                    json.dumps(values["axes"], ensure_ascii=False),
                    json.dumps(values.get("base_parameters", {}), ensure_ascii=False),
                    values.get("raw_parameters"),
                    values["output_mode"],
                    "queued",
                    values["total_runs"],
                    created_at,
                ),
            )
        return self.get_sweep(sweep_id)

    def get_sweep(self, sweep_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM sweeps WHERE id=?", (sweep_id,)).fetchone()
            item = self._row(row)
            if item:
                counts = dict(
                    connection.execute(
                        "SELECT status,COUNT(*) count FROM runs WHERE sweep_id=? GROUP BY status",
                        (sweep_id,),
                    ).fetchall()
                )
                item["counts"] = counts
                if counts and sum(counts.values()) == item["total_runs"]:
                    active = sum(
                        counts.get(value, 0) for value in ("queued", "running", "cancelling")
                    )
                    if active:
                        item["status"] = "running"
                    elif counts.get("failed", 0) or counts.get("interrupted", 0):
                        item["status"] = "completed_with_errors"
                    elif counts.get("cancelled", 0) == item["total_runs"]:
                        item["status"] = "cancelled"
                    else:
                        item["status"] = "succeeded"
            return item

    def list_sweeps(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            ids = [
                row[0]
                for row in connection.execute(
                    "SELECT id FROM sweeps ORDER BY created_at DESC"
                ).fetchall()
            ]
        return [self.get_sweep(sweep_id) for sweep_id in ids]

    def create_run(self, values: dict[str, Any]) -> dict[str, Any]:
        run_id = values.get("id") or uuid.uuid4().hex
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO runs(
                    id,project_id,sweep_id,engine_id,profile_id,name,parameters_json,
                    raw_parameters,rendered_parameters,output_mode,status,progress,
                    current_time,tend,error,run_dir,pid,created_at,started_at,finished_at,
                    engine_version,manifest_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id,
                    values["project_id"],
                    values.get("sweep_id"),
                    values["engine_id"],
                    values["profile_id"],
                    values["name"],
                    json.dumps(values.get("parameters", {}), ensure_ascii=False),
                    values.get("raw_parameters"),
                    values.get("rendered_parameters"),
                    values["output_mode"],
                    values.get("status", RunStatus.queued.value),
                    values.get("progress", 0.0),
                    values.get("current_time"),
                    values.get("tend"),
                    values.get("error"),
                    values["run_dir"],
                    values.get("pid"),
                    values.get("created_at", utcnow()),
                    values.get("started_at"),
                    values.get("finished_at"),
                    values.get("engine_version"),
                    json.dumps(values.get("manifest"), ensure_ascii=False)
                    if values.get("manifest") is not None
                    else None,
                ),
            )
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            return self._row(
                connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            )

    def list_runs(
        self, *, project_id: str | None = None, sweep_id: str | None = None, limit: int = 200
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if project_id:
            clauses.append("project_id=?")
            params.append(project_id)
        if sweep_id:
            clauses.append("sweep_id=?")
            params.append(sweep_id)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM runs{where} ORDER BY created_at DESC LIMIT ?", params
            ).fetchall()
        return [self._row(row) for row in rows]

    def update_run(self, run_id: str, **changes: Any) -> dict[str, Any] | None:
        if not changes:
            return self.get_run(run_id)
        encoded: dict[str, Any] = {}
        for key, value in changes.items():
            if key == "parameters":
                encoded["parameters_json"] = json.dumps(value, ensure_ascii=False)
            elif key == "manifest":
                encoded["manifest_json"] = json.dumps(value, ensure_ascii=False)
            elif isinstance(value, RunStatus):
                encoded[key] = value.value
            else:
                encoded[key] = value
        assignments = ",".join(f"{key}=?" for key in encoded)
        with self.connect() as connection:
            connection.execute(
                f"UPDATE runs SET {assignments} WHERE id=?",
                [*encoded.values(), run_id],
            )
        return self.get_run(run_id)

    def claim_next_run(self) -> dict[str, Any] | None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT id FROM runs WHERE status=? ORDER BY created_at LIMIT 1",
                (RunStatus.queued.value,),
            ).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None
            run_id = row["id"]
            changed = connection.execute(
                """UPDATE runs SET status=?,started_at=?,error=NULL
                   WHERE id=? AND status=?""",
                (RunStatus.running.value, utcnow(), run_id, RunStatus.queued.value),
            ).rowcount
            connection.execute("COMMIT")
        return self.get_run(run_id) if changed else None

    def recover_interrupted(self) -> int:
        with self.connect() as connection:
            return connection.execute(
                """UPDATE runs SET status=?,finished_at=?,error=?
                   WHERE status IN (?,?)""",
                (
                    RunStatus.interrupted.value,
                    utcnow(),
                    "Worker 重启，原计算进程状态未知；可检查日志后重试。",
                    RunStatus.running.value,
                    RunStatus.cancelling.value,
                ),
            ).rowcount

    def request_cancel(self, run_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                connection.execute("COMMIT")
                return None
            if row["status"] == RunStatus.queued.value:
                connection.execute(
                    """UPDATE runs SET status=?,finished_at=?,error=?
                       WHERE id=? AND status=?""",
                    (
                        RunStatus.cancelled.value,
                        utcnow(),
                        "任务在启动前被取消。",
                        run_id,
                        RunStatus.queued.value,
                    ),
                )
            elif row["status"] == RunStatus.running.value:
                connection.execute(
                    "UPDATE runs SET status=? WHERE id=? AND status=?",
                    (RunStatus.cancelling.value, run_id, RunStatus.running.value),
                )
            connection.execute("COMMIT")
        return self.get_run(run_id)

    def delete_run_record(self, run_id: str) -> bool:
        with self.connect() as connection:
            return connection.execute("DELETE FROM runs WHERE id=?", (run_id,)).rowcount > 0


_database: Database | None = None


def get_database() -> Database:
    global _database
    if _database is None:
        from .config import get_settings

        _database = Database(get_settings().database_path)
        _database.init()
    return _database


def reset_database_for_tests(path: Path) -> Database:
    global _database
    _database = Database(path)
    _database.init()
    return _database
