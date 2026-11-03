import json

import observatorio.cli as cli
from observatorio.sources.base import RunResult, Source


class Ok(Source):
    id, nombre, entidad, url, licencia, cadencia = "ok", "Fuente ok", "Prueba", "https://x", "MIT", "diaria"

    def run(self, ctx):
        return RunResult(changed=True, rows_total=3, rows_new=3, coverage=("2026-01-01", "2026-01-03"))


class Boom(Ok):
    id = "boom"

    def run(self, ctx):
        raise ValueError("servicio caído")


def test_run_sources_records_status_and_continues_after_errors(data_dir):
    failures = cli.run_sources([Boom(), Ok()], since=None, force=False)
    manifest = json.loads((data_dir / "estado.json").read_text())
    assert failures == 1
    assert manifest["fuentes"]["boom"]["estado"] == "error"
    assert "servicio caído" in manifest["fuentes"]["boom"]["mensaje"]
    ok = manifest["fuentes"]["ok"]
    assert ok["estado"] == "ok" and ok["filas"] == 3
    assert ok["cobertura"] == {"desde": "2026-01-01", "hasta": "2026-01-03"}
    assert ok["ultimo_cambio"] == ok["ultima_revision"]


def test_error_keeps_last_known_coverage(data_dir):
    cli.run_sources([Ok()], since=None, force=False)

    class OkThenBoom(Ok):
        def run(self, ctx):
            raise RuntimeError("timeout")

    cli.run_sources([OkThenBoom()], since=None, force=False)
    entry = json.loads((data_dir / "estado.json").read_text())["fuentes"]["ok"]
    assert entry["estado"] == "error"
    assert entry["filas"] == 3 and entry["cobertura"]["hasta"] == "2026-01-03"


def test_unknown_source_returns_usage_error(data_dir, capsys):
    assert cli.main(["run", "no-existe"]) == 2
    assert "desconocidas" in capsys.readouterr().err


def test_warning_is_not_a_failure(data_dir):
    class Fallback(Ok):
        id = "fallback"

        def run(self, ctx):
            return RunResult(changed=False, rows_total=1, warning=True, message="se usó el respaldo")

    assert cli.run_sources([Fallback()], since=None, force=False) == 0
    entry = json.loads((data_dir / "estado.json").read_text())["fuentes"]["fallback"]
    assert entry["estado"] == "aviso"
