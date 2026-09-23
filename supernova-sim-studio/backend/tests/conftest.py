from __future__ import annotations

from pathlib import Path

import pytest

from snstudio.config import Settings
from snstudio.database import Database
from snstudio.engines import EngineRegistry

PARAMETERS = """# test template
outdir = "Data"
profile_name = "profiles/stripped_star.short"
comp_profile_name = "profiles/stripped_star.iso.dat"
initial_data = "Thermal_Bomb"
final_energy = 1.0d51
bomb_tstart = 0.0d0
bomb_tend = 0.1d0
bomb_mass_spread = 0.1d0
bomb_start_point = 1
piston_vel = 5.0d9
piston_tstart = 0.0d0
piston_tend = 1.0d-2
imax = 100
grid_mode = "adaptive_runtime"
mass_excision = 1
mass_excised = 1.4
radiation = 1
eoskey = 2
Ni_switch = 1
Ni_mass = 0.03
Ni_period = 5.0d4
saha_ncomps = 3
boxcar_smoothing = 1
opacity_floor_envelope = 0.01
opacity_floor_core = 0.24
ntmax = 100000
tend = 100.0
dtout = 10.0
dtout_scalar = 10.0
dtout_check = 1000.0
ntout = -1
ntout_scalar = -1
ntout_check = -1
ntinfo = 10
dtmin = 1.0d-10
dtmax = 10.0
sedov = 0
Ni_mix_fraction = 0.31
Ni_mix_kernel = 1
output_mode = 0
"""


DUMMY_SOLVER = r"""#!/usr/bin/env python3
from pathlib import Path
import time

out = Path("Data")
if not out.is_dir():
    print("*** Output directory does not exist.")
    raise SystemExit(0)
print("      nt           time          dtime       max(rho)       shockpos", flush=True)
for nt, current in [(0, 0.0), (10, 50.0), (20, 100.0)]:
    print(f"{nt:8d} {current:14.6E} {1.0:14.6E} {1.0:14.6E} {1.0:14.6E}", flush=True)
    time.sleep(0.01)
(out / "lum_observed.dat").write_text("0 1e40\n86400 2e40\n")
(out / "vel_photo.dat").write_text("0 1e8\n86400 2e8\n")
(out / "T_eff.dat").write_text("0 5000\n86400 6000\n")
(out / "magnitudes.dat").write_text("0 5000 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20\n86400 6000 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21\n")
(out / "run_summary.dat").write_text("# test\ntend_actual = 100\n")
print("Done! :-) tend reached after       20 timesteps", flush=True)
"""


def create_engine(root: Path) -> Path:
    (root / "profiles").mkdir(parents=True)
    (root / "tables").mkdir()
    (root / "parameters").write_text(PARAMETERS)
    (root / "profiles" / "stripped_star.short").write_text("1 2\n2 3\n3 4\n")
    (root / "profiles" / "stripped_star.iso.dat").write_text("1 0.5\n2 0.5\n3 0.5\n")
    (root / "tables" / "BolCorr.dat").write_text("# test\n")
    binary = root / "snec"
    binary.write_text(DUMMY_SOLVER)
    binary.chmod(0o755)
    return root


@pytest.fixture()
def studio(tmp_path: Path):
    engine = create_engine(tmp_path / "engine")
    settings = Settings(
        data_dir=tmp_path / "data",
        supersnec_root=engine,
        snec_root=engine,
        stella_root=None,
        frontend_dist=tmp_path / "missing-frontend",
        worker_concurrency=2,
        poll_interval=0.01,
    )
    settings.ensure_directories()
    database = Database(settings.database_path)
    database.init()
    registry = EngineRegistry(settings)
    return settings, database, registry
