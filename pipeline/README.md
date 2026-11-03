# Pipeline de datos

Descarga, valida y normaliza las fuentes abiertas del Observatorio Territorial Colombia. Cada fuente es un módulo en `src/observatorio/sources/` y escribe archivos Parquet en el directorio de datos (`OBS_DATA_DIR`, por defecto `../data`).

```bash
uv sync                                  # instala dependencias
uv run observatorio list                 # fuentes registradas
uv run observatorio run                  # actualiza todas las fuentes
uv run observatorio run usgs-sismos      # actualiza una sola
uv run observatorio run ideam-temperatura --desde 2025-01-01   # recarga histórica
uv run observatorio status               # estado de cada fuente
uv run pytest                            # pruebas
```

Consulta [`docs/ARQUITECTURA.md`](../docs/ARQUITECTURA.md) para el diseño y [`docs/FUENTES.md`](../docs/FUENTES.md) para el catálogo de fuentes.
