---
name: sn-lightcurve-plot-style
description: "Standardize supernova multiband light-curve plotting in Python/Matplotlib. Use when Codex needs to create or patch a plot_style.py helper, choose wavelength-ordered filters, stable per-band colors, magnitude offsets, survey markers, in-axes legends, or publication-style SN photometry/model light-curve figures under result/figures or an existing project output convention."
---

# SN Light Curve Plot Style

Use this skill to make SN multiband light-curve plots consistent across projects without hand-tuning colors, offsets, markers, and legends in every notebook.

## Asset

- `assets/plot_style.py`: reusable Matplotlib helper for wavelength-ordered filter styles, magnitude offsets, survey markers, photometry points, model curves, and in-axes legends.

Use the asset as code. Do not load the full file into context unless the user asks to modify or debug the helper.

## Workflow

1. Prefer an existing local `plot_style.py`; inspect it and patch only missing pieces.
2. If no local helper exists, copy `assets/plot_style.py` into the project root or a small reusable module such as `src/plot_style.py`.
3. Build band styles from the active filters, not from a hardcoded visual order.
4. Sort filters by effective wavelength from short to long.
5. Use one offset step for the plot and center on a useful optical band, usually `r`, `ZTF r`, or `SDSS r`.
6. Plot model curves with `plot_model_band()`.
7. Plot observed points with `plot_photometry()` when the user asks for data points.
8. Save figures under `result/figures/` unless the project already has a clearer output convention.

## Filter Rules

- Treat effective wavelength as the plotting-order convention, not precision synthetic photometry.
- Keep colors stable by physical band identity: UV purple, `u` violet, `g` green, `r` orange-red, `i/z/y` brown, NIR darker brown.
- Preserve survey or instrument identity with markers, not by changing colors for the same physical band.
- Use system-specific keys when available, such as `sdss_g`, `ztf_g`, `atlas_c`, `uvot_uvw1`, `ps1_r`, `lsst_i`, or `mephisto_r`.
- If the table only has `band`, parse labels such as `ZTF-g`, `Swift UVW1`, `Mephisto-r`, or `SDSS i`.
- If the table has both `survey` and `band`, call `set_band_styles_from_table(..., system_col="survey", band_col="band")`.

The helper includes GALEX, Swift/UVOT, Johnson, Cousins, SDSS, PS1, LSST/Rubin, ZTF, ATLAS, Mephisto, SkyMapper, 2MASS, Gaia, TESS, and WISE.

## Notebook Pattern

For observed photometry:

```python
from plot_style import (
    apply_sn_style,
    set_band_styles_from_table,
    plot_photometry,
    setup_lightcurve_axes,
    lightcurve_legend,
    band_style_table,
)

apply_sn_style()
styles = set_band_styles_from_table(
    data,
    system_col="survey",
    band_col="band",
    offset_step=1.0,
    center_band="ZTF r",
)
band_style_table(styles)
```

For model-only curves:

```python
from plot_style import (
    apply_sn_style,
    set_band_styles_by_wavelength,
    plot_model_band,
    setup_lightcurve_axes,
    lightcurve_legend_inside_clear,
    band_wavelength_nm,
    offset_label,
)

bands = ["SDSS u", "SDSS g", "SDSS r", "SDSS i", "SDSS z"]
styles = set_band_styles_by_wavelength(
    bands,
    offset_step=1.0,
    center_band="SDSS r",
)
```

When a model needs frequency, use the same filter table:

```python
for row in band_style_table(styles):
    band = row["band"]
    wavelength_nm = band_wavelength_nm(band, system="SDSS")
    nu_obs = c / (wavelength_nm * 1.0e-7)
    mag, *_ = model.light_curve(t_sec, nu_obs, theta)
    plot_model_band(
        ax,
        t_day,
        mag,
        system="SDSS",
        band=band,
        label=f"SDSS {band}{offset_label(row['offset'])}",
    )

lightcurve_legend_inside_clear(ax, ncol=1)
```

## Figure Rules

- Use linear time unless the user explicitly asks otherwise.
- Invert magnitude axes; `setup_lightcurve_axes()` does this through `ylim=(faint, bright)`.
- Keep legends inside the axes by default.
- Use `lightcurve_legend_inside_clear(ax, ncol=1)` for model-only multiband plots.
- Move or rewrite the legend if it covers the peak, decline, or model comparisons.
- Use direct inline labels only after inspecting the rendered output for overlaps.

## Validation

After creating or patching a helper:

1. Run `python -m py_compile plot_style.py` with the user's working Python if available.
2. Generate a small SDSS `ugriz` or mixed-system model-only plot.
3. Check that SDSS wavelength order is `u, g, r, i, z` and that `r=0` when centered on `r`.
4. Check that labels and legends stay inside the axes and do not cover curves.
5. Show the output PNG in the final response when running inside the Codex desktop app.
