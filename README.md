# Codex Skills

Personal Codex skills managed as a normal Git repository.

## Layout

- `skills/` - versioned skill folders copied from `~/.codex/skills`.
- `tools/sync_from_codex_skills.ps1` - copy selected local skills into this repo.
- `tools/install_to_codex_skills.ps1` - copy skills from this repo back into `~/.codex/skills`.

System skills and generated runtime skills are intentionally excluded.

## Included Skills

- `astrophysics-paper-data-finder`
- `hatch-pet`
- `sn-lightcurve-plot-style`

## Sync From Local Codex

```powershell
.\tools\sync_from_codex_skills.ps1
```

To sync only one skill:

```powershell
.\tools\sync_from_codex_skills.ps1 -Skill sn-lightcurve-plot-style
```

## Install Back To Codex

```powershell
.\tools\install_to_codex_skills.ps1
```

To install only one skill:

```powershell
.\tools\install_to_codex_skills.ps1 -Skill sn-lightcurve-plot-style
```

## GitHub

If GitHub CLI is installed and authenticated:

```powershell
gh repo create codex-skills --private --source . --remote origin --push
```

Without GitHub CLI, create a private empty repository on GitHub, then run:

```powershell
git remote add origin https://github.com/<USER>/codex-skills.git
git branch -M main
git push -u origin main
```

