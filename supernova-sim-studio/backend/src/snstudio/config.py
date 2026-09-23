from __future__ import annotations

import os
import platform
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def default_data_dir() -> Path:
    override = os.environ.get("SNSTUDIO_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Supernova Simulation Studio"
    return Path.home() / ".local" / "share" / "supernova-sim-studio"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SNSTUDIO_", extra="ignore")

    data_dir: Path = default_data_dir()
    host: str = "127.0.0.1"
    port: int = 8787
    worker_concurrency: int = 4
    poll_interval: float = 0.35
    max_sweep_runs: int = 500
    supersnec_root: Path = Path(
        "/Users/zyh/Library/CloudStorage/OneDrive-个人/ResearchOps/01_personal_projects/"
        "11-Early_Radiation/SuperSNEC"
    )
    snec_root: Path = Path("/Users/zyh/Desktop/software/SNEC")
    stella_root: Path | None = Path("/Users/zyh/Desktop/software/OpenStella")
    frontend_dist: Path = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    enable_fake_engine: bool = False
    api_url: str = "http://127.0.0.1:8787"

    @property
    def database_path(self) -> Path:
        return self.data_dir / "studio.sqlite3"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def profiles_dir(self) -> Path:
        return self.data_dir / "profiles"

    @property
    def trash_dir(self) -> Path:
        return self.data_dir / "trash"

    def ensure_directories(self) -> None:
        for path in (self.data_dir, self.runs_dir, self.profiles_dir, self.trash_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
