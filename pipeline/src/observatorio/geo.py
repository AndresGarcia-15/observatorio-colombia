"""Asignación de puntos (sismos, fuegos, estaciones) a municipios del MGN."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import numpy as np
import polars as pl
import shapely
from shapely.geometry import shape

PACKAGED_REFERENCE = Path(__file__).parent / "reference" / "municipios_mgn2024.geojson.gz"


def reference_path(data_dir: Path) -> Path:
    """Capa descargada más reciente o, si no hay, la copia del MGN 2024 incluida en el paquete."""
    downloaded = data_dir / "referencia" / "municipios.geojson"
    return downloaded if downloaded.exists() else PACKAGED_REFERENCE


def read_geojson(path: Path) -> dict:
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return json.loads(raw.decode("utf-8"))


class MunicipioLocator:
    """Busca el código DIVIPOLA del municipio que contiene cada punto (lon, lat)."""

    def __init__(self, features: list[dict]) -> None:
        self.codes = np.array([f["properties"]["cod_mpio"] for f in features], dtype=object)
        self.geoms = [shape(f["geometry"]) for f in features]
        self.tree = shapely.STRtree(self.geoms)

    @classmethod
    def from_geojson(cls, path: Path) -> MunicipioLocator:
        return cls(read_geojson(path)["features"])

    def locate(self, lon: list[float] | np.ndarray, lat: list[float] | np.ndarray) -> list[str | None]:
        lon = np.asarray(lon, dtype=float)
        lat = np.asarray(lat, dtype=float)
        out: list[str | None] = [None] * len(lon)
        if len(lon) == 0:
            return out
        points = shapely.points(lon, lat)
        point_idx, poly_idx = self.tree.query(points, predicate="within")
        for p, g in zip(point_idx.tolist(), poly_idx.tolist(), strict=True):
            if out[p] is None:
                out[p] = self.codes[g]
        return out

    def add_column(self, df: pl.DataFrame, lon: str = "lon", lat: str = "lat", name: str = "cod_mpio") -> pl.DataFrame:
        codes = self.locate(df[lon].to_numpy(), df[lat].to_numpy())
        return df.with_columns(pl.Series(name, codes, dtype=pl.Utf8))
