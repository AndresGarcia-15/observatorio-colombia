"""Límites municipales del Marco Geoestadístico Nacional (DANE).

Es la capa de referencia que usan las demás fuentes para asignar cada punto a
un municipio. Se intenta primero el servicio del DANE y, si no responde, la
copia del MGN que publica el IGAC.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from .base import RunContext, RunResult, Source

log = logging.getLogger(__name__)

ENDPOINTS = [
    {
        "nombre": "DANE MGN 2024",
        "url": "https://geoportal.dane.gov.co/mparcgis/rest/services/MGN2024/Serv_CapasMGN_2024/FeatureServer/317/query",
        "campos": {
            "cod_mpio": "mpio_cdpmp",
            "cod_dpto": "dpto_ccdgo",
            "municipio": "mpio_cnmbr",
            "departamento": "dpto_cnmbr",
            "area_km2": "mpio_narea",
        },
        "orden": "mpio_cdpmp",
    },
    {
        "nombre": "IGAC, copia del MGN (vigencia 2021)",
        "url": "https://mapas.igac.gov.co/server/rest/services/ObservatorioInmobiliario/MunicipiosOIC/FeatureServer/1/query",
        "campos": {
            "cod_mpio": "mpio_cdpmp",
            "cod_dpto": "dpto_ccdgo",
            "municipio": "mpio_cnmbr",
            "departamento": "dpto_cnmbr",
            "area_km2": "mpio_narea",
        },
        "orden": "mpio_cdpmp",
    },
]
PAGE = 500
MAX_AGE = timedelta(days=30)
EXPECTED_MIN = 1100  # Colombia tiene 1.122 municipios y áreas no municipalizadas


class MgnMunicipios(Source):
    id = "mgn-municipios"
    nombre = "Límites municipales (Marco Geoestadístico Nacional)"
    entidad = "DANE"
    url = "https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/"
    licencia = "Uso libre con atribución al DANE"
    cadencia = "anual"

    def run(self, ctx: RunContext) -> RunResult:
        path = ctx.data_dir / "referencia" / "municipios.geojson"
        if path.exists() and not ctx.force:
            # La fecha se guarda dentro del archivo: las fechas del sistema de archivos
            # no sobreviven al ciclo de git en GitHub Actions.
            current = json.loads(path.read_text(encoding="utf-8"))
            downloaded = datetime.fromisoformat(current.get("descargado", "2000-01-01T00:00:00+00:00"))
            if ctx.now - downloaded < MAX_AGE:
                return RunResult(
                    changed=False, rows_total=len(current["features"]), message="Capa vigente; se revisa cada 30 días."
                )
        errors = []
        for ep in ENDPOINTS:
            try:
                features = self._download(ctx, ep)
            except Exception as exc:  # una caída del servicio no debe tumbar el pipeline
                log.warning("No se pudo descargar %s: %s", ep["nombre"], exc)
                errors.append(f"{ep['nombre']}: {exc}")
                continue
            if len(features) < EXPECTED_MIN:
                errors.append(f"{ep['nombre']}: solo {len(features)} municipios")
                continue
            old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            changed = old is None or old.get("features") != features
            data = {
                "type": "FeatureCollection",
                "fuente": ep["nombre"],
                "descargado": ctx.now.isoformat(timespec="seconds"),
                "features": features,
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            return RunResult(
                changed=changed,
                rows_total=len(features),
                rows_new=len(features) if old is None else 0,
                files=["referencia/municipios.geojson"],
                message=f"Fuente: {ep['nombre']}",
            )
        if path.exists():
            n = len(json.loads(path.read_text(encoding="utf-8"))["features"])
            return RunResult(
                changed=False,
                rows_total=n,
                message="Servicios caídos; se conserva la capa anterior. " + " | ".join(errors),
            )
        raise RuntimeError("No se pudo obtener la capa de municipios. " + " | ".join(errors))

    @staticmethod
    def _download(ctx: RunContext, ep: dict) -> list[dict]:
        out: list[dict] = []
        offset = 0
        fields = ep["campos"]
        while True:
            params = {
                "where": "1=1",
                "outFields": ",".join(fields.values()),
                "outSR": 4326,
                "maxAllowableOffset": 0.0008,  # ~90 m: suficiente para ubicar puntos
                "geometryPrecision": 5,
                "orderByFields": ep["orden"],
                "resultOffset": offset,
                "resultRecordCount": PAGE,
                "f": "geojson",
            }
            page = ctx.client.get_json(ep["url"], params)
            feats = page.get("features", [])
            for f in feats:
                p = f["properties"]
                props = {k: p.get(v) for k, v in fields.items()}
                props["cod_mpio"] = str(props["cod_mpio"]).zfill(5)
                props["cod_dpto"] = str(props["cod_dpto"]).zfill(2)
                props["area_km2"] = round(float(props["area_km2"] or 0), 2)
                if f.get("geometry"):
                    out.append({"type": "Feature", "properties": props, "geometry": f["geometry"]})
            if len(feats) < PAGE:
                break
            offset += PAGE
        return out
