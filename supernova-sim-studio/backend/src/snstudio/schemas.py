from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class RunStatus(StrEnum):
    queued = "queued"
    running = "running"
    cancelling = "cancelling"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"
    interrupted = "interrupted"


TERMINAL_STATUSES = {
    RunStatus.succeeded,
    RunStatus.failed,
    RunStatus.cancelled,
    RunStatus.interrupted,
}


class Engine(BaseModel):
    id: str
    name: str
    family: str
    version: str
    enabled: bool
    reason: str | None = None
    capabilities: list[str] = Field(default_factory=list)
    license: str | None = None


class ParameterField(BaseModel):
    key: str
    label: str
    group: str
    type: Literal["integer", "number", "string", "enum", "boolean"]
    default: Any = None
    unit: str | None = None
    minimum: float | None = None
    maximum: float | None = None
    choices: list[Any] | None = None
    description: str = ""
    advanced: bool = False
    sweepable: bool = True


class ParameterSchema(BaseModel):
    engine_id: str
    fields: list[ParameterField]
    template: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)


class Project(ProjectCreate):
    id: str
    created_at: datetime


class ProfilePair(BaseModel):
    id: str
    name: str
    structure_filename: str
    composition_filename: str
    sha256: str
    source: Literal["builtin", "upload"]
    engine_id: str | None = None
    size_bytes: int = 0
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RunSpec(BaseModel):
    project_id: str = "default"
    engine_id: str = "supersnec"
    profile_id: str = "builtin:supersnec:stripped_star"
    name: str = Field(default="SNEC run", min_length=1, max_length=160)
    parameters: dict[str, Any] = Field(default_factory=dict)
    raw_parameters: str | None = None
    output_mode: Literal["full", "minimal"] = "full"


class RunPreview(BaseModel):
    valid: bool
    rendered_parameters: str
    normalized_parameters: dict[str, Any]
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    engine: Engine
    profile: ProfilePair


class SweepAxis(BaseModel):
    kind: Literal["list", "linear", "log"]
    values: list[Any] | None = None
    start: float | None = None
    stop: float | None = None
    steps: int | None = Field(default=None, ge=2, le=1000)

    @model_validator(mode="after")
    def validate_shape(self) -> SweepAxis:
        if self.kind == "list" and not self.values:
            raise ValueError("list 扫描必须提供 values")
        if self.kind in {"linear", "log"}:
            if self.start is None or self.stop is None or self.steps is None:
                raise ValueError(f"{self.kind} 扫描必须提供 start、stop 和 steps")
            if self.kind == "log" and (self.start <= 0 or self.stop <= 0):
                raise ValueError("log 扫描的 start/stop 必须大于 0")
        return self


class SweepSpec(BaseModel):
    project_id: str = "default"
    engine_id: str = "supersnec"
    profile_id: str = "builtin:supersnec:stripped_star"
    name: str = Field(default="Parameter sweep", min_length=1, max_length=160)
    base_parameters: dict[str, Any] = Field(default_factory=dict)
    raw_parameters: str | None = None
    axes: dict[str, SweepAxis]
    output_mode: Literal["full", "minimal"] = "minimal"

    @field_validator("axes")
    @classmethod
    def require_axes(cls, value: dict[str, SweepAxis]) -> dict[str, SweepAxis]:
        if not value:
            raise ValueError("至少需要一个扫描参数")
        return value


class SweepPreview(BaseModel):
    valid: bool
    count: int
    combinations: list[dict[str, Any]]
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class Run(BaseModel):
    id: str
    project_id: str
    sweep_id: str | None = None
    engine_id: str
    profile_id: str
    name: str
    parameters: dict[str, Any]
    raw_parameters: str | None = None
    rendered_parameters: str | None = None
    output_mode: str
    status: RunStatus
    progress: float = 0.0
    current_time: float | None = None
    tend: float | None = None
    error: str | None = None
    run_dir: str
    pid: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    engine_version: str | None = None
    manifest: dict[str, Any] | None = None


class Sweep(BaseModel):
    id: str
    project_id: str
    engine_id: str
    profile_id: str
    name: str
    axes: dict[str, Any]
    base_parameters: dict[str, Any]
    output_mode: str
    status: str
    total_runs: int
    created_at: datetime


class ProgressEvent(BaseModel):
    run_id: str
    status: RunStatus
    progress: float
    current_time: float | None = None
    tend: float | None = None
    message: str | None = None


class Artifact(BaseModel):
    path: str
    size_bytes: int
    sha256: str | None = None


class ArtifactManifest(BaseModel):
    run_id: str
    engine_id: str
    engine_version: str
    parameters_sha256: str
    artifacts: list[Artifact]
    completed_at: datetime


class Series(BaseModel):
    id: str
    label: str
    kind: Literal["luminosity", "magnitude", "velocity", "temperature"]
    x: list[float]
    y: list[float]
    x_unit: str = "day"
    y_unit: str
    inverted_y: bool = False


class DoctorReport(BaseModel):
    ok: bool
    data_dir: str
    database: str
    engines: list[Engine]
    checks: list[dict[str, Any]]
