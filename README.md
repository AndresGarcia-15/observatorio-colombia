# Datos del Observatorio Territorial Colombia

Esta rama la genera automáticamente el workflow «Pipeline de datos» del repositorio [AndresGarcia-15/observatorio-colombia](https://github.com/AndresGarcia-15/observatorio-colombia). No la edites a mano: se reemplaza cada día.

## Estructura

```
estado.json                               estado, cobertura y última actualización de cada fuente
referencia/municipios.geojson             límites municipales del MGN (códigos DIVIPOLA)
clima/ideam_temperatura/AAAA-MM.parquet   temperatura diaria por estación
clima/ideam_temperatura_estaciones.parquet
clima/ideam_precipitacion/AAAA-MM.parquet lluvia diaria por estación
clima/ideam_precipitacion_estaciones.parquet
incendios/firms/AAAA-MM.parquet           fuegos activos VIIRS
sismos/usgs/AAAA.parquet                  sismos M≥4
```

Para leer un conjunto completo con DuckDB:

```sql
SELECT * FROM 'clima/ideam_temperatura/*.parquet' WHERE qc = 'ok';
```

## Diccionario

### `clima/ideam_temperatura`

| Columna | Tipo | Descripción |
|---|---|---|
| `station_id` | texto | Código de la estación del IDEAM |
| `date` | fecha | Día en hora de Colombia |
| `t_mean_c`, `t_min_c`, `t_max_c` | decimal | Temperatura media, mínima y máxima del día (°C) |
| `n_obs` | entero | Lecturas usadas (24 si es horaria, 144 si es cada 10 minutos) |
| `sensor` | texto | Código del sensor usado |
| `qc` | texto | `ok` o el motivo por el que el día es sospechoso (ver docs/ARQUITECTURA.md) |

### `clima/ideam_precipitacion`

Igual que la temperatura, con `precip_mm` (lluvia total del día) y `precip_max_mm` (mayor lectura individual).

### `clima/*_estaciones.parquet`

`station_id`, `name`, `category`, `technology`, `status`, `department_name`, `municipality_name`, `lat`, `lon`, `altitude_m`, `operator` y `cod_mpio` (municipio según el MGN).

### `incendios/firms`

| Columna | Descripción |
|---|---|
| `satellite` | Suomi NPP, NOAA-20 o NOAA-21 |
| `acq_datetime_utc` | Fecha y hora del paso del satélite (UTC) |
| `lat`, `lon` | Centro del píxel de 375 m |
| `frp_mw` | Potencia radiativa del fuego (megavatios) |
| `bright_ti4_k` | Temperatura de brillo del canal I4 (kelvin) |
| `confidence` | baja, nominal o alta |
| `day_night` | día o noche |
| `cod_mpio` | Municipio según el MGN |

### `sismos/usgs`

`event_id`, `time_utc`, `lon`, `lat`, `depth_km`, `mag`, `mag_type`, `place`, `status` (automatic o reviewed), `updated_utc` y `cod_mpio` (vacío si el epicentro está en el mar o fuera de Colombia).
