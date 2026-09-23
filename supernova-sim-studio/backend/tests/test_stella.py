from __future__ import annotations

from pathlib import Path

import pytest

from snstudio.engines.stella import (
    OPENSTELLA_COMMIT,
    StellaAdapter,
    parse_stella_parameters,
    photospheric_velocity,
)

STELLA_DAT = """   EPS HMIN HMAX
   0.003 1.D-14 5.D+4
   METH JSTART MAXORD KNadap
   2 0 4 -4
   NSTA NSTB TcurA TcurB
   -4500 -1 0. 400.
   NSTMAX NDebug NOUT IOUT MBATCH
   36000 100000 900 -10 900
   AMNI XMNI
   8.D-01 0.4d0
   AMHT EBurst tBurst tstart
   0.d-5 0.d-5 0.d-5 0.d0
   EKO mass-frac tri-profile us
   0.d-5 0.d0 9.d-1 1.d0 +1.
   THRMAT CRAP CONV EDTM CHNCND Givdtl
   1.D-30 1.D0 F T T F
   floors
   1.D-08 1.D-03 3.D-02 1.D-02 1.D-04
   weights
   1.d-0 1.d-0 1.D-01 1.D-00
   FitTau TAUTOL Rvis AQ BQ DRT NRT SCAT
   1.5D01 1.3D0 1.D0 2.D0 1.D+00 1. 1 T
   NTO
   3
   0.24d0
   0.5d0
   1.d0
"""


def create_stella_root(root: Path) -> Path:
    (root / "run" / "eve").mkdir(parents=True)
    (root / "run" / "vladsf").mkdir()
    (root / "run" / "strad").mkdir()
    (root / ".snstudio-openstella-version").write_text(OPENSTELLA_COMMIT + "\n")
    binary = root / "run" / "strad" / "xstella6y12m.exe"
    binary.write_text("#!/bin/sh\nexit 0\n")
    binary.chmod(0o755)
    (root / "run" / "strad" / "m030307mhomo.dat").write_text(STELLA_DAT)
    for suffix in ("mod", "rho", "xni"):
        (root / "run" / "eve" / f"m030307mhomo.{suffix}").write_text(suffix)
    for suffix in ("1", "2", "3", "4", "5", "6", "ab"):
        (root / "run" / "vladsf" / f"m030307mhomo.{suffix}").write_text(suffix)
    return root


def test_stella_parameter_parse_render_and_validation(tmp_path: Path) -> None:
    adapter = StellaAdapter(create_stella_root(tmp_path / "stella"))
    values, errors = parse_stella_parameters(STELLA_DAT)
    assert not errors
    assert values["TcurB"] == "400."
    rendered, normalized, errors, warnings = adapter.validate_and_render(
        {"TcurB": 2.0, "SCAT": False}, None, "minimal"
    )
    assert not errors
    assert normalized["tend"] == 2.0
    assert "2.0d0" in rendered
    assert rendered.splitlines()[21].endswith("F")
    assert any("原生核心输出" in warning for warning in warnings)

    _, _, errors, _ = adapter.validate_and_render({"TcurB": 0.01}, None, "full")
    assert any("不能小于" in error for error in errors)
    _, _, errors, _ = adapter.validate_and_render({"not_a_parameter": 1}, None, "full")
    assert any("未知 STELLA 参数" in error for error in errors)


def test_stella_doctor_stage_progress_and_isolation(tmp_path: Path) -> None:
    adapter = StellaAdapter(create_stella_root(tmp_path / "stella"))
    assert adapter.doctor().enabled
    profile = adapter.builtin_profiles()[0].model_dump(mode="python")
    rendered, _, errors, _ = adapter.validate_and_render({"TcurB": 1.0}, None, "full")
    assert not errors
    first = tmp_path / "run-a"
    second = tmp_path / "run-b"
    adapter.stage(first, profile, rendered)
    adapter.stage(second, profile, rendered)
    assert (first / "workspace" / "eve" / "m030307mhomo.mod").is_symlink()
    assert (second / "workspace" / "res").is_dir()
    assert first / "workspace" != second / "workspace"
    assert adapter.command(first) == [str(first / "run-stella")]
    progress = adapter.parse_progress("  42 189 1 Hu=1.d0 td= 0.50 Ncnd=0", 1.0)
    assert progress == (0.5, 0.5)


def test_stella_completion_and_standard_series(tmp_path: Path) -> None:
    adapter = StellaAdapter(create_stella_root(tmp_path / "stella"))
    run_dir = tmp_path / "run"
    result_dir = run_dir / "workspace" / "res"
    result_dir.mkdir(parents=True)
    (result_dir / "result.tt").write_text(
        "0.5 6000 1e14 5500 1e14 8e13 -17 -16 -16.5 -17 -17.2 -17.1 -17 0\n"
    )
    (result_dir / "result.lbol").write_text("0.5 42.0 42.5 40.0 41.0\n")
    (result_dir / "result.swd").write_text("real swd\n")
    (result_dir / "result.res").write_text("real res\n")
    assert not adapter.validate_completion(run_dir, 0, "STOP Normal stop of stella")
    series = {item.id: item for item in adapter.parse_series(run_dir)}
    assert set(series) == {"lbol", "t_eff", "v_ph", "mag_U", "mag_B", "mag_V", "mag_R", "mag_I"}
    assert series["lbol"].y[0] == pytest.approx(10**42.5)
    assert series["mag_R"].y == [-17.1]
    assert series["mag_I"].y == [-17.2]
    assert series["v_ph"].y[0] == pytest.approx(photospheric_velocity(0.5, 8e13))

    errors = adapter.validate_completion(tmp_path / "missing", 0, "")
    assert any("正常完成标志" in error for error in errors)
    assert any("result.tt" in error for error in errors)
