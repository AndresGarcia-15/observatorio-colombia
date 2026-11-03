"""Almacenamiento en Parquet particionado con actualización por llave (upsert).

Cada conjunto de datos vive en una carpeta con un archivo por partición, por
ejemplo ``clima/ideam_temperatura/2026-11.parquet``. Al actualizar solo se
reescriben las particiones que realmente cambiaron, lo que mantiene los
cambios diarios pequeños.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import polars as pl


@dataclass
class UpsertStats:
    rows_in: int = 0
    rows_new: int = 0
    rows_updated: int = 0
    partitions_written: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.partitions_written)


def write_parquet_atomic(df: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.write_parquet(tmp, compression="zstd", statistics=True)
    os.replace(tmp, path)


def upsert_partitioned(
    df: pl.DataFrame,
    base_dir: Path,
    keys: list[str],
    partition_col: str,
    sort_by: list[str] | None = None,
) -> UpsertStats:
    """Inserta o reemplaza filas por ``keys`` dentro de cada partición de ``partition_col``.

    La columna de partición debe ser texto (por ejemplo ``"2026-11"`` o ``"2026"``).
    Las filas nuevas ganan sobre las existentes con la misma llave.
    """
    stats = UpsertStats(rows_in=df.height)
    if df.is_empty():
        return stats
    base_dir.mkdir(parents=True, exist_ok=True)
    sort_by = sort_by or keys
    for (part,), chunk in df.group_by([partition_col], maintain_order=True):
        path = base_dir / f"{part}.parquet"
        chunk = chunk.drop(partition_col)
        if path.exists():
            old = pl.read_parquet(path)
            chunk = chunk.select(old.columns) if set(old.columns) == set(chunk.columns) else chunk
            old_keys = old.select(keys)
            n_existing = chunk.join(old_keys, on=keys, how="semi").height
            merged = pl.concat([old, chunk], how="diagonal_relaxed").unique(subset=keys, keep="last")
            merged = merged.sort(sort_by)
            if merged.equals(old.sort(sort_by)):
                continue
            stats.rows_new += chunk.height - n_existing
            # Filas que existían y cambiaron de valor.
            changed = chunk.join(old, on=chunk.columns, how="anti").join(old_keys, on=keys, how="semi")
            stats.rows_updated += changed.height
        else:
            merged = chunk.unique(subset=keys, keep="last").sort(sort_by)
            stats.rows_new += merged.height
        write_parquet_atomic(merged, path)
        stats.partitions_written.append(path.name)
    return stats


def read_dataset(base_dir: Path) -> pl.DataFrame:
    """Lee todas las particiones de un conjunto de datos; devuelve un DataFrame vacío si no hay."""
    files = sorted(base_dir.glob("*.parquet")) if base_dir.exists() else []
    if not files:
        return pl.DataFrame()
    return pl.concat([pl.read_parquet(f) for f in files], how="diagonal_relaxed")


def write_table(df: pl.DataFrame, path: Path, keys: list[str]) -> bool:
    """Escribe una tabla pequeña sin particiones (por ejemplo, un catálogo de estaciones).

    Combina con lo existente por ``keys`` y devuelve True si el archivo cambió.
    """
    if path.exists():
        old = pl.read_parquet(path)
        merged = pl.concat([old, df], how="diagonal_relaxed").unique(subset=keys, keep="last").sort(keys)
        if merged.equals(old.sort(keys)):
            return False
    else:
        merged = df.unique(subset=keys, keep="last").sort(keys)
    write_parquet_atomic(merged, path)
    return True
