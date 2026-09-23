from __future__ import annotations

import hashlib
import math
import re
import subprocess
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

from ..parameters import parse_fortran_number
from ..schemas import Artifact, ArtifactManifest, Engine, ParameterField, ProfilePair, Series


class EngineAdapter(ABC):
    id: str
    display_name: str
    family: str
    capabilities: ClassVar[list[str]] = ["single-run"]
    license_name: str | None = None

    @abstractmethod
    def doctor(self) -> Engine:
        raise NotImplementedError

    @abstractmethod
    def parameter_fields(self) -> list[ParameterField]:
        raise NotImplementedError

    @abstractmethod
    def template_text(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def validate_and_render(
        self, parameters: dict[str, Any], raw_parameters: str | None, output_mode: str
    ) -> tuple[str, dict[str, Any], list[str], list[str]]:
        raise NotImplementedError

    @abstractmethod
    def builtin_profiles(self) -> list[ProfilePair]:
        raise NotImplementedError

    @abstractmethod
    def stage(
        self,
        run_dir: Path,
        profile: dict[str, Any],
        rendered_parameters: str,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def command(self, run_dir: Path) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def validate_completion(self, run_dir: Path, return_code: int, log_text: str) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def parse_series(self, run_dir: Path) -> list[Series]:
        raise NotImplementedError

    def parse_progress(self, line: str, tend: float | None) -> tuple[float, float | None] | None:
        match = re.match(r"^\s*\d+\s+([+\-\d.Ee]+)\s+([+\-\d.Ee]+)", line)
        if not match:
            return None
        current = parse_fortran_number(match.group(1))
        progress = min(max(current / tend, 0.0), 0.995) if tend and tend > 0 else 0.0
        return progress, current

    def version(self) -> str:
        return "unknown"

    def build_manifest(self, run_id: str, run_dir: Path, parameters_text: str) -> ArtifactManifest:
        artifacts: list[Artifact] = []
        checksum_targets = {
            "run.log",
            "parameters",
            "Data/run_summary.dat",
            "Data/lum_observed.dat",
        }
        for path in sorted(run_dir.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(run_dir).as_posix()
            digest = sha256_file(path) if relative in checksum_targets else None
            artifacts.append(Artifact(path=relative, size_bytes=path.stat().st_size, sha256=digest))
        return ArtifactManifest(
            run_id=run_id,
            engine_id=self.id,
            engine_version=self.version(),
            parameters_sha256=hashlib.sha256(parameters_text.encode()).hexdigest(),
            artifacts=artifacts,
            completed_at=datetime.now(UTC),
        )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_version(root: Path, binary: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
        suffix = (
            "-dirty"
            if subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            ).stdout.strip()
            else ""
        )
        return result.stdout.strip()[:12] + suffix
    except (OSError, subprocess.SubprocessError):
        return f"sha256:{sha256_file(binary)[:12]}" if binary.is_file() else "missing"


def read_numeric_table(path: Path, minimum_columns: int) -> list[list[float]]:
    rows: list[list[float]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip() or line.lstrip().startswith(("#", '"')):
            continue
        try:
            row = [parse_fortran_number(value) for value in line.split()]
        except ValueError:
            continue
        if len(row) >= minimum_columns and all(math_is_finite(value) for value in row):
            rows.append(row)
    return rows


def math_is_finite(value: float) -> bool:
    return math.isfinite(value)
