"""Sismos de magnitud 4 o más en Colombia y su entorno (catálogo ComCat del USGS)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl

from ..config import BBOX_COLOMBIA
from ..storage import read_dataset, upsert_partitioned
from .base import RunContext, RunResult, Source

API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
MIN_MAG = 4.0
FIRST_YEAR = 1973
REVISION_WINDOW = timedelta(days=30)  # el USGS revisa magnitudes y ubicaciones días después

SCHEMA = {
    "event_id": pl.Utf8,
    "time_utc": pl.Datetime("ms", "UTC"),
    "lon": pl.Float64,
    "lat": pl.Float64,
    "depth_km": pl.Float64,
    "mag": pl.Float64,
    "mag_type": pl.Utf8,
    "place": pl.Utf8,
    "status": pl.Utf8,
    "updated_utc": pl.Datetime("ms", "UTC"),
}


def parse(geojson: dict) -> pl.DataFrame:
    rows = []
    for f in geojson.get("features", []):
        p, (lon, lat, depth) = f["properties"], f["geometry"]["coordinates"][:3]
        if p.get("mag") is None or p.get("time") is None:
            continue
        rows.append(
            {
                "event_id": f["id"],
                "time_utc": datetime.fromtimestamp(p["time"] / 1000, tz=UTC),
                "lon": float(lon),
                "lat": float(lat),
                "depth_km": float(depth) if depth is not None else None,
                "mag": float(p["mag"]),
                "mag_type": p.get("magType"),
                "place": p.get("place"),
                "status": p.get("status"),
                "updated_utc": datetime.fromtimestamp((p.get("updated") or p["time"]) / 1000, tz=UTC),
            }
        )
    return pl.DataFrame(rows, schema=SCHEMA)


def validate(df: pl.DataFrame) -> pl.DataFrame:
    lo, la, hi, ha = BBOX_COLOMBIA
    return df.filter(
        pl.col("lon").is_between(lo, hi)
        & pl.col("lat").is_between(la, ha)
        & pl.col("mag").is_between(0, 10)
        & (pl.col("depth_km").is_null() | pl.col("depth_km").is_between(-5, 800))
    )


class UsgsSismos(Source):
    id = "usgs-sismos"
    nombre = "Sismos de magnitud 4 o más"
    entidad = "Servicio Geológico de Estados Unidos (USGS)"
    url = "https://earthquake.usgs.gov/earthquakes/search/"
    licencia = "Dominio público (USGS)"
    cadencia = "tiempo real"

    def run(self, ctx: RunContext) -> RunResult:
        base = ctx.data_dir / "sismos" / "usgs"
        existing = read_dataset(base)
        if ctx.since:
            start = datetime(ctx.since.year, ctx.since.month, ctx.since.day, tzinfo=UTC)
        elif existing.is_empty():
            start = datetime(FIRST_YEAR, 1, 1, tzinfo=UTC)
        else:
            start = existing["time_utc"].max() - REVISION_WINDOW
        lo, la, hi, ha = BBOX_COLOMBIA
        params = {
            "format": "geojson",
            "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
            "endtime": ctx.now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S"),
            "minlatitude": la,
            "maxlatitude": ha,
            "minlongitude": lo,
            "maxlongitude": hi,
            "minmagnitude": MIN_MAG,
            "orderby": "time-asc",
            "limit": 20000,
        }
        df = validate(parse(ctx.client.get_json(API, params)))
        if df.height >= 20000:
            raise RuntimeError("La consulta llegó al tope de 20.000 eventos; divide el rango de fechas.")
        df = ctx.locator.add_column(df).with_columns(pl.col("time_utc").dt.year().cast(pl.Utf8).alias("year"))
        stats = upsert_partitioned(df, base, keys=["event_id"], partition_col="year", sort_by=["time_utc", "event_id"])
        full = read_dataset(base)
        return RunResult(
            changed=stats.changed,
            rows_total=full.height,
            rows_new=stats.rows_new,
            coverage=(full["time_utc"].min().date().isoformat(), full["time_utc"].max().date().isoformat()),
            files=[f"sismos/usgs/{p}" for p in stats.partitions_written],
            message=f"{df.height} eventos consultados desde {start.date()}; {stats.rows_updated} revisados por el USGS.",
        )
