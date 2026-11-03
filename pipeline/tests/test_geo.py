from observatorio.geo import PACKAGED_REFERENCE, MunicipioLocator, reference_path


def test_locator_assigns_points(locator):
    assert locator.locate([-74.0, -70.0, -77.0], [4.5, -4.0, 7.0]) == ["11001", "91001", None]


def test_packaged_reference_is_used_when_nothing_downloaded(tmp_path):
    assert reference_path(tmp_path) == PACKAGED_REFERENCE


def test_packaged_reference_locates_real_cities():
    loc = MunicipioLocator.from_geojson(PACKAGED_REFERENCE)
    assert len(loc.codes) >= 1100
    # Plaza de Bolívar (Bogotá), Parque Berrío (Medellín), Leticia
    assert loc.locate([-74.0760, -75.5684, -69.9406], [4.5981, 6.2500, -4.2153]) == ["11001", "05001", "91001"]
