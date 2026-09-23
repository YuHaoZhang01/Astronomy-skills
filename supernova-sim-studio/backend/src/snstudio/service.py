from __future__ import annotations

import uuid
from typing import Any

from .config import Settings
from .database import Database
from .engines import EngineRegistry
from .parameters import expand_sweep
from .schemas import RunPreview, RunSpec, SweepPreview, SweepSpec
from .storage import resolve_profile


class StudioService:
    def __init__(self, settings: Settings, database: Database, registry: EngineRegistry):
        self.settings = settings
        self.database = database
        self.registry = registry

    def preview_run(self, spec: RunSpec) -> RunPreview:
        try:
            adapter = self.registry.get(spec.engine_id)
        except KeyError as exc:
            raise ValueError(str(exc)) from exc
        engine = adapter.doctor()
        profile = resolve_profile(spec.profile_id, self.database, self.registry)
        if profile is None:
            raise ValueError(f"找不到模型：{spec.profile_id}")
        rendered, normalized, errors, warnings = adapter.validate_and_render(
            spec.parameters, spec.raw_parameters, spec.output_mode
        )
        if not engine.enabled:
            errors.append(engine.reason or "引擎不可用")
        if adapter.family == "STELLA" and profile.get("engine_id") != spec.engine_id:
            errors.append("STELLA 目前只接受已预计算 opacity 的 STELLA 内置模型")
        elif profile.get("engine_id") and profile["engine_id"] != spec.engine_id:
            warnings.append("该内置模型来自另一个 SNEC 引擎，将复制后尝试运行")
        from .schemas import ProfilePair

        return RunPreview(
            valid=not errors,
            rendered_parameters=rendered,
            normalized_parameters=normalized,
            errors=errors,
            warnings=warnings,
            engine=engine,
            profile=ProfilePair.model_validate(profile),
        )

    def submit_run(self, spec: RunSpec, *, sweep_id: str | None = None) -> dict[str, Any]:
        if self.database.get_project(spec.project_id) is None:
            raise ValueError(f"找不到项目：{spec.project_id}")
        preview = self.preview_run(spec)
        if not preview.valid:
            raise ValueError("；".join(preview.errors))
        run_id = uuid.uuid4().hex
        return self.database.create_run(
            {
                "id": run_id,
                "project_id": spec.project_id,
                "sweep_id": sweep_id,
                "engine_id": spec.engine_id,
                "profile_id": spec.profile_id,
                "name": spec.name,
                "parameters": spec.parameters,
                "raw_parameters": spec.raw_parameters,
                "rendered_parameters": preview.rendered_parameters,
                "output_mode": spec.output_mode,
                "run_dir": str(self.settings.runs_dir / run_id),
                "tend": float(preview.normalized_parameters.get("tend", 0)) or None,
                "engine_version": preview.engine.version,
            }
        )

    def preview_sweep(self, spec: SweepSpec) -> SweepPreview:
        combinations = expand_sweep(spec.axes)
        errors: list[str] = []
        warnings: list[str] = []
        if len(combinations) > self.settings.max_sweep_runs:
            errors.append(
                f"扫描包含 {len(combinations)} 个任务，超过上限 {self.settings.max_sweep_runs}"
            )
        adapter = self.registry.get(spec.engine_id)
        sweepable = {field.key for field in adapter.parameter_fields() if field.sweepable}
        for key in spec.axes:
            if key not in sweepable:
                errors.append(f"参数 {key} 不支持扫描或不存在")
        for index, combination in enumerate(combinations):
            run_spec = RunSpec(
                project_id=spec.project_id,
                engine_id=spec.engine_id,
                profile_id=spec.profile_id,
                name=f"{spec.name} #{index + 1}",
                parameters={**spec.base_parameters, **combination},
                raw_parameters=spec.raw_parameters,
                output_mode=spec.output_mode,
            )
            try:
                preview = self.preview_run(run_spec)
            except ValueError as exc:
                errors.append(str(exc))
                break
            if preview.errors:
                errors.extend(f"组合 #{index + 1}: {error}" for error in preview.errors)
                if len(errors) >= 20:
                    errors.append("错误过多，已停止继续检查")
                    break
        if spec.output_mode == "full" and len(combinations) > 20:
            warnings.append("大量 full-output 任务会占用较多磁盘，建议使用 minimal")
        return SweepPreview(
            valid=not errors,
            count=len(combinations),
            combinations=combinations[:20],
            errors=errors,
            warnings=warnings,
        )

    def submit_sweep(self, spec: SweepSpec) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        preview = self.preview_sweep(spec)
        if not preview.valid:
            raise ValueError("；".join(preview.errors))
        combinations = expand_sweep(spec.axes)
        sweep = self.database.create_sweep(
            {
                "project_id": spec.project_id,
                "engine_id": spec.engine_id,
                "profile_id": spec.profile_id,
                "name": spec.name,
                "axes": {key: value.model_dump() for key, value in spec.axes.items()},
                "base_parameters": spec.base_parameters,
                "raw_parameters": spec.raw_parameters,
                "output_mode": spec.output_mode,
                "total_runs": len(combinations),
            }
        )
        runs: list[dict[str, Any]] = []
        for index, combination in enumerate(combinations):
            run_spec = RunSpec(
                project_id=spec.project_id,
                engine_id=spec.engine_id,
                profile_id=spec.profile_id,
                name=f"{spec.name} #{index + 1}",
                parameters={**spec.base_parameters, **combination},
                raw_parameters=spec.raw_parameters,
                output_mode=spec.output_mode,
            )
            runs.append(self.submit_run(run_spec, sweep_id=sweep["id"]))
        return sweep, runs

    def retry_run(self, run_id: str) -> dict[str, Any]:
        run = self.database.get_run(run_id)
        if run is None:
            raise ValueError("任务不存在")
        spec = RunSpec(
            project_id=run["project_id"],
            engine_id=run["engine_id"],
            profile_id=run["profile_id"],
            name=f"{run['name']} · retry",
            parameters=run["parameters"],
            raw_parameters=run["raw_parameters"],
            output_mode=run["output_mode"],
        )
        return self.submit_run(spec, sweep_id=run.get("sweep_id"))
