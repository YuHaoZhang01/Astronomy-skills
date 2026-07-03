import numpy as np
from scipy.integrate import quad, solve_ivp


M_sun = 1.9885e33  # g
R_sun = 6.96e10  # cm
c = 2.99792458e10  # cm/s
day = 86400  # s
hp = 6.626e-27  # Planck constant (erg s)
kb = 1.381e-16  # Boltzmann constant (erg/K)
sigma_SB = 5.670374419e-5  # Stefan-Boltzmann constant (erg cm^-2 s^-1 K^-4)
pi = np.pi
pc = 3.086e18  # 1 parsec (cm)
Mpc = 1e6 * pc
km = 1e5
H0 = 71.0 * km / Mpc
Omega_m = 0.27
Omega_L = 0.73
epsilon_Ni = 3.9e10  # specific heating rate of Ni (erg/s/g)
epsilon_Co = 6.8e9  # specific heating rate of Co (erg/s/g)
tau_Ni = 8.8 * day  # decay timescale of Ni (s)
tau_Co = 111.3 * day  # decay timescale of Co (s)
epsilon_ratio = epsilon_Co / (epsilon_Ni - epsilon_Co)


def DL(z):
    """Luminosity distance in cm for given redshift z."""
    func = lambda x: 1.0 / (Omega_m * (1.0 + x)**3.0 + Omega_L)**0.5
    FirstTerm = (1 + z) * c / H0
    Int_func = quad(func, 0, z)[0]
    return FirstTerm * Int_func


def _blackbody_mag_ab(z, DL_z, t, nu_obs, theta, luminosity_func):
    """Shared blackbody SED wrapper for model luminosity functions."""
    nu_rest = nu_obs * (1 + z)
    L_bol, T_eff, R_ph = luminosity_func(t, theta)
    expo = hp * nu_rest / (kb * T_eff)

    if expo > 700:
        F_nu = 0.0
    else:
        F_nu = ((2.0 * pi * hp * nu_rest**3 / c**2)
                * (R_ph / DL_z)**2
                / np.expm1(expo))

    F_nu = max(F_nu, 1.0e-300)
    M_nu = -2.5 * np.log10(F_nu) - 48.6 - 2.5 * np.log10(1 + z)

    return M_nu, F_nu, L_bol, T_eff


class ArnettNi:
    """
    Arnett-type supernova light curve model powered by 56Ni/56Co radioactive decay
    with initial thermal energy and gamma-ray leakage.

    Energy sources:
        1. 56Ni -> 56Co -> 56Fe radioactive decay chain
        2. Initial thermal energy from shock breakout

    Reference: Arnett 1982, ApJ, 253, 785
    """

    def __init__(self, z, kappa=0.1, kappa_gamma=0.1, T_floor=1000.0):
        """
        Parameters
        ----------
        z : float
            Redshift of the source.
        kappa : float
            Mean opacity of ejecta (cm^2/g), default 0.1.
        kappa_gamma : float
            Gamma-ray opacity (cm^2/g), default 0.1.
        T_floor : float
            Minimum effective temperature floor (K), default 1000.
        """
        self.z = z
        self.DL_z = DL(z)
        self.kappa = kappa
        self.kappa_gamma = kappa_gamma
        self.T_floor = T_floor

    def luminosity(self, t, theta):
        """
        Calculate bolometric luminosity, effective temperature, and photosphere radius.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        theta : array-like
            Model parameters: [M_ej, M_Ni, E_K].
            A legacy/special-case form [M_ej, M_Ni, E_K, E_Th, R0] is also accepted.
            - M_ej : ejecta mass (M_sun)
            - M_Ni : 56Ni mass (M_sun)
            - E_K  : kinetic energy (1e51 erg)
            - E_Th : initial thermal energy (1e51 erg), default 0
            - R0   : initial radius (R_sun), default 1

        Returns
        -------
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        R_ph  : float
            Photosphere radius (cm).
        """
        z = self.z
        kappa = self.kappa
        kappa_gamma = self.kappa_gamma
        T_floor = self.T_floor

        t_rest = max(t / (1.0 + z), 1.0e-30)

        if len(theta) == 3:
            M_ej, M_Ni, E_K = theta
            E_Th = 0.0
            R0 = 1.0
        elif len(theta) == 5:
            M_ej, M_Ni, E_K, E_Th, R0 = theta
        else:
            raise ValueError(
                "ArnettNi theta must be [M_ej, M_Ni, E_K] "
                "or [M_ej, M_Ni, E_K, E_Th, R0]."
            )
        M_ej = M_ej * M_sun
        M_Ni = M_Ni * M_sun
        E_K = E_K * 1.0e51
        E_Th = E_Th * 1.0e51
        R0 = R0 * R_sun

        v_ej = (2.0 * E_K / M_ej)**0.5
        tau_d = (2.0 * kappa * M_ej / (13.8 * v_ej * c))**0.5
        tau_1 = (2.0 * kappa * M_ej / (13.8 * v_ej**2))**0.5
        t_ex = R0 / v_ej
        t_diff = kappa * M_ej / (13.8 * v_ej * c)
        y_ex = t_ex / tau_d
        L_Th0 = E_Th / t_diff
        t_gamma = ((2.0 * kappa_gamma * M_ej) / (13.8 * v_ej**2))**0.5
        L_heat0 = M_Ni * (epsilon_Ni - epsilon_Co)

        y = t_rest / tau_d
        y_tau = tau_1 / tau_d

        def f_heat(y_):
            t_ = max(y_ * tau_d, 1.0e-30)
            radioactive = (
                np.exp(-t_ / tau_Ni)
                + np.exp(-t_ / tau_Co) * epsilon_ratio
            )
            gamma_deposition = 1.0 - np.exp(-(t_gamma / t_)**2.0)
            return radioactive * gamma_deposition

        def func_heat(x):
            return (x + y_ex) * np.exp(x*x + 2*x*y_ex) * f_heat(x)

        if y < 2.0 * y_tau:
            I_heat = quad(func_heat, 0, y, epsrel=1.49e-02)[0]
            L_bol = (
                2.0 * L_heat0 * np.exp(-(y*y + 2*y*y_ex)) * I_heat
                + L_Th0 * np.exp(-(y*y + 2*y*y_ex))
            )
        else:
            L_bol = (
                L_heat0 * f_heat(y)
                + L_Th0 * np.exp(-(y*y + 2*y*y_ex))
            )

        L_bol = max(L_bol, 1.0e-300)
        R_ph = R0 + v_ej * t_rest
        T_eff = (L_bol / (4.0 * pi * sigma_SB * R_ph**2))**0.25
        if T_eff < T_floor:
            T_eff = T_floor
            R_ph = (L_bol / (4.0 * pi * sigma_SB * T_floor**4))**0.5

        return L_bol, T_eff, R_ph

    def mag_ab(self, t, nu_obs, theta):
        """
        Calculate AB magnitude at a given observed frequency.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, M_Ni, E_K], or special-case
            [M_ej, M_Ni, E_K, E_Th, R0].

        Returns
        -------
        M_nu : float
            AB magnitude.
        F_nu : float
            Flux density (erg/s/cm^2/Hz).
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        """
        return _blackbody_mag_ab(self.z, self.DL_z, t, nu_obs, theta, self.luminosity)

    def light_curve(self, t_array, nu_obs, theta):
        """
        Calculate light curve over a time array.

        Parameters
        ----------
        t_array : ndarray
            Time array in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, M_Ni, E_K], or special-case
            [M_ej, M_Ni, E_K, E_Th, R0].

        Returns
        -------
        M_nu : ndarray
            AB magnitude array.
        F_nu : ndarray
            Flux density array.
        L_bol : ndarray
            Bolometric luminosity array.
        T_eff : ndarray
            Effective temperature array.
        """
        n = len(t_array)
        M_nu = np.zeros(n)
        F_nu = np.zeros(n)
        L_bol = np.zeros(n)
        T_eff = np.zeros(n)
        for i in range(n):
            M_nu[i], F_nu[i], L_bol[i], T_eff[i] = self.mag_ab(t_array[i], nu_obs, theta)
        return M_nu, F_nu, L_bol, T_eff


class ArnettMagnetar:
    """
    Arnett-type supernova light curve model powered by millisecond magnetar spin-down
    with initial thermal energy (shock cooling).

    Energy sources:
        1. Magnetar spin-down dipole radiation
        2. Initial thermal energy from shock breakout

    Reference: Kasen & Bildsten 2010, ApJ, 717, 245
    """

    def __init__(self, z, kappa_gamma=0.1, T_floor=5000.0):
        """
        Parameters
        ----------
        z : float
            Redshift of the source.
        kappa_gamma : float
            Gamma-ray opacity (cm^2/g), default 0.1.
        T_floor : float
            Minimum effective temperature floor (K), default 5000.
        """
        self.z = z
        self.DL_z = DL(z)
        self.kappa_gamma = kappa_gamma
        self.T_floor = T_floor

    def luminosity(self, t, theta):
        """
        Calculate bolometric luminosity, effective temperature, and photosphere radius.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, E_Th, R0, kappa]
            - M_ej : ejecta mass (M_sun)
            - P_ms : magnetar spin period (ms)
            - B_14 : magnetic field strength (1e14 G)
            - E_K  : kinetic energy (1e51 erg)
            - E_Th : initial thermal energy (1e51 erg)
            - R0   : initial radius (R_sun)
            - kappa: mean opacity (cm^2/g)

        Returns
        -------
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        R_ph  : float
            Photosphere radius (cm).
        """
        z = self.z
        kappa_gamma = self.kappa_gamma
        T_floor = self.T_floor

        t_rest = t / (1 + z)

        M_ej, P_ms, B_14, E_K, E_Th, R0, kappa = theta
        M_ej = M_ej * M_sun
        E_K = E_K * 1e51
        E_Th = E_Th * 1e51
        R0 = R0 * R_sun

        E_mag = 2.6e52 * P_ms**(-2.0)
        t_sd = 1.3e5 * P_ms**2.0 * B_14**(-2.0)
        L_sd_i = E_mag / t_sd

        v_ej = (2.0 * (E_K + E_mag) / M_ej)**0.5

        tau_d = (2.0 * kappa * M_ej / (13.8 * v_ej * c))**0.5
        tau_1 = (2.0 * kappa * M_ej / (13.8 * v_ej**2))**0.5
        t_ex = R0 / v_ej
        t_diff = kappa * M_ej / (13.8 * v_ej * c)
        y_ex = t_ex / tau_d
        L_Th0 = E_Th / t_diff
        t_gamma = ((2.0 * kappa_gamma * M_ej) / (13.8 * v_ej**2))**0.5
        L_heat0 = L_sd_i

        y = t_rest / tau_d
        y_tau = tau_1 / tau_d

        def f_heat(y_):
            t_ = max(y_ * tau_d, 1.0e-30)
            return ((1 - np.exp(-(t_gamma / t_)**2.0))
                    / (1.0 + t_ / t_sd)**2.0)

        def func_heat(x):
            return (x + y_ex) * np.exp(x*x + 2*x*y_ex) * f_heat(x)

        if y < 2 * y_tau:
            I_heat = quad(func_heat, 0, y, epsrel=1.49e-02)[0]
            L_bol = (2 * L_heat0 * np.exp(-(y*y + 2*y*y_ex)) * I_heat
                     + L_Th0 * np.exp(-(y*y + 2*y*y_ex)))
        else:
            L_bol = (L_heat0 * f_heat(y)
                     + L_Th0 * np.exp(-(y*y + 2*y*y_ex)))

        L_bol = max(L_bol, 1.0e-300)
        R_ph = R0 + v_ej * t_rest
        T_eff = (L_bol / (4 * pi * sigma_SB * R_ph**2))**0.25
        if T_eff < T_floor:
            T_eff = T_floor
            R_ph = (L_bol / (4.0 * pi * sigma_SB * T_floor**4))**0.5

        return L_bol, T_eff, R_ph

    def mag_ab(self, t, nu_obs, theta):
        """
        Calculate AB magnitude at a given observed frequency.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, E_Th, R0, kappa]

        Returns
        -------
        M_nu : float
            AB magnitude.
        F_nu : float
            Flux density (erg/s/cm^2/Hz).
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        """
        return _blackbody_mag_ab(self.z, self.DL_z, t, nu_obs, theta, self.luminosity)

    def light_curve(self, t_array, nu_obs, theta):
        """
        Calculate light curve over a time array.

        Parameters
        ----------
        t_array : ndarray
            Time array in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, E_Th, R0, kappa]

        Returns
        -------
        M_nu : ndarray
            AB magnitude array.
        F_nu : ndarray
            Flux density array.
        L_bol : ndarray
            Bolometric luminosity array.
        T_eff : ndarray
            Effective temperature array.
        """
        n = len(t_array)
        M_nu = np.zeros(n)
        F_nu = np.zeros(n)
        L_bol = np.zeros(n)
        T_eff = np.zeros(n)
        for i in range(n):
            M_nu[i], F_nu[i], L_bol[i], T_eff[i] = self.mag_ab(t_array[i], nu_obs, theta)
        return M_nu, F_nu, L_bol, T_eff


class Kasen2010Magnetar:
    """
    Kasen & Bildsten 2010 magnetar-powered supernova model.

    This class uses the magnetic dipole spin-down luminosity as the power input
    and an Arnett-style diffusion integral for the emergent bolometric luminosity.

    Reference: Kasen & Bildsten 2010, ApJ, 717, 245
    """

    def __init__(self, z, kappa_gamma=0.1, T_floor=5000.0):
        """
        Parameters
        ----------
        z : float
            Redshift of the source.
        kappa_gamma : float
            Gamma-ray opacity (cm^2/g), default 0.1.
        T_floor : float
            Minimum effective temperature floor (K), default 5000.
        """
        self.z = z
        self.DL_z = DL(z)
        self.kappa_gamma = kappa_gamma
        self.T_floor = T_floor

    def magnetar_power(self, t_rest, P_ms, B_14):
        """
        Calculate magnetar spin-down power at rest-frame time.

        Parameters
        ----------
        t_rest : float
            Rest-frame time since explosion in seconds.
        P_ms : float
            Magnetar spin period (ms).
        B_14 : float
            Dipole field strength (1e14 G).

        Returns
        -------
        L_sd : float
            Spin-down luminosity (erg/s).
        E_mag : float
            Initial rotational energy (erg).
        t_sd : float
            Spin-down time scale (s).
        """
        E_mag = 2.0e52 * P_ms**(-2.0)
        t_sd = 1.3e5 * P_ms**2.0 * B_14**(-2.0)
        L_sd = (E_mag / t_sd) / (1.0 + t_rest / t_sd)**2.0
        return L_sd, E_mag, t_sd

    def luminosity(self, t, theta):
        """
        Calculate bolometric luminosity, effective temperature, and photosphere radius.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, R0, kappa]
            - M_ej : ejecta mass (M_sun)
            - P_ms : magnetar spin period (ms)
            - B_14 : magnetic field strength (1e14 G)
            - E_K  : kinetic energy before magnetar injection (1e51 erg)
            - R0   : initial radius (R_sun)
            - kappa: mean opacity (cm^2/g)

        Returns
        -------
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        R_ph  : float
            Photosphere radius (cm).
        """
        z = self.z
        kappa_gamma = self.kappa_gamma
        T_floor = self.T_floor

        t_rest = t / (1 + z)

        M_ej, P_ms, B_14, E_K, R0, kappa = theta
        M_ej = M_ej * M_sun
        E_K = E_K * 1e51
        R0 = R0 * R_sun

        _, E_mag, _ = self.magnetar_power(0.0, P_ms, B_14)
        v_ej = (2.0 * (E_K + E_mag) / M_ej)**0.5
        tau_d = (2.0 * kappa * M_ej / (13.8 * v_ej * c))**0.5
        t_gamma = ((2.0 * kappa_gamma * M_ej) / (13.8 * v_ej**2))**0.5
        y = t_rest / tau_d

        def func_heat(x):
            t_ = max(x * tau_d, 1.0e-30)
            L_sd, _, _ = self.magnetar_power(t_, P_ms, B_14)
            deposition = 1.0 - np.exp(-(t_gamma / t_)**2.0)
            return x * np.exp(x*x) * L_sd * deposition

        if y < 20.0:
            I_heat = quad(func_heat, 0, y, epsrel=1.49e-02)[0]
            L_bol = 2.0 * np.exp(-y*y) * I_heat
        else:
            L_sd, _, _ = self.magnetar_power(t_rest, P_ms, B_14)
            deposition = 1.0 - np.exp(-(t_gamma / max(t_rest, 1.0e-30))**2.0)
            L_bol = L_sd * deposition

        L_bol = max(L_bol, 1.0e-300)
        R_ph = R0 + v_ej * t_rest
        T_eff = (L_bol / (4 * pi * sigma_SB * R_ph**2))**0.25
        if T_eff < T_floor:
            T_eff = T_floor
            R_ph = (L_bol / (4.0 * pi * sigma_SB * T_floor**4))**0.5

        return L_bol, T_eff, R_ph

    def mag_ab(self, t, nu_obs, theta):
        """
        Calculate AB magnitude at a given observed frequency.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, R0, kappa]

        Returns
        -------
        M_nu : float
            AB magnitude.
        F_nu : float
            Flux density (erg/s/cm^2/Hz).
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        """
        return _blackbody_mag_ab(self.z, self.DL_z, t, nu_obs, theta, self.luminosity)

    def light_curve(self, t_array, nu_obs, theta):
        """
        Calculate light curve over a time array.

        Parameters
        ----------
        t_array : ndarray
            Time array in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, R0, kappa]

        Returns
        -------
        M_nu : ndarray
            AB magnitude array.
        F_nu : ndarray
            Flux density array.
        L_bol : ndarray
            Bolometric luminosity array.
        T_eff : ndarray
            Effective temperature array.
        """
        n = len(t_array)
        M_nu = np.zeros(n)
        F_nu = np.zeros(n)
        L_bol = np.zeros(n)
        T_eff = np.zeros(n)
        for i in range(n):
            M_nu[i], F_nu[i], L_bol[i], T_eff[i] = self.mag_ab(t_array[i], nu_obs, theta)
        return M_nu, F_nu, L_bol, T_eff


class OmandSarin2024Magnetar:
    """
    Generalized semi-analytic magnetar-driven supernova model from
    Omand & Sarin 2024 (MNRAS 527, 6455; DOI: 10.1093/mnras/stad3645).

    theta = [M_ej, log10_L0, log10_t_sd, n_brake, f_Ni, E_SN, R0, kappa]
    """

    L_NI = 6.45e43
    L_CO = 1.45e43
    T_NI = 8.8 * day
    T_CO = 111.3 * day

    def __init__(self, z, kappa_gamma=0.1, T_floor=5000.0, cutoff_blackbody=False):
        self.z = z
        self.DL_z = DL(z)
        self.kappa_gamma = kappa_gamma
        self.T_floor = T_floor
        self.cutoff_blackbody = cutoff_blackbody

    @staticmethod
    def dipole_logL0_logtsd(P_ms, B_14, M_NS=1.4):
        """Map vacuum-dipole P0/B parameters to Omand & Sarin's L0/t_SD."""
        L0 = 2.0e47 * P_ms**(-4.0) * B_14**2.0
        t_sd = 1.3e5 * P_ms**2.0 * B_14**(-2.0) * (M_NS / 1.4)
        return np.log10(L0), np.log10(t_sd)

    def spin_down_power(self, t_rest, log10_L0, log10_t_sd, n_brake):
        L0 = 10.0**log10_L0
        t_sd = 10.0**log10_t_sd
        exponent = (1.0 + n_brake) / (1.0 - n_brake)
        t_safe = np.maximum(np.asarray(t_rest, dtype=float), 0.0)
        return L0 * (1.0 + t_safe / t_sd)**exponent

    def rotational_energy(self, log10_L0, log10_t_sd, n_brake):
        return 0.5 * (n_brake - 1.0) * 10.0**log10_L0 * 10.0**log10_t_sd

    def radioactive_power(self, t_rest, M_ej, f_Ni):
        t_safe = np.maximum(np.asarray(t_rest, dtype=float), 0.0)
        return (
            f_Ni * M_ej / M_sun
            * (
                self.L_NI * np.exp(-t_safe / self.T_NI)
                + self.L_CO * np.exp(-t_safe / self.T_CO)
            )
        )

    def _unpack_theta(self, theta):
        M_ej, log10_L0, log10_t_sd, n_brake, f_Ni, E_SN, R0, kappa = theta
        return {
            "M_ej": M_ej * M_sun,
            "log10_L0": log10_L0,
            "log10_t_sd": log10_t_sd,
            "n_brake": n_brake,
            "f_Ni": f_Ni,
            "E_SN": E_SN * 1.0e51,
            "R0": R0 * R_sun,
            "kappa": kappa,
        }

    def _bolometric_luminosity(self, E_int, R_ej, t_rest, qnt):
        E_int = max(E_int, 0.0)
        R_ej = max(R_ej, 1.0)
        volume = 4.0 * pi * R_ej**3 / 3.0
        tau = qnt["kappa"] * qnt["M_ej"] * R_ej / volume
        tau = max(tau, 0.0)
        if tau > 1.0:
            return E_int * c / max(tau * R_ej, 1.0)
        return E_int * c / R_ej

    def _rhs(self, t_rest, y, qnt):
        E_int = max(y[0], 0.0)
        v_ej = np.clip(y[1], 1.0, 0.95 * c)
        R_ej = max(y[2], qnt["R0"])
        t_safe = max(t_rest, 1.0)

        L_sd = self.spin_down_power(
            t_safe, qnt["log10_L0"], qnt["log10_t_sd"], qnt["n_brake"]
        )
        A_leak = 3.0 * self.kappa_gamma * qnt["M_ej"] / (4.0 * pi * v_ej**2)
        xi = -np.expm1(-A_leak / t_safe**2.0)
        L_ra = self.radioactive_power(t_safe, qnt["M_ej"], qnt["f_Ni"])
        L_bol = self._bolometric_luminosity(E_int, R_ej, t_safe, qnt)
        pdv = E_int * v_ej / R_ej

        dE_dt = float(xi * L_sd + L_ra - L_bol - pdv)
        if y[0] <= 0.0 and dE_dt < 0.0:
            dE_dt = 0.0
        dv_dt = c**2 * E_int / (qnt["M_ej"] * R_ej * v_ej**2)
        if y[1] >= 0.95 * c and dv_dt > 0.0:
            dv_dt = 0.0
        return [dE_dt, float(dv_dt), float(v_ej)]

    def _evolve(self, t_array, theta):
        qnt = self._unpack_theta(theta)
        t_obs = np.asarray(t_array, dtype=float)
        t_rest = np.maximum(t_obs / (1.0 + self.z), 0.0)
        order = np.argsort(t_rest)
        t_sorted = t_rest[order]
        t_max = float(np.max(t_sorted)) if len(t_sorted) else 0.0

        v0 = np.sqrt(2.0 * qnt["E_SN"] / qnt["M_ej"])
        v0 = min(max(v0, 1.0), 0.5 * c)
        y0 = [1.0e30, v0, qnt["R0"]]

        if t_max <= 0.0:
            sol_y = np.array(y0, dtype=float).reshape(3, 1)
        else:
            t_eval = np.unique(t_sorted)
            max_step = max(min(t_max / 1000.0, 0.05 * day), 10.0)
            sol = solve_ivp(
                lambda t, y: self._rhs(t, y, qnt),
                (0.0, t_max),
                y0,
                t_eval=t_eval,
                method="DOP853",
                rtol=1.0e-5,
                atol=[1.0e28, 1.0e2, 1.0e8],
                max_step=max_step,
            )
            if not sol.success:
                raise RuntimeError(f"OmandSarin2024Magnetar integration failed: {sol.message}")
            lookup = {float(t): sol.y[:, i] for i, t in enumerate(sol.t)}
            sol_y = np.column_stack([lookup[float(t)] for t in t_sorted])

        L_sorted = np.zeros_like(t_sorted)
        T_sorted = np.zeros_like(t_sorted)
        Rph_sorted = np.zeros_like(t_sorted)
        V_sorted = np.zeros_like(t_sorted)
        for i, (t_i, y_i) in enumerate(zip(t_sorted, sol_y.T)):
            E_int = max(y_i[0], 0.0)
            v_ej = np.clip(y_i[1], 1.0, 0.95 * c)
            R_ej = max(y_i[2], qnt["R0"])
            L_bol = max(self._bolometric_luminosity(E_int, R_ej, max(t_i, 1.0), qnt), 1.0e-300)
            T_phot = (L_bol / (4.0 * pi * sigma_SB * R_ej**2))**0.25
            R_ph = R_ej
            if T_phot < self.T_floor:
                T_phot = self.T_floor
                R_ph = np.sqrt(L_bol / (4.0 * pi * sigma_SB * self.T_floor**4))
            L_sorted[i] = L_bol
            T_sorted[i] = T_phot
            Rph_sorted[i] = R_ph
            V_sorted[i] = v_ej

        inv_order = np.empty_like(order)
        inv_order[order] = np.arange(len(order))
        return (
            L_sorted[inv_order],
            T_sorted[inv_order],
            Rph_sorted[inv_order],
            V_sorted[inv_order],
        )

    def luminosity(self, t, theta):
        L_bol, T_eff, R_ph, _ = self._evolve(np.array([t], dtype=float), theta)
        return L_bol[0], T_eff[0], R_ph[0]

    def mag_ab(self, t, nu_obs, theta):
        if not self.cutoff_blackbody:
            return _blackbody_mag_ab(self.z, self.DL_z, t, nu_obs, theta, self.luminosity)
        L_bol, T_eff, R_ph = self.luminosity(t, theta)
        return self._cutoff_mag_ab(L_bol, T_eff, R_ph, nu_obs)

    def _cutoff_mag_ab(self, L_bol, T_eff, R_ph, nu_obs):
        nu_rest = nu_obs * (1.0 + self.z)
        lambda_rest_cm = c / nu_rest
        cutoff_absorption = min(1.0, lambda_rest_cm / 3000.0e-8)
        expo = hp * nu_rest / (kb * T_eff)
        if expo > 700.0:
            F_nu = 0.0
        else:
            F_nu = (
                (2.0 * pi * hp * nu_rest**3 / c**2)
                * (R_ph / self.DL_z)**2
                / np.expm1(expo)
                * cutoff_absorption
            )
        F_nu = max(F_nu, 1.0e-300)
        M_nu = -2.5 * np.log10(F_nu) - 48.6 - 2.5 * np.log10(1.0 + self.z)
        return M_nu, F_nu, L_bol, T_eff

    def light_curve(self, t_array, nu_obs, theta):
        L_bol, T_eff, R_ph, _ = self._evolve(t_array, theta)
        if self.cutoff_blackbody:
            M_nu = np.zeros_like(L_bol)
            F_nu = np.zeros_like(L_bol)
            for i in range(len(L_bol)):
                M_nu[i], F_nu[i], _, _ = self._cutoff_mag_ab(
                    L_bol[i], T_eff[i], R_ph[i], nu_obs
                )
            return M_nu, F_nu, L_bol, T_eff

        nu_rest = nu_obs * (1.0 + self.z)
        expo = hp * nu_rest / (kb * T_eff)
        F_nu = np.zeros_like(L_bol)
        valid = expo <= 700.0
        F_nu[valid] = (
            (2.0 * pi * hp * nu_rest**3 / c**2)
            * (R_ph[valid] / self.DL_z)**2
            / np.expm1(expo[valid])
        )
        F_nu = np.maximum(F_nu, 1.0e-300)
        M_nu = -2.5 * np.log10(F_nu) - 48.6 - 2.5 * np.log10(1.0 + self.z)
        return M_nu, F_nu, L_bol, T_eff


class Zhu2026Magnetar:
    """
    Zhu & Zhang 2026 magnetar model for stripped-envelope supernovae.

    This implementation follows the semi-analytical internal-energy evolution in
    Zhu & Zhang (2026), Section 2.1: magnetar spin-down feeds the ejecta internal
    energy, while radiative diffusion and pdV work cool it. The same class
    interface as the other notebook models is preserved.
    """

    def __init__(self, z, kappa_gamma=0.30, T_floor=5000.0, delta=1.0, n=10.0):
        """
        Parameters
        ----------
        z : float
            Redshift of the source.
        kappa_gamma : float
            Effective gamma-ray opacity (cm^2/g), default 0.30 as in Zhu & Zhang.
        T_floor : float
            Minimum photospheric temperature (K), default 5000.
        delta : float
            Inner ejecta density power-law index, default 1.
        n : float
            Outer ejecta density power-law index, default 10.
        """
        self.z = z
        self.DL_z = DL(z)
        self.kappa_gamma = kappa_gamma
        self.T_floor = T_floor
        self.delta = float(delta)
        self.n = float(n)
        self.I_mag = 1.0e45
        self.R_mag = 1.0e6

    def magnetar_power(self, t_rest, P_ms, B_14):
        """
        Magnetic dipole spin-down luminosity.

        Parameters
        ----------
        t_rest : float or ndarray
            Rest-frame time since explosion (s).
        P_ms : float
            Initial spin period (ms).
        B_14 : float
            Polar magnetic field strength (1e14 G).
        """
        P = P_ms * 1.0e-3
        Bp = B_14 * 1.0e14
        omega = 2.0 * pi / P
        E_rot = 0.5 * self.I_mag * omega**2
        t_sd = 3.0 * c**3 * self.I_mag / (Bp**2 * self.R_mag**6 * omega**2)
        L_sd_i = E_rot / t_sd
        L_sd = L_sd_i / (1.0 + np.asarray(t_rest) / t_sd)**2.0
        return L_sd, E_rot, t_sd

    def _unpack_theta(self, theta):
        M_ej, P_ms, B_14, E_K, R0, kappa = theta
        return {
            "M_ej": M_ej * M_sun,
            "P_ms": P_ms,
            "B_14": B_14,
            "E_K": E_K * 1.0e51,
            "R0": R0 * R_sun,
            "kappa": kappa,
        }

    def _emergent_luminosity(self, E_int, R, kappa, M_ej):
        E_int = max(E_int, 0.0)
        R = max(R, 1.0)
        tau = 3.0 * kappa * M_ej / (4.0 * pi * R**2)
        if tau > 1.0e-8:
            escape = -np.expm1(-tau)
            return c * E_int / (R * tau) * escape
        return c * E_int / R

    def _rhs(self, t_rest, y, qnt):
        E_int = max(y[0], 0.0)
        v_ej = max(y[1], 1.0)
        R = max(y[2], qnt["R0"])

        L_sd = self.magnetar_power(t_rest, qnt["P_ms"], qnt["B_14"])[0]
        tau_gamma = 3.0 * self.kappa_gamma * qnt["M_ej"] / (4.0 * pi * R**2)
        L_sd *= -np.expm1(-tau_gamma)
        L_SN = self._emergent_luminosity(E_int, R, qnt["kappa"], qnt["M_ej"])
        adiabatic = E_int * v_ej / R

        dE_dt = float(L_sd - adiabatic - L_SN)
        if y[0] <= 0.0 and dE_dt < 0.0:
            dE_dt = 0.0
        dv_dt = E_int / (R * qnt["M_ej"])
        dR_dt = v_ej

        return [dE_dt, dv_dt, dR_dt]

    def _photosphere(self, t_rest, L_bol, v_ej, E_kin, qnt):
        t_eff = max(t_rest, 1.0)
        L_bol = max(L_bol, 1.0e-300)
        delta = self.delta
        n = self.n
        M_ej = qnt["M_ej"]
        kappa = qnt["kappa"]

        zeta_rho = (n - 3.0) * (3.0 - delta) / (4.0 * pi * (n - delta))
        zeta_v = (2.0 * (5.0 - delta) * (n - 5.0)
                  / ((n - 3.0) * (3.0 - delta)))**0.5
        v_tr = zeta_v * max(E_kin / M_ej, 1.0)**0.5
        K_tau = kappa * zeta_rho * M_ej / (v_tr**2 * t_eff**2)
        target_tau = 2.0 / 3.0

        tau_at_vtr = K_tau / (n - 1.0)
        if target_tau <= tau_at_vtr:
            x = (target_tau * (n - 1.0) / K_tau)**(1.0 / (1.0 - n))
        else:
            inner_term = target_tau / K_tau - 1.0 / (n - 1.0)
            if abs(delta - 1.0) < 1.0e-8:
                x = np.exp(-inner_term)
            else:
                base = max(1.0 - inner_term * (1.0 - delta), 1.0e-12)
                x = base**(1.0 / (1.0 - delta))

        v_ph = max(x * v_tr, 1.0)
        R_ph = max(v_ph * t_eff, qnt["R0"])
        T_bb = (L_bol / (4.0 * pi * sigma_SB * R_ph**2))**0.25

        if T_bb < self.T_floor:
            R_floor = (L_bol / (4.0 * pi * sigma_SB * self.T_floor**4))**0.5
            R_ph = R_floor
            T_bb = self.T_floor

        return T_bb, R_ph

    def _evolve(self, t_array, theta):
        qnt = self._unpack_theta(theta)
        t_obs = np.asarray(t_array, dtype=float)
        t_rest = np.maximum(t_obs / (1.0 + self.z), 0.0)
        order = np.argsort(t_rest)
        t_sorted = t_rest[order]
        t_max = float(np.max(t_sorted)) if len(t_sorted) else 0.0

        v0 = (2.0 * qnt["E_K"] / qnt["M_ej"])**0.5
        y0 = [1.0e30, v0, qnt["R0"]]

        if t_max <= 0.0:
            sol_y = np.array(y0, dtype=float).reshape(3, 1)
        else:
            t_eval = np.unique(t_sorted)
            max_step = max(min(t_max / 800.0, 0.1 * day), 10.0)
            sol = solve_ivp(
                lambda t, y: self._rhs(t, y, qnt),
                (0.0, t_max),
                y0,
                t_eval=t_eval,
                method="DOP853",
                rtol=1.0e-5,
                atol=[1.0e30, 1.0e2, 1.0e8],
                max_step=max_step,
            )
            if not sol.success:
                raise RuntimeError(f"Zhu2026Magnetar integration failed: {sol.message}")
            lookup = {float(t): sol.y[:, i] for i, t in enumerate(sol.t)}
            sol_y = np.column_stack([lookup[float(t)] for t in t_sorted])

        L_sorted = np.zeros_like(t_sorted)
        T_sorted = np.zeros_like(t_sorted)
        Rph_sorted = np.zeros_like(t_sorted)
        for i, (t_rest_i, y_i) in enumerate(zip(t_sorted, sol_y.T)):
            E_int = max(y_i[0], 0.0)
            v_ej = max(y_i[1], 1.0)
            R = max(y_i[2], qnt["R0"])
            L_bol = self._emergent_luminosity(E_int, R, qnt["kappa"], qnt["M_ej"])
            E_kin = 0.5 * qnt["M_ej"] * v_ej**2
            T_eff, R_ph = self._photosphere(t_rest_i, L_bol, v_ej, E_kin, qnt)
            L_sorted[i] = max(L_bol, 1.0e-300)
            T_sorted[i] = T_eff
            Rph_sorted[i] = R_ph

        # Once the ejecta becomes optically thin, the analytic tau=2/3 solution
        # can recede to an unphysically tiny radius and make optical bands brighten.
        # Keep the emitting radius from collapsing after its maximum expansion.
        Rph_sorted = np.maximum.accumulate(Rph_sorted)
        T_sorted = (L_sorted / (4.0 * pi * sigma_SB * Rph_sorted**2))**0.25
        below_floor = T_sorted < self.T_floor
        if np.any(below_floor):
            Rph_sorted[below_floor] = np.sqrt(
                L_sorted[below_floor] / (4.0 * pi * sigma_SB * self.T_floor**4)
            )
            T_sorted[below_floor] = self.T_floor

        inv_order = np.empty_like(order)
        inv_order[order] = np.arange(len(order))
        return L_sorted[inv_order], T_sorted[inv_order], Rph_sorted[inv_order]

    def luminosity(self, t, theta):
        """
        Calculate bolometric luminosity, effective temperature, and photosphere radius.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, R0, kappa]
            - M_ej : ejecta mass (M_sun)
            - P_ms : magnetar initial spin period (ms)
            - B_14 : polar magnetic field strength (1e14 G)
            - E_K  : initial kinetic energy (1e51 erg)
            - R0   : initial radius (R_sun)
            - kappa: optical opacity (cm^2/g)
        """
        L_bol, T_eff, R_ph = self._evolve(np.array([t], dtype=float), theta)
        return L_bol[0], T_eff[0], R_ph[0]

    def mag_ab(self, t, nu_obs, theta):
        return _blackbody_mag_ab(self.z, self.DL_z, t, nu_obs, theta, self.luminosity)

    def light_curve(self, t_array, nu_obs, theta):
        """
        Calculate light curve over a time array.

        Parameters
        ----------
        t_array : ndarray
            Time array in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, P_ms, B_14, E_K, R0, kappa]
        """
        L_bol, T_eff, R_ph = self._evolve(t_array, theta)
        nu_rest = nu_obs * (1.0 + self.z)
        expo = hp * nu_rest / (kb * T_eff)
        F_nu = np.zeros_like(L_bol)
        valid = expo <= 700.0
        F_nu[valid] = ((2.0 * pi * hp * nu_rest**3 / c**2)
                       * (R_ph[valid] / self.DL_z)**2
                       / np.expm1(expo[valid]))
        F_nu = np.maximum(F_nu, 1.0e-300)
        M_nu = -2.5 * np.log10(F_nu) - 48.6 - 2.5 * np.log10(1.0 + self.z)
        return M_nu, F_nu, L_bol, T_eff


class Chatzopoulos2012CSM:
    """
    Chatzopoulos, Wheeler & Vinko 2012 ejecta-CSM interaction model.

    The shock input luminosity is calculated from self-similar forward and reverse
    shock terms. The emergent luminosity is then computed with an Arnett-like
    diffusion integral through the optically thick CSM.

    Reference: Chatzopoulos, Wheeler & Vinko 2012, ApJ, 746, 121
    """

    def __init__(self, z, A=1.0, B_f=1.0, B_r=1.0, T_floor=1000.0):
        """
        Parameters
        ----------
        z : float
            Redshift of the source.
        A : float
            Self-similar shock-radius coefficient.
        B_f : float
            Forward-shock coefficient.
        B_r : float
            Reverse-shock coefficient.
        T_floor : float
            Minimum effective temperature floor (K), default 1000.
        """
        self.z = z
        self.DL_z = DL(z)
        self.A = A
        self.B_f = B_f
        self.B_r = B_r
        self.T_floor = T_floor

    def _csm_quantities(self, theta):
        M_ej, M_csm, E_SN, R0, rho_csm, kappa, n, delta, s, efficiency = theta
        M_ej = M_ej * M_sun
        M_csm = M_csm * M_sun
        E_SN = E_SN * 1e51
        R0 = R0 * R_sun
        s = float(s)
        n = float(n)
        delta = float(delta)

        v_ej = (10.0 * E_SN / (3.0 * M_ej))**0.5
        g_n = (1.0 / (4.0 * pi * (n - delta))
               * (2.0 * (5.0 - delta) * (n - 5.0) * E_SN)**((n - 3.0) / 2.0)
               / ((3.0 - delta) * (n - 3.0) * M_ej)**((n - 5.0) / 2.0))

        q = rho_csm * R0**s

        if abs(s - 3.0) < 1.0e-8:
            raise ValueError("The CSM density index s cannot be 3.")

        R_csm = (((3.0 - s) * M_csm / (4.0 * pi * q) + R0**(3.0 - s))
                 ** (1.0 / (3.0 - s)))

        if abs(s - 1.0) < 1.0e-8:
            R_ph = R_csm * np.exp(-2.0 / (3.0 * kappa * q))
        else:
            R_ph_arg = -2.0 * (1.0 - s) / (3.0 * kappa * q) + R_csm**(1.0 - s)
            R_ph = R_ph_arg**(1.0 / (1.0 - s)) if R_ph_arg > 0 else R_csm

        R_ph = min(max(R_ph, R0), R_csm)
        M_csm_th = abs(4.0 * pi * q / (3.0 - s) * (R_ph**(3.0 - s) - R0**(3.0 - s)))
        M_csm_th = max(M_csm_th, 1.0e-30)

        t_i = max(R0 / v_ej, 1.0)

        t_FS = (abs((3.0 - s) * q**((3.0 - n) / (n - s))
                    * (self.A * g_n)**((s - 3.0) / (n - s))
                    / (4.0 * pi * self.B_f**(3.0 - s)))
                ** ((n - s) / ((n - 3.0) * (3.0 - s)))
                * M_csm_th**((n - s) / ((n - 3.0) * (3.0 - s))))

        rs_term = 1.0 - ((3.0 - n) * M_ej
                         / (4.0 * pi * v_ej**(3.0 - n) * g_n))
        rs_term = max(rs_term, 1.0e-30)
        t_RS = (v_ej / (self.B_r * (self.A * g_n / q)**(1.0 / (n - s)))
                * rs_term**(1.0 / (3.0 - n)))**((n - s) / (s - 3.0))

        tau_diff = (2.0 * kappa * M_csm_th / (13.8 * c * v_ej))**0.5

        return {
            "M_ej": M_ej,
            "M_csm": M_csm,
            "E_SN": E_SN,
            "R0": R0,
            "rho_csm": rho_csm,
            "kappa": kappa,
            "n": n,
            "delta": delta,
            "s": s,
            "efficiency": efficiency,
            "v_ej": v_ej,
            "g_n": g_n,
            "q": q,
            "R_csm": R_csm,
            "R_ph_static": R_ph,
            "M_csm_th": M_csm_th,
            "t_i": t_i,
            "t_FS": t_FS,
            "t_RS": t_RS,
            "tau_diff": tau_diff,
        }

    def input_luminosity(self, t_rest, theta):
        """
        Calculate forward and reverse shock power before diffusion.

        Parameters
        ----------
        t_rest : float
            Rest-frame time since explosion in seconds.
        theta : array-like
            Model parameters: [M_ej, M_csm, E_SN, R0, rho_csm, kappa, n, delta, s, efficiency]

        Returns
        -------
        L_in : float
            Total shock input luminosity (erg/s).
        L_FS : float
            Forward-shock input luminosity (erg/s).
        L_RS : float
            Reverse-shock input luminosity (erg/s).
        """
        qnt = self._csm_quantities(theta)
        tau = max(t_rest - qnt["t_i"], 0.0)
        if tau <= 0.0:
            return 0.0, 0.0, 0.0

        n = qnt["n"]
        s = qnt["s"]
        q = qnt["q"]
        g_n = qnt["g_n"]
        t_eff = tau + qnt["t_i"]
        power_index = (2.0*n + 6.0*s - n*s - 15.0) / (n - s)

        L_FS = (2.0 * pi / (n - s)**3
                * g_n**((5.0 - s) / (n - s))
                * q**((n - 5.0) / (n - s))
                * (n - 3.0)**2
                * (n - 5.0)
                * self.B_f**(5.0 - s)
                * self.A**((5.0 - s) / (n - s))
                * t_eff**power_index
                * (qnt["t_FS"] > tau))

        L_RS = (2.0 * pi
                * (self.A * g_n / q)**((5.0 - n) / (n - s))
                * self.B_r**(5.0 - n)
                * g_n
                * ((3.0 - s) / (n - s))**3
                * t_eff**power_index
                * (qnt["t_RS"] > tau))

        L_FS = qnt["efficiency"] * L_FS
        L_RS = qnt["efficiency"] * L_RS
        L_in = L_FS + L_RS

        return L_in, L_FS, L_RS

    def luminosity(self, t, theta):
        """
        Calculate bolometric luminosity, effective temperature, and photosphere radius.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        theta : array-like
            Model parameters: [M_ej, M_csm, E_SN, R0, rho_csm, kappa, n, delta, s, efficiency]
            - M_ej      : ejecta mass (M_sun)
            - M_csm     : CSM mass (M_sun)
            - E_SN      : explosion energy (1e51 erg)
            - R0        : inner CSM radius (R_sun)
            - rho_csm   : CSM density at R0 (g/cm^3)
            - kappa     : CSM/ejecta opacity (cm^2/g)
            - n         : outer ejecta density power-law index
            - delta     : inner ejecta density power-law index
            - s         : CSM density power-law index, 0 shell or 2 wind
            - efficiency: kinetic-to-radiation conversion efficiency

        Returns
        -------
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        R_ph  : float
            Photosphere radius (cm).
        """
        z = self.z
        T_floor = self.T_floor

        t_rest = t / (1 + z)
        qnt = self._csm_quantities(theta)
        tau_diff = qnt["tau_diff"]
        y = t_rest / tau_diff

        def func_heat(x):
            t_ = x * tau_diff
            L_in, _, _ = self.input_luminosity(t_, theta)
            return x * np.exp(x*x) * L_in

        if y < 20.0:
            I_heat = quad(func_heat, 0, y, epsrel=1.49e-02)[0]
            L_bol = 2.0 * np.exp(-y*y) * I_heat
        else:
            L_bol = self.input_luminosity(t_rest, theta)[0]
        L_bol = max(L_bol, 1.0e-300)

        R_ph = qnt["R_ph_static"]
        T_eff = (L_bol / (4 * pi * sigma_SB * R_ph**2))**0.25
        T_eff = max(T_eff, T_floor)

        return L_bol, T_eff, R_ph

    def mag_ab(self, t, nu_obs, theta):
        """
        Calculate AB magnitude at a given observed frequency.

        Parameters
        ----------
        t : float
            Time since explosion in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, M_csm, E_SN, R0, rho_csm, kappa, n, delta, s, efficiency]

        Returns
        -------
        M_nu : float
            AB magnitude.
        F_nu : float
            Flux density (erg/s/cm^2/Hz).
        L_bol : float
            Bolometric luminosity (erg/s).
        T_eff : float
            Effective temperature (K).
        """
        return _blackbody_mag_ab(self.z, self.DL_z, t, nu_obs, theta, self.luminosity)

    def light_curve(self, t_array, nu_obs, theta):
        """
        Calculate light curve over a time array.

        Parameters
        ----------
        t_array : ndarray
            Time array in seconds (observer frame).
        nu_obs : float
            Observed frequency (Hz).
        theta : array-like
            Model parameters: [M_ej, M_csm, E_SN, R0, rho_csm, kappa, n, delta, s, efficiency]

        Returns
        -------
        M_nu : ndarray
            AB magnitude array.
        F_nu : ndarray
            Flux density array.
        L_bol : ndarray
            Bolometric luminosity array.
        T_eff : ndarray
            Effective temperature array.
        """
        n = len(t_array)
        M_nu = np.zeros(n)
        F_nu = np.zeros(n)
        L_bol = np.zeros(n)
        T_eff = np.zeros(n)
        for i in range(n):
            M_nu[i], F_nu[i], L_bol[i], T_eff[i] = self.mag_ab(t_array[i], nu_obs, theta)
        return M_nu, F_nu, L_bol, T_eff
