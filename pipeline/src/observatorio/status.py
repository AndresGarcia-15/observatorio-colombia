"""Manifiesto ``estado.json``: qué se revisó, cuándo cambió y qué cubre cada fuente.

La aplicación web lo lee para mostrar la frescura de cada dato.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


@dataclass
class SourceStatus:
    id: str
    nombre: str
    entidad: str
    url: str
    licencia: str
    cadencia: str
    estado: str = "pendiente"  # ok | sin_cambios | error | pendiente
    mensaje: str = ""
    ultima_revision: str | None = None
    ultimo_cambio: str | None = None
    filas: int | None = None
    filas_nuevas: int = 0
    cobertura: dict[str, str | None] = field(default_factory=lambda: {"desde": None, "hasta": None})
    archivos: list[str] = field(default_factory=list)


def load(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": SCHEMA_VERSION, "generado": None, "fuentes": {}}


def save(path: Path, manifest: dict[str, Any], now: datetime) -> None:
    manifest["version"] = SCHEMA_VERSION
    manifest["generado"] = now.isoformat(timespec="seconds")
    manifest["fuentes"] = dict(sorted(manifest["fuentes"].items()))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def previous(manifest: dict[str, Any], source_id: str) -> dict[str, Any]:
    return manifest["fuentes"].get(source_id, {})


def put(manifest: dict[str, Any], status: SourceStatus) -> None:
    manifest["fuentes"][status.id] = asdict(status)
