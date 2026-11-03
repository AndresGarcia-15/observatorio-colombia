"""Línea de comandos: ``observatorio list | run | status``."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, datetime

from . import status as st
from .config import COT, data_dir
from .http import HttpClient
from .sources import BY_ID, REGISTRY, RunContext, Source

log = logging.getLogger("observatorio")


def run_sources(sources: list[Source], since: date | None, force: bool) -> int:
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "estado.json"
    manifest = st.load(manifest_path)
    now = datetime.now(COT)
    failures = 0
    with HttpClient() as client:
        ctx = RunContext(data_dir=root, client=client, now=now, since=since, force=force)
        for src in sources:
            prev = st.previous(manifest, src.id)
            s = st.SourceStatus(
                id=src.id,
                nombre=src.nombre,
                entidad=src.entidad,
                url=src.url,
                licencia=src.licencia,
                cadencia=src.cadencia,
                ultimo_cambio=prev.get("ultimo_cambio"),
                filas=prev.get("filas"),
                cobertura=prev.get("cobertura") or {"desde": None, "hasta": None},
            )
            t0 = time.monotonic()
            try:
                res = src.run(ctx)
            except Exception as exc:
                failures += 1
                s.estado, s.mensaje = "error", f"{type(exc).__name__}: {exc}"[:500]
                log.error("✗ %s: %s", src.id, s.mensaje)
            else:
                s.estado = "aviso" if res.warning else ("ok" if res.changed else "sin_cambios")
                s.mensaje, s.filas, s.filas_nuevas, s.archivos = res.message, res.rows_total, res.rows_new, res.files
                if res.coverage != (None, None):
                    s.cobertura = {"desde": res.coverage[0], "hasta": res.coverage[1]}
                if res.changed:
                    s.ultimo_cambio = now.isoformat(timespec="seconds")
                log.info(
                    "✓ %s: %s (%d filas, %d nuevas) en %.1f s",
                    src.id,
                    s.estado,
                    res.rows_total,
                    res.rows_new,
                    time.monotonic() - t0,
                )
            s.ultima_revision = now.isoformat(timespec="seconds")
            st.put(manifest, s)
            st.save(manifest_path, manifest, now)  # se guarda tras cada fuente por si algo falla después
    return failures


def cmd_list(_: argparse.Namespace) -> int:
    for s in REGISTRY:
        print(f"{s.id:22} {s.cadencia:38} {s.entidad}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    manifest = st.load(data_dir() / "estado.json")
    if not manifest["fuentes"]:
        print("Aún no hay estado. Ejecuta: observatorio run")
        return 0
    print(f"Generado: {manifest['generado']}")
    for f in manifest["fuentes"].values():
        cov = f["cobertura"]
        print(
            f"{f['id']:22} {f['estado']:12} filas={f['filas'] or 0:>8}  {cov['desde']} → {cov['hasta']}  {f['mensaje'][:80]}"
        )
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    unknown = [i for i in args.fuentes if i not in BY_ID]
    if unknown:
        print(f"Fuentes desconocidas: {', '.join(unknown)}. Usa 'observatorio list'.", file=sys.stderr)
        return 2
    chosen = [BY_ID[i] for i in args.fuentes] if args.fuentes else REGISTRY
    since = date.fromisoformat(args.desde) if args.desde else None
    failures = run_sources(chosen, since, args.force)
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="observatorio", description="Pipeline de datos del Observatorio Territorial Colombia"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="Lista las fuentes registradas").set_defaults(fn=cmd_list)
    sub.add_parser("status", help="Muestra el estado de cada fuente").set_defaults(fn=cmd_status)
    p_run = sub.add_parser("run", help="Actualiza las fuentes (todas si no se indica ninguna)")
    p_run.add_argument("fuentes", nargs="*", help="ids de las fuentes a actualizar")
    p_run.add_argument("--desde", help="Recarga desde esta fecha (AAAA-MM-DD)")
    p_run.add_argument("--force", action="store_true", help="Ignora la vigencia de capas de referencia")
    p_run.set_defaults(fn=cmd_run)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
