from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import threading
import time
import traceback
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .database import Database, get_database, utcnow
from .engines import EngineRegistry
from .schemas import RunStatus
from .storage import resolve_profile

logger = logging.getLogger(__name__)


class Worker:
    def __init__(self, settings: Settings, database: Database, registry: EngineRegistry):
        self.settings = settings
        self.database = database
        self.registry = registry
        self.stop_event = threading.Event()
        self.running_processes: dict[str, subprocess.Popen[Any]] = {}
        self.process_lock = threading.Lock()

    def stop(self) -> None:
        self.stop_event.set()
        with self.process_lock:
            for process in self.running_processes.values():
                self._terminate(process)

    @staticmethod
    def _terminate(process: subprocess.Popen[Any]) -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def execute(self, run: dict[str, Any]) -> None:
        run_id = run["id"]
        run_dir = Path(run["run_dir"])
        try:
            adapter = self.registry.get(run["engine_id"])
            profile = resolve_profile(run["profile_id"], self.database, self.registry)
            if profile is None:
                raise RuntimeError(f"找不到模型：{run['profile_id']}")
            final_parameters = adapter.stage(run_dir, profile, run["rendered_parameters"])
            self.database.update_run(run_id, rendered_parameters=final_parameters)
            log_path = run_dir / "run.log"
            with log_path.open("w") as log_handle:
                process = subprocess.Popen(
                    adapter.command(run_dir),
                    cwd=run_dir,
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                with self.process_lock:
                    self.running_processes[run_id] = process
                self.database.update_run(run_id, pid=process.pid)
                parsed_lines = 0
                while process.poll() is None:
                    current = self.database.get_run(run_id)
                    if self.stop_event.is_set() or (
                        current and current["status"] == RunStatus.cancelling.value
                    ):
                        self._terminate(process)
                        break
                    parsed_lines = self._update_progress(adapter, run, log_path, parsed_lines)
                    time.sleep(self.settings.poll_interval)
                return_code = process.wait()
                self._update_progress(adapter, run, log_path, parsed_lines)
            with self.process_lock:
                self.running_processes.pop(run_id, None)
            log_text = log_path.read_text(errors="replace")
            current = self.database.get_run(run_id)
            if current and current["status"] == RunStatus.cancelling.value:
                self.database.update_run(
                    run_id,
                    status=RunStatus.cancelled,
                    finished_at=utcnow(),
                    pid=None,
                    error="任务已按请求取消。",
                )
                return
            if self.stop_event.is_set():
                self.database.update_run(
                    run_id,
                    status=RunStatus.interrupted,
                    finished_at=utcnow(),
                    pid=None,
                    error="Worker 已停止；计算进程已终止，可检查日志后重试。",
                )
                return
            errors = adapter.validate_completion(run_dir, return_code, log_text)
            manifest = adapter.build_manifest(run_id, run_dir, final_parameters)
            manifest_data = manifest.model_dump(mode="json")
            (run_dir / "manifest.json").write_text(
                json.dumps(manifest_data, ensure_ascii=False, indent=2)
            )
            if errors:
                self.database.update_run(
                    run_id,
                    status=RunStatus.failed,
                    finished_at=utcnow(),
                    pid=None,
                    error="；".join(errors),
                    manifest=manifest_data,
                )
            else:
                self.database.update_run(
                    run_id,
                    status=RunStatus.succeeded,
                    progress=1.0,
                    current_time=run.get("tend"),
                    finished_at=utcnow(),
                    pid=None,
                    manifest=manifest_data,
                )
        except Exception as exc:  # noqa: BLE001 -- worker boundary must persist every failure
            run_dir.mkdir(parents=True, exist_ok=True)
            with (run_dir / "worker-error.log").open("a") as handle:
                handle.write(traceback.format_exc())
            self.database.update_run(
                run_id,
                status=RunStatus.failed,
                finished_at=utcnow(),
                pid=None,
                error=f"运行器异常：{exc}",
            )
            with self.process_lock:
                self.running_processes.pop(run_id, None)

    def _update_progress(
        self, adapter, run: dict[str, Any], log_path: Path, parsed_lines: int
    ) -> int:
        if not log_path.exists():
            return parsed_lines
        lines = log_path.read_text(errors="replace").splitlines()
        for line in lines[parsed_lines:]:
            parsed = adapter.parse_progress(line, run.get("tend"))
            if parsed:
                progress, current_time = parsed
                self.database.update_run(run["id"], progress=progress, current_time=current_time)
        return len(lines)

    def run_forever(self, *, once: bool = False) -> None:
        self.database.recover_interrupted()
        futures: set[Future[Any]] = set()
        with ThreadPoolExecutor(max_workers=max(1, self.settings.worker_concurrency)) as executor:
            while not self.stop_event.is_set():
                futures = {future for future in futures if not future.done()}
                while len(futures) < self.settings.worker_concurrency:
                    run = self.database.claim_next_run()
                    if run is None:
                        break
                    futures.add(executor.submit(self.execute, run))
                if once and not futures and self.database.claim_next_run() is None:
                    break
                time.sleep(self.settings.poll_interval)
            for future in futures:
                try:
                    future.result()
                except Exception:
                    logger.exception("Worker future failed during shutdown")


def main() -> None:
    settings = get_settings()
    worker = Worker(settings, get_database(), EngineRegistry(settings))
    signal.signal(signal.SIGINT, lambda *_: worker.stop())
    signal.signal(signal.SIGTERM, lambda *_: worker.stop())
    worker.run_forever()


if __name__ == "__main__":
    main()
