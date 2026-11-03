"""Límites municipales del Marco Geoestadístico Nacional (DANE).

Es la capa de referencia que usan las demás fuentes para asignar cada punto a
un municipio. El paquete incluye una copia del MGN 2024; esta fuente intenta
renovarla desde el DANE y, si no responde, desde la copia que publica el IGAC.
El geoportal del DANE rechaza conexiones desde centros de datos en la nube,
así que en GitHub Actions lo normal es que la renovación use el IGAC.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from ..geo import read_geojson, reference_path
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
PAGE = 250
PAGE_TIMEOUT = 240.0  # el servicio del IGAC tarda cerca de un minuto por página
MAX_AGE = timedelta(days=30)
RETRY_AFTER_FAILURE = timedelta(days=7)
EXPECTED_MIN = 1100  # Colombia tiene 1.122 municipios y áreas no municipalizadas


class MgnMunicipios(Source):
    id = "mgn-municipios"
    nombre = "Límites municipales (Marco Geoestadístico Nacional)"
    entidad = "DANE"
    url = "https://geoportal.dane.gov.co/servicios/descarga-y-metadatos/datos-geoestadisticos/"
    licencia = "Uso libre con atribución al DANE"
    cadencia = "anual"

    def run(self, ctx: RunContext) -> RunResult:
        """Intenta renovar la capa cada 30 días. Si los servicios fallan, se sigue usando la
        copia vigente (la descargada antes o la del MGN 2024 incluida en el paquete): las
        demás fuentes nunca dependen de que esta descarga funcione."""
        path = ctx.data_dir / "referencia" / "municipios.geojson"
        attempt_path = ctx.data_dir / "referencia" / "intento.json"
        ref = reference_path(ctx.data_dir)
        current = read_geojson(ref)
        n_current = len(current["features"])
        downloaded = datetime.fromisoformat(current.get("descargado", "2000-01-01T00:00:00+00:00"))
        if not ctx.force:
            if ctx.now - downloaded < MAX_AGE:
                return RunResult(
                    changed=False, rows_total=n_current, message=f"Capa vigente ({current.get('fuente')})."
                )
            if attempt_path.exists():
                last = datetime.fromisoformat(json.loads(attempt_path.read_text(encoding="utf-8"))["ultimo_intento"])
                if ctx.now - last < RETRY_AFTER_FAILURE:
                    return RunResult(
                        changed=False,
                        rows_total=n_current,
                        warning=True,
                        message=f"El último intento falló; se reintenta tras {RETRY_AFTER_FAILURE.days} días. "
                        f"Se usa {current.get('fuente')}.",
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
            changed = current.get("features") != features
            data = {
                "type": "FeatureCollection",
                "fuente": ep["nombre"],
                "descargado": ctx.now.isoformat(timespec="seconds"),
                "features": features,
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            attempt_path.unlink(missing_ok=True)
            return RunResult(
                changed=changed,
                rows_total=len(features),
                files=["referencia/municipios.geojson"],
                message=f"Capa renovada desde {ep['nombre']}.",
            )
        attempt_path.parent.mkdir(parents=True, exist_ok=True)
        attempt_path.write_text(json.dumps({"ultimo_intento": ctx.now.isoformat(timespec="seconds")}), encoding="utf-8")
        return RunResult(
            changed=False,
            rows_total=n_current,
            warning=True,
            message=f"No se pudo renovar; se usa {current.get('fuente')}. " + " | ".join(errors),
        )

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
            page = ctx.client.get_json(ep["url"], params, timeout=PAGE_TIMEOUT)
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
