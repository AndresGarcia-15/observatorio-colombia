"""Asignación de puntos (sismos, fuegos, estaciones) a municipios del MGN."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl
import shapely
from shapely.geometry import shape


class MunicipioLocator:
    """Busca el código DIVIPOLA del municipio que contiene cada punto (lon, lat)."""

    def __init__(self, features: list[dict]) -> None:
        self.codes = np.array([f["properties"]["cod_mpio"] for f in features], dtype=object)
        self.geoms = [shape(f["geometry"]) for f in features]
        self.tree = shapely.STRtree(self.geoms)

    @classmethod
    def from_geojson(cls, path: Path) -> MunicipioLocator:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(data["features"])

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
