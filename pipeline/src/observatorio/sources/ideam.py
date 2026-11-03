"""Observaciones de las estaciones automáticas del IDEAM, resumidas por día.

Los conjuntos de datos.gov.co publican lecturas cada 1 a 60 minutos. El
resumen diario se calcula en el servidor (SoQL) para descargar poco.

Decisiones:
* Algunas estaciones reportan la misma variable con dos sensores; para cada
  estación y día se conserva el sensor con más lecturas.
* Los datos crudos traen sensores dañados (temperaturas fijas en 0 °C o de
  40 °C a 180 m de altura). No se borran: cada día lleva una columna ``qc``
  con ``ok`` o el motivo por el que es sospechoso. La web usa solo ``ok``.
* La ubicación y altitud de las estaciones vienen del Catálogo Nacional de
  Estaciones del IDEAM, no de las observaciones.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from ..storage import read_dataset, upsert_partitioned, write_table
from .base import RunContext, RunResult, Source

SODA = "https://www.datos.gov.co/resource/{dataset}.json"
CATALOG = "hp9r-jxuu"  # Catálogo Nacional de Estaciones del IDEAM
CHUNK_DAYS = 7
DEFAULT_HISTORY_DAYS = 60
LATE_DATA_DAYS = 3  # se vuelven a pedir los últimos días porque llegan lecturas tardías
SODA_LIMIT = 50000

# Temperatura media anual esperada según la altitud, ajustada con las normales
# 1991-2020 del IDEAM (362 estaciones, error típico 1,1 °C).
LAPSE_INTERCEPT_C = 28.5
LAPSE_PER_M = -0.00556
MAX_DEVIATION_C = 8.0
MAX_DAILY_RANGE_C = 25.0
MAX_DAILY_PRECIP_MM = 400.0

CATALOG_COLUMNS = [
    "codigo", "nombre", "categoria", "tecnologia", "estado", "departamento",
    "municipio", "latitud", "longitud", "altitud", "entidad",
]  # fmt: skip


def fetch_catalog(ctx: RunContext) -> pl.DataFrame:
    """Catálogo de estaciones; se descarga una sola vez por ejecución."""
    if "ideam_catalog" not in ctx.cache:
        rows = ctx.client.get_json(
            SODA.format(dataset=CATALOG),
            {"$select": ", ".join(CATALOG_COLUMNS), "$limit": str(SODA_LIMIT)},
        )
        ctx.cache["ideam_catalog"] = parse_catalog(rows)
    return ctx.cache["ideam_catalog"]


def parse_catalog(rows: list[dict]) -> pl.DataFrame:
    df = pl.DataFrame(rows, schema={c: pl.Utf8 for c in CATALOG_COLUMNS})
    return df.select(
        pl.col("codigo").alias("station_id"),
        pl.col("nombre").str.replace(r"\s*\[\d+\]\s*$", "").str.strip_chars().alias("name"),
        pl.col("categoria").alias("category"),
        pl.col("tecnologia").alias("technology"),
        pl.col("estado").alias("status"),
        pl.col("departamento").alias("department_name"),
        pl.col("municipio").alias("municipality_name"),
        pl.col("latitud").cast(pl.Float64, strict=False).alias("lat"),
        pl.col("longitud").cast(pl.Float64, strict=False).alias("lon"),
        pl.col("altitud").cast(pl.Float64, strict=False).alias("altitude_m"),
        pl.col("entidad").alias("operator"),
    ).unique(subset=["station_id"], keep="first", maintain_order=True)


class IdeamDaily(Source):
    """Fuente genérica: una variable del IDEAM resumida por estación y día."""

    dataset: str
    folder: str
    metrics: tuple[tuple[str, str], ...]  # (columna, agregación SoQL)
    valid_range: tuple[float, float]
    licencia = "CC BY-SA 4.0 (datos.gov.co)"
    entidad = "IDEAM"
    cadencia = "diaria (lecturas cada 1 a 60 minutos)"

    @property
    def url(self) -> str:  # type: ignore[override]
        return f"https://www.datos.gov.co/d/{self.dataset}"

    def daily_query(self, start: date, end: date) -> dict[str, str]:
        aggs = ", ".join(f"{soql} as {col}" for col, soql in self.metrics)
        lo, hi = self.valid_range
        return {
            "$select": f"codigoestacion, codigosensor, date_trunc_ymd(fechaobservacion) as dia, {aggs}, count(*) as n",
            "$where": f"fechaobservacion >= '{start}T00:00:00' and fechaobservacion < '{end}T00:00:00' "
            f"and valorobservado::number between {lo} and {hi}",
            "$group": "codigoestacion, codigosensor, dia",
            "$limit": str(SODA_LIMIT),
        }

    def parse_daily(self, rows: list[dict]) -> pl.DataFrame:
        cols = ["codigoestacion", "codigosensor", "dia", "n", *(c for c, _ in self.metrics)]
        df = pl.DataFrame(rows, schema={c: pl.Utf8 for c in cols})
        if df.is_empty():
            return df
        df = df.with_columns(
            pl.col("dia").str.slice(0, 10).str.to_date().alias("date"),
            pl.col("n").cast(pl.Int32),
            *[pl.col(c).cast(pl.Float64).round(2) for c, _ in self.metrics],
        )
        # Un sensor por estación y día: el que tiene más lecturas.
        df = df.sort(["codigoestacion", "date", "n", "codigosensor"], descending=[False, False, True, False]).unique(
            subset=["codigoestacion", "date"], keep="first", maintain_order=True
        )
        return df.select(
            pl.col("codigoestacion").alias("station_id"),
            "date",
            *[c for c, _ in self.metrics],
            pl.col("n").alias("n_obs"),
            pl.col("codigosensor").alias("sensor"),
        )

    def quality(self, df: pl.DataFrame, stations: pl.DataFrame) -> pl.DataFrame:
        """Agrega la columna ``qc``. Cada variable define sus reglas."""
        return df.with_columns(pl.lit("ok").alias("qc"))

    def run(self, ctx: RunContext) -> RunResult:
        base = ctx.data_dir / "clima" / self.folder
        existing = read_dataset(base)
        today = ctx.now.date()  # ctx.now está en hora de Colombia
        if ctx.since:
            start = ctx.since
        elif existing.is_empty():
            start = today - timedelta(days=DEFAULT_HISTORY_DAYS)
        else:
            start = existing["date"].max() - timedelta(days=LATE_DATA_DAYS)
        end = today  # se excluye el día en curso porque aún está incompleto
        if start >= end:
            return RunResult(changed=False, rows_total=existing.height, message="Sin días completos nuevos.")

        frames = []
        cursor = start
        while cursor < end:
            stop = min(cursor + timedelta(days=CHUNK_DAYS), end)
            rows = ctx.client.get_json(SODA.format(dataset=self.dataset), self.daily_query(cursor, stop))
            if len(rows) >= SODA_LIMIT:
                raise RuntimeError(f"Consulta truncada entre {cursor} y {stop}; reduce CHUNK_DAYS.")
            frames.append(self.parse_daily(rows))
            cursor = stop
        frames = [f for f in frames if not f.is_empty()]
        if not frames:
            return RunResult(changed=False, rows_total=existing.height, message=f"Sin lecturas entre {start} y {end}.")
        df = pl.concat(frames)

        catalog = fetch_catalog(ctx)
        stations = catalog.filter(pl.col("station_id").is_in(df["station_id"].unique().implode()))
        stations = ctx.locator.add_column(stations.filter(pl.col("lat").is_not_null()))
        df = self.quality(df, stations).with_columns(pl.col("date").dt.strftime("%Y-%m").alias("month"))

        stats = upsert_partitioned(
            df, base, keys=["station_id", "date"], partition_col="month", sort_by=["date", "station_id"]
        )
        files = [f"clima/{self.folder}/{p}" for p in stats.partitions_written]
        if write_table(stations, ctx.data_dir / "clima" / f"{self.folder}_estaciones.parquet", keys=["station_id"]):
            files.append(f"clima/{self.folder}_estaciones.parquet")

        full = read_dataset(base)
        suspicious = df.filter(pl.col("qc") != "ok").height
        return RunResult(
            changed=bool(files),
            rows_total=full.height,
            rows_new=stats.rows_new,
            coverage=(full["date"].min().isoformat(), full["date"].max().isoformat()),
            files=files,
            message=f"{df['station_id'].n_unique()} estaciones entre {start} y {end - timedelta(days=1)}; "
            f"{suspicious} de {df.height} días marcados como sospechosos.",
        )


class IdeamTemperatura(IdeamDaily):
    id = "ideam-temperatura"
    nombre = "Temperatura del aire, resumen diario por estación"
    dataset = "sbwg-7ju4"
    folder = "ideam_temperatura"
    valid_range = (-10, 46)
    metrics = (
        ("t_mean_c", "avg(valorobservado::number)"),
        ("t_min_c", "min(valorobservado::number)"),
        ("t_max_c", "max(valorobservado::number)"),
    )

    def quality(self, df: pl.DataFrame, stations: pl.DataFrame) -> pl.DataFrame:
        expected = LAPSE_INTERCEPT_C + LAPSE_PER_M * pl.col("altitude_m")
        return (
            df.join(stations.select("station_id", "altitude_m"), on="station_id", how="left")
            .with_columns(
                pl.when((pl.col("t_min_c") == 0) & (pl.col("t_max_c") == 0))
                .then(pl.lit("sensor_en_cero"))
                .when((pl.col("t_mean_c") - expected).abs() > MAX_DEVIATION_C)
                .then(pl.lit("no_coincide_con_altitud"))
                .when(pl.col("t_max_c") - pl.col("t_min_c") > MAX_DAILY_RANGE_C)
                .then(pl.lit("rango_diario_anormal"))
                .otherwise(pl.lit("ok"))
                .alias("qc")
            )
            .drop("altitude_m")
        )


class IdeamPrecipitacion(IdeamDaily):
    id = "ideam-precipitacion"
    nombre = "Precipitación, total diario por estación"
    dataset = "s54a-sgyg"
    folder = "ideam_precipitacion"
    valid_range = (0, 200)  # mm por lectura; descarta valores imposibles
    metrics = (
        ("precip_mm", "sum(valorobservado::number)"),
        ("precip_max_mm", "max(valorobservado::number)"),
    )

    def quality(self, df: pl.DataFrame, stations: pl.DataFrame) -> pl.DataFrame:
        return df.with_columns(
            pl.when(pl.col("precip_mm") > MAX_DAILY_PRECIP_MM)
            .then(pl.lit("acumulado_anormal"))
            .otherwise(pl.lit("ok"))
            .alias("qc")
        )
