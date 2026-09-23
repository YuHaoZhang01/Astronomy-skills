from __future__ import annotations

import pytest

from snstudio.parameters import (
    SNEC_FIELDS,
    SUPERSNEC_FIELDS,
    SweepAxis,
    expand_sweep,
    parse_fortran_number,
    parse_parameter_text,
    render_parameter_text,
)


def test_parse_and_render_preserves_comments_and_fortran_values() -> None:
    template = 'final_energy = 1.0d51 # erg\ngridding = "from_file_by_mass"\n'
    parsed = parse_parameter_text(template)
    assert parsed["final_energy"] == "1.0d51"
    rendered = render_parameter_text(
        template,
        {"final_energy": 2.0e51, "gridding": "uniform_in_mass"},
        SNEC_FIELDS,
    )
    assert "2.0d51" in rendered
    assert '"uniform_in_mass"' in rendered
    assert "# erg" in rendered
    assert parse_fortran_number("1.0d51") == pytest.approx(1.0e51)


def test_numeric_enums_are_not_quoted() -> None:
    template = 'eoskey = 2\noutput_mode = 0\ngrid_mode = "adaptive_runtime"\n'
    rendered = render_parameter_text(
        template,
        {"eoskey": 1, "output_mode": 1, "grid_mode": "legacy_pattern"},
        SUPERSNEC_FIELDS,
    )
    assert "eoskey                       = 1" in rendered
    assert "output_mode                  = 1" in rendered
    assert 'grid_mode                    = "legacy_pattern"' in rendered


def test_number_field_uses_fortran_double_even_for_integer_json() -> None:
    template = "tend = 5.0d6\nNi_mass = 0.05d0\n"
    rendered = render_parameter_text(
        template,
        {"tend": 5000000, "Ni_mass": 0.03},
        SUPERSNEC_FIELDS,
    )
    assert "tend                         = 5000000.0d0" in rendered
    assert "Ni_mass                      = 0.03d0" in rendered


def test_expand_linear_log_and_list_sweep() -> None:
    combinations = expand_sweep(
        {
            "Ni_mass": SweepAxis(kind="list", values=[0.03, 0.05]),
            "final_energy": SweepAxis(kind="log", start=1e50, stop=1e51, steps=2),
        }
    )
    assert len(combinations) == 4
    assert combinations[0] == {"Ni_mass": 0.03, "final_energy": pytest.approx(1e50)}
    assert combinations[-1]["final_energy"] == pytest.approx(1e51)


def test_validation_rejects_bad_enum_and_range() -> None:
    from snstudio.parameters import normalize_and_validate

    normalized, errors, _ = normalize_and_validate(
        {"initial_data": "Not_A_Real_Mode", "Ni_mass": -0.1},
        SUPERSNEC_FIELDS,
    )
    assert normalized["initial_data"] == "Not_A_Real_Mode"
    assert any("initial_data 必须是" in error for error in errors)
    assert any("Ni_mass" in error and "小于" in error for error in errors)
