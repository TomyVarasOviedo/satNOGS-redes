# Minuta — Planificación del Proyecto Final de Redes de Datos II

- **Fecha:** 01/08/2026
- **Tema:** Definición del alcance del dashboard de monitoreo satelital con la API de SatNOGS (Unidad N° 6: Redes Satelitales y Nuevas Tecnologías Inalámbricas)

## Asistentes

- Estudiante (autor del proyecto)
- Asistente de desarrollo (opencode)

## Objetivo

Definir la funcionalidad y el alcance del proyecto final para Redes de Datos II, que consiste en un dashboard web que consume la API de SatNOGS y explica, mediante una simulación, el proceso de comunicaciones satelitales.

## Temas tratados

### 1. Contexto y stack tecnológico

- Backend: Python + FastAPI (actúa como *middleware* entre el Frontend y SatNOGS).
- Frontend: ReactJS + Vite.
- Estructura existente del repositorio: `backend/` (con `main.py`, `utils/config.py`, variables de entorno) y `frontend/` (vacío al inicio de la charla).

### 2. Análisis de la API de SatNOGS

- **SatNOGS Network API** (`network.satnogs.org/api/`):
  - `observations/`: pasadas con `norad_cat_id`, TLE, frecuencias, modo, baud, `rise/set_azimuth`, `max_altitude`, `status`.
  - `stations/`: red global de estaciones terrenas.
- **SatNOGS DB API** (`db.satnogs.org/api/`):
  - `satellites/`, `transmitters/`, `modes/`, `telemetry/`, `tle/`.
- **Hallazgo clave:** el `payload` y `demoddata` de las observaciones son **URLs a archivos** (audio `.ogg`, datos crudos), no telemetría inline. La **temperatura** proviene de la DB `telemetry/`, que **requiere token** (401 sin autenticación). No todos los satélites transmiten temperatura.

### 3. Propuesta de tres vías de desarrollo

1. **Vía 1 — Dashboard de monitoreo en vivo:** datos reales de SatNOGS con mapa de estaciones, pasadas futuras y curvas de elevación/Doppler. Complejidad baja-media.
2. **Vía 2 — Simulador educativo del enlace:** globo 3D, animación del pase, Doppler, budget de enlace, uplink → downlink → telemetría. Complejidad media-alta (~14-17 h).
3. **Vía 3 — Laboratorio de red satelital:** simulación de constelación, handover, latencia y protocolos (capa de red). Complejidad alta.

Se descartaron las Vías 2 y 3 por el límite de 15 h de trabajo disponible.

### 4. Decisión final: dashboard con buscador y mapa 2D

Se acordó el siguiente alcance:

- **Buscador de satélites** por nombre (catálogo de la SatNOGS DB).
- **Ficha del satélite** al seleccionarlo:
  - Frecuencia de transmisión (uplink/downlink).
  - Modo de modulación.
  - Baud rate.
  - Temperatura de la última observación (sujeta a disponibilidad del token y del satélite).
- **Mapa 2D** (MapLibre/Leaflet) que muestra:
  - Posición del satélite según su última observación (calculada con TLE + SGP4 en el backend).
  - Estación terrena receptora.
  - Huella de cobertura (*footprint*).
- **Botón educativo animado:** explica paso a paso cómo SatNOGS obtiene los datos (satélite → estación terrena → cliente SatNOGS → Network/DB → nuestra API → dashboard).

### 5. Endpoints definidos para el backend

- `GET /api/satellites?search=` → buscador por nombre.
- `GET /api/satellites/{norad_id}` → datos del satélite + transpondedores.
- `GET /api/satellites/{norad_id}/last-observation` → última observación con `status=good`.
- `GET /api/satellites/{norad_id}/telemetry` → última trama decodificada (temperatura), con fallback.
- `GET /api/satellites/{norad_id}/position` → posición sub-satélite + estación receptora + footprint.

### 6. Decisión sobre la temperatura

La temperatura se obtiene de la telemetría de la DB con el token existente (`DB_TOKEN_SATONGS`). Ante ausencia de datos o fallo de autenticación, se mostrará *"sin datos de temperatura"* (degradación elegante).

### 7. Estimación de tiempo

| Tarea | Horas |
|---|---|
| Backend: buscador + detalle de satélite + transpondedores (cache) | 2.5 |
| Backend: última observación + posición SGP4 | 2.5 |
| Backend: telemetría con token + fallback | 1.5 |
| Frontend: buscador + ficha de KPIs | 2 |
| Frontend: mapa 2D con satélite/estación/footprint | 2.5 |
| Overlay animado del proceso | 1.5 |
| Pullido, errores, degradación, pruebas | 1.5 |
| **Total** | **~14 h** ✓ |

### 8. Actualización de la documentación

- `AGENTES.md` fue reescrito para reflejar el alcance decidido (propósito, tecnologías, fuentes de datos, endpoints, vistas y estructura del proyecto).

## Acuerdos y próximos pasos

1. Implementar el backend FastAPI con los endpoints definidos y la integración con SatNOGS.
2. Construir el frontend React con buscador, ficha de KPIs y mapa 2D.
3. Desarrollar el overlay animado del proceso de obtención de datos.
4. Mantener las buenas prácticas de `AGENTES.md` (SoC, RESTful inversa, gestión de secretos, resiliencia).
5. Iniciar la fase de refactor e implementación del backend en la siguiente iteración de trabajo.

# Session de opencode

```bash
opencode -s ses_040f1d9cfffehQgkW5Rrzz0jOf
```
