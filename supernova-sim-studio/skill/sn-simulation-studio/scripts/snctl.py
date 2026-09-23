#!/usr/bin/env python3
"""Locate and execute the deterministic Supernova Simulation Studio client."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def locate() -> str:
    configured = os.environ.get("SNSTUDIO_CLI")
    candidates = [
        configured,
        shutil.which("snctl"),
        "/Users/zyh/Desktop/SNfitting-skill/supernova-sim-studio/snctl",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise SystemExit(
        "找不到 snctl。请设置 SNSTUDIO_CLI，或从项目目录运行 ./snstudio install-skill。"
    )


if __name__ == "__main__":
    executable = locate()
    os.execv(executable, [executable, *sys.argv[1:]])
