from datetime import date

import polars as pl

from observatorio.storage import read_dataset, upsert_partitioned, write_table


def frame(rows):
    return pl.DataFrame(rows, schema={"id": pl.Utf8, "d": pl.Date, "v": pl.Float64, "part": pl.Utf8}, orient="row")


def test_upsert_writes_one_file_per_partition(tmp_path):
    df = frame([("a", date(2026, 1, 1), 1.0, "2026-01"), ("b", date(2026, 2, 1), 2.0, "2026-02")])
    stats = upsert_partitioned(df, tmp_path, keys=["id"], partition_col="part")
    assert stats.rows_new == 2
    assert sorted(p.name for p in tmp_path.glob("*.parquet")) == ["2026-01.parquet", "2026-02.parquet"]
    assert "part" not in read_dataset(tmp_path).columns


def test_upsert_is_idempotent(tmp_path):
    df = frame([("a", date(2026, 1, 1), 1.0, "2026-01")])
    upsert_partitioned(df, tmp_path, keys=["id"], partition_col="part")
    stats = upsert_partitioned(df, tmp_path, keys=["id"], partition_col="part")
    assert not stats.changed
    assert stats.rows_new == 0


def test_upsert_replaces_changed_rows_and_adds_new(tmp_path):
    upsert_partitioned(frame([("a", date(2026, 1, 1), 1.0, "2026-01")]), tmp_path, keys=["id"], partition_col="part")
    stats = upsert_partitioned(
        frame([("a", date(2026, 1, 1), 9.0, "2026-01"), ("c", date(2026, 1, 3), 3.0, "2026-01")]),
        tmp_path,
        keys=["id"],
        partition_col="part",
    )
    out = read_dataset(tmp_path).sort("id")
    assert stats.rows_new == 1
    assert stats.rows_updated == 1
    assert out["v"].to_list() == [9.0, 3.0]


def test_read_dataset_empty_dir(tmp_path):
    assert read_dataset(tmp_path / "no-existe").is_empty()


def test_write_table_reports_changes(tmp_path):
    path = tmp_path / "t.parquet"
    df = pl.DataFrame({"k": ["x"], "v": [1]})
    assert write_table(df, path, keys=["k"]) is True
    assert write_table(df, path, keys=["k"]) is False
    assert write_table(pl.DataFrame({"k": ["x"], "v": [2]}), path, keys=["k"]) is True
