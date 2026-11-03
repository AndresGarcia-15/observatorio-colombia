# Hoja de ruta

El proyecto nació como un prototipo interactivo (v0) y se está reconstruyendo como un producto con datos que se actualizan solos. Cada fase deja algo funcionando y publicado.

Leyenda: ✅ hecho · 🔄 en curso · ⬜ pendiente

## Fase 0 · Prototipo (v0) ✅

- ✅ Tablero en un solo archivo HTML con D3 y Three.js: 9 secciones, más de 90 indicadores, mapa municipal, catastro 3D de Bogotá y modo reto.
- ✅ Publicado en GitHub Pages como referencia visual (`prototype/`). Sus datos quedaron congelados al 22 de octubre de 2026.

## Fase 1 · Base del repositorio 🔄

- ✅ Estructura del monorepo (`pipeline/`, `docs/`, `prototype/`; `web/` se llena en la fase 3).
- ✅ Documentación: README, arquitectura, catálogo de fuentes, diccionario de datos.
- ✅ Licencia MIT para el código; los datos conservan la licencia de cada entidad.
- ✅ CI: lint (ruff) y pruebas (pytest) en cada push.
- ⬜ Activar GitHub Pages (Settings → Pages → Source: GitHub Actions).
- ⬜ Captura animada (GIF) del tablero para el README.

## Fase 2 · Pipeline de datos 🔄

Actualización diaria automática con GitHub Actions. Los datos se publican en la rama `data` como Parquet.

- ✅ Núcleo: cliente HTTP con reintentos, almacenamiento Parquet particionado con *upsert*, manifiesto `estado.json`.
- ✅ Capa de referencia: límites municipales del MGN (DANE, con respaldo automático en la copia del IGAC si el DANE no responde).
- ✅ IDEAM temperatura y precipitación diarias por estación, con control de calidad.
- ✅ NASA FIRMS: fuegos activos VIIRS (3 satélites), ubicados por municipio.
- ✅ USGS: sismos M≥4 desde 1973, con revisiones de los últimos 30 días.
- ⬜ Recarga histórica del IDEAM desde 2020 (`--desde 2020-01-01`).
- ⬜ Policía Nacional: homicidios, violencia intrafamiliar y masacres (mensual).
- ⬜ UNGRD: emergencias por tipo de evento.
- ⬜ Fuentes anuales del prototipo: censo 2018, IPM, NBI, déficit habitacional, pobreza, PIB, educación, FURAG, CNMH, coca, agricultura.
- ⬜ DANE: proyecciones de población municipal como denominador de las tasas.
- ⬜ SGC: fallas, volcanes, amenaza sísmica NSR-10 (capas estáticas) y catálogo nacional de sismos.
- ⬜ Catastro de Bogotá por manzana (anual) y generación de teselas vectoriales (PMTiles).
- ⬜ Registraduría: resultados oficiales del escrutinio 2026.
- ⬜ Aviso automático (issue en GitHub) cuando una fuente falle dos días seguidos.

## Fase 3 · Aplicación web ⬜

`web/`: React + TypeScript + Vite. Lee directamente los Parquet publicados.

- ⬜ Esqueleto, sistema de diseño (tokens claro/oscuro) y navegación por secciones.
- ⬜ DuckDB-WASM para consultar los Parquet en el navegador y filtrar de forma cruzada.
- ⬜ Mapa con MapLibre GL: coropletas municipales, capas de puntos (sismos, fuegos, estaciones) y líneas (fallas).
- ⬜ Secciones migradas del prototipo: panorama, población, seguridad, economía, vivienda, clima, riesgos, política.
- ⬜ Página «Estado de los datos» a partir de `estado.json`.
- ⬜ Despliegue diario: el sitio se reconstruye cuando cambian los datos.

## Fase 4 · 3D y modo reto ⬜

- ⬜ Catastro 3D de Bogotá con deck.gl (manzanas extruidas por pisos, avalúo o valor del suelo).
- ⬜ Municipios como prismas con dos indicadores (altura y color).
- ⬜ Modo reto: trivia, «adivina cómo sigue la serie» y juego de geografía, con puntaje local.

## Fase 5 · Calidad y presentación ⬜

- ⬜ Pruebas end-to-end con Playwright y presupuesto de rendimiento con Lighthouse CI.
- ⬜ Accesibilidad (WCAG 2.1 AA): teclado, contraste, lectores de pantalla.
- ⬜ Dominio propio y vista previa para redes sociales (Open Graph).
- ⬜ Analista con IA (opcional, requiere presupuesto para la API).
