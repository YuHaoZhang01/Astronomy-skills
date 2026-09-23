from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, ClassVar

from ..parameters import (
    coerce_value,
    format_fortran_value,
    normalize_and_validate,
    parse_fortran_number,
)
from ..schemas import Engine, ParameterField, ProfilePair, Series
from .base import EngineAdapter, file_version, read_numeric_table, sha256_file

OPENSTELLA_COMMIT = "6c6ad649a9987595da7fc57e735f640c5375e329"
PROFILE_NAME = "m030307mhomo"
RESULT_NAME = "result"
LIGHT_SPEED_CGS = 2.99792458e10


def field(
    key: str,
    label: str,
    group: str,
    type_: str,
    default: Any,
    *,
    unit: str | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    choices: list[Any] | None = None,
    description: str = "",
    advanced: bool = False,
    sweepable: bool = True,
) -> ParameterField:
    return ParameterField(
        key=key,
        label=label,
        group=group,
        type=type_,
        default=default,
        unit=unit,
        minimum=minimum,
        maximum=maximum,
        choices=choices,
        description=description,
        advanced=advanced,
        sweepable=sweepable,
    )


STELLA_FIELDS = [
    field("EPS", "刚性积分精度", "积分", "number", 0.003, minimum=1e-8, maximum=1.0),
    field("HMIN", "最小时间步", "积分", "number", 1e-14, unit="s", minimum=0),
    field("HMAX", "最大时间步", "积分", "number", 5e4, unit="s", minimum=0),
    field("METH", "积分方法", "积分", "enum", 2, choices=[1, 2]),
    field("JSTART", "初始积分阶", "积分", "integer", 0, advanced=True),
    field("MAXORD", "最大积分阶", "积分", "integer", 4, minimum=1, maximum=12),
    field("KNadap", "自适应网格模式", "网格", "enum", -4, choices=[-4, 4]),
    field("NSTA", "起始模型编号", "时间", "integer", -4500, advanced=True),
    field("NSTB", "末模型编号", "时间", "integer", -1, advanced=True),
    field("TcurA", "起始时刻", "时间", "number", 0.0, unit="day", minimum=0),
    field("TcurB", "结束时刻", "时间", "number", 400.0, unit="day", minimum=0.11),
    field("NSTMAX", "最大时间步数", "时间", "integer", 36000, minimum=1),
    field("NDebug", "调试步间隔", "输出", "integer", 100000, minimum=1, advanced=True),
    field("NOUT", "输出步间隔", "输出", "integer", 900, minimum=1),
    field("IOUT", "剖面输出模式", "输出", "integer", -10, advanced=True),
    field("MBATCH", "批处理步间隔", "输出", "integer", 900, minimum=1, advanced=True),
    field("AMNI", "Ni 污染质量范围", "镍", "number", 0.8, unit="M☉", minimum=0),
    field("XMNI", "56Ni 质量参数", "镍", "number", 0.4, minimum=0),
    field("AMHT", "加热核心质量", "能量注入", "number", 0.0, unit="M☉", minimum=0),
    field("EBurst", "注入能量", "能量注入", "number", 0.0, unit="1e50 erg", minimum=0),
    field("tBurst", "注入持续时间", "能量注入", "number", 0.0, unit="s", minimum=0),
    field("tstart", "注入开始时间", "能量注入", "number", 0.0, unit="s", minimum=0),
    field("EKOB", "动能注入", "能量注入", "number", 0.0, unit="1e50 erg", minimum=0),
    field("AI1", "三角速度质量分数 1", "能量注入", "number", 0.0, advanced=True),
    field("AI2", "三角速度质量分数 2", "能量注入", "number", 0.9, advanced=True),
    field("AI3", "三角速度质量分数 3", "能量注入", "number", 1.0, advanced=True),
    field("US", "外向速度符号", "能量注入", "number", 1.0, advanced=True),
    field("THRMAT", "热物质下限", "数值下限", "number", 1e-30, minimum=0, advanced=True),
    field("CRAP", "人工粘性系数", "积分", "number", 1.0, minimum=0, advanced=True),
    field("CONV", "启用对流", "物理", "boolean", False, advanced=True),
    field("EDTM", "演化物质温度", "物理", "boolean", True, advanced=True),
    field("CHNCND", "允许条件变化", "物理", "boolean", True, advanced=True),
    field("Givdtl", "输出详细步长", "输出", "boolean", False, advanced=True),
    field("FLOOR_R", "半径下限", "数值下限", "number", 1e-8, minimum=0, advanced=True),
    field("FLOOR_V", "速度下限", "数值下限", "number", 1e-3, minimum=0, advanced=True),
    field("FLOOR_T", "温度下限", "数值下限", "number", 3e-2, minimum=0, advanced=True),
    field(
        "FLOOR_RADIAT",
        "辐射场下限",
        "数值下限",
        "number",
        1e-2,
        minimum=0,
        advanced=True,
    ),
    field(
        "FLOOR_UCONV",
        "对流速度下限",
        "数值下限",
        "number",
        1e-4,
        minimum=0,
        advanced=True,
    ),
    field("Wacc_R", "半径误差权重", "误差权重", "number", 1.0, minimum=0, advanced=True),
    field("Wacc_V", "速度误差权重", "误差权重", "number", 1.0, minimum=0, advanced=True),
    field("Wacc_T", "温度误差权重", "误差权重", "number", 0.1, minimum=0, advanced=True),
    field(
        "Wacc_RADIAT",
        "辐射误差权重",
        "误差权重",
        "number",
        1.0,
        minimum=0,
        advanced=True,
    ),
    field("FitTau", "拟合光深", "辐射", "number", 15.0, minimum=0),
    field("TAUTOL", "光深容差", "辐射", "number", 1.3, minimum=0),
    field("Rvis", "粘性尺度", "辐射", "number", 1.0, minimum=0, advanced=True),
    field("AQ", "人工粘性 AQ", "辐射", "number", 2.0, minimum=0, advanced=True),
    field("BQ", "人工粘性 BQ", "辐射", "number", 1.0, minimum=0, advanced=True),
    field("DRT", "辐射时间因子", "辐射", "number", 1.0, minimum=0, advanced=True),
    field("NRT", "辐射子步数", "辐射", "integer", 1, minimum=1, advanced=True),
    field("SCAT", "启用散射", "辐射", "boolean", True),
]

# Zero-based line numbers and token order in the official OpenStella *.dat format.
STELLA_LAYOUT: dict[int, list[str]] = {
    1: ["EPS", "HMIN", "HMAX"],
    3: ["METH", "JSTART", "MAXORD", "KNadap"],
    5: ["NSTA", "NSTB", "TcurA", "TcurB"],
    7: ["NSTMAX", "NDebug", "NOUT", "IOUT", "MBATCH"],
    9: ["AMNI", "XMNI"],
    11: ["AMHT", "EBurst", "tBurst", "tstart"],
    13: ["EKOB", "AI1", "AI2", "AI3", "US"],
    15: ["THRMAT", "CRAP", "CONV", "EDTM", "CHNCND", "Givdtl"],
    17: ["FLOOR_R", "FLOOR_V", "FLOOR_T", "FLOOR_RADIAT", "FLOOR_UCONV"],
    19: ["Wacc_R", "Wacc_V", "Wacc_T", "Wacc_RADIAT"],
    21: ["FitTau", "TAUTOL", "Rvis", "AQ", "BQ", "DRT", "NRT", "SCAT"],
}


class StellaAdapter(EngineAdapter):
    id = "stella"
    display_name = "OpenStella / STELLA"
    family = "STELLA"
    license_name = "GPL-3.0"
    capabilities: ClassVar[list[str]] = [
        "single-run",
        "parameter-sweep",
        "progress",
        "standard-series",
    ]

    def __init__(self, root: Path | None):
        self.root = root.expanduser().resolve() if root else None

    @property
    def binary(self) -> Path:
        return (self.root or Path("/missing")) / "run" / "strad" / "xstella6y12m.exe"

    @property
    def template_path(self) -> Path:
        return (self.root or Path("/missing")) / "run" / "strad" / f"{PROFILE_NAME}.dat"

    def version(self) -> str:
        if self.root is None:
            return "not-configured"
        marker = self.root / ".snstudio-openstella-version"
        if marker.is_file():
            return marker.read_text(errors="replace").strip()[:40]
        return file_version(self.root, self.binary)

    def required_profile_files(self) -> list[Path]:
        if self.root is None:
            return []
        files = [
            self.root / "run" / "eve" / f"{PROFILE_NAME}.mod",
            self.root / "run" / "eve" / f"{PROFILE_NAME}.rho",
            self.root / "run" / "eve" / f"{PROFILE_NAME}.xni",
            self.template_path,
        ]
        files.extend(
            self.root / "run" / "vladsf" / f"{PROFILE_NAME}.{index}"
            for index in range(1, 7)
        )
        files.append(self.root / "run" / "vladsf" / f"{PROFILE_NAME}.ab")
        return files

    def doctor(self) -> Engine:
        missing: list[str] = []
        if self.root is None or not self.root.is_dir():
            missing.append("OpenStella 根目录")
        else:
            if not self.binary.is_file() or not self.binary.stat().st_mode & 0o111:
                missing.append("可执行文件 run/strad/xstella6y12m.exe")
            for path in self.required_profile_files():
                if not path.is_file() or path.stat().st_size == 0:
                    missing.append(str(path.relative_to(self.root)))
            version = self.version()
            if version not in {OPENSTELLA_COMMIT, OPENSTELLA_COMMIT[:12]}:
                missing.append(f"固定提交 {OPENSTELLA_COMMIT[:12]}（当前 {version}）")
        return Engine(
            id=self.id,
            name=self.display_name,
            family=self.family,
            version=self.version(),
            enabled=not missing,
            reason=f"缺少或不匹配：{', '.join(missing)}" if missing else None,
            capabilities=self.capabilities if not missing else [],
            license=self.license_name,
        )

    def parameter_fields(self) -> list[ParameterField]:
        values, errors = parse_stella_parameters(self.template_text())
        if errors:
            return STELLA_FIELDS
        result: list[ParameterField] = []
        for item in STELLA_FIELDS:
            try:
                default = coerce_stella_value(values[item.key], item)
            except (KeyError, TypeError, ValueError):
                result.append(item)
            else:
                result.append(item.model_copy(update={"default": default}))
        return result

    def template_text(self) -> str:
        return self.template_path.read_text(errors="replace") if self.template_path.is_file() else ""

    def validate_and_render(
        self, parameters: dict[str, Any], raw_parameters: str | None, output_mode: str
    ) -> tuple[str, dict[str, Any], list[str], list[str]]:
        template = raw_parameters if raw_parameters is not None else self.template_text()
        source, errors = parse_stella_parameters(template)
        warnings: list[str] = []
        fields = self.parameter_fields()
        known = {item.key for item in fields}
        for key in parameters:
            if key not in known:
                errors.append(f"未知 STELLA 参数：{key}")
        requested = {**source, **{key: value for key, value in parameters.items() if key in known}}
        normalized, validation_errors, validation_warnings = normalize_stella_values(
            requested, fields
        )
        errors.extend(validation_errors)
        warnings.extend(validation_warnings)
        if normalized:
            if float(normalized["TcurB"]) <= float(normalized["TcurA"]):
                errors.append("TcurB 必须大于 TcurA")
            if float(normalized["HMAX"]) <= float(normalized["HMIN"]):
                errors.append("HMAX 必须大于 HMIN")
            if abs(int(normalized["NSTA"])) <= abs(int(normalized["NSTB"])):
                errors.append("官方重启约定要求 abs(NSTA) > abs(NSTB)")
            normalized["tend"] = float(normalized["TcurB"])
        if output_mode == "minimal":
            warnings.append("OpenStella 不支持 SNEC output_mode；仍保留原生核心输出")
        rendered = render_stella_parameters(template, normalized) if not errors else template
        return rendered, normalized, errors, warnings

    def builtin_profiles(self) -> list[ProfilePair]:
        if self.root is None or any(
            not path.is_file() for path in self.required_profile_files()
        ):
            return []
        files = self.required_profile_files()
        digest = sha256_file(files[0]) + sha256_file(files[2]) + sha256_file(files[-1])
        return [
            ProfilePair(
                id=f"builtin:{self.id}:{PROFILE_NAME}",
                name="OpenStella 官方 m030307mhomo（90 zones）",
                structure_filename=f"{PROFILE_NAME}.mod",
                composition_filename=f"{PROFILE_NAME}.xni",
                sha256=digest[:64],
                source="builtin",
                engine_id=self.id,
                size_bytes=sum(path.stat().st_size for path in files),
                metadata={
                    "structure_path": str(files[0]),
                    "composition_path": str(files[2]),
                    "rho_path": str(files[1]),
                    "template_path": str(self.template_path),
                    "opacity_paths": [
                        str(self.root / "run" / "vladsf" / f"{PROFILE_NAME}.{index}")
                        for index in range(1, 7)
                    ]
                    + [str(self.root / "run" / "vladsf" / f"{PROFILE_NAME}.ab")],
                    "zones": 90,
                    "upstream_commit": OPENSTELLA_COMMIT,
                },
            )
        ]

    def stage(self, run_dir: Path, profile: dict[str, Any], rendered_parameters: str) -> str:
        if profile.get("engine_id") != self.id:
            raise RuntimeError("STELLA 目前只接受已构建 opacity 的 STELLA 内置模型")
        run_dir.mkdir(parents=True, exist_ok=False)
        workspace = run_dir / "workspace"
        strad = workspace / "strad"
        eve = workspace / "eve"
        opacity = workspace / "vladsf"
        results = workspace / "res"
        for directory in (strad, eve, opacity, results):
            directory.mkdir(parents=True)

        metadata = profile.get("metadata") or {}
        managed = {
            Path(metadata["structure_path"]): eve / f"{PROFILE_NAME}.mod",
            Path(metadata["composition_path"]): eve / f"{PROFILE_NAME}.xni",
            Path(metadata["rho_path"]): eve / f"{PROFILE_NAME}.rho",
        }
        for source, target in managed.items():
            if not source.is_file():
                raise RuntimeError(f"STELLA 模型文件缺失：{source}")
            target.symlink_to(source)
        for raw_path in metadata.get("opacity_paths", []):
            source = Path(raw_path)
            if not source.is_file():
                raise RuntimeError(f"STELLA opacity 文件缺失：{source}")
            (opacity / source.name).symlink_to(source)

        final_text = rendered_parameters.rstrip() + "\n"
        (run_dir / "parameters").write_text(final_text)
        (strad / f"{RESULT_NAME}.dat").write_text(final_text)
        (strad / "strad.1").write_text(
            "Run Results Model Nickel Opacity\n"
            f"{RESULT_NAME} {RESULT_NAME}.res {PROFILE_NAME} {PROFILE_NAME} "
            f"{PROFILE_NAME}.1\n"
        )
        (run_dir / "profile.json").write_text(
            json.dumps(
                {
                    "id": profile["id"],
                    "name": profile["name"],
                    "upstream_commit": OPENSTELLA_COMMIT,
                    "model_sha256": sha256_file(Path(metadata["structure_path"])),
                    "composition_sha256": sha256_file(Path(metadata["composition_path"])),
                    "opacity_sha256": {
                        Path(path).name: sha256_file(Path(path))
                        for path in metadata.get("opacity_paths", [])
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        runner = run_dir / "run-stella"
        runner.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "RUN_ROOT=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
            "cd \"$RUN_ROOT/workspace/strad\"\n"
            "export HOMEStella=..\n"
            f"exec {shell_quote(str(self.binary))}\n"
        )
        runner.chmod(0o755)
        return final_text

    def command(self, run_dir: Path) -> list[str]:
        return [str(run_dir / "run-stella")]

    def parse_progress(self, line: str, tend: float | None) -> tuple[float, float | None] | None:
        match = re.search(r"\btd=\s*([+\-\d.DEe]+)", line)
        if not match:
            return None
        current = parse_fortran_number(match.group(1))
        progress = min(max(current / tend, 0.0), 0.995) if tend and tend > 0 else 0.0
        return progress, current

    def validate_completion(self, run_dir: Path, return_code: int, log_text: str) -> list[str]:
        errors: list[str] = []
        if return_code != 0:
            errors.append(f"STELLA 退出码为 {return_code}")
        lowered = log_text.lower()
        if "normal stop of stella" not in lowered:
            errors.append("日志中没有 STELLA 正常完成标志")
        for marker in ("segmentation fault", "fortran runtime error", "mpi_abort"):
            if marker in lowered:
                errors.append(f"日志包含失败标志：{marker}")
        for suffix in ("tt", "lbol", "swd", "res"):
            path = self.result_path(run_dir, suffix)
            if path is None or path.stat().st_size == 0:
                errors.append(f"缺少核心 STELLA 结果：{RESULT_NAME}.{suffix}")
        tt_path = self.result_path(run_dir, "tt")
        lbol_path = self.result_path(run_dir, "lbol")
        if tt_path and not read_numeric_table(tt_path, 14):
            errors.append("STELLA .tt 结果不可解析")
        if lbol_path and not read_numeric_table(lbol_path, 5):
            errors.append("STELLA .lbol 结果不可解析")
        return errors

    def result_path(self, run_dir: Path, suffix: str) -> Path | None:
        for directory in (run_dir / "workspace" / "res", run_dir / "workspace" / "strad"):
            candidate = directory / f"{RESULT_NAME}.{suffix}"
            if candidate.is_file():
                return candidate
        return None

    def parse_series(self, run_dir: Path) -> list[Series]:
        result: list[Series] = []
        lbol_path = self.result_path(run_dir, "lbol")
        tt_path = self.result_path(run_dir, "tt")
        lbol = read_numeric_table(lbol_path, 5) if lbol_path else []
        tt = read_numeric_table(tt_path, 14) if tt_path else []
        if lbol:
            result.append(
                Series(
                    id="lbol",
                    label="L_bol",
                    kind="luminosity",
                    x=[row[0] for row in lbol],
                    y=[10**row[2] for row in lbol],
                    y_unit="erg/s",
                )
            )
        if tt:
            result.append(
                Series(
                    id="t_eff",
                    label="T_eff",
                    kind="temperature",
                    x=[row[0] for row in tt],
                    y=[row[3] for row in tt],
                    y_unit="K",
                )
            )
            velocity_rows = [row for row in tt if row[0] >= 0 and row[5] > 0]
            if velocity_rows:
                result.append(
                    Series(
                        id="v_ph",
                        label="v_ph",
                        kind="velocity",
                        x=[row[0] for row in velocity_rows],
                        y=[photospheric_velocity(row[0], row[5]) for row in velocity_rows],
                        y_unit="km/s",
                    )
                )
            for label, column in (("U", 7), ("B", 8), ("V", 9), ("R", 11), ("I", 10)):
                result.append(
                    Series(
                        id=f"mag_{label}",
                        label=label,
                        kind="magnitude",
                        x=[row[0] for row in tt],
                        y=[row[column] for row in tt],
                        y_unit="mag",
                        inverted_y=True,
                    )
                )
        return result


def parse_stella_parameters(text: str) -> tuple[dict[str, str], list[str]]:
    if not text.strip():
        return {}, ["找不到可用的 STELLA .dat 模板"]
    lines = text.splitlines()
    values: dict[str, str] = {}
    errors: list[str] = []
    for line_number, keys in STELLA_LAYOUT.items():
        if line_number >= len(lines):
            errors.append(f"STELLA .dat 缺少第 {line_number + 1} 行")
            continue
        tokens = lines[line_number].split()
        if len(tokens) != len(keys):
            errors.append(
                f"STELLA .dat 第 {line_number + 1} 行应有 {len(keys)} 个值，当前为 {len(tokens)}"
            )
            continue
        values.update(zip(keys, tokens, strict=True))
    if len(lines) > 23:
        try:
            nto = int(parse_fortran_number(lines[23].split()[0]))
            output_times = [
                parse_fortran_number(line.split()[0]) for line in lines[24 : 24 + nto]
            ]
            if len(output_times) != nto:
                errors.append(f"STELLA .dat 声明 NTO={nto}，但只有 {len(output_times)} 个输出时刻")
            if output_times != sorted(output_times) or any(value <= 0 for value in output_times):
                errors.append("STELLA .dat 输出时刻必须为递增正数")
        except (IndexError, ValueError):
            errors.append("STELLA .dat 的 NTO/输出时刻不可解析")
    else:
        errors.append("STELLA .dat 缺少 NTO 与输出时刻")
    return values, errors


def coerce_stella_value(value: Any, item: ParameterField) -> Any:
    if item.type == "boolean" and isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"t", ".true."}:
            return True
        if normalized in {"f", ".false."}:
            return False
    return coerce_value(value, item)


def normalize_stella_values(
    values: dict[str, Any], fields: list[ParameterField]
) -> tuple[dict[str, Any], list[str], list[str]]:
    adapted: dict[str, Any] = {}
    field_map = {item.key: item for item in fields}
    errors: list[str] = []
    for key, value in values.items():
        try:
            adapted[key] = coerce_stella_value(value, field_map[key])
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{key}: {exc}")
    normalized, validation_errors, warnings = normalize_and_validate(adapted, fields)
    return normalized, errors + validation_errors, warnings


def render_stella_parameters(template: str, values: dict[str, Any]) -> str:
    lines = template.splitlines()
    field_map = {item.key: item for item in STELLA_FIELDS}
    for line_number, keys in STELLA_LAYOUT.items():
        rendered: list[str] = []
        for key in keys:
            value = values[key]
            if field_map[key].type == "boolean":
                rendered.append("T" if value else "F")
            else:
                rendered.append(format_fortran_value(value, field_map[key]))
        lines[line_number] = "   " + "   ".join(rendered)
    return "\n".join(lines).rstrip() + "\n"


def photospheric_velocity(time_days: float, radius_cm: float) -> float:
    denominator = time_days * 86400.0 + radius_cm / LIGHT_SPEED_CGS
    return radius_cm / denominator / 1e5 if denominator > 0 else math.nan


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\\''") + "'"
