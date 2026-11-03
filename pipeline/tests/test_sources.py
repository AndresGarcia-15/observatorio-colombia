from datetime import date

import polars as pl

from observatorio.sources.firms import parse as parse_firms
from observatorio.sources.ideam import IdeamPrecipitacion, IdeamTemperatura, parse_catalog
from observatorio.sources.usgs import parse as parse_usgs
from observatorio.sources.usgs import validate as validate_usgs

# --- USGS -------------------------------------------------------------------


def quake(eid, lon, lat, mag, depth=10.0):
    return {
        "id": eid,
        "geometry": {"coordinates": [lon, lat, depth]},
        "properties": {
            "mag": mag,
            "time": 1_700_000_000_000,
            "updated": 1_700_000_100_000,
            "magType": "mww",
            "place": "Colombia",
            "status": "reviewed",
        },
    }


def test_usgs_parse_and_validate():
    fc = {"features": [quake("a", -74.0, 4.6, 5.1), quake("b", -60.0, 4.6, 6.0), quake("c", -74.0, 4.6, None)]}
    df = validate_usgs(parse_usgs(fc))
    assert df["event_id"].to_list() == ["a"]  # fuera de la caja y sin magnitud quedan fuera
    assert df.schema["time_utc"] == pl.Datetime("ms", "UTC")


def test_usgs_locates_municipio(locator):
    df = validate_usgs(parse_usgs({"features": [quake("a", -74.0, 4.6, 5.1), quake("b", -77.0, 7.0, 4.2)]}))
    assert locator.add_column(df)["cod_mpio"].to_list() == ["11001", None]


# --- FIRMS ------------------------------------------------------------------

FIRMS_CSV = """latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,confidence,version,bright_ti5,frp,daynight
4.50000,-74.00000,330.5,0.4,0.4,2026-11-02,0648,N,n,2.0NRT,290.1,5.3,N
-3.80000,-70.00000,340.1,0.4,0.4,2026-11-02,1812,N,h,2.0NRT,295.2,12.0,D
-20.00000,-60.00000,330.0,0.4,0.4,2026-11-02,1812,N,l,2.0NRT,290.0,1.0,D
"""


def test_firms_parse_filters_bbox_and_translates():
    df = parse_firms(FIRMS_CSV, "Suomi NPP")
    assert df.height == 2
    assert df["confidence"].to_list() == ["nominal", "alta"]
    assert df["day_night"].to_list() == ["noche", "día"]
    assert df["acq_datetime_utc"][0].hour == 6 and df["acq_datetime_utc"][0].minute == 48


# --- IDEAM ------------------------------------------------------------------


def test_ideam_keeps_sensor_with_more_readings():
    rows = [
        {
            "codigoestacion": "001",
            "codigosensor": "0068",
            "dia": "2026-11-01T00:00:00.000",
            "t_mean_c": "14.0",
            "t_min_c": "8",
            "t_max_c": "20",
            "n": "10",
        },
        {
            "codigoestacion": "001",
            "codigosensor": "0071",
            "dia": "2026-11-01T00:00:00.000",
            "t_mean_c": "14.5",
            "t_min_c": "8",
            "t_max_c": "21",
            "n": "24",
        },
        {
            "codigoestacion": "002",
            "codigosensor": "0071",
            "dia": "2026-11-01T00:00:00.000",
            "t_mean_c": "27.1",
            "t_min_c": "22",
            "t_max_c": "33",
            "n": "24",
        },
    ]
    df = IdeamTemperatura().parse_daily(rows)
    assert df.height == 2
    assert df.filter(pl.col("station_id") == "001")["sensor"].item() == "0071"
    assert df.columns == ["station_id", "date", "t_mean_c", "t_min_c", "t_max_c", "n_obs", "sensor"]


def test_ideam_query_excludes_impossible_values():
    q = IdeamPrecipitacion().daily_query(date(2026, 11, 1), date(2026, 11, 8))
    assert "between 0 and 200" in q["$where"]
    assert "sum(valorobservado::number) as precip_mm" in q["$select"]


def test_ideam_catalog_is_cleaned():
    rows = [
        {
            "codigo": "0011045010",
            "nombre": "AEROPUERTO EL CARAÑO [11045010]",
            "categoria": "Sinóptica",
            "tecnologia": "Automática",
            "estado": "Activa",
            "departamento": "Chocó",
            "municipio": "Quibdó",
            "latitud": "5.69",
            "longitud": "-76.64",
            "altitud": "53",
            "entidad": "IDEAM",
        }
    ]
    df = parse_catalog(rows)
    assert df["name"].item() == "AEROPUERTO EL CARAÑO"
    assert df["lat"].item() == 5.69 and df["altitude_m"].item() == 53


def temp_day(station, mean, tmin, tmax):
    return {"station_id": station, "date": date(2026, 11, 1), "t_mean_c": mean, "t_min_c": tmin, "t_max_c": tmax}


def test_temperature_quality_flags():
    stations = pl.DataFrame({"station_id": ["bog", "llano"], "altitude_m": [2550.0, 180.0]})
    df = pl.DataFrame(
        [
            temp_day("bog", 14.0, 8.0, 20.0),  # Bogotá normal
            temp_day("bog", 0.0, 0.0, 0.0),  # sensor pegado en cero
            temp_day("llano", 39.9, 30.0, 49.0),  # 40 °C de media a 180 m: no cuadra
            temp_day("llano", 27.0, 10.0, 40.0),  # oscilación de 30 °C en un día
        ]
    )
    qc = IdeamTemperatura().quality(df, stations)["qc"].to_list()
    assert qc == ["ok", "sensor_en_cero", "no_coincide_con_altitud", "rango_diario_anormal"]
