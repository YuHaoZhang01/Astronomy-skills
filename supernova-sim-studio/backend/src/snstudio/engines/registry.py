from __future__ import annotations

from ..config import Settings
from .base import EngineAdapter
from .snec import SnecAdapter
from .stella import StellaAdapter


class EngineRegistry:
    def __init__(self, settings: Settings):
        self.settings = settings
        engines: list[EngineAdapter] = [
            SnecAdapter(settings.supersnec_root, supersnec=True),
            SnecAdapter(settings.snec_root, supersnec=False),
            StellaAdapter(settings.stella_root),
        ]
        self._engines = {engine.id: engine for engine in engines}

    def all(self) -> list[EngineAdapter]:
        return list(self._engines.values())

    def get(self, engine_id: str) -> EngineAdapter:
        try:
            return self._engines[engine_id]
        except KeyError as exc:
            raise KeyError(f"未知引擎：{engine_id}") from exc
