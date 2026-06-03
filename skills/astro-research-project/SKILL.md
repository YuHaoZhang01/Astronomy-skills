---
name: astro-research-project
description: Create, organize, and extend lightweight astronomy or astrophysics research projects with a stable top-level structure. Use when starting a new research project, reorganizing an existing project folder, adding analysis code, generating plots or tables, saving outputs, updating configs, or keeping later project work consistent with data, notebook, src, result, configs, and docs.
---

# Astro Research Project

## Goal

Keep astronomy research projects clean, reproducible, and easy to return to later. Use light engineering discipline without turning the project into a software product.

Apply this skill throughout the project lifecycle, not only at initialization. When adding code, figures, tables, configs, documentation, or data-processing steps later, keep the same structure and naming rules.

## Standard Top-Level Structure

Use these six top-level folders:

```text
project_name/
+-- data/
+-- notebook/
+-- src/
+-- result/
+-- configs/
+-- docs/
```

Create `README.md` at the project root when initializing a project or when the project lacks a clear entry point.

Do not force fixed second-level folders. Create subfolders only when they are useful for the current project. Avoid empty placeholder folders and empty placeholder files.

## Folder Responsibilities

- `data/`: Store input data and derived datasets. Create subfolders only when needed, such as raw, processed, external, spectra, lightcurves, catalogs, or samples.
- `notebook/`: Store exploratory notebooks, quick checks, temporary analysis, and interactive inspection. Do not make notebooks the only final reproducible workflow when stable scripts are appropriate.
- `src/`: Store formal project code: data loading, cleaning, analysis, plotting, fitting, and small workflow scripts. File names should be short and task-based.
- `result/`: Store generated outputs such as figures, tables, logs, model outputs, and intermediate products. Separate interim and final outputs when both exist.
- `configs/`: Store paths, thresholds, sample definitions, column names, units, cosmology, plotting style, and run parameters. Simple projects can use one `default.yaml`.
- `docs/`: Store project notes, data provenance, processing decisions, figure notes, paper notes, and explanations that should remain readable later.

## Placement Rules

Before creating or modifying files, classify the task:

- New data or downloaded material goes under `data/`.
- Exploratory or checking work goes under `notebook/`.
- Reusable or formal Python code goes under `src/`.
- Generated figures, tables, logs, and model outputs go under `result/`.
- Parameters and paths go under `configs/`.
- Human-readable notes and provenance go under `docs/`.

When a task produces both temporary checks and confirmed outputs, keep them separate under `result/`. Prefer short subfolder names such as `interim` and `final` only when this distinction is useful for the current project.

Do not move, overwrite, or delete original data unless the user explicitly asks. Prefer preserving raw inputs and writing derived data as new outputs.

## Naming Rules

Use short, readable names.

- Use lowercase `snake_case` for code, data products, figures, tables, and config files.
- Prefer 1 to 3 words for code files.
- Prefer 2 to 4 words for figures and tables.
- Avoid long filenames that encode every parameter.
- Avoid vague version names such as `new`, `old`, `final_final`, `version2`, or `updated`.
- Put parameter details, sample definitions, and version notes in `configs/`, `docs/`, logs, or README text instead of long filenames.

Good examples:

```text
z_dist.pdf
lc_fit.pdf
cmd_plot.png
sample_table.csv
fit_params.yaml
make_sample.py
plot_lc.py
```

Avoid:

```text
redshift_distribution_for_all_type_ibn_supernovae_after_quality_filter_with_bin_size_0p02.pdf
final_final_revised_plot_version3.png
comprehensive_analysis_pipeline_with_all_quality_filters.py
```

## Code Organization

Keep code practical and research-oriented.

- Do not create a complex Python package, class hierarchy, web app, database, Docker setup, or CI workflow unless the user explicitly asks.
- Keep the top-level project structure stable, but create second-level files only when the project needs them.
- Put repeated logic in functions under `src/`.
- Keep one-off workflow scripts short and readable.
- Keep important scientific parameters out of function bodies; place them in `configs/` when they may change.
- Prefer standard scientific Python tools: `numpy`, `pandas`, `scipy`, `matplotlib`, `astropy`, and `pyyaml` when appropriate.
- Use `astropy` for FITS, coordinates, time, units, and cosmology when relevant.

Suggested short module names, only when useful:

```text
io.py
clean.py
analyze.py
plot.py
utils.py
```

Do not create these files just to complete a template.

## Figures, Tables, and Outputs

Treat generated outputs as part of the project structure.

- Save figures under `result/`, with subfolders only when useful.
- Save tables under `result/`, with subfolders only when useful.
- Separate interim/check outputs from user-confirmed final outputs when both exist.
- Prefer PDF for publication-style figures and PNG for quick checks.
- Use clear axis labels, units, legends, and captions or notes where appropriate.
- Make figures reproducible from code and config whenever possible.
- Do not manually edited figures as the only source of truth; update the plotting code or config.

When the user asks for a plot, decide whether it is exploratory, diagnostic, or final. If unclear, treat it as interim until the user confirms it is final.

## Configs

Use `configs/` to reduce scattered hard-coded values.

Simple projects can use:

```text
configs/default.yaml
```

Larger projects may add focused config files such as:

```text
paths.yaml
sample.yaml
plotting.yaml
cosmology.yaml
```

Keep configurable values in configs when they affect reproducibility:

- input and output paths
- sample cuts and thresholds
- column names and units
- redshift ranges or filter selections
- cosmology parameters
- plotting sizes, DPI, colors, and output formats

## Documentation Updates

When initializing or substantially changing a project, update `README.md` or `docs/` with:

- project purpose
- data sources and provenance
- main workflow or run order
- important configs
- output locations
- notes distinguishing interim and final results

Keep documentation concise. Record decisions that would help the user understand the project after several months.

## Completion Checklist

Before finishing a task with this skill:

- The six top-level folders are respected.
- New files are placed by responsibility, not convenience.
- No unnecessary second-level folders or empty files were created.
- Names are short, clear, and stable.
- Interim and final outputs are distinguishable when needed.
- Configurable scientific parameters are not scattered through code.
- README or docs are updated when the project structure, workflow, or outputs changed.
