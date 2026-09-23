from __future__ import annotations

from pathlib import Path

from snstudio.engines.snec import SnecAdapter


def test_exit_zero_without_artifacts_is_failure(studio, tmp_path: Path) -> None:
    settings, _, _ = studio
    adapter = SnecAdapter(settings.supersnec_root, supersnec=True)
    run_dir = tmp_path / "empty-run"
    (run_dir / "Data").mkdir(parents=True)
    errors = adapter.validate_completion(
        run_dir,
        0,
        "*** Output directory does not exist.\n",
    )
    assert any("失败标志" in error for error in errors)
    assert any("完成标志" in error for error in errors)
    assert any("run_summary" in error for error in errors)


def test_original_bad_gridding_enum_is_rejected(studio) -> None:
    settings, _, _ = studio
    adapter = SnecAdapter(settings.snec_root, supersnec=False)
    raw = adapter.template_text().replace(
        'grid_mode = "adaptive_runtime"', 'gridding = "uniform_by_mass"'
    )
    _, _, errors, _ = adapter.validate_and_render({}, raw, "full")
    assert any("uniform_in_mass" in error for error in errors)


def test_original_full_output_does_not_warn_about_minimal(studio) -> None:
    settings, _, _ = studio
    adapter = SnecAdapter(settings.snec_root, supersnec=False)
    _, _, errors, warnings = adapter.validate_and_render({}, None, "full")
    assert not errors
    assert not any("minimal" in warning for warning in warnings)


def test_parameter_schema_defaults_come_from_each_engine_template(studio) -> None:
    settings, _, _ = studio
    (settings.snec_root / "parameters").write_text(
        (settings.snec_root / "parameters").read_text().replace("imax = 100", "imax = 1000")
    )
    adapter = SnecAdapter(settings.snec_root, supersnec=False)
    defaults = {field.key: field.default for field in adapter.parameter_fields()}
    assert defaults["imax"] == 1000


def test_stage_quotes_managed_paths(studio, tmp_path: Path) -> None:
    _settings, _, registry = studio
    adapter = registry.get("supersnec")
    profile = adapter.builtin_profiles()[0].model_dump()
    profile["structure_path"] = profile["metadata"]["structure_path"]
    profile["composition_path"] = profile["metadata"]["composition_path"]
    rendered, _, errors, _ = adapter.validate_and_render({}, None, "minimal")
    assert not errors
    final = adapter.stage(tmp_path / "run", profile, rendered)
    assert 'outdir                       = "Data"' in final
    assert 'profile_name                 = "profiles/model.short"' in final
    assert (tmp_path / "run" / "Data").is_dir()
