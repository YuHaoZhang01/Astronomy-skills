"""Reusable plotting style for multiband supernova light curves.

The style is wavelength-driven:

- filter effective wavelength controls sorting and magnitude offset
- filter/band identity controls a stable color
- survey/instrument controls marker shape
- offsets are added to magnitudes before plotting
- magnitude axes are drawn inverted

The wavelength table is meant for consistent plotting, not precision synthetic
photometry. Values are approximate effective wavelengths in nm, mostly rounded
from SVO Filter Profile Service entries.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any
import re

import matplotlib as mpl
import numpy as np


@dataclass(frozen=True)
class BandStyle:
    color: str
    offset: float
    wavelength_nm: float | None = None


@dataclass(frozen=True)
class FilterInfo:
    system: str
    band: str
    wavelength_nm: float
    color: str


BAND_COLORS: dict[str, str] = {
    "fuv": "#3f007d",
    "uvw2": "#54278f",
    "uvm2": "#6a51a3",
    "uvw1": "#807dba",
    "nuv": "#756bb1",
    "u": "#7b61ff",
    "b": "#3b5bdb",
    "gbp": "#2b8cbe",
    "g": "#1b9e77",
    "c": "#3b5bdb",
    "w": "#7f7f7f",
    "white": "#737373",
    "clear": "#737373",
    "open": "#737373",
    "v": "#66a61e",
    "r": "#d95f02",
    "o": "#e59f00",
    "i": "#8c6d31",
    "grp": "#8c510a",
    "z": "#6f4e37",
    "y": "#5d4037",
    "t": "#8c6d31",
    "j": "#8d5524",
    "h": "#6b4226",
    "k": "#4e342e",
    "ks": "#4e342e",
    "w1": "#5d4037",
    "w2": "#4e342e",
    "w3": "#3e2723",
    "w4": "#2d1b16",
}


FILTER_SYSTEMS: dict[str, dict[str, tuple[float, str]]] = {
    "galex": {
        "fuv": (154.885, BAND_COLORS["fuv"]),
        "nuv": (230.337, BAND_COLORS["nuv"]),
    },
    "uvot": {
        "uvw2": (208.395, BAND_COLORS["uvw2"]),
        "uvm2": (224.503, BAND_COLORS["uvm2"]),
        "uvw1": (268.167, BAND_COLORS["uvw1"]),
        "u": (352.088, BAND_COLORS["u"]),
        "white": (387.562, BAND_COLORS["white"]),
        "b": (434.528, BAND_COLORS["b"]),
        "v": (541.145, BAND_COLORS["v"]),
    },
    "johnson": {
        "u": (367.827, BAND_COLORS["u"]),
        "b": (436.505, BAND_COLORS["b"]),
        "v": (545.177, BAND_COLORS["v"]),
        "r": (698.586, BAND_COLORS["r"]),
        "i": (856.343, BAND_COLORS["i"]),
    },
    "cousins": {
        "r": (635.735, BAND_COLORS["r"]),
        "i": (782.865, BAND_COLORS["i"]),
    },
    "sdss": {
        "u": (360.804, BAND_COLORS["u"]),
        "g": (467.178, BAND_COLORS["g"]),
        "r": (614.112, BAND_COLORS["r"]),
        "i": (745.789, BAND_COLORS["i"]),
        "z": (892.278, BAND_COLORS["z"]),
    },
    "ps1": {
        "g": (481.016, BAND_COLORS["g"]),
        "w": (598.070, "#7f7f7f"),
        "r": (615.547, BAND_COLORS["r"]),
        "open": (643.187, BAND_COLORS["clear"]),
        "i": (750.303, BAND_COLORS["i"]),
        "z": (866.836, BAND_COLORS["z"]),
        "y": (961.360, BAND_COLORS["y"]),
    },
    "lsst": {
        "u": (375.120, BAND_COLORS["u"]),
        "g": (474.066, BAND_COLORS["g"]),
        "r": (617.234, BAND_COLORS["r"]),
        "i": (750.097, BAND_COLORS["i"]),
        "z": (867.890, BAND_COLORS["z"]),
        "y": (971.182, BAND_COLORS["y"]),
    },
    "ztf": {
        "g": (474.648, BAND_COLORS["g"]),
        "r": (636.638, BAND_COLORS["r"]),
        "i": (782.903, BAND_COLORS["i"]),
    },
    "atlas": {
        "c": (518.242, BAND_COLORS["c"]),
        "o": (662.982, BAND_COLORS["o"]),
    },
    # Current local workflow convention from EP250108a-fitting_Ni_Arnett.ipynb.
    "mephisto": {
        "u": (340.000, BAND_COLORS["u"]),
        "v": (390.000, BAND_COLORS["v"]),
        "g": (525.000, BAND_COLORS["g"]),
        "r": (630.000, BAND_COLORS["r"]),
        "i": (830.000, BAND_COLORS["i"]),
        "z": (970.000, BAND_COLORS["z"]),
    },
    "skymapper": {
        "u": (350.022, BAND_COLORS["u"]),
        "v": (387.868, BAND_COLORS["v"]),
        "g": (501.605, BAND_COLORS["g"]),
        "r": (607.685, BAND_COLORS["r"]),
        "i": (773.283, BAND_COLORS["i"]),
        "z": (912.025, BAND_COLORS["z"]),
    },
    "2mass": {
        "j": (1235.000, BAND_COLORS["j"]),
        "h": (1662.000, BAND_COLORS["h"]),
        "ks": (2159.000, BAND_COLORS["ks"]),
    },
    "gaia": {
        "gbp": (504.161, BAND_COLORS["gbp"]),
        "g": (585.088, BAND_COLORS["g"]),
        "grp": (769.074, BAND_COLORS["grp"]),
    },
    "tess": {
        "t": (745.264, BAND_COLORS["t"]),
    },
    "wise": {
        "w1": (3352.600, BAND_COLORS["w1"]),
        "w2": (4602.800, BAND_COLORS["w2"]),
        "w3": (11560.800, BAND_COLORS["w3"]),
        "w4": (22088.300, BAND_COLORS["w4"]),
    },
}


# Generic, system-free fallbacks. These are used when the data only says "g"
# instead of "ZTF g" or "SDSS g".
BAND_WAVELENGTH_NM: dict[str, float] = {
    "fuv": 154.885,
    "uvw2": 208.395,
    "uvm2": 224.503,
    "uvw1": 268.167,
    "nuv": 230.337,
    "u": 365.0,
    "b": 436.0,
    "gbp": 504.161,
    "g": 477.0,
    "c": 518.242,
    "w": 598.070,
    "white": 387.562,
    "clear": 550.0,
    "open": 643.187,
    "v": 545.0,
    "r": 623.0,
    "o": 662.982,
    "i": 763.0,
    "grp": 769.074,
    "z": 900.0,
    "y": 970.0,
    "t": 745.264,
    "j": 1235.0,
    "h": 1662.0,
    "ks": 2159.0,
    "k": 2159.0,
    "w1": 3352.6,
    "w2": 4602.8,
    "w3": 11560.8,
    "w4": 22088.3,
}


SYSTEM_ALIASES: dict[str, str] = {
    "swift": "uvot",
    "uvot": "uvot",
    "sloan": "sdss",
    "sdss": "sdss",
    "panstarrs": "ps1",
    "pan_starrs": "ps1",
    "pan-starrs": "ps1",
    "ps1": "ps1",
    "palomar": "ztf",
    "ztf": "ztf",
    "atlas": "atlas",
    "mephisto": "mephisto",
    "mep": "mephisto",
    "lsst": "lsst",
    "rubin": "lsst",
    "skymapper": "skymapper",
    "2mass": "2mass",
    "twomass": "2mass",
    "gaia": "gaia",
    "galex": "galex",
    "tess": "tess",
    "wise": "wise",
    "johnson": "johnson",
    "cousins": "cousins",
}


BAND_ALIASES: dict[str, str] = {
    "cyan": "c",
    "orange": "o",
    "clear": "clear",
    "open": "open",
    "white": "white",
    "bp": "gbp",
    "gbp": "gbp",
    "g_bp": "gbp",
    "gblue": "gbp",
    "rp": "grp",
    "grp": "grp",
    "g_rp": "grp",
    "gred": "grp",
    "rc": "r",
    "r_c": "r",
    "ic": "i",
    "i_c": "i",
    "ks": "ks",
    "k_s": "ks",
    "red": "t",
}


DEFAULT_BAND_SEQUENCE: tuple[str, ...] = ("g", "c", "r", "o", "i")
WAVELENGTH_COLOR_SEQUENCE: tuple[str, ...] = (
    "#54278f",
    "#3b5bdb",
    "#1b9e77",
    "#d95f02",
    "#e59f00",
    "#8c6d31",
    "#4e342e",
)


SURVEY_MARKERS: dict[str, str] = {
    "ztf": "o",
    "slt": "s",
    "atlas": "^",
    "mephisto": "D",
    "swift": "v",
    "uvot": "v",
    "sdss": "P",
    "ps1": "X",
    "lsst": "h",
    "gaia": "*",
    "tess": "p",
    "wise": "8",
}


APJ_RC: dict[str, Any] = {
    "figure.figsize": (3.5, 2.6),
    "figure.dpi": 200,
    "savefig.dpi": 600,
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset": "cm",
    "axes.labelsize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.linewidth": 0.8,
    "xtick.direction": "in",
    "ytick.direction": "in",
    "xtick.major.size": 4,
    "ytick.major.size": 4,
    "xtick.minor.size": 2.5,
    "ytick.minor.size": 2.5,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.visible": True,
    "ytick.minor.visible": True,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).strip().lower()).strip("_")


def _is_missing(value: Any) -> bool:
    try:
        return value is None or value != value
    except TypeError:
        return value is None


def normalize_system(system: str | None) -> str:
    if _is_missing(system):
        return ""
    key = _compact(system)
    return SYSTEM_ALIASES.get(key, key)


def normalize_band_name(band: str) -> str:
    key = _compact(str(band).replace("'", "prime"))
    key = key.replace("_filter", "").replace("_band", "")
    return BAND_ALIASES.get(key, key)


def _filter_info_table() -> dict[str, FilterInfo]:
    table: dict[str, FilterInfo] = {}
    for system, filters in FILTER_SYSTEMS.items():
        for band, (wavelength_nm, color) in filters.items():
            table[f"{system}_{band}"] = FilterInfo(
                system=system,
                band=band,
                wavelength_nm=wavelength_nm,
                color=color,
            )
    return table


FILTER_INFO: dict[str, FilterInfo] = _filter_info_table()


def canonical_filter_key(band: str, system: str | None = None) -> str:
    """Return a canonical key like ``ztf_g`` or a generic key like ``g``."""
    if not _is_missing(system):
        sys_key = normalize_system(system)
        band_key = normalize_band_name(band)
        key = f"{sys_key}_{band_key}"
        if key in FILTER_INFO:
            return key
        if sys_key == "atlas" and band_key in {"cyan", "orange"}:
            return f"atlas_{BAND_ALIASES[band_key]}"
        return band_key

    raw = str(band).strip()
    direct = _compact(raw)
    if direct in FILTER_INFO:
        return direct

    tokens = [tok for tok in re.split(r"[/.:_\-\s]+", raw.lower()) if tok]
    if len(tokens) >= 2:
        band_key = normalize_band_name(tokens[-1])
        for token in reversed(tokens[:-1]):
            sys_key = normalize_system(token)
            key = f"{sys_key}_{band_key}"
            if key in FILTER_INFO:
                return key
            if sys_key == "atlas" and band_key in {"cyan", "orange"}:
                return f"atlas_{BAND_ALIASES[band_key]}"

    return normalize_band_name(raw)


def normalize_band(band: str) -> str:
    """Backward-compatible alias for canonical_filter_key()."""
    return canonical_filter_key(band)


def base_band_name(band: str, system: str | None = None) -> str:
    key = canonical_filter_key(band, system=system)
    if key in FILTER_INFO:
        return FILTER_INFO[key].band
    return BAND_ALIASES.get(key, key)


def display_band(band: str, system: str | None = None) -> str:
    base = base_band_name(band, system=system)
    labels = {
        "fuv": "FUV",
        "nuv": "NUV",
        "uvw2": "UVW2",
        "uvm2": "UVM2",
        "uvw1": "UVW1",
        "gbp": "BP",
        "grp": "RP",
        "ks": "Ks",
        "w1": "W1",
        "w2": "W2",
        "w3": "W3",
        "w4": "W4",
    }
    return labels.get(base, base)


def apply_sn_style() -> None:
    """Apply the reusable light-curve figure style."""
    mpl.rcParams.update(APJ_RC)


def normalized_wavelengths(
    wavelengths: Mapping[str, float] | None = None,
) -> dict[str, float]:
    merged = dict(BAND_WAVELENGTH_NM)
    merged.update({key: info.wavelength_nm for key, info in FILTER_INFO.items()})
    if wavelengths:
        for band, wavelength_nm in wavelengths.items():
            merged[canonical_filter_key(band)] = float(wavelength_nm)
    return merged


def band_wavelength_nm(
    band: str,
    system: str | None = None,
    wavelengths: Mapping[str, float] | None = None,
) -> float | None:
    key = canonical_filter_key(band, system=system)
    wave = normalized_wavelengths(wavelengths)
    if key in wave:
        return wave[key]
    return wave.get(base_band_name(key))


def sort_bands_by_wavelength(
    bands: Iterable[str],
    wavelengths: Mapping[str, float] | None = None,
    *,
    systems: Iterable[str | None] | None = None,
) -> list[str]:
    """Return unique filter keys sorted from short to long effective wavelength."""
    wave = normalized_wavelengths(wavelengths)
    unique = filter_keys_from_columns(bands, systems=systems)
    return sorted(unique, key=lambda key: (wave.get(key, np.inf), key))


def _unique_filter_keys(keys: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for key in keys:
        if key and key not in seen:
            unique.append(key)
            seen.add(key)
    return unique


def filter_keys_from_columns(
    bands: Iterable[str],
    *,
    systems: Iterable[str | None] | None = None,
) -> list[str]:
    """Return unique canonical filter keys from band and optional system columns."""
    if systems is None:
        return _unique_filter_keys(canonical_filter_key(band) for band in bands)
    return _unique_filter_keys(
        canonical_filter_key(band, system=system)
        for band, system in zip(bands, systems)
    )


def _column_values(table: Any, column: str) -> list[Any]:
    if isinstance(table, Mapping):
        return list(table[column])
    try:
        return list(table[column])
    except (KeyError, TypeError):
        pass
    try:
        return [row[column] for row in table]
    except (KeyError, TypeError) as exc:
        raise TypeError(
            "table must be a pandas-like table, mapping of columns, or records"
        ) from exc


def filter_keys_from_table(
    table: Any,
    *,
    band_col: str = "band",
    system_col: str | None = None,
) -> list[str]:
    """Return unique canonical filter keys from a photometry table."""
    bands = _column_values(table, band_col)
    if system_col is None:
        return filter_keys_from_columns(bands)
    systems = _column_values(table, system_col)
    return filter_keys_from_columns(bands, systems=systems)


def available_filter_systems() -> dict[str, tuple[str, ...]]:
    """Return built-in systems and bands, sorted by wavelength within each system."""
    systems: dict[str, list[tuple[float, str]]] = {}
    for info in FILTER_INFO.values():
        systems.setdefault(info.system, []).append((info.wavelength_nm, info.band))
    return {
        system: tuple(band for _, band in sorted(items))
        for system, items in sorted(systems.items())
    }


def band_style_table(
    styles: Mapping[str, BandStyle] | None = None,
) -> list[dict[str, Any]]:
    """Return the active styles as rows for quick notebook inspection."""
    rows: list[dict[str, Any]] = []
    for key, style in (styles or BAND_STYLES).items():
        info = FILTER_INFO.get(key)
        system = "" if info is None else info.system
        band = base_band_name(key)
        rows.append(
            {
                "key": key,
                "system": system,
                "band": band,
                "wavelength_nm": style.wavelength_nm,
                "offset": style.offset,
                "color": style.color,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            np.inf if row["wavelength_nm"] is None else row["wavelength_nm"],
            row["key"],
        ),
    )


def _rank_color(rank: int, n_bands: int, colors: Iterable[str] | None = None) -> str:
    palette = tuple(colors or WAVELENGTH_COLOR_SEQUENCE)
    x = 0.5 if n_bands <= 1 else rank / (n_bands - 1)
    cmap = mpl.colors.LinearSegmentedColormap.from_list("sn_wavelength_order", palette)
    return mpl.colors.to_hex(cmap(x))


def filter_color(band: str, system: str | None = None) -> str:
    key = canonical_filter_key(band, system=system)
    if key in FILTER_INFO:
        return FILTER_INFO[key].color
    return BAND_COLORS.get(base_band_name(key), "#666666")


def make_band_styles_by_wavelength(
    bands: Iterable[str],
    *,
    offset_step: float = 2.0,
    center_band: str | None = None,
    wavelengths: Mapping[str, float] | None = None,
    colors: Mapping[str, str] | None = None,
    color_sequence: Iterable[str] | None = None,
) -> dict[str, BandStyle]:
    """Build band styles from wavelength order.

    Shorter wavelengths get positive offsets and longer wavelengths get negative
    offsets. Known filters keep stable colors across projects; unknown filters
    are colored from the rank palette.
    """
    ordered = sort_bands_by_wavelength(bands, wavelengths=wavelengths)
    wave = normalized_wavelengths(wavelengths)
    normalized_colors = {
        canonical_filter_key(band): color for band, color in (colors or {}).items()
    }
    normalized_colors.update({
        base_band_name(band): color for band, color in (colors or {}).items()
    })

    center_index = 0.5 * (len(ordered) - 1)
    if center_band is not None:
        center_key = canonical_filter_key(center_band)
        center_base = base_band_name(center_key)
        if center_key in ordered:
            center_index = float(ordered.index(center_key))
        else:
            for i, band in enumerate(ordered):
                if base_band_name(band) == center_base:
                    center_index = float(i)
                    break

    styles: dict[str, BandStyle] = {}
    for rank, band in enumerate(ordered):
        base = base_band_name(band)
        offset = (center_index - rank) * float(offset_step)
        default_color = (
            filter_color(band)
            if band in FILTER_INFO or base in BAND_COLORS
            else _rank_color(rank, len(ordered), color_sequence)
        )
        color = (
            normalized_colors.get(band)
            or normalized_colors.get(base)
            or default_color
        )
        styles[band] = BandStyle(color=color, offset=offset, wavelength_nm=wave.get(band))
    return styles


def set_band_styles_by_wavelength(
    bands: Iterable[str] = DEFAULT_BAND_SEQUENCE,
    *,
    offset_step: float = 2.0,
    center_band: str | None = None,
    wavelengths: Mapping[str, float] | None = None,
    colors: Mapping[str, str] | None = None,
    color_sequence: Iterable[str] | None = None,
) -> dict[str, BandStyle]:
    """Set the module-level band style table from the active dataset filters."""
    global BAND_STYLES
    BAND_STYLES = make_band_styles_by_wavelength(
        bands,
        offset_step=offset_step,
        center_band=center_band,
        wavelengths=wavelengths,
        colors=colors,
        color_sequence=color_sequence,
    )
    return BAND_STYLES


def set_band_styles_from_table(
    table: Any,
    *,
    band_col: str = "band",
    system_col: str | None = None,
    offset_step: float = 2.0,
    center_band: str | None = None,
    wavelengths: Mapping[str, float] | None = None,
    colors: Mapping[str, str] | None = None,
    color_sequence: Iterable[str] | None = None,
) -> dict[str, BandStyle]:
    """Set active styles from a photometry table's band and optional system columns."""
    return set_band_styles_by_wavelength(
        filter_keys_from_table(table, band_col=band_col, system_col=system_col),
        offset_step=offset_step,
        center_band=center_band,
        wavelengths=wavelengths,
        colors=colors,
        color_sequence=color_sequence,
    )


def register_band_wavelength(
    band: str,
    wavelength_nm: float,
    *,
    system: str | None = None,
    color: str | None = None,
) -> str:
    """Add or override a filter wavelength used for sorting future style tables."""
    if system is None:
        key = normalize_band_name(band)
        BAND_WAVELENGTH_NM[key] = float(wavelength_nm)
        if color is not None:
            BAND_COLORS[key] = color
        return key

    sys_key = normalize_system(system)
    band_key = normalize_band_name(band)
    key = f"{sys_key}_{band_key}"
    filter_color_value = color or BAND_COLORS.get(band_key, "#666666")
    FILTER_INFO[key] = FilterInfo(sys_key, band_key, float(wavelength_nm), filter_color_value)
    return key


def register_filter_system(
    system: str,
    wavelengths: Mapping[str, float],
    *,
    colors: Mapping[str, str] | None = None,
) -> dict[str, FilterInfo]:
    """Register a custom filter system such as an instrument-specific filter set."""
    registered: dict[str, FilterInfo] = {}
    for band, wavelength_nm in wavelengths.items():
        key = register_band_wavelength(
            band,
            wavelength_nm,
            system=system,
            color=(colors or {}).get(band),
        )
        registered[key] = FILTER_INFO[key]
    return registered


# Default preview style. Real datasets should usually call set_band_styles_by_wavelength().
BAND_STYLES: dict[str, BandStyle] = make_band_styles_by_wavelength(
    DEFAULT_BAND_SEQUENCE,
    offset_step=2.0,
    center_band="r",
)


def band_style(band: str, system: str | None = None) -> BandStyle:
    key = canonical_filter_key(band, system=system)
    base = base_band_name(key)
    if key in BAND_STYLES:
        return BAND_STYLES[key]
    if base in BAND_STYLES:
        return BAND_STYLES[base]
    return BandStyle(filter_color(key), 0.0, band_wavelength_nm(key))


def band_color(band: str, system: str | None = None) -> str:
    return band_style(band, system=system).color


def band_offset(band: str, system: str | None = None) -> float:
    return band_style(band, system=system).offset


def normalize_survey(survey: str | None) -> str:
    if survey is None:
        return ""
    return normalize_system(survey)


def survey_marker(survey: str | None) -> str:
    key = normalize_survey(survey)
    return SURVEY_MARKERS.get(key, SURVEY_MARKERS.get(_compact(survey or ""), "o"))


def offset_label(offset: float) -> str:
    if abs(offset) < 1.0e-12:
        return ""
    return f" (${offset:+g}$)"


def photometry_label(
    survey: str | None,
    band: str,
    offset: float | None = None,
) -> str:
    off = band_offset(band, system=survey) if offset is None else float(offset)
    survey_part = "" if survey is None else str(survey).strip().upper()
    band_part = display_band(band, system=survey)
    return f"{survey_part} {band_part}{offset_label(off)}".strip()


def shifted_mag(
    mag: Any,
    band: str,
    offset: float | None = None,
    *,
    system: str | None = None,
) -> np.ndarray:
    off = band_offset(band, system=system) if offset is None else float(offset)
    return np.asarray(mag, dtype=float) + off


def plot_photometry(
    ax: Any,
    t_day: Any,
    mag: Any,
    err: Any | None = None,
    *,
    survey: str | None = None,
    band: str,
    offset: float | None = None,
    label: str | None = None,
    **kwargs: Any,
) -> Any:
    """Plot one observed photometry series with standard marker/color/offset."""
    color = kwargs.pop("color", band_color(band, system=survey))
    marker = kwargs.pop("marker", survey_marker(survey))
    fmt = kwargs.pop("fmt", marker)
    label = photometry_label(survey, band, offset) if label is None else label

    return ax.errorbar(
        t_day,
        shifted_mag(mag, band, offset, system=survey),
        yerr=err,
        fmt=fmt,
        color=color,
        ecolor=color,
        markerfacecolor=kwargs.pop("markerfacecolor", "none"),
        markeredgecolor=kwargs.pop("markeredgecolor", "black"),
        markeredgewidth=kwargs.pop("markeredgewidth", 0.8),
        markersize=kwargs.pop("markersize", 4.0),
        capsize=kwargs.pop("capsize", 2.0),
        elinewidth=kwargs.pop("elinewidth", 0.8),
        linestyle=kwargs.pop("linestyle", "none"),
        label=label,
        **kwargs,
    )


def plot_model_band(
    ax: Any,
    t_day: Any,
    mag: Any,
    *,
    band: str,
    system: str | None = None,
    offset: float | None = None,
    lo: Any | None = None,
    hi: Any | None = None,
    label: str | None = None,
    alpha: float = 0.18,
    lw: float = 1.4,
    **kwargs: Any,
) -> Any:
    """Plot one model light curve, optionally with a confidence envelope."""
    color = kwargs.pop("color", band_color(band, system=system))
    if lo is not None and hi is not None:
        ax.fill_between(
            t_day,
            shifted_mag(lo, band, offset, system=system),
            shifted_mag(hi, band, offset, system=system),
            color=color,
            alpha=alpha,
            linewidth=0,
        )
    return ax.plot(
        t_day,
        shifted_mag(mag, band, offset, system=system),
        color=color,
        lw=lw,
        label=label,
        **kwargs,
    )


def setup_lightcurve_axes(
    ax: Any,
    *,
    xlim: tuple[float, float] | None = (0.0, 300.0),
    ylim: tuple[float, float] | None = (26.5, 12.0),
    xlabel: str = "Days since first detection (days)",
    ylabel: str = "Apparent magnitude (mag)",
) -> None:
    """Apply standard axes labels, limits, minor ticks, and inverted magnitude axis."""
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xlim is not None:
        ax.set_xlim(*xlim)
    if ylim is not None:
        ax.set_ylim(*ylim)
    elif ax.get_ylim()[0] < ax.get_ylim()[1]:
        ax.invert_yaxis()
    ax.minorticks_on()
    ax.tick_params(which="both", top=False, right=False)


def lightcurve_legend(
    ax: Any,
    *,
    ncol: int = 3,
    loc: str = "lower center",
    **kwargs: Any,
) -> Any:
    """Draw the compact multi-column legend used by the reference figure."""
    legend_kwargs = dict(
        frameon=False,
        ncol=ncol,
        loc=loc,
        columnspacing=1.2,
        handletextpad=0.5,
        borderaxespad=0.7,
    )
    legend_kwargs.update(kwargs)
    return ax.legend(**legend_kwargs)


def _legend_overlap_score(
    ax: Any,
    legend: Any,
    *,
    pad_px: float = 6.0,
    samples_per_segment: int = 8,
) -> float:
    renderer = ax.figure.canvas.get_renderer()
    bbox = legend.get_window_extent(renderer).expanded(1.04, 1.12)
    bbox = mpl.transforms.Bbox.from_extents(
        bbox.x0 - pad_px,
        bbox.y0 - pad_px,
        bbox.x1 + pad_px,
        bbox.y1 + pad_px,
    )

    axes_bbox = ax.get_window_extent(renderer)
    overlap_area = max(0.0, min(bbox.x1, axes_bbox.x1) - max(bbox.x0, axes_bbox.x0))
    overlap_area *= max(0.0, min(bbox.y1, axes_bbox.y1) - max(bbox.y0, axes_bbox.y0))
    outside_area = max(0.0, bbox.width * bbox.height - overlap_area)
    score = outside_area / 100.0

    for line in ax.lines:
        if not line.get_visible():
            continue
        try:
            x = np.asarray(line.get_xdata(orig=False), dtype=float)
            y = np.asarray(line.get_ydata(orig=False), dtype=float)
        except (TypeError, ValueError):
            continue
        finite = np.isfinite(x) & np.isfinite(y)
        if np.count_nonzero(finite) == 0:
            continue
        points = ax.transData.transform(np.column_stack([x[finite], y[finite]]))
        if len(points) > 1:
            fractions = np.linspace(0.0, 1.0, samples_per_segment)
            starts = points[:-1]
            deltas = points[1:] - points[:-1]
            points = (
                starts[:, None, :]
                + deltas[:, None, :] * fractions[None, :, None]
            ).reshape(-1, 2)
        inside = (
            (points[:, 0] >= bbox.x0)
            & (points[:, 0] <= bbox.x1)
            & (points[:, 1] >= bbox.y0)
            & (points[:, 1] <= bbox.y1)
        )
        score += float(np.count_nonzero(inside))
    return score


def lightcurve_legend_inside_clear(
    ax: Any,
    *,
    ncol: int = 1,
    locs: Iterable[str] = (
        "upper right",
        "lower right",
        "center right",
        "upper left",
        "lower left",
        "upper center",
        "lower center",
        "center left",
        "center",
    ),
    pad_px: float = 6.0,
    samples_per_segment: int = 8,
    **kwargs: Any,
) -> Any:
    """Place an in-axes legend where it overlaps plotted curves least."""
    fig = ax.figure
    best_loc: str | None = None
    best_score = np.inf
    for loc in locs:
        legend = lightcurve_legend(ax, ncol=ncol, loc=loc, **kwargs)
        fig.canvas.draw()
        score = _legend_overlap_score(
            ax,
            legend,
            pad_px=pad_px,
            samples_per_segment=samples_per_segment,
        )
        legend.remove()
        if score < best_score:
            best_score = score
            best_loc = loc
        if score <= 0.0:
            break

    legend = lightcurve_legend(
        ax,
        ncol=ncol,
        loc=best_loc or "upper right",
        **kwargs,
    )
    legend._sn_overlap_score = best_score
    return legend


def lightcurve_legend_outside(
    ax: Any,
    *,
    ncol: int = 1,
    side: str = "right",
    **kwargs: Any,
) -> Any:
    """Place the legend outside the axes, only when explicitly requested."""
    side_key = side.lower()
    if side_key == "right":
        defaults = {"loc": "center left", "bbox_to_anchor": (1.02, 0.5)}
    elif side_key == "top":
        defaults = {"loc": "lower center", "bbox_to_anchor": (0.5, 1.02)}
    elif side_key == "bottom":
        defaults = {"loc": "upper center", "bbox_to_anchor": (0.5, -0.18)}
    else:
        raise ValueError("side must be 'right', 'top', or 'bottom'")

    defaults.update(kwargs)
    return lightcurve_legend(ax, ncol=ncol, **defaults)
