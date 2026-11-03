"""Configuración compartida del pipeline."""

from __future__ import annotations

import os
from datetime import timedelta, timezone
from pathlib import Path

REPO_URL = "https://github.com/AndresGarcia-15/observatorio-colombia"
USER_AGENT = f"observatorio-colombia/0.1 (+{REPO_URL})"

# Zona horaria oficial de Colombia (UTC-5, sin horario de verano).
COT = timezone(timedelta(hours=-5), name="COT")

# Caja que cubre el territorio continental, San Andrés y Providencia.
# (lon_min, lat_min, lon_max, lat_max)
BBOX_COLOMBIA = (-82.0, -4.3, -66.8, 13.5)


def data_dir() -> Path:
    """Directorio raíz de los datos. Se puede cambiar con la variable OBS_DATA_DIR."""
    default = Path(__file__).resolve().parents[3] / "data"
    return Path(os.environ.get("OBS_DATA_DIR", default)).resolve()


def in_bbox(lon: float, lat: float, bbox: tuple[float, float, float, float] = BBOX_COLOMBIA) -> bool:
    return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]
