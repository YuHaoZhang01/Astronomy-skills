# SNEC and OpenStella parameter and result guidance

## High-value parameters

- `final_energy` is the target explosion energy in erg.
- `Ni_mass` is the radioactive nickel mass in solar masses.
- `Ni_mix_fraction` is a SuperSNEC ejecta-mass fraction in `[0, 1]`.
- `Ni_mix_kernel` selects step (`1`), exponential (`2`), or two-component (`3`) mixing.
- `imax` controls zone count; the SuperSNEC default is `100`, while high-resolution reference runs may be much slower.
- `tend`, `dtout*`, and `dtmax` are seconds. Result time axes returned by the API are days.
- `grid_mode` is SuperSNEC-specific. Original SNEC uses `gridding`; its uniform-mass value is exactly `uniform_in_mass`, not the broken example value `uniform_by_mass`.
- The bundled original-SNEC `parameters` and `GridPattern.dat` baseline use `15Msol_RSG` with `imax=1000`. Changing the profile or `imax` can require a matching grid setup; a syntactically valid preview cannot prove that the legacy mapper accepts a different pair, so monitor the first runtime log and final manifest.
- A single run defaults to full output. Sweeps should normally use minimal output, which retains bolometric luminosity, photospheric velocity, synthetic magnitudes, and the run summary while omitting large spatial dumps.

Keep the profile pair fixed unless the request explicitly changes the progenitor. The Studio owns `outdir`, `profile_name`, and `comp_profile_name`; never override them.

## OpenStella parameters

- Select engine `stella` and a discovered `builtin:stella:*` profile. The current integration uses the official 90-zone `m030307mhomo` model with matching precomputed opacity tables; SNEC uploads cannot be substituted.
- `TcurA` and `TcurB` are in days and define the simulated interval. `TcurB` must exceed `TcurA`; the bundled model currently enforces `TcurB >= 0.11 day` so core outputs can be produced.
- `XMNI` and `AMNI` control the bundled model's nickel inputs. Do not translate them mechanically to SNEC `Ni_mass` without checking the OpenStella model assumptions.
- `NOUT`, `IOUT`, and `MBATCH` control native output cadence. OpenStella does not implement SNEC `output_mode`; a sweep requested as minimal still retains its core native files.
- Parameter snapshots preserve Fortran `D` exponents. Use the schema's exact names and preview before submission.
- A successful run requires exit code 0, `Normal stop of stella`, and non-empty, parseable `.tt`, `.lbol`, `.swd`, and `.res` artifacts. `IFAIL=3` can be a recoverable step-size fallback; only the API final state is authoritative.

## Standard series

- `lbol`: bolometric luminosity in `erg/s`, normally plotted on a logarithmic y-axis.
- `v_ph`: photospheric velocity in `km/s`.
- `t_eff`: effective temperature in K; it may be absent from minimal output.
- `mag_PTF_R`, `mag_u`, `mag_g`, `mag_r`, `mag_i`, `mag_z`, `mag_U`, `mag_B`, `mag_V`, `mag_R`, `mag_I`: synthetic magnitudes with an inverted magnitude axis.

OpenStella currently returns `lbol`, `v_ph`, `t_eff`, and `mag_U/B/V/R/I`. Its time axes are already normalized to days, luminosity is converted from `log10(erg/s)` to `erg/s`, and velocity is returned in `km/s`.

For comparisons, identify both physical changes and numerical changes. A different engine version, profile checksum, `imax`, grid mode, or output cadence can affect interpretation even when explosion parameters match.
