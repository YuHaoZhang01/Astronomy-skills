# Astronomy-skills

Personal Codex skills for astronomy research workflows, shared as reusable examples for light-curve plotting, model fitting, and research automation.

## Skills

- [`astro-research-project`](skills/astro-research-project/SKILL.md): keep early work, experiments, and intermediate outputs in `exploration/`; preserve selected valuable results and their reproducible code, configs, and input provenance in `final/`.
- `sn-lightcurve-plot-style`: standardize wavelength-ordered multiband SN light-curve plotting.
- `snfit`: preserve the SNFit model library and guide readable emcee fitting and final plotting code.

- [`sn-paper-writing`](skills/sn-paper-writing/SKILL.md): corpus-derived paragraph structure, sentence choices, and evidence-calibrated revision for supernova and transient papers; also supports explicitly requested local style distillation.

## Supernova simulation studio

- [`supernova-sim-studio`](supernova-sim-studio/README.md): Chinese Web UI, persistent worker, REST API and CLI for SNEC, SuperSNEC and OpenStella. Includes macOS startup and Ubuntu 24.04 Docker Compose/Tailscale deployment scripts.
- [`sn-simulation-studio`](skills/sn-simulation-studio/SKILL.md): Agent Skill for parameter previews, simulations, logs and result comparisons.

From a clone, run `cd supernova-sim-studio` and `./snstudio start`. The first launch requires `uv`, Node.js and `pnpm` to install dependencies and build the frontend. Solver installations are separate; configure `SNSTUDIO_SUPERSNEC_ROOT`, `SNSTUDIO_SNEC_ROOT` and `SNSTUDIO_STELLA_ROOT` for your machine. The bundled defaults refer to the author's local Mac paths.

Install the Skill with `./snstudio install-skill`, and set `SNSTUDIO_CLI` to the absolute path of this clone's `supernova-sim-studio/snctl`. For remote use, set `SNSTUDIO_API_URL` to the server URL.

Solver source code, model data, simulation outputs, dependencies and credentials are not included. Solver licenses remain separate from this repository's license: SNEC/SuperSNEC use CC BY-NC-SA 4.0; OpenStella uses GPL-3.0. Mac native execution has been tested; remote Ubuntu deployment still needs validation on a target server.

## Supernova paper writing

`sn-paper-writing` is self-contained and can use its bundled writing rules without the original reference papers or a separate `journal-adapt` installation.

Install it with the existing repository helper:

```powershell
.\tools\install_to_codex_skills.ps1 -Skill sn-paper-writing
```

You can also install `skills/sn-paper-writing` from this repository using your Codex skill installer.

Example request:

```text
Use $sn-paper-writing to revise the section I provide. Preserve equations,
numerical results, citations, and claim strength, and explain the changes.
```

The public package contains instructions and anonymous structural summaries only. Reference PDFs, paper Markdown, page images, extraction caches, source manifests, and paragraph-level private audit records are excluded. New research inputs should stay in the research project, outside the skill directory.

See [scope and provenance](skills/sn-paper-writing/references/provenance.md) for corpus coverage and limits. The skill adapts the MIT-licensed [journal-adapt-writing-skill](https://github.com/WantongC/journal-adapt-writing-skill) workflow; its license notice is preserved in the skill folder.
