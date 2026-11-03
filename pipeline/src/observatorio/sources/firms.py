"""Fuegos activos detectados por los satélites VIIRS (NASA FIRMS).

Los archivos abiertos de FIRMS cubren los últimos 7 días. El pipeline los
descarga a diario y acumula el histórico; los solapes se eliminan por llave.
"""

from __future__ import annotations

import io
from datetime import UTC

import polars as pl

from ..config import BBOX_COLOMBIA
from ..storage import read_dataset, upsert_partitioned
from .base import RunContext, RunResult, Source

BASE = "https://firms.modaps.eosdis.nasa.gov/data/active_fire"
FEEDS = {
    "Suomi NPP": f"{BASE}/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_South_America_7d.csv",
    "NOAA-20": f"{BASE}/noaa-20-viirs-c2/csv/J1_VIIRS_C2_South_America_7d.csv",
    "NOAA-21": f"{BASE}/noaa-21-viirs-c2/csv/J2_VIIRS_C2_South_America_7d.csv",
}
KEYS = ["satellite", "acq_datetime_utc", "lat", "lon"]
CONFIDENCE = {"l": "baja", "n": "nominal", "h": "alta"}


def parse(csv_text: str, satellite: str) -> pl.DataFrame:
    df = pl.read_csv(io.StringIO(csv_text), infer_schema_length=0)
    if df.is_empty():
        return df
    lo, la, hi, ha = BBOX_COLOMBIA
    return df.select(
        pl.lit(satellite).alias("satellite"),
        (pl.col("acq_date") + " " + pl.col("acq_time").str.zfill(4))
        .str.strptime(pl.Datetime("ms"), "%Y-%m-%d %H%M")
        .dt.replace_time_zone(str(UTC))
        .alias("acq_datetime_utc"),
        pl.col("latitude").cast(pl.Float64).round(5).alias("lat"),
        pl.col("longitude").cast(pl.Float64).round(5).alias("lon"),
        pl.col("frp").cast(pl.Float64).alias("frp_mw"),
        pl.col("bright_ti4").cast(pl.Float64).alias("bright_ti4_k"),
        pl.col("confidence").str.to_lowercase().replace(CONFIDENCE).alias("confidence"),
        pl.col("daynight").replace({"D": "día", "N": "noche"}).alias("day_night"),
        pl.col("version").alias("version"),
    ).filter(pl.col("lon").is_between(lo, hi) & pl.col("lat").is_between(la, ha))


class FirmsFuegos(Source):
    id = "firms-fuegos"
    nombre = "Fuegos activos (VIIRS)"
    entidad = "NASA FIRMS"
    url = "https://firms.modaps.eosdis.nasa.gov/"
    licencia = "Datos abiertos de la NASA; citar a NASA FIRMS"
    cadencia = "tiempo casi real"

    def run(self, ctx: RunContext) -> RunResult:
        frames, notes = [], []
        for sat, url in FEEDS.items():
            try:
                frames.append(parse(ctx.client.get_text(url), sat))
            except Exception as exc:  # un satélite caído no detiene a los demás
                notes.append(f"{sat}: {exc}")
        frames = [f for f in frames if not f.is_empty()]
        if not frames:
            raise RuntimeError("No se pudo leer ningún archivo de FIRMS. " + " | ".join(notes))
        df = pl.concat(frames)
        # Solo se guardan los fuegos dentro de un municipio colombiano.
        df = ctx.locator.add_column(df).filter(pl.col("cod_mpio").is_not_null())
        df = df.with_columns(pl.col("acq_datetime_utc").dt.strftime("%Y-%m").alias("month"))
        base = ctx.data_dir / "incendios" / "firms"
        stats = upsert_partitioned(df, base, keys=KEYS, partition_col="month", sort_by=KEYS)
        full = read_dataset(base)
        first, last = full["acq_datetime_utc"].min(), full["acq_datetime_utc"].max()
        return RunResult(
            changed=stats.changed,
            rows_total=full.height,
            rows_new=stats.rows_new,
            coverage=(first.date().isoformat(), last.date().isoformat()),
            files=[f"incendios/firms/{p}" for p in stats.partitions_written],
            message=f"{df.height} detecciones en Colombia en los últimos 7 días."
            + (" Avisos: " + " | ".join(notes) if notes else ""),
        )
