---
name: sn-simulation-studio
description: Control and inspect SNEC, SuperSNEC, or OpenStella simulations through Supernova Simulation Studio. Use when Codex should validate parameters, preview or submit a run or sweep, monitor logs, compare results, download artifacts, or diagnose configured supernova engines. Do not use this skill to edit solver source code or fabricate output from an unavailable engine.
---

# Supernova Simulation Studio

Use the Studio API through `scripts/snctl.py`. Prefer `--json` so IDs, states, and validation errors remain unambiguous. The client reads `SNSTUDIO_API_URL`; when unset it targets `http://127.0.0.1:8787`.

## Workflow

1. Run `python scripts/snctl.py --json doctor`, then list engines and profiles when the requested identifiers are not known.
2. Build the smallest parameter override needed. Read [references/parameters.md](references/parameters.md) when choosing or interpreting SNEC/OpenStella parameters or result series.
3. Preview every single run or sweep. Do not submit an invalid preview or bypass an unavailable engine.
4. A direct user request to start one run authorizes that one validated submission. Before submitting a sweep, report its total run count, axes, profile, engine, and output mode, then obtain confirmation.
5. Status, logs, results, comparisons, and artifact listings are read-only and may be queried directly. Treat only the API's final state and manifest as authoritative; a solver process exit code alone does not establish success.
6. Obtain confirmation immediately before cancelling or deleting. Deletion moves files to the Studio trash directory but still changes the task catalog.

Use `run preview`/`run submit` with JSON overrides for single jobs. Sweep commands accept a JSON specification file. If the client cannot reach the API, report the configured URL and suggest `snstudio doctor`/`snstudio start`; do not run the solver directly as a fallback.

For OpenStella use engine `stella` with the listed `builtin:stella:*` profile; uploaded SNEC `.short/.iso.dat` pairs are not compatible with its precomputed opacity tables. Do not treat transient `IFAIL=3` lines as terminal failures—wait for the API final state and the required `.tt/.lbol/.swd/.res` manifest entries.
