import json
from pathlib import Path

import pytest

from observatorio.geo import MunicipioLocator


def square(x0: float, y0: float, size: float = 1.0) -> dict:
    ring = [[x0, y0], [x0 + size, y0], [x0 + size, y0 + size], [x0, y0 + size], [x0, y0]]
    return {"type": "Polygon", "coordinates": [ring]}


@pytest.fixture
def municipios() -> list[dict]:
    """Dos municipios ficticios: Bogotá en (-74.5..-73.5, 4..5) y Leticia en (-70.5..-69.5, -4.3..-3.3)."""
    return [
        {"type": "Feature", "properties": {"cod_mpio": "11001"}, "geometry": square(-74.5, 4.0)},
        {"type": "Feature", "properties": {"cod_mpio": "91001"}, "geometry": square(-70.5, -4.3)},
    ]


@pytest.fixture
def locator(municipios) -> MunicipioLocator:
    return MunicipioLocator(municipios)


@pytest.fixture
def data_dir(tmp_path: Path, municipios, monkeypatch) -> Path:
    ref = tmp_path / "referencia"
    ref.mkdir()
    (ref / "municipios.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "descargado": "2099-01-01T00:00:00+00:00", "features": municipios})
    )
    monkeypatch.setenv("OBS_DATA_DIR", str(tmp_path))
    return tmp_path
