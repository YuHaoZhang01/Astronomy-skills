from __future__ import annotations

import hashlib
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from .config import Settings
from .database import Database, utcnow
from .engines import EngineRegistry

SAFE_FILENAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")
MAX_PROFILE_BYTES = 250 * 1024 * 1024


def validate_filename(filename: str, suffix: str) -> str:
    if filename != Path(filename).name or not SAFE_FILENAME.fullmatch(filename):
        raise ValueError("文件名只能包含字母、数字、点、下划线和连字符")
    if not filename.endswith(suffix):
        raise ValueError(f"文件必须以 {suffix} 结尾")
    return filename


def nonempty_data_lines(data: bytes) -> int:
    count = 0
    for raw_line in data.splitlines():
        line = raw_line.strip()
        if line and not line.startswith(b"#"):
            count += 1
    return count


def store_profile_pair(
    settings: Settings,
    database: Database,
    *,
    name: str,
    structure_filename: str,
    structure_data: bytes,
    composition_filename: str,
    composition_data: bytes,
) -> dict[str, Any]:
    validate_filename(structure_filename, ".short")
    validate_filename(composition_filename, ".iso.dat")
    if not name.strip():
        raise ValueError("模型名称不能为空")
    total_size = len(structure_data) + len(composition_data)
    if total_size > MAX_PROFILE_BYTES:
        raise ValueError("模型文件总大小不能超过 250 MiB")
    if not structure_data or not composition_data:
        raise ValueError("结构与组分文件都不能为空")
    structure_rows = nonempty_data_lines(structure_data)
    composition_rows = nonempty_data_lines(composition_data)
    if structure_rows < 3 or composition_rows < 3:
        raise ValueError("模型文件没有足够的数据行")
    ratio = max(structure_rows, composition_rows) / min(structure_rows, composition_rows)
    if ratio > 4:
        raise ValueError("结构与组分文件的数据行数差异过大，请检查是否匹配")
    profile_id = uuid.uuid4().hex
    directory = settings.profiles_dir / profile_id
    directory.mkdir(parents=True, exist_ok=False)
    structure_path = directory / "model.short"
    composition_path = directory / "model.iso.dat"
    structure_path.write_bytes(structure_data)
    composition_path.write_bytes(composition_data)
    digest = hashlib.sha256(structure_data + b"\0" + composition_data).hexdigest()
    return database.create_profile(
        {
            "id": profile_id,
            "name": name.strip(),
            "structure_path": str(structure_path),
            "composition_path": str(composition_path),
            "structure_filename": structure_filename,
            "composition_filename": composition_filename,
            "sha256": digest,
            "source": "upload",
            "engine_id": None,
            "size_bytes": total_size,
            "metadata": {
                "structure_rows": structure_rows,
                "composition_rows": composition_rows,
            },
            "created_at": utcnow(),
        }
    )


def all_profiles(database: Database, registry: EngineRegistry) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for adapter in registry.all():
        profiles.extend(profile.model_dump(mode="json") for profile in adapter.builtin_profiles())
    profiles.extend(database.list_profiles())
    return profiles


def resolve_profile(
    profile_id: str, database: Database, registry: EngineRegistry
) -> dict[str, Any] | None:
    if profile_id.startswith("builtin:"):
        parts = profile_id.split(":", 2)
        if len(parts) != 3:
            return None
        try:
            adapter = registry.get(parts[1])
        except KeyError:
            return None
        for profile in adapter.builtin_profiles():
            if profile.id == profile_id:
                item = profile.model_dump(mode="json")
                item["structure_path"] = profile.metadata["structure_path"]
                item["composition_path"] = profile.metadata["composition_path"]
                return item
        return None
    return database.get_profile(profile_id)


def safe_artifact(run_dir: Path, relative: str) -> Path:
    if not relative or relative.startswith(("/", "\\")):
        raise ValueError("无效 artifact 路径")
    target = (run_dir / relative).resolve()
    root = run_dir.resolve()
    if not target.is_relative_to(root) or not target.is_file() or target.is_symlink():
        raise ValueError("artifact 不存在或路径不安全")
    return target


def move_run_to_trash(settings: Settings, run: dict[str, Any]) -> Path | None:
    source = Path(run["run_dir"])
    if not source.exists():
        return None
    target = settings.trash_dir / f"{run['id']}-{uuid.uuid4().hex[:8]}"
    shutil.move(str(source), str(target))
    return target
