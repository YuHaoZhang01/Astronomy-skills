# Astronomy Skills

Reusable Codex skills for astronomy research workflows, starting with publication-style supernova light-curve plotting and designed to grow into a small open collection of repeatable research automation patterns.

**GitHub description:** Open Codex skills for astronomy research workflows, including supernova light-curve plotting, reusable analysis conventions, and publication-ready figure helpers.

## Why This Repository Exists

Research projects often reuse the same small workflows: plotting multiband light curves, organizing outputs, checking public data, preparing figures, or turning notebook habits into repeatable code. This repository stores those workflows as Codex skills so they can be reused across projects instead of rebuilt in every notebook.

The goal is lightweight research infrastructure, not a large software framework. Each skill should be narrow, practical, and easy to copy, inspect, modify, and run.

## Repository Layout

- `skills/` - versioned Codex skill folders.
- `tools/sync_from_codex_skills.ps1` - copy selected local skills from `~/.codex/skills` into this repo.
- `tools/install_to_codex_skills.ps1` - copy skills from this repo back into `~/.codex/skills`.

System skills, runtime cache folders, generated images, and local machine state are intentionally excluded.

## Included Skills

### `sn-lightcurve-plot-style`

A Matplotlib helper skill for supernova multiband light-curve figures.

It standardizes:

- filter ordering by effective wavelength
- stable colors for common astronomy bands and surveys
- magnitude offsets
- model-only and data-plus-model light-curve plotting
- in-axes legends that avoid covering model curves
- figure outputs under `results/figures`

Built-in systems include SDSS, ZTF, ATLAS, Swift/UVOT, PS1, LSST/Rubin, Mephisto, Gaia, 2MASS, WISE, and related common filter sets.

## Using The Skills

Clone or download this repository, then install the skills into your local Codex skills folder:

```powershell
.\tools\install_to_codex_skills.ps1
```

Install only one skill:

```powershell
.\tools\install_to_codex_skills.ps1 -Skill sn-lightcurve-plot-style
```

After installation, invoke the skill in Codex with:

```text
Use $sn-lightcurve-plot-style to make a wavelength-ordered SDSS ugriz model light-curve plot.
```

## Updating Skills From Local Codex

When a skill is improved locally under `~/.codex/skills`, sync it back into this repository:

```powershell
.\tools\sync_from_codex_skills.ps1
```

Sync only one skill:

```powershell
.\tools\sync_from_codex_skills.ps1 -Skill sn-lightcurve-plot-style
```

Then review and commit the changes:

```powershell
git status
git add .
git commit -m "Update SN light-curve plot style skill"
```

## Adding New Skills

New skills should be workflow-oriented and small enough to inspect quickly. Good candidates include:

- repeated astronomy plotting conventions
- public data search and download workflows
- project scaffolds for reproducible analysis
- notebook-to-script cleanup routines
- figure/table export helpers

Prefer skills that encode stable research habits and avoid project-specific secrets, private data paths, API tokens, or generated outputs.

## Publishing To GitHub

If GitHub CLI is installed and authenticated:

```powershell
gh repo create astronomy-skills --public --source . --remote origin --push
```

Without GitHub CLI, create a public empty repository on GitHub, then run:

```powershell
git remote add origin https://github.com/<USER>/astronomy-skills.git
git branch -M main
git push -u origin main
```

## License

Add an open-source license before broad reuse. MIT or BSD-3-Clause are common choices for lightweight research tooling, but the final license choice should be explicit.
