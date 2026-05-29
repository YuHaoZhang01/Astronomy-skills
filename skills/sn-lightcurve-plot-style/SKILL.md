---
name: sn-lightcurve-plot-style
description: Standardize supernova multiband light-curve plotting in Python/Matplotlib. Use when Codex needs to create, repair, or reuse a plotting helper for SN photometry or model light curves with wavelength-ordered filters, stable per-band colors, magnitude offsets, survey markers, SDSS/ZTF/ATLAS/Swift/PS1/LSST/Mephisto style conventions, or publication-style figures saved under results/figures.
---

# SN Light Curve Plot Style

Use this skill to make supernova light-curve plots look consistent across projects without hand-tuning colors and offsets in every notebook.

## Workflow

1. Prefer an existing local `plot_style.py` if present. Inspect it and patch only missing pieces.
2. If no local helper exists, copy `assets/plot_style.py` from this skill into the project root or a small reusable module such as `src/<project>/plot_style.py`.
3. Build band styles from the active filters, not from a hardcoded visual order. Use effective wavelength order from short to long.
4. Use one offset step for the whole plot. Center on a useful optical band, usually `r`, `ZTF r`, or `SDSS r`.
5. Plot models with `plot_model_band()`. Plot data with `plot_photometry()` only when the user asks for observed points.
6. Save figures to `results/figures` unless the project already has a clearer output convention.

## Filter Rules

- Treat effective wavelength as the source of truth for sorting and offsets.
- Keep colors stable by physical band identity: UV purple, `u` violet, `g` green, `r` orange-red, `i/z/y` brown, NIR darker brown.
- Preserve survey/instrument identity with markers for data, not with different colors for the same physical band.
- Use system-specific keys when available, for example `sdss_g`, `ztf_g`, `atlas_c`, `uvot_uvw1`, `mephisto_r`.
- If the table only has `band`, parse names such as `ZTF-g`, `Swift UVW1`, `Mephisto-r`, or `SDSS i`.
- If the table has both `survey` and `band`, call `set_band_styles_from_table(..., system_col="survey", band_col="band")`.

Built-in systems in the template include `GALEX`, `Swift/UVOT`, `Johnson`, `Cousins`, `SDSS`, `PS1`, `LSST/Rubin`, `ZTF`, `ATLAS`, `Mephisto`, `SkyMapper`, `2MASS`, `Gaia`, `TESS`, and `WISE`.

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

bands = ["SDSS u", "SDSS g", "SDSS r", "SDSS z", "SDSS i"]
styles = set_band_styles_by_wavelength(
    bands,
    offset_step=1.0,
    center_band="SDSS r",
)
```

When calling a physical model that needs frequency, use the same filter table:

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

## Figure Defaults

- Use linear time on the x-axis unless the user explicitly asks otherwise.
- Invert magnitude axes. `setup_lightcurve_axes()` does this through `ylim=(faint, bright)`.
- Keep the legend inside the axes by default. Do not move the legend outside unless the user explicitly asks for an outside legend.
- Do not let labels or legends cover model curves. For model-only multiband plots, prefer `lightcurve_legend_inside_clear(ax, ncol=1)`, which tests several in-axes locations and chooses the one with the least curve overlap.
- If automatic placement is not good enough, manually set `lightcurve_legend(ax, loc="upper right", ncol=1)` or another empty in-axes region after inspecting the rendered figure. Never accept a final plot where labels obscure the light-curve peak, decline, or model comparisons.
- For direct inline band labels, put labels near curve endpoints with small offsets and a light background, then inspect the rendered PNG/PDF for overlaps.
- Do not use the effective wavelength table for precision synthetic photometry; it is a plotting-order convention.

## Validation

After creating or patching a helper:

1. Run `python -m py_compile plot_style.py` with the user's working Python if available.
2. Generate a small SDSS `ugriz` or mixed-system model-only plot.
3. Check that order and offsets match wavelength order, for example SDSS should be `u, g, r, i, z` with `r=0` if centered on `r`.
4. Check that labels and legends stay inside the axes and do not cover model curves. Change the in-axes `loc` or use `lightcurve_legend_inside_clear()` if there is any overlap.
5. Show the output PNG in the final response when running inside the Codex desktop app.
