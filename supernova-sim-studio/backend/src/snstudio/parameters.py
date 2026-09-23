from __future__ import annotations

import math
import re
from itertools import product
from typing import Any

from .schemas import ParameterField, SweepAxis

PARAMETER_LINE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[^#=][^=]*?)\s*=\s*(?P<value>.*?)(?P<comment>\s+#.*)?$"
)


def parse_parameter_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        match = PARAMETER_LINE.match(line)
        if not match:
            continue
        key = match.group("key").strip()
        value = match.group("value").strip()
        if key:
            values[key] = value
    return values


def parse_fortran_number(value: str | float) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return float(value.strip().replace("D", "E").replace("d", "e"))


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def coerce_value(value: Any, field: ParameterField) -> Any:
    if field.type == "integer":
        return int(parse_fortran_number(value))
    if field.type == "number":
        return parse_fortran_number(value)
    if field.type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        normalized = strip_quotes(str(value)).lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"{field.key} 不是合法布尔值")
    if field.type == "enum" and field.choices:
        sample = field.choices[0]
        if isinstance(sample, int) and not isinstance(sample, bool):
            return int(parse_fortran_number(value))
        if isinstance(sample, float):
            return parse_fortran_number(value)
    return strip_quotes(str(value))


def format_fortran_value(value: Any, field: ParameterField | None = None) -> str:
    if field and (
        field.type == "string"
        or (field.type == "enum" and field.choices and isinstance(field.choices[0], str))
    ):
        return f'"{strip_quotes(str(value))}"'
    if isinstance(value, bool):
        return "1" if value else "0"
    if field and field.type == "number":
        number = parse_fortran_number(value)
        if not math.isfinite(number):
            raise ValueError("参数不能是 NaN 或无穷大")
        rendered = f"{number:.12g}".lower()
        if "e" in rendered:
            mantissa, exponent = rendered.split("e", maxsplit=1)
            if "." not in mantissa:
                mantissa += ".0"
            return f"{mantissa}d{int(exponent)}"
        if "." not in rendered:
            rendered += ".0"
        return f"{rendered}d0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("参数不能是 NaN 或无穷大")
        return f"{value:.12g}"
    return str(value).strip()


def render_parameter_text(
    template: str,
    overrides: dict[str, Any],
    fields: list[ParameterField],
    *,
    append_missing: bool = False,
) -> str:
    field_map = {field.key: field for field in fields}
    pending = dict(overrides)
    rendered: list[str] = []
    for line in template.splitlines():
        match = PARAMETER_LINE.match(line)
        if not match:
            rendered.append(line)
            continue
        key = match.group("key").strip()
        if key not in pending:
            rendered.append(line)
            continue
        field = field_map.get(key)
        formatted = format_fortran_value(pending.pop(key), field)
        comment = match.group("comment") or ""
        rendered.append(f"{match.group('indent')}{key:<28} = {formatted}{comment}")
    if append_missing and pending:
        rendered.append("")
        rendered.append("# Added by Supernova Simulation Studio")
        for key, value in pending.items():
            rendered.append(f"{key:<28} = {format_fortran_value(value, field_map.get(key))}")
    return "\n".join(rendered).rstrip() + "\n"


def normalize_and_validate(
    raw_values: dict[str, Any], fields: list[ParameterField], *, allow_unknown: bool = False
) -> tuple[dict[str, Any], list[str], list[str]]:
    field_map = {field.key: field for field in fields}
    normalized: dict[str, Any] = {}
    errors: list[str] = []
    warnings: list[str] = []
    for key, raw in raw_values.items():
        field = field_map.get(key)
        if field is None:
            if allow_unknown:
                normalized[key] = raw
                warnings.append(f"未知参数 {key} 将按原值传给求解器")
            else:
                errors.append(f"未知参数：{key}")
            continue
        try:
            value = coerce_value(raw, field)
        except (TypeError, ValueError) as exc:
            errors.append(f"{key}: {exc}")
            continue
        if field.choices is not None and value not in field.choices:
            errors.append(f"{key} 必须是 {field.choices} 之一，当前为 {value!r}")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not math.isfinite(float(value)):
                errors.append(f"{key} 不能为 NaN 或无穷大")
            if field.minimum is not None and value < field.minimum:
                errors.append(f"{key} 不能小于 {field.minimum}")
            if field.maximum is not None and value > field.maximum:
                errors.append(f"{key} 不能大于 {field.maximum}")
        normalized[key] = value
    return normalized, errors, warnings


def axis_values(axis: SweepAxis) -> list[Any]:
    if axis.kind == "list":
        return list(axis.values or [])
    assert axis.start is not None and axis.stop is not None and axis.steps is not None
    if axis.kind == "linear":
        step = (axis.stop - axis.start) / (axis.steps - 1)
        return [axis.start + index * step for index in range(axis.steps)]
    start = math.log10(axis.start)
    stop = math.log10(axis.stop)
    step = (stop - start) / (axis.steps - 1)
    return [10 ** (start + index * step) for index in range(axis.steps)]


def expand_sweep(axes: dict[str, SweepAxis]) -> list[dict[str, Any]]:
    keys = list(axes)
    values = [axis_values(axes[key]) for key in keys]
    return [dict(zip(keys, combination, strict=True)) for combination in product(*values)]


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


COMMON_FIELDS = [
    field(
        "initial_data",
        "爆炸方式",
        "爆炸",
        "enum",
        "Thermal_Bomb",
        choices=["Thermal_Bomb", "Piston_Explosion"],
    ),
    field("final_energy", "最终爆炸能量", "爆炸", "number", 1.0e51, unit="erg", minimum=0),
    field("bomb_tstart", "热炸弹开始时间", "爆炸", "number", 0.0, unit="s", minimum=0),
    field("bomb_tend", "热炸弹结束时间", "爆炸", "number", 0.1, unit="s", minimum=0),
    field("bomb_mass_spread", "能量注入质量范围", "爆炸", "number", 0.1, unit="M☉", minimum=0),
    field("bomb_start_point", "能量注入起始网格", "爆炸", "integer", 1, minimum=1),
    field("piston_vel", "活塞速度", "爆炸", "number", 5.0e9, unit="cm/s", minimum=0, advanced=True),
    field(
        "piston_tstart", "活塞开始时间", "爆炸", "number", 0.0, unit="s", minimum=0, advanced=True
    ),
    field(
        "piston_tend", "活塞结束时间", "爆炸", "number", 0.01, unit="s", minimum=0, advanced=True
    ),
    field("imax", "计算网格数", "网格", "integer", 100, minimum=20, maximum=10000),
    field("mass_excision", "启用质量切除", "网格", "boolean", True),
    field("mass_excised", "切除质量", "网格", "number", 1.4, unit="M☉", minimum=0),
    field("radiation", "启用辐射输运", "演化", "boolean", True),
    field("eoskey", "状态方程", "演化", "enum", 2, choices=[1, 2]),
    field("Ni_switch", "启用 56Ni", "镍混合", "boolean", True),
    field("Ni_mass", "56Ni 质量", "镍混合", "number", 0.03, unit="M☉", minimum=0),
    field(
        "Ni_period",
        "Ni 加热更新周期",
        "镍混合",
        "number",
        5.0e4,
        unit="s",
        minimum=0,
        advanced=True,
    ),
    field("saha_ncomps", "Saha 组分数", "演化", "integer", 3, minimum=0, advanced=True),
    field("boxcar_smoothing", "启用 Boxcar 混合", "镍混合", "boolean", True),
    field(
        "opacity_floor_envelope",
        "包层不透明度下限",
        "演化",
        "number",
        0.01,
        minimum=0,
        advanced=True,
    ),
    field(
        "opacity_floor_core", "核心不透明度下限", "演化", "number", 0.24, minimum=0, advanced=True
    ),
    field("ntmax", "最大时间步数", "时间", "integer", 10_000_000_000_000, minimum=1, advanced=True),
    field("tend", "演化结束时间", "时间", "number", 5.0e6, unit="s", minimum=1),
    field("dtout", "剖面输出间隔", "输出", "number", 5.0e5, unit="s", minimum=0),
    field("dtout_scalar", "标量输出间隔", "输出", "number", 1.0e5, unit="s", minimum=0),
    field("dtout_check", "检查点间隔", "输出", "number", 1.7e9, unit="s", minimum=0, advanced=True),
    field("ntout", "按步输出剖面", "输出", "integer", -1, advanced=True),
    field("ntout_scalar", "按步输出标量", "输出", "integer", -1, advanced=True),
    field("ntout_check", "按步输出检查点", "输出", "integer", -1, advanced=True),
    field("ntinfo", "日志步间隔", "输出", "integer", 1000, minimum=1),
    field("dtmin", "最小时间步", "时间", "number", 1.0e-10, unit="s", minimum=0, advanced=True),
    field("dtmax", "最大时间步", "时间", "number", 1.0e5, unit="s", minimum=0),
    field("sedov", "Sedov 测试模式", "测试", "boolean", False, advanced=True),
]


SUPERSNEC_FIELDS = COMMON_FIELDS + [
    field(
        "grid_mode",
        "网格模式",
        "网格",
        "enum",
        "adaptive_runtime",
        choices=["adaptive_runtime", "legacy_pattern"],
    ),
    field(
        "grid_pattern_file",
        "固定网格文件",
        "网格",
        "string",
        "tables/GridPattern.dat",
        advanced=True,
        sweepable=False,
    ),
    field("grid_surface_alpha", "表面网格集中强度", "网格", "number", 7.0, minimum=0),
    field(
        "grid_relax_days",
        "首次重网格时间",
        "网格",
        "number",
        5.0,
        unit="day",
        minimum=0,
        advanced=True,
    ),
    field(
        "grid_min_cell_frac",
        "最小单元质量比例",
        "网格",
        "number",
        1.0e-4,
        minimum=0,
        maximum=1,
        advanced=True,
    ),
    field(
        "grid_update_interval_days",
        "重网格间隔",
        "网格",
        "number",
        1.0,
        unit="day",
        minimum=0,
        advanced=True,
    ),
    field("grid_debug", "输出网格诊断", "输出", "boolean", False, advanced=True),
    field("Ni_mix_fraction", "56Ni 混合范围", "镍混合", "number", 0.31, minimum=0, maximum=1),
    field(
        "Ni_mix_component2_fraction",
        "外层 Ni 分量",
        "镍混合",
        "number",
        0.0,
        minimum=0,
        maximum=1,
        advanced=True,
    ),
    field(
        "Ni_mix_component2_extent",
        "外层 Ni 范围",
        "镍混合",
        "number",
        0.31,
        minimum=0,
        maximum=1,
        advanced=True,
    ),
    field("Ni_mix_kernel", "Ni 混合核", "镍混合", "enum", 1, choices=[1, 2, 3]),
    field(
        "Ni_period_max",
        "Ni 最大更新周期",
        "镍混合",
        "number",
        5.456e5,
        unit="s",
        minimum=0,
        advanced=True,
    ),
    field(
        "Ni_fractional_change", "Ni 更新变化阈值", "镍混合", "number", 0.7, minimum=0, advanced=True
    ),
    field("Ni_quad_npoints", "Gamma 积分点数", "镍混合", "integer", 70, minimum=10, advanced=True),
    field("smooth_ni_luminosity", "平滑 Ni 光度", "镍混合", "boolean", False, advanced=True),
    field("boxcar_smooth_ni", "单独平滑 Ni", "镍混合", "boolean", True, advanced=True),
    field(
        "boxcar_nominal_mass_msun",
        "Boxcar 质量宽度",
        "镍混合",
        "number",
        0.4,
        unit="M☉",
        minimum=0,
        advanced=True,
    ),
    field(
        "boxcar_number_iterations",
        "Boxcar 迭代次数",
        "镍混合",
        "integer",
        4,
        minimum=0,
        advanced=True,
    ),
    field(
        "boxcar_ni_nominal_mass_msun",
        "Ni Boxcar 质量宽度",
        "镍混合",
        "number",
        0.4,
        unit="M☉",
        minimum=0,
        advanced=True,
    ),
    field(
        "boxcar_ni_number_iterations",
        "Ni Boxcar 迭代次数",
        "镍混合",
        "integer",
        4,
        minimum=0,
        advanced=True,
    ),
    field("dtout_mid", "中期剖面间隔", "输出", "number", 1.0e5, unit="s", minimum=0, advanced=True),
    field(
        "dtout_fast", "早期剖面间隔", "输出", "number", 5.0e4, unit="s", minimum=0, advanced=True
    ),
    field(
        "dtout_scalar_mid",
        "中期标量间隔",
        "输出",
        "number",
        5.0e4,
        unit="s",
        minimum=0,
        advanced=True,
    ),
    field(
        "dtout_scalar_fast",
        "早期标量间隔",
        "输出",
        "number",
        1.0e4,
        unit="s",
        minimum=0,
        advanced=True,
    ),
    field(
        "output_mid_transition_days",
        "早/中期切换",
        "输出",
        "number",
        10.0,
        unit="day",
        minimum=0,
        advanced=True,
    ),
    field(
        "output_late_transition_days",
        "中/晚期切换",
        "输出",
        "number",
        20.0,
        unit="day",
        minimum=0,
        advanced=True,
    ),
    field("epstol_hydro", "流体收敛阈值", "求解器", "number", 1.0e-4, minimum=0, advanced=True),
    field("epstol_rad", "辐射收敛阈值", "求解器", "number", 1.0e-4, minimum=0, advanced=True),
    field("itmax_hydro", "流体最大迭代", "求解器", "integer", 100, minimum=1, advanced=True),
    field("itmax_rad", "辐射最大迭代", "求解器", "integer", 300, minimum=1, advanced=True),
    field("ni_raytrace_opt", "优化 Ni 射线追踪", "求解器", "boolean", True, advanced=True),
    field("output_mode", "输出模式", "输出", "enum", 0, choices=[0, 1], advanced=True),
]


SNEC_FIELDS = COMMON_FIELDS + [
    field(
        "gridding",
        "网格模式",
        "网格",
        "enum",
        "from_file_by_mass",
        choices=["uniform_in_mass", "from_file_by_mass"],
    ),
    field("Ni_boundary_mass", "Ni 混合边界质量", "镍混合", "number", 5.0, unit="M☉", minimum=0),
]
