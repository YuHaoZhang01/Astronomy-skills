from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, ClassVar

from ..parameters import (
    SNEC_FIELDS,
    SUPERSNEC_FIELDS,
    coerce_value,
    normalize_and_validate,
    parse_parameter_text,
    render_parameter_text,
)
from ..schemas import Engine, ParameterField, ProfilePair, Series
from .base import EngineAdapter, file_version, read_numeric_table, sha256_file

FILTERS = ["PTF_R", "u", "g", "r", "i", "z", "U", "B", "V", "R", "I"]
ERROR_MARKERS = (
    "Output directory does not exist",
    "not implemented",
    "Fortran runtime error",
    "Segmentation fault",
    "floating invalid",
)


class SnecAdapter(EngineAdapter):
    capabilities: ClassVar[list[str]] = [
        "single-run",
        "parameter-sweep",
        "progress",
        "standard-series",
    ]
    license_name = "CC BY-NC-SA 4.0"

    def __init__(self, root: Path, *, supersnec: bool):
        self.root = root.expanduser().resolve()
        self.supersnec = supersnec
        self.id = "supersnec" if supersnec else "snec-1.01"
        self.display_name = "SuperSNEC" if supersnec else "SNEC 1.01"
        self.family = "SNEC"
        self.binary = self.root / "snec"

    def version(self) -> str:
        return file_version(self.root, self.binary)

    def doctor(self) -> Engine:
        missing: list[str] = []
        for path, label in (
            (self.root, "求解器目录"),
            (self.binary, "snec 可执行文件"),
            (self.root / "parameters", "parameters 模板"),
            (self.root / "profiles", "profiles 目录"),
            (self.root / "tables", "tables 目录"),
        ):
            if not path.exists():
                missing.append(label)
        if self.binary.exists() and not self.binary.is_file():
            missing.append("snec 不是普通文件")
        if self.binary.is_file() and not self.binary.stat().st_mode & 0o111:
            missing.append("snec 不可执行")
        return Engine(
            id=self.id,
            name=self.display_name,
            family=self.family,
            version=self.version(),
            enabled=not missing,
            reason=f"缺少：{', '.join(missing)}" if missing else None,
            capabilities=self.capabilities,
            license=self.license_name,
        )

    def parameter_fields(self) -> list[ParameterField]:
        fields = SUPERSNEC_FIELDS if self.supersnec else SNEC_FIELDS
        template_values = parse_parameter_text(self.template_text())
        resolved: list[ParameterField] = []
        for field in fields:
            if field.key not in template_values:
                resolved.append(field)
                continue
            try:
                default = coerce_value(template_values[field.key], field)
            except (TypeError, ValueError):
                resolved.append(field)
            else:
                resolved.append(field.model_copy(update={"default": default}))
        return resolved

    def template_text(self) -> str:
        path = self.root / "parameters"
        return path.read_text(errors="replace") if path.is_file() else ""

    def validate_and_render(
        self, parameters: dict[str, Any], raw_parameters: str | None, output_mode: str
    ) -> tuple[str, dict[str, Any], list[str], list[str]]:
        fields = self.parameter_fields()
        template = raw_parameters if raw_parameters is not None else self.template_text()
        if not template.strip():
            return "", {}, ["找不到可用 parameters 模板"], []
        source_values = parse_parameter_text(template)
        requested = {**source_values, **parameters}
        reserved = {"outdir", "profile_name", "comp_profile_name"}
        requested_for_validation = {
            key: value for key, value in requested.items() if key not in reserved
        }
        known_keys = {field.key for field in fields}
        visible = {
            key: value for key, value in requested_for_validation.items() if key in known_keys
        }
        normalized, errors, warnings = normalize_and_validate(visible, fields)
        for key in parameters:
            if key in reserved:
                errors.append(f"{key} 由运行器管理，不能手工覆盖")
            elif key not in known_keys:
                errors.append(f"未知参数：{key}")
        if not self.supersnec and strip_value(requested.get("gridding")) == "uniform_by_mass":
            errors.append("原版 SNEC 使用 uniform_in_mass；uniform_by_mass 会静默退出")
        if normalized.get("initial_data") == "Thermal_Bomb":
            start = float(normalized.get("bomb_tstart", 0))
            end = float(normalized.get("bomb_tend", 0))
            if end <= start:
                errors.append("Thermal_Bomb 要求 bomb_tend > bomb_tstart")
        if float(normalized.get("dtmax", 1)) <= float(normalized.get("dtmin", 0)):
            errors.append("dtmax 必须大于 dtmin")
        if self.supersnec:
            normalized["output_mode"] = 0 if output_mode == "full" else 1
        elif output_mode == "minimal":
            warnings.append("原版 SNEC 不支持 minimal output；将保留完整输出")
        rendered = render_parameter_text(
            template,
            {
                **parameters,
                **({"output_mode": normalized["output_mode"]} if self.supersnec else {}),
            },
            fields,
        )
        return rendered, normalized, errors, warnings

    def builtin_profiles(self) -> list[ProfilePair]:
        profiles: list[ProfilePair] = []
        directory = self.root / "profiles"
        if not directory.is_dir():
            return profiles
        for structure in sorted(directory.glob("*.short")):
            base = structure.name.removesuffix(".short")
            composition = directory / f"{base}.iso.dat"
            if not composition.is_file():
                continue
            combined = sha256_file(structure) + sha256_file(composition)
            profiles.append(
                ProfilePair(
                    id=f"builtin:{self.id}:{base}",
                    name=base.replace("_", " "),
                    structure_filename=structure.name,
                    composition_filename=composition.name,
                    sha256=combined[:64],
                    source="builtin",
                    engine_id=self.id,
                    size_bytes=structure.stat().st_size + composition.stat().st_size,
                    metadata={
                        "structure_path": str(structure),
                        "composition_path": str(composition),
                    },
                )
            )
        return profiles

    def stage(self, run_dir: Path, profile: dict[str, Any], rendered_parameters: str) -> str:
        run_dir.mkdir(parents=True, exist_ok=False)
        profile_dir = run_dir / "profiles"
        output_dir = run_dir / "Data"
        profile_dir.mkdir()
        output_dir.mkdir()
        structure_source = Path(profile["structure_path"])
        composition_source = Path(profile["composition_path"])
        structure_target = profile_dir / "model.short"
        composition_target = profile_dir / "model.iso.dat"
        shutil.copy2(structure_source, structure_target)
        shutil.copy2(composition_source, composition_target)
        (run_dir / "tables").symlink_to(self.root / "tables", target_is_directory=True)
        reserved = {
            "outdir": '"Data"',
            "profile_name": '"profiles/model.short"',
            "comp_profile_name": '"profiles/model.iso.dat"',
        }
        final_text = render_parameter_text(
            rendered_parameters,
            reserved,
            self.parameter_fields(),
            append_missing=True,
        )
        (run_dir / "parameters").write_text(final_text)
        (run_dir / "profile.json").write_text(
            json.dumps(
                {
                    "id": profile["id"],
                    "name": profile["name"],
                    "structure_sha256": sha256_file(structure_target),
                    "composition_sha256": sha256_file(composition_target),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return final_text

    def command(self, run_dir: Path) -> list[str]:
        return [str(self.binary)]

    def validate_completion(self, run_dir: Path, return_code: int, log_text: str) -> list[str]:
        errors: list[str] = []
        if return_code != 0:
            errors.append(f"求解器退出码为 {return_code}")
        for marker in ERROR_MARKERS:
            if marker.lower() in log_text.lower():
                errors.append(f"日志包含失败标志：{marker}")
        if "Done! :-)" not in log_text:
            errors.append("日志中没有 SNEC 完成标志")
        required = ["lum_observed.dat", "vel_photo.dat", "magnitudes.dat"]
        for filename in required:
            path = run_dir / "Data" / filename
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"缺少核心结果：Data/{filename}")
        if self.supersnec:
            summary = run_dir / "Data" / "run_summary.dat"
            if not summary.is_file() or summary.stat().st_size == 0:
                errors.append("缺少核心结果：Data/run_summary.dat")
        return errors

    def parse_series(self, run_dir: Path) -> list[Series]:
        data = run_dir / "Data"
        series: list[Series] = []
        lbol = read_numeric_table(data / "lum_observed.dat", 2)
        if lbol:
            series.append(make_series("lbol", "L_bol", "luminosity", lbol, 1, "erg/s"))
        velocity = read_numeric_table(data / "vel_photo.dat", 2)
        if velocity:
            item = make_series("v_ph", "v_ph", "velocity", velocity, 1, "km/s")
            item.y = [value / 1.0e5 for value in item.y]
            series.append(item)
        temperature = read_numeric_table(data / "T_eff.dat", 2)
        if temperature:
            series.append(make_series("t_eff", "T_eff", "temperature", temperature, 1, "K"))
        magnitudes = read_numeric_table(data / "magnitudes.dat", 13)
        if magnitudes:
            for index, name in enumerate(FILTERS, start=2):
                series.append(
                    make_series(f"mag_{name}", name, "magnitude", magnitudes, index, "mag", True)
                )
        return series


def strip_value(value: Any) -> str:
    return str(value or "").strip().strip("\"'")


def make_series(
    id_: str,
    label: str,
    kind: str,
    rows: list[list[float]],
    column: int,
    unit: str,
    inverted: bool = False,
) -> Series:
    return Series(
        id=id_,
        label=label,
        kind=kind,
        x=[row[0] / 86400.0 for row in rows],
        y=[row[column] for row in rows],
        y_unit=unit,
        inverted_y=inverted,
    )
