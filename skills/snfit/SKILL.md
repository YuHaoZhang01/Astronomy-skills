---
name: snfit
description: "SNFit supernova light-curve model archive and workflow guidance. Use when Codex needs to inspect or reuse the SNFit model library, build or optimize an emcee fitting workflow for a selected supernova model, or generate final light-curve plotting code in a readable notebook-oriented style with explicit constants, explicit band splits, lnprior/lnlike/lnprob, visible emcee controls, and explicit ax.errorbar/ax.plot calls."
---

# SNFit

Use this skill for two tasks:

1. Preserve and reuse the SNFit source code under `src/`.
2. Write emcee fitting and final plotting code in the user's preferred readable script/notebook shape.

Keep the skill simple: `SKILL.md` contains the rules, and `src/` contains code assets and style examples.

## Source Files

- `src/model.py`: archived SNFit model library. Prefer this for new fitting code.
- `src/plot_style.py`: archived plotting helper. Use it only when the user asks for reusable plot helpers.
- `src/emcee_workflow_style.py`: generic emcee workflow style sample. It is not tied to ArnettNi or any single model.
- `src/final_plot_style.py`: generic final plotting style sample. It is not tied to ArnettNi or any single model.

Do not mention the source notebook, example event, or example target name in generated code or prose unless the user explicitly asks for it. Extract the code organization style only.

## Model Rules

- Treat `src/model.py` as the primary model source.
- Do not use `SNLC.py` unless the user explicitly asks for old-code compatibility.
- Keep every model's theta order explicit in comments, priors, labels, summaries, and plot annotations.
- For `ArnettNi`, default fitting parameters are `[M_ej, M_Ni, E_K]`; `E_Th=0` and `R0=1` are fixed unless the user asks otherwise.
- Pass model time in observer-frame seconds and observed frequency in Hz.
- Guard likelihood evaluation against `t <= 0` and non-finite model output.

## Emcee Code Style

When writing a fitting script or notebook, follow the shape of `src/emcee_workflow_style.py`.

Keep:

- direct imports at the top;
- constants and filter wavelengths visible near the top;
- explicit data selection for each band;
- variables like `t_g`, `M_g`, `M_g_err`, `t_r`, `M_r`, `M_r_err`;
- plain functions named `M_ab`, `model_optical_loop`, `lnprior`, `lnlike`, and `lnprob`;
- visible `theta0`, `ndim`, `nwalkers`, `niter`, `pos`, `sampler`, and `samples`.

Optimize without changing the readable shape:

- convert pandas columns to NumPy arrays once;
- compute each band's residuals as arrays inside `chi_band`;
- avoid `.iloc` loops inside `lnlike`;
- use `multiprocessing.Pool` and `emcee.backends.HDFBackend` in scripts when useful;
- keep notebook versions multiprocessing-free if pickling causes trouble.

## Final Plot Code Style

When the user asks for a final plotting program, follow `src/final_plot_style.py`.

The final output should be a readable plotting script, not a plotting framework. Prefer:

- `fig, ax = plt.subplots(figsize=(8, 6), dpi=300)`;
- one explicit `ax.errorbar(...)` call per observed band;
- one explicit `ax.plot(...)` call per model curve and band;
- visible magnitude offsets like `M_g - 4` and model curves with matching offsets;
- a parameter text box using `ax.annotate(...)`;
- explicit legend, labels, title, limits, x-scale, and magnitude-axis direction;
- `fig.tight_layout(...)`, `fig.savefig(...)`, and `plt.show()`.

Do not hide the final figure behind a generic loop or helper class unless the user asks for a reusable plotting library.

## Validation

For source or template changes:

```bash
python -m py_compile src/model.py src/plot_style.py src/emcee_workflow_style.py src/final_plot_style.py
```

For generated fitting code:

1. Check `lnprob(theta0)` is finite.
2. Run a short sampler before long emcee runs.
3. Confirm saved chain/posterior dimensions match `ndim`.
4. Generate the final plot and inspect labels, offsets, and axis direction.
