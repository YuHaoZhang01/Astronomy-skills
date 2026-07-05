from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from model import c, day


# =========================
# 1. Data and constants
# =========================
df = pd.read_csv("./photometry.csv", header=0)
data = df[df["discard"] == "n"]

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

nm = 1.0e-7
lambda_g = 472.0 * nm
lambda_r = 641.5 * nm
lambda_i = 783.5 * nm
Mephisto_g = 525.0 * nm

nu_g = c / lambda_g
nu_r = c / lambda_r
nu_i = c / lambda_i
nu_g_M = c / Mephisto_g


def model_optical_loop(x, nu, theta):
    """Replace this body with the selected SNFit model call."""
    raise NotImplementedError("Call the chosen model.light_curve(x, nu, theta) here.")


# =========================
# 2. Load posterior
# =========================
outdir = Path("./emcee_out")
samples = np.load(outdir / "posterior_flat.npy")
theta16 = np.percentile(samples, 16, axis=0)
theta50 = np.percentile(samples, 50, axis=0)
theta84 = np.percentile(samples, 84, axis=0)

t_s = np.linspace(0.0001, 100, 1000) * day


# =========================
# 3. Final figure
# =========================
params_text = (
    r"$p_1={:.2f}$".format(theta50[0]) + "\n"
    + r"$p_2={:.2f}$".format(theta50[1]) + "\n"
    + r"$p_3={:.2f}$".format(theta50[2])
)

fig, ax = plt.subplots(figsize=(8, 6), dpi=300)

ax.errorbar(
    t_g,
    M_g - 4,
    yerr=M_g_err,
    fmt="o",
    color="g",
    label=r"$g-4$",
    ecolor="g",
    elinewidth=1,
    capsize=3,
    markeredgecolor="black",
)
ax.errorbar(
    t_g_M,
    M_g_M - 2,
    yerr=M_g_M_err,
    fmt="o",
    color="b",
    label=r"Mephisto $g-2$",
    ecolor="b",
    elinewidth=1,
    capsize=3,
    markeredgecolor="black",
)
ax.errorbar(
    t_r,
    M_r,
    yerr=M_r_err,
    fmt="o",
    color="r",
    label=r"$r$",
    ecolor="r",
    elinewidth=1,
    capsize=3,
    markeredgecolor="black",
)
ax.errorbar(
    t_i,
    M_i + 2,
    yerr=M_i_err,
    fmt="o",
    color="y",
    label=r"$i+2$",
    ecolor="y",
    elinewidth=1,
    capsize=3,
    markeredgecolor="black",
)

ax.plot(t_s / day, model_optical_loop(t_s, nu_g, theta50) - 4, linestyle="--", color="g")
ax.plot(t_s / day, model_optical_loop(t_s, nu_g_M, theta50) - 2, linestyle="--", color="b")
ax.plot(t_s / day, model_optical_loop(t_s, nu_r, theta50), linestyle="--", color="r")
ax.plot(t_s / day, model_optical_loop(t_s, nu_i, theta50) + 2, linestyle="--", color="y")

ax.annotate(
    params_text,
    xy=(0.75, 0.85),
    xycoords="axes fraction",
    fontsize=10,
    bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="gray", alpha=0.85),
)

ax.legend(
    loc="upper left",
    ncol=4,
    handlelength=2.5,
    borderpad=1.0,
    shadow=False,
)

ax.set_xlabel(r"Time since trigger (days)", fontsize=12)
ax.set_ylabel(r"AB magnitude", fontsize=12)
ax.set_title("Supernova light-curve model fitting", fontsize=12)
ax.set_xlim([0.5, 100])
ax.set_ylim([26, 13])
ax.set_xscale("log")
ax.set_xticks([1, 10, 100])
ax.set_xticklabels([1, 10, 100])

fig.tight_layout(pad=1.5)
fig.savefig("lightcurve_final.pdf", dpi=300, bbox_inches="tight")
plt.show()
