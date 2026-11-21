---
name: astro-research-project
description: "Organize astronomy research into numbered exploration versions and a final workspace. Use when initializing or changing research project layouts, tracking experiments and intermediate outputs, or preserving selected results with reproducible code, configs, and data provenance."
---

# Astro Research Project

Separate the research process from the results worth keeping. Keep practical, reproducible workflows without turning a research project into a software product.

## Two primary folders

Organize by maturity first, then by file responsibility:

```text
project_name/
|-- README.md
|-- exploration/                Early work and the complete exploratory process
|   |-- CHANGELOG.md            Dated history of all exploration versions
|   |-- v1/
|   |   |-- README.md           Version purpose, work, and findings
|   |   |-- src/
|   |   |-- configs/
|   |   `-- result/
|   `-- v2/
|       |-- README.md
|       `-- notebook/
`-- final/                      Selected valuable results and their reproduction
    |-- README.md               Result index, value, provenance, and commands
    |-- src/                    Stable analysis and plotting entry scripts
    |-- configs/                Parameters for the selected results
    |-- data/                   Frozen inputs or immutable input references
    |-- result/                 Selected figures, tables, and other products
    `-- docs/                   Interpretation, checks, and source mapping
```

Use `exploration/` and `final/` as the two primary work areas. Put exploratory work under `exploration/vN/` even for small projects. Create responsibility folders (`src/`, `notebook/`, `configs/`, `data/`, `result/`, `docs/`) only when the work needs them. Use descriptive titles in version notes and add topic subfolders inside a version if needed.

Keep root metadata and necessary existing infrastructure. Large raw archives and external engines may stay at their current locations with documented references. Do not duplicate them merely to match the tree.

## Track exploration versions

- Start the first exploratory work in `exploration/v1/`. For a new question or a material change to the method, model, inputs, sample, or run plan, create the next version using the highest existing number plus one. Record which earlier version it builds on, if any. Routine fixes, planned parameter scans, and reruns can stay in the current version when they serve the same question and plan.
- Create `exploration/vN/README.md` when the version starts. Record its title, start date, scientific question, purpose, and predecessor or baseline. As work progresses, record what changed, the data and configs used, how to run it, links to key outputs, findings (including failed attempts), and the next step. When starting a new version, keep the previous version's code, configs, and outputs intact. Link to shared inputs or exact earlier outputs where needed.
- Maintain one project-wide `exploration/CHANGELOG.md`. Add a dated entry when each version starts and append dated entries for milestones, findings, or a decision to stop. Keep entries in chronological order and link each one to that version's README with a short account of what happened. Use actual calendar dates in `YYYY-MM-DD` format; mark historical dates as unknown if they cannot be verified. If resuming an existing project, read the changelog and relevant version README before placing new work.

Example changelog entry:

```markdown
| Date | Version | What happened |
| --- | --- | --- |
| 2026-01-15 | [v1](v1/README.md) | Started the baseline nickel model fit. |
| 2026-01-16 | [v1](v1/README.md) | Finished the fit; early-time residuals remained. |
| 2026-01-17 | [v2](v2/README.md) | Started testing a second model against the same light curve. |
```

## Route work by maturity

- Put initial ideas, literature/data checks, notebooks, trial code, debugging, parameter scans, intermediate data, diagnostic plots, logs, and unsuccessful attempts in the relevant `exploration/vN/`.
- If a result's status is unspecified, keep it in `exploration/`. Finishing a run or producing an attractive plot does not make it final.
- Put selected, checked results worth retaining in `final/`: scientific findings, figures, tables, useful datasets, fitted parameters, or reusable analysis products. They do not have to be part of a manuscript or ready for publication.
- Treat the user's request to retain a result, prepare a final deliverable, or promote a named finding as selection; do not ask for the same selection again. Otherwise, suggest candidates while keeping them exploratory.
- Keep later experiments and alternative versions in `exploration/`. Update the retained result when the improved version is selected, preserving the provenance of earlier retained or submitted versions.

## Place files within each area

- `src/`: analysis, fitting, simulation helpers, and plotting code. Keep version-specific code in its version. When reusing shared helpers, record the implementation or revision used if changes would affect reproduction.
- `notebook/`: interactive exploration and checks. A retained result should also have a clear reproduction command or documented notebook execution order.
- `data/`: inputs and derived datasets. Preserve raw inputs and write transformed data as new files.
- `configs/`: scientific parameters, sample definitions, units, paths, plotting settings, and run settings.
- `result/`: generated plots, tables, model products, and logs. Save exploratory outputs under `exploration/vN/result/` and selected products under `final/result/`.
- `docs/` and README files: assumptions, provenance, decisions, interpretation, and reproduction instructions. Personal understanding and knowledge-base tasks follow the user's vault location and rules.

Add `final/manuscript/` only when manuscript work is in scope. Figure source scripts normally live in `final/src/`; if a manuscript already uses a dedicated figure-script folder, preserve that clear convention. Generated PDF/PNG files still belong under `final/result/`.

## Promote a valuable result

Promotion preserves a reproducible result, not just a copied image.

1. Identify the selected result, why it is useful, its scientific assumptions, source exploration, and relevant checks.
2. Bring only the necessary analysis/plotting code, focused configs, and inputs into `final/`. Keep the exploratory history in place. Reuse stable methods through a pinned dependency or preserve the required implementation with source provenance; avoid two diverging active copies of a solver.
3. Freeze the required input tables/curves, or reference immutable external inputs with location, checksum/version, and retrieval instructions. Retained results must not silently read changing exploratory outputs, a `latest` folder, or whichever run happens to be newest.
4. Separate expensive model generation from quick plotting. Document both commands and the required settings; a plotting command should not unexpectedly launch an expensive simulation.
5. Record each retained result's purpose, exact exploration version and run, entry script, config, inputs, outputs, reproduction command, and checks in `final/README.md` or a compact manifest. Link back to the source version's README.
6. Reproduce the selected product, check the relevant numerical invariants, and visually inspect retained figures. Use matching PDF and PNG outputs for publication-style figures when appropriate; other products should use formats suited to their purpose.

Keep scientific model changes in analysis code/configs rather than hidden inside stylistic plot edits. Distinguish simulations, fits, controlled remappings, and schematic illustrations in result notes. Do not overwrite frozen inputs or submitted versions silently.

## Names, paths, and practical code

- Use short lowercase `snake_case` filenames describing the question or result, such as `lc_fit.pdf`, `fit_params.yaml`, or `plot_lc.py`. Include a manuscript figure ID only when applicable. Put parameter/version details in configs or provenance records instead of long filenames or `final_final` names.
- Resolve paths from the script or an explicitly supplied project root, supporting execution from another current working directory. Check path depth after migrations rather than assuming every script has the same `parents[n]`.
- Avoid new machine-specific absolute paths in portable configs. Follow the user's required Python interpreter when running or documenting local commands.
- Prefer ordinary functions and standard scientific Python libraries. Keep repeated logic in `src/` and variable scientific parameters in focused configs. Introduce packages, services, or workflow frameworks only when the work actually needs them.
- Use clear figure labels, units, legends, and relevant notes. Keep code/configs as the reproducible source of truth rather than relying only on manually edited figures.

## Existing projects

Inspect README files, entry scripts, imports, configs, raw data, and external engines before proposing moves. Respect established names such as `paper/` when they already serve the selected-results role, and explain the mapping to `final/` rather than adding a competing third area.

A request to update this skill changes the rules; it does not by itself authorize moving files in unrelated research projects. For a design-only task, provide the target tree and current-to-target mapping while preserving working entrypoints.

When a project migration is requested:

1. Map complete workflows and their dependencies to the two areas. Group provisional work into versions using the available history, and document each version and the shared timeline. Keep related work together if there is no evidence of distinct versions. Retain only selected results in the final area.
2. Migrate a coherent workflow at a time, updating imports, paths, configs, documentation, and output destinations together. Preserve original data and useful exploratory history; do not remove them as cleanup.
3. Verify a small reproduction from another working directory and compare scientific outputs to the previous version. Directory changes must not silently change the science.
4. Keep a move map for substantial migrations. Check resolved paths before recursive moves or deletion and follow host safety rules.

## Completion

Confirm that each new exploration version has its own README and a dated entry in the shared changelog, and that both records reflect substantive progress. Check that raw data and exploratory history are preserved, selected results are separate, and each retained result has a usable reproduction path. State what was physically changed, what remains in the existing layout, and where the selected outputs and reproduction commands are located.
