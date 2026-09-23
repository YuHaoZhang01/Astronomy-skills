from __future__ import annotations

import threading
import time
from pathlib import Path

from snstudio.schemas import RunSpec, SweepAxis, SweepSpec
from snstudio.service import StudioService
from snstudio.worker import Worker


def test_preview_submit_and_worker_success(studio) -> None:
    settings, database, registry = studio
    service = StudioService(settings, database, registry)
    spec = RunSpec(parameters={"Ni_mass": 0.04, "tend": 100.0})
    preview = service.preview_run(spec)
    assert preview.valid
    run = service.submit_run(spec)
    worker = Worker(settings, database, registry)
    claimed = database.claim_next_run()
    assert claimed and claimed["id"] == run["id"]
    worker.execute(claimed)
    finished = database.get_run(run["id"])
    assert finished["status"] == "succeeded"
    assert finished["progress"] == 1.0
    assert finished["current_time"] == 100.0
    series = registry.get("supersnec").parse_series(Path(finished["run_dir"]))
    assert {item.id for item in series} >= {"lbol", "v_ph", "mag_g"}
    assert next(item for item in series if item.id == "v_ph").y[-1] == 2000


def test_sweep_preview_and_limit(studio) -> None:
    settings, database, registry = studio
    settings.max_sweep_runs = 3
    service = StudioService(settings, database, registry)
    spec = SweepSpec(
        axes={
            "Ni_mass": SweepAxis(kind="list", values=[0.01, 0.02]),
            "final_energy": SweepAxis(kind="list", values=[1e51, 2e51]),
        }
    )
    preview = service.preview_sweep(spec)
    assert preview.count == 4
    assert not preview.valid
    assert "超过上限" in preview.errors[0]


def test_running_jobs_become_interrupted_after_restart(studio) -> None:
    settings, database, registry = studio
    service = StudioService(settings, database, registry)
    run = service.submit_run(RunSpec())
    assert database.claim_next_run()["status"] == "running"
    assert database.recover_interrupted() == 1
    assert database.get_run(run["id"])["status"] == "interrupted"


SLOW_SOLVER = r"""#!/usr/bin/env python3
import time
print("      nt           time          dtime       max(rho)       shockpos", flush=True)
for nt in range(200):
    print(f"{nt:8d} {float(nt):14.6E} {1.0:14.6E} {1.0:14.6E} {1.0:14.6E}", flush=True)
    time.sleep(0.02)
"""


def wait_for_pid(database, run_id: str) -> None:
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        if database.get_run(run_id)["pid"]:
            return
        time.sleep(0.01)
    raise AssertionError("worker process did not start")


def test_running_cancel_terminates_process_group(studio) -> None:
    settings, database, registry = studio
    (settings.supersnec_root / "snec").write_text(SLOW_SOLVER)
    service = StudioService(settings, database, registry)
    run = service.submit_run(RunSpec())
    claimed = database.claim_next_run()
    worker = Worker(settings, database, registry)
    thread = threading.Thread(target=worker.execute, args=(claimed,))
    thread.start()
    wait_for_pid(database, run["id"])
    database.request_cancel(run["id"])
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert database.get_run(run["id"])["status"] == "cancelled"


def test_worker_shutdown_marks_running_job_interrupted(studio) -> None:
    settings, database, registry = studio
    (settings.supersnec_root / "snec").write_text(SLOW_SOLVER)
    service = StudioService(settings, database, registry)
    run = service.submit_run(RunSpec())
    claimed = database.claim_next_run()
    worker = Worker(settings, database, registry)
    thread = threading.Thread(target=worker.execute, args=(claimed,))
    thread.start()
    wait_for_pid(database, run["id"])
    worker.stop()
    thread.join(timeout=5)
    assert not thread.is_alive()
    assert database.get_run(run["id"])["status"] == "interrupted"


def test_terminal_state_is_not_changed_by_late_cancel(studio) -> None:
    _, database, _ = studio
    run_id = database.create_run(
        {
            "project_id": "default",
            "engine_id": "supersnec",
            "profile_id": "builtin:supersnec:stripped_star",
            "name": "finished",
            "parameters": {},
            "output_mode": "full",
            "run_dir": "/tmp/not-used",
            "status": "succeeded",
        }
    )["id"]
    assert database.request_cancel(run_id)["status"] == "succeeded"
