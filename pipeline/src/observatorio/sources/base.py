"""Contrato común de las fuentes de datos."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import cached_property
from pathlib import Path

from ..geo import MunicipioLocator
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
        path = self.data_dir / "referencia" / "municipios.geojson"
        if not path.exists():
            raise RuntimeError("Falta la capa de municipios. Ejecuta primero la fuente 'mgn-municipios'.")
        return MunicipioLocator.from_geojson(path)


@dataclass
class RunResult:
    changed: bool
    rows_total: int
    rows_new: int = 0
    coverage: tuple[str | None, str | None] = (None, None)
    files: list[str] = field(default_factory=list)
    message: str = ""


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
