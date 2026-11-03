# Catálogo de fuentes

El pipeline revisa todas las fuentes cada día, pero cada entidad publica a su propio ritmo. La columna «Ritmo de la entidad» indica con qué frecuencia cambian realmente los datos.

## En el pipeline

| Id | Datos | Entidad | Ritmo de la entidad | Desde | Licencia |
|---|---|---|---|---|---|
| `mgn-municipios` | Límites municipales (1.122) | DANE, respaldo IGAC | anual | MGN 2024 | Uso libre con atribución |
| `ideam-temperatura` | Temperatura media, mínima y máxima diaria por estación | IDEAM ([sbwg-7ju4](https://www.datos.gov.co/d/sbwg-7ju4)) | diario | últimos 60 días (ampliable) | CC BY-SA 4.0 |
| `ideam-precipitacion` | Lluvia total diaria por estación | IDEAM ([s54a-sgyg](https://www.datos.gov.co/d/s54a-sgyg)) | diario | últimos 60 días (ampliable) | CC BY-SA 4.0 |
| `firms-fuegos` | Fuegos activos VIIRS (Suomi NPP, NOAA-20, NOAA-21) | [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | varias veces al día | se acumula desde la primera ejecución | Datos abiertos de la NASA, con cita |
| `usgs-sismos` | Sismos M≥4 en Colombia y alrededores | [USGS ComCat](https://earthquake.usgs.gov/earthquakes/search/) | tiempo real | 1973 | Dominio público |

El catálogo de estaciones del IDEAM ([hp9r-jxuu](https://www.datos.gov.co/d/hp9r-jxuu)) aporta la ubicación y altitud de cada estación.

## Por incorporar (usadas en el prototipo)

| Datos | Entidad | Ritmo | Notas |
|---|---|---|---|
| Homicidios, violencia intrafamiliar, masacres | Policía Nacional (datos.gov.co) | mensual, 3 a 4 semanas de rezago | |
| Emergencias por tipo | UNGRD (datos.gov.co) | irregular | Los códigos DIVIPOLA vienen incompletos; se requiere cruce por nombre |
| Hechos del conflicto armado | Centro Nacional de Memoria Histórica | irregular | |
| Censo 2018, IPM, NBI, déficit habitacional | DANE (Geoportal) | fijo o anual | |
| Pobreza monetaria y Gini | DANE (GEIH) | anual | |
| PIB departamental | DANE (cuentas departamentales) | anual | |
| Cobertura y deserción escolar | Ministerio de Educación | anual | |
| Afiliación al sistema de salud | Ministerio de Salud | mensual | |
| Internet fijo | MinTIC | trimestral | |
| Saber 11 | ICFES | anual | |
| Desempeño institucional y PDET | Función Pública (FURAG) | anual | |
| Cultivos de coca | SIMCI / ODC | anual | La serie abierta llega a 2019 |
| Agricultura | Evaluaciones Agropecuarias Municipales | anual | La serie abierta llega a 2018 |
| Fallas, volcanes, amenaza sísmica | Servicio Geológico Colombiano | fijo | |
| Catastro por manzana de Bogotá | UAECD | anual | Pisos, avalúo, valor del suelo y uso |
| Calidad del aire (PM2,5) | IDEAM, SISAIRE | anual | |
| Elecciones 2026 | Registraduría | fijo | El prototipo usó el preconteo publicado por prensa |
| Proyecciones de población | DANE | anual | Para calcular tasas con la población actual |

## Atribución

Si reutilizas estos datos, cita a la entidad original. Los conjuntos de datos.gov.co se publican con CC BY-SA 4.0, que exige atribuir y compartir las obras derivadas con la misma licencia. Las detecciones de fuego deben citar a NASA FIRMS (LANCE). Los datos del USGS son de dominio público.
