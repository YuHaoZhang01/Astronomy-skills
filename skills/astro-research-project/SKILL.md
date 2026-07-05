---
name: astro-research-project
description: "Create, organize, and extend lightweight astronomy or astrophysics research projects. Use when Codex needs to initialize a research folder, reorganize project files, place notebooks, data, source code, configs, docs, plots, tables, logs, or later analysis outputs under a stable data/notebook/src/result/configs/docs structure while keeping names short and work reproducible."
---

# Astro Research Project

Use light engineering discipline for astronomy research work. Keep projects clean and reproducible without turning them into software products.

## Structure

Use these top-level folders:

```text
project_name/
+-- data/
+-- notebook/
+-- src/
+-- result/
+-- configs/
+-- docs/
```

When initializing a project, create the six folders and a concise root `README.md`. For later work, preserve this structure and avoid unnecessary second-level folders or empty placeholder files.

## Placement

Place files by responsibility:

- `data/`: input data and derived datasets. Preserve raw inputs; write cleaned or merged data as new files.
- `notebook/`: exploratory notebooks, quick checks, temporary analysis, and interactive inspection.
- `src/`: reusable or formal Python code for loading, cleaning, analysis, fitting, plotting, and small workflows.
- `result/`: generated figures, tables, logs, model outputs, and intermediate products.
- `configs/`: paths, thresholds, sample definitions, column names, units, cosmology, plotting settings, and run parameters.
- `docs/`: project notes, data provenance, processing decisions, figure notes, paper notes, and explanations for later reuse.

Separate interim checks from final outputs only when both exist. Use short subfolders such as `result/interim/` and `result/final/` when that distinction helps.

Do not move, overwrite, or delete original data unless the user explicitly asks.

## Naming

Use short, readable names.

- Use lowercase `snake_case` for code, data products, figures, tables, and config files.
- Prefer 1 to 3 words for code files.
- Prefer 2 to 4 words for figures and tables.
- Avoid names such as `new`, `old`, `final_final`, `version2`, or `updated`.
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

## Code

Keep code practical and research-oriented.

- Do not create a complex package, class hierarchy, web app, database, Docker setup, or CI workflow unless the user asks.
- Put repeated logic in functions under `src/`.
- Keep one-off workflow scripts short and readable.
- Move configurable scientific parameters to `configs/` when they may change.
- Prefer `numpy`, `pandas`, `scipy`, `matplotlib`, `astropy`, and `pyyaml` when useful.
- Use `astropy` for FITS, coordinates, time, units, and cosmology when relevant.

Use short module names only when the project needs them:

```text
io.py
clean.py
analyze.py
plot.py
utils.py
```

## Figures And Tables

Save generated outputs under `result/` unless an existing project convention is already clearer.

- Use PDF for publication-style figures and PNG for quick checks.
- Use clear labels, units, legends, and captions or notes where appropriate.
- Make figures reproducible from code and config whenever possible.
- Do not treat manually edited figures as the only source of truth.

When the user asks for a plot, classify it as exploratory, diagnostic, or final. If unclear, save it as interim until the user confirms it is final.

## Configs And Docs

Use `configs/default.yaml` for simple projects. Add focused files such as `paths.yaml`, `sample.yaml`, `plotting.yaml`, or `cosmology.yaml` only when useful.

Update `README.md` or `docs/` when initializing a project or substantially changing structure, workflow, data provenance, configs, output locations, or final results.

Keep documentation concise. Record decisions that would matter after several months.

## Completion Check

Before finishing:

1. Confirm new files follow the six-folder structure.
2. Confirm names are short, stable, and descriptive.
3. Confirm raw data was preserved.
4. Confirm interim and final outputs are distinguishable when needed.
5. Confirm configurable scientific parameters are not scattered through code.
6. Update README or docs when the project structure, workflow, or outputs changed.
