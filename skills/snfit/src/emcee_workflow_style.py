from pathlib import Path
import multiprocessing

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import emcee
import corner

from model import c, day


# =========================
# 1. Data and constants
# =========================
data_path = Path("./photometry.csv")
outdir = Path("./emcee_out")
outdir.mkdir(exist_ok=True)

z = 0.176  ## redshift

nm = 1.0e-7
lambda_g = 472.0 * nm
lambda_r = 641.5 * nm
lambda_i = 783.5 * nm
Mephisto_g = 525.0 * nm

nu_g = c / lambda_g
nu_r = c / lambda_r
nu_i = c / lambda_i
nu_g_M = c / Mephisto_g


# =========================
# 2. Read photometry
# =========================
df = pd.read_csv(data_path, header=0)
data1 = df[df["discard"] == "n"]
data = data1[data1["time_day"] > 10]

i_band_data = data[(data["band"].str.lower() == "i") | (data["band"] == "Mephisto-i")]
i_band_detection = i_band_data[i_band_data["upperlimit"] == "n"]
t_i = i_band_detection["time_day"].to_numpy(dtype=float)
M_i = i_band_detection["flux"].to_numpy(dtype=float)
M_i_err = i_band_detection["eflux"].to_numpy(dtype=float)

r_band_data = data[(data["band"].str.lower() == "r") | (data["band"] == "Mephisto-r")]
r_band_detection = r_band_data[r_band_data["upperlimit"] == "n"]
t_r = r_band_detection["time_day"].to_numpy(dtype=float)
M_r = r_band_detection["flux"].to_numpy(dtype=float)
M_r_err = r_band_detection["eflux"].to_numpy(dtype=float)

g_band_data = data[data["band"].str.lower() == "g"]
g_band_detection = g_band_data[g_band_data["upperlimit"] == "n"]
t_g = g_band_detection["time_day"].to_numpy(dtype=float)
M_g = g_band_detection["flux"].to_numpy(dtype=float)
M_g_err = g_band_detection["eflux"].to_numpy(dtype=float)

g_M_band_data = data[data["band"] == "Mephisto-g"]
g_M_band_detection = g_M_band_data[g_M_band_data["upperlimit"] == "n"]
t_g_M = g_M_band_detection["time_day"].to_numpy(dtype=float)
M_g_M = g_M_band_detection["flux"].to_numpy(dtype=float)
M_g_M_err = g_M_band_detection["eflux"].to_numpy(dtype=float)


# =========================
# 3. Model wrapper
# =========================
def M_ab(t, nu, theta):
    """Replace this body with the selected SNFit model call."""
    raise NotImplementedError("Call the chosen model.light_curve(t, nu, theta) here.")


def model_optical_loop(x, nu, theta):
    x = np.asarray(x, dtype=float)
    x = np.maximum(x, 1.0e-6)
    return M_ab(x, nu, theta)


# =========================
# 4. Likelihood
# =========================
theta0 = np.array([...])  ## write theta order here


def lnprior(theta):
    """Keep the parameter bounds explicit and readable."""
    ...
    return -np.inf


def chi_band(t_day, mag, err, nu, theta):
    if len(t_day) == 0:
        return 0.0
    t_obs = np.maximum(t_day, 1.0e-6) * day
    model_mag = model_optical_loop(t_obs, nu, theta)
    if not np.all(np.isfinite(model_mag)):
        return np.inf
    return np.sum((mag - model_mag) ** 2.0 / err**2.0)


def lnlike(theta):
    chi_i = chi_band(t_i, M_i, M_i_err, nu_i, theta)
    chi_r = chi_band(t_r, M_r, M_r_err, nu_r, theta)
    chi_g = chi_band(t_g, M_g, M_g_err, nu_g, theta)
    chi_g_M = chi_band(t_g_M, M_g_M, M_g_M_err, nu_g_M, theta)
    chi_tot = chi_i + chi_r + chi_g + chi_g_M
    if not np.isfinite(chi_tot):
        return -np.inf
    return -0.5 * chi_tot


def lnprob(theta):
    lp = lnprior(theta)
    if not np.isfinite(lp):
        return -np.inf
    return lp + lnlike(theta)


# =========================
# 5. Run emcee
# =========================
ndim = len(theta0)
nwalkers = 60
niter = 2000
burnin = 1000
thin = 10

rng = np.random.default_rng(20260705)
pos = [theta0 + 1.0e-4 * rng.normal(size=ndim) for i in range(nwalkers)]

use_multiprocessing = False
backend = emcee.backends.HDFBackend(outdir / "backend.h5")
backend.reset(nwalkers, ndim)

if use_multiprocessing:
    ncpu = min(max(multiprocessing.cpu_count() - 1, 1), nwalkers)
    with multiprocessing.Pool(processes=ncpu) as pool:
        sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, pool=pool, backend=backend)
        sampler.run_mcmc(pos, niter, progress=True)
else:
    sampler = emcee.EnsembleSampler(nwalkers, ndim, lnprob, backend=backend)
    sampler.run_mcmc(pos, niter, progress=True)

chain = sampler.get_chain()
logprob = sampler.get_log_prob()
samples = sampler.get_chain(discard=burnin, thin=thin, flat=True)

np.savez(outdir / "mcmc_chain.npz", chain=chain, logprob=logprob)
np.save(outdir / "posterior_flat.npy", samples)
