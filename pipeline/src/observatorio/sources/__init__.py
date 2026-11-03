"""Registro de fuentes. El orden importa: la capa de municipios va primero."""

from .base import RunContext, RunResult, Source
from .firms import FirmsFuegos
from .ideam import IdeamPrecipitacion, IdeamTemperatura
from .mgn import MgnMunicipios
from .usgs import UsgsSismos

REGISTRY: list[Source] = [
    MgnMunicipios(),
    IdeamTemperatura(),
    IdeamPrecipitacion(),
    FirmsFuegos(),
    UsgsSismos(),
]
BY_ID = {s.id: s for s in REGISTRY}

__all__ = ["BY_ID", "REGISTRY", "RunContext", "RunResult", "Source"]
