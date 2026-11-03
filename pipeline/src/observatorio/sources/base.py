"""Contrato común de las fuentes de datos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import cached_property
from pathlib import Path

from ..geo import MunicipioLocator, reference_path
from ..http import HttpClient


@dataclass
class RunContext:
    data_dir: Path
    client: HttpClient
    now: datetime
    since: date | None = None  # recarga desde una fecha (backfill)
    force: bool = False
    cache: dict = field(default_factory=dict)  # datos compartidos entre fuentes en una ejecución

    @cached_property
    def locator(self) -> MunicipioLocator:
        return MunicipioLocator.from_geojson(reference_path(self.data_dir))


@dataclass
class RunResult:
    changed: bool
    rows_total: int
    rows_new: int = 0
    coverage: tuple[str | None, str | None] = (None, None)
    files: list[str] = field(default_factory=list)
    message: str = ""
    warning: bool = False  # funcionó con un respaldo; no cuenta como falla


class Source(ABC):
    """Una fuente sabe descargarse, validarse y escribirse en el directorio de datos."""

    id: str
    nombre: str
    entidad: str
    url: str
    licencia: str
    cadencia: str  # cada cuánto publica la entidad, no cada cuánto revisamos

    @abstractmethod
    def run(self, ctx: RunContext) -> RunResult: ...

    def __repr__(self) -> str:
        return f"<Source {self.id}>"
