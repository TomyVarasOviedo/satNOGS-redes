# Documento de Definición del Proyecto (AGENTES)

> Este documento es la **fuente de verdad** del proyecto. Cualquier agente (humano o IA) que trabaje en este repositorio debe leerlo completo antes de tocar código.

## 1. Propósito del Proyecto

<<<<<<< Updated upstream
Dashboard de monitoreo de telecomunicaciones satelitales para la asignatura **Redes de Datos II** (Unidad N° 6: Redes Satelitales y Nuevas Tecnologías Inalámbricas). El sistema establece la analogía entre la monitorización de infraestructura terrestre (routers, switches, enlaces WAN) y la infraestructura aeroespacial (satélites de órbita baja - LEO), consumiendo la red global y abierta de estaciones terrenas **SatNOGS**.
=======
El presente proyecto tiene como objetivo principal diseñar e implementar un sistema de monitoreo de telecomunicaciones satelitales, concebido como trabajo final para la asignatura Redes de Datos II.
>>>>>>> Stashed changes

Funcionalidades principales:

*   **Buscador de satélites** por nombre (catálogo de la SatNOGS DB).
*   **Ficha del satélite** al seleccionarlo: frecuencia de transmisión (uplink/downlink), modo de modulación, baud rate y temperatura de su última observación.
*   **Mapa 2D** con la posición del satélite según su última observación, la estación terrena receptora y su huella de cobertura (*footprint*).
*   **Botón educativo animado** que explica, paso a paso, cómo SatNOGS obtiene los datos: satélite → estación terrena → cliente SatNOGS → Network/DB → nuestra API → dashboard.

El sistema actúa como una capa de abstracción que consume, limpia y presenta la información de la red satelital de forma relevante para el estudio de las redes de datos modernas, facilitando la comprensión de los desafíos inherentes a las transmisiones espaciales (ventanas de visibilidad, efecto Doppler y calidad del enlace).

## 2. Tecnologías Empleadas

<<<<<<< Updated upstream
*   **Backend:** Python + FastAPI (actúa como *middleware* entre el Frontend y las APIs de SatNOGS). Propagación orbital con `skyfield`/`sgp4` para calcular la posición sub-satélite. Caché en memoria de respuestas para reducir latencia.
*   **Frontend:** ReactJS + Vite. Mapa 2D con MapLibre (o Leaflet). Componentes funcionales reutilizables y manejo de estado predecible y eficiente.
=======
Para garantizar un desarrollo ágil, eficiente y alineado con los estándares actuales del mercado, la arquitectura del proyecto se divide en dos tecnologías principales:

*   **Backend:** Python 3.11 + FastAPI (procesamiento de datos, interconexión con APIs externas, lógica de red y cómputo orbital).
*   **Frontend:** ReactJS con Vite (interfaz de usuario reactiva, modular y de alto rendimiento). **Aún no existe**: debe crearse desde cero en la raíz del repo.
>>>>>>> Stashed changes

## 3. Directrices y Buenas Prácticas (Best Practices)

El ciclo de desarrollo e implementación de ambas capas del sistema deberá regirse estrictamente por las siguientes mejores prácticas de la industria:

*   **Separación de Responsabilidades (SoC):** El Frontend actuará única y exclusivamente como una capa de presentación (UI) y consumo de datos. Toda lógica de negocio, autenticación con servicios de terceros, formateo de metadatos, control de peticiones, sanitización de respuestas y **cómputo científico (propagación orbital, Doppler, link budget)** debe ocurrir de forma aislada en el Backend.
*   **Arquitectura RESTful Inversa:** El Backend en Python actuará como un "middleware" o API de paso entre el Frontend local y SatNOGS, exponiendo endpoints REST limpios. El Frontend **nunca** consulta SatNOGS directamente.
*   **Gestión de Secretos y Configuración:** Las credenciales, tokens de acceso, puertos y URIs nunca se incluyen de forma estática en el código (zero hardcoding). Se usan variables de entorno (`.env`, ya gitignoreado). Referencia de variables: ver `backend/utils/config.py` y `backend/requests/.environments/request.local.env`.
*   **Componentización y Reusabilidad:** React se estructurará mediante componentes funcionales aislados y reutilizables, con manejo de estado predecible.
*   **Resiliencia y Clean Code:** Manejo estructurado de errores (`try/except` robustos, *Error Boundaries*), degradación elegante ante caídas de la red de origen, código limpio, variables descriptivas y modularidad. Se exige implementar la estrategia de resiliencia definida en la sección 8.
*   **Código sin comentarios redundantes:** No se agregan comentarios salvo que aporten información no evidente (ej. fórmulas físicas con su fuente).

## 4. Fuentes de Datos de SatNOGS

*   **SatNOGS Network API** (`network.satnogs.org/api/`): observaciones de pasadas (`observations/`) — con `norad_cat_id`, TLE, frecuencias, modo, baud, `rise_azimuth`/`set_azimuth`, `max_altitude`, `status` — y estaciones terrenas (`stations/`).
*   **SatNOGS DB API** (`db.satnogs.org/api/`): catálogo de satélites (`satellites/`), transpondedores (`transmitters/`) y telemetría decodificada (`telemetry/`).
*   **Nota sobre telemetría/temperatura:** la temperatura se obtiene de la telemetría decodificada de la DB (requiere `DB_TOKEN_SATONGS`). No todos los satélites la transmiten; ante ausencia o fallo de autenticación se muestra *"sin datos de temperatura"* (degradación elegante).

## 5. Estructura del Backend (Endpoints REST)

*   `GET /api/satellites?search=` → buscador de satélites por nombre.
*   `GET /api/satellites/{norad_id}` → datos del satélite + transpondedores (frecuencias, modo, baud).
*   `GET /api/satellites/{norad_id}/last-observation` → última observación con `status=good`.
*   `GET /api/satellites/{norad_id}/telemetry` → última trama decodificada (temperatura, etc.), con fallback controlado.
*   `GET /api/satellites/{norad_id}/position` → posición sub-satélite calculada con TLE + SGP4 al instante de la última observación, estación receptora y footprint.

## 6. Estructura del Frontend (Vistas)

*   Vista de búsqueda y selección de satélite.
*   Ficha con KPIs del satélite (frecuencias, modo, baud, temperatura, última observación).
*   Mapa 2D con marcadores del satélite y de la estación receptora, y círculo de cobertura.
*   Overlay animado "¿Cómo obtiene SatNOGS los datos?".

## 7. Estructura del Proyecto

El repositorio mantendrá un desacoplamiento absoluto en dos directorios principales. Ningún dominio cruza las fronteras de su carpeta designada:

```text
📦 Raíz del Proyecto
<<<<<<< Updated upstream
 ┣ 📂 Backend/
 ┃ ┗ 📜 (Contendrá exclusivamente la lógica del servidor Python, manejadores de rutas,
 ┃      servicios de conexión a SatNOGS, propagación orbital, entornos virtuales y
 ┃      configuración del servidor).
 ┣ 📂 Frontend/
 ┃ ┗ 📜 (Contendrá exclusivamente la aplicación ReactJS, componentes de interfaz visual,
 ┃      vistas, mapa 2D, hojas de estilo y empaquetadores como Vite o Webpack).
 ┗ 📜 AGENTES.md (Documento de definición arquitectónica)
```
=======
 ┣ 📂 backend/          # Solo lógica Python: servidor, rutas, servicios, cómputo, caché, scripts
 ┣ 📂 frontend/         # Solo la app React: vistas, componentes, estilos, build
 ┣ 📂 docs/             # Documentación, resúmenes y minutas
 ┗ 📜 AGENTES.md        # Este documento (fuente de verdad)
```

## 5. Contexto Técnico y Fuentes de Datos

### 5.1 APIs de SatNOGS consumidas (desde el backend)

| Fuente | Base URL | Uso | Token (`backend/utils/config.py`) |
|--------|----------|-----|-----------------------------------|
| DB API | `https://db.satnogs.org/api` | Metadatos de satélites y telemetría | `DB_TOKEN_SATNOGS` / `DB_URL_SATNOGS` |
| Network API | `https://network.satnogs.org/api` | Observaciones de pases desde estaciones terrenas | `NETWORK_TOKEN` / `NETWORK_URL` |

### 5.2 Endpoints actuales del backend (FastAPI en `backend/main.py`)

| Endpoint | Descripción | Estado |
|----------|-------------|--------|
| `GET /` | Health check | OK |
| `GET /satelite/{satelite_id}` | Metadatos por UUID `sat_id` (formato `XXXX-XXXX-XXXX-XXXX`) | OK |
| `GET /satelites/{satelite_name}` | Búsqueda por nombre (limit/offset, caché LRU) | OK |
| `GET /observations/{satelite_id}` | Observaciones por `sat_id` | OK |
| `GET /observations/id/{id}` | Observación puntual por ID | **BUG**: falla con 301. SatNOGS exige barra final `/observations/{id}/`. Corregir con `follow_redirects=True` o URL con `/` final. |
| `GET /telemetry/{satelite_id}` | Telemetría | **BROKEN**: el recurso real devuelve 404 (ver TODO en el código). El endpoint válido es `DB_URL/telemetry/?satellite={norad}`. **Fuera del alcance prioritario** de este plan, pero debe quedar documentado. |

### 5.3 Esquema de datos reales (verificado en respuestas capturadas en `backend/requests/.timeline/*.bodies/`)

**Satélite** (DB API): `sat_id` (UUID), `norad_cat_id` (int), `name`, `names`, `image`, `status`, `decayed`, `launched`, `countries`, `telemetries`, `updated`.

**Observación** (Network API): `id`, `start`, `end`, `ground_station`, `station_name`, `station_lat`, `station_lng`, `station_alt`, `rise_azimuth`, `set_azimuth`, `max_altitude`, `vetted_status`, `status`, `observation_frequency`, `observer`, plus bloque `transmitter_*`:
- `transmitter_downlink_low` (Hz nominal), `transmitter_downlink_drift` (Hz máximo de deriva Doppler), `transmitter_mode` (CW/FM/GFSK...), `transmitter_baud`, `transmitter_description`.
- **TLE embebida:** `tle0`, `tle1`, `tle2` — la entrada para toda la propagación orbital.

> **Nota de inglés vs. dominio:** la API y el código existente usan `satelite` (sin tilde) en rutas y variables. Mantener esa convención para no romper la compatibilidad.

## 6. Dirección del Proyecto (DECISIÓN TOMADA)

**Opción A — NOC Satelital: Predicción de pases + Calidad de enlace.**

Construir un **planificador/calculadora orbital** que determine, para cualquier satélite LEO/MEO/GEO conocido por SatNOGS y cualquier estación terrena:

1. **Dónde estará** el satélite: predicción de pasos visibles (ventanas AOS/LOS), posición (elevación/acimut/distancia) en el tiempo y ground track en un mapa.
2. **Cómo captarlo:** corrección Doppler (frecuencia a sintonizar en cada instante) y cálculo de link budget (¿la señal llega con fuerza suficiente para decodificar?).
3. **Confiabilidad:** validación de las predicciones contra las observaciones reales de la red global SatNOGS (métricas de error cuantitativas).

El problema real que resuelve: un operador/ingeniero de red o radioaficionado necesita anticipar ventanas de enlace y dimensionar la recepción sin ceguera; hoy SatNOGS solo ofrece datos históricos/puntuales, no predicción ni análisis de enlace.

**Alcance:** predicción computacional, corrección de frecuencia y estimación de calidad de enlace basada en modelos físicos y datos reales de SatNOGS. NO incluye demodulación de radiofrequency real (requeriría hardware SDR/antena y excede Redes de Datos II).

### 6.1 Mapeo con la materia (`docs/Redes_Satelitales_Resumen.md`)

| Tema del doc | Feature del proyecto |
|---|---|
| §2 Espectro y propagación (LOS, bandas L/C/X/Ku/Ka, atenuación) | Link budget por banda/frecuencia; visibilidad = LOS a estación |
| §3 Arquitectura satelital (LEO 640–1600 km, MEO, GEO 36 000 km, HEO) | Clasificación orbital automática desde TLE + footprints |
| §4 Multiplexación y acceso al medio | El modelo de pase/utilización de estaciones se apoya en datos de uso real de la red (dato de carga) |
| §5 Enlaces (SCPC/MCPC/VSAT, hub-and-spoke, bandas Ku/C) | Dimensionamiento de enlace: FSL, CNR, margen por baud/modo |

## 7. Conceptos Técnicos a Implementar

Cada agente debe entender estos conceptos antes de tocar la capa de cómputo:

- **TLE (Two-Line Elements):** formato de 2 líneas que describe la órbita en una época. En nuestros datos vienen incrustadas (`tle0/1/2`) en cada observación. El movimiento medio (rev/día) → período → altura orbital vía tercera ley de Kepler (`a = (μ(T/2π)²)^(1/3)`, μ = 398 600.4418 km³/s²) → clasificar LEO/MEO/GEO.
- **Propagación orbital (SGP4/SDP4):** modelo que calcula posición/velocidad satelital en el tiempo. Se implementa con la librería **`skyfield`** (envuelve `sgp4`). Entrada: TLE + lista de instantes. Salida: geocéntrico y topocéntrico (elevación, acimut, distancia, velocidad radial) relativo a la estación.
- **Pase (AOS/LOS):** elevar el satélite por sobre una **máscara de horizonte** (default 10°, configurable). AOS = adquisición, LOS = pérdida. Cada pase: `start`, `end`, `max_altitude`, `rise/set_azimuth`, duración. Se calcula propagando en pasos (ej. 30–60 s) sobre un horizonte temporal de 1–7 días.
- **Efecto Doppler:** `Δf(t) = -f_nominal · v_radial(t)/c`. Para LEO alcanza ~±10 kHz en UHF. El backend debe devolver la **curva de frecuencia a sintonizar** y el drift máximo. Validación real disponible: `transmitter_downlink_drift` y la diferencia entre `transmitter_downlink_low` y `observation_frequency`.
- **Link budget:** FSL (free-space loss) `= 20·log10(d_km) + 20·log10(f_MHz) + 32.44`, con distancia de slant `d = -R·sin(E) + sqrt(R²sin²E + h² + 2Rh)` (R = 6371 km). Con ganancia de antena, EIRP y temperatura de ruido → estimación de CNR: `CNR ≈ EIRP − FSL + G_r − k − T − BW` (en dB). Margen vs. umbral de decodificación según `transmitter_baud`/`mode` reales.
- **Ground track y footprint:** proyección del punto subsatelital y círculo de cobertura (radio de visibilidad según altura y elevación mínima). Para visualizar en mapa.
- **Validación:** comparar predicción vs. histórico real (observaciones de SatNOGS para el mismo `sat_id`/estación). Métricas: error en `start`/`end` (segundos), error en `max_altitude` (grados), error de frecuencia Doppler (Hz).

## 8. Resiliencia y Preparación de Datos (Pendiente de implementar)

La minuta `docs/2026-08-05-resiliencia-backend-conectividad-limitada.md` define la estrategia **no implementada todavía**. Ejecutar en la Fase 0:

1. Lista fija de satélites a monitorear en `backend/utils/config.py` (fuente de verdad, con sus `sat_id` y NORAD).
2. `backend/utils/cache.py` — `CacheManager`: `get/set/key_for`, archivos JSON por endpoint bajo `CACHE_DIR`, TTL por entrada, escritura atómica.
3. `backend/services/satnogs.py` — `fetch_with_cache`: caché fresca → llamada a SatNOGS con **timeout + reintentos con backoff** → actualización de caché → si falla y hay caché vieja, servir *stale* → si no hay nada, error limpio. **Circuit breaker**.
4. `backend/services/refresher.py` — hilo en background que refresca satélites configurados respetando TTL y circuit breaker.
5. `backend/scripts/prefetch.py` — precarga con buena conexión (el caché se copia al equipo con mala red).
6. `.env` — nuevas vars: `CACHE_DIR`, `REQUEST_TIMEOUT`, `RETRY_*`, `CIRCUIT_*`, `REFRESH_INTERVAL`, `DEFAULT_TTL_*`.
7. Headers de respuesta `X-Source` (live/cache/stale) y `X-Cache-Age`.
8. Corregir bugs conocidos: `/observations/id/{id}` (301) y documentar el estado de `/telemetry/{id}`.

## 9. Plan de Implementación (duración estimada: 4–5 semanas)

### Fase 0 — Base y saneamiento (Semana 1)
**Objetivo:** backend estable, resiliente y reproducible; frontend scaffold.
- Fix bug `/observations/id/{id}` (barra final / follow_redirects).
- Timeouts y reintentos en todos los handlers (reemplazar `requests` sincrónicos usados dentro de handlers async).
- Implementar sección 8 (caché a disco, circuit breaker, refresher, prefetch, headers `X-Source`/`X-Cache-Age`).
- Crear `frontend/` con Vite + React + Router; estructura de vistas (páginas placeholder) y consumo del backend vía proxy.
- **DoD:** `backend` levanta con o sin internet sirviendo caché; cada endpoint devuelve headers de origen; el frontend compila y muestra una vista base consumiendo `/satelites/{nombre}`.

### Fase 1 — Núcleo orbital (Semana 2)
**Objetivo:** predicción de posición y pases; clasificación orbital.
- Agregar dependencia `skyfield`.
- `backend/services/orbits.py` — wrapper: `classify_orbit(tle)`, `propagate(tle, times)` (elev/az/dist/v_radial), `ground_track(tle, start, end, step)`, `find_passes(tle, station, horizon, days)`.
- Nuevos endpoints:
  - `GET /orbits/classify?sat_id=...` → órbita, período, altura, tipo (LEO/MEO/GEO/HEO).
  - `GET /predictions/passes?sat_id=...&lat=...&lng=...&alt=...&horizon_deg=10&days=2` → tabla de pases (AOS/LOS, max_alt, rise/set_az, duración).
  - `GET /predictions/groundtrack?sat_id=...&from=...&to=...&step=60` → serie `[{t, lat, lng, alt, elev, az, dist}]`.
- Caché de propagación (las TLE cambian cada ~horas; la propagación es determinista: caché por TLE + horario).
- **DoD:** los 3 endpoints devuelven datos numéricamente correctos para LUSAT/ISS contra TLE reales; frontend muestra tabla de pases y mapa con ground track de un satélite elegido.

### Fase 2 — Enlace: Doppler y link budget (Semana 3)
**Objetivo:** cuantificar qué y cómo captar.
- `backend/services/linkbudget.py` — FSL, distancia de slant, CNR, margen; umbral por baud/modo.
- `backend/services/doppler.py` — curva `f(t)` predicha + drift máximo + frecuencia inicial.
- Nuevos endpoints:
  - `GET /predictions/doppler?sat_id=...&lat=...&lng=...&freq_hz=...` → `[{t, freq, delta}]` + máximos.
  - `GET /linkbudget?sat_id=...&lat=...&lng=...&freq_hz=...&eirp_dbm=...&gain_dbi=...&noise_k=...` → FSL, distancia, CNR, margen vs umbral.
- Frontend: vista "Doppler" (gráfica frecuencia vs. tiempo) y vista "Link budget" (calculadora con inputs).
- **DoD:** los valores de FSL/CNR/Doppler son consistentes con las fórmulas de la sección 7; la vista te dice "sí/no vas a decodificar" con el margen.

### Fase 3 — Validación, integración y entrega (Semana 4)
**Objetivo:** cerrar el ciclo predicción↔realidad y pulir el producto.
- `GET /validation/satellite?sat_id=...&days=7` → para cada pase histórico (observaciones reales) compara con la predicción: `error_start_s`, `error_end_s`, `error_max_alt_deg`; agrega error Doppler promedio.
- Vista Frontend "Validación": métricas de error, lista de pases predichos vs. reales, distribución del error.
- Reporte/README final: descripción del problema, arquitectura, fórmulas, resultados de validación, capturas.
- Integración completa de todas las vistas con navegación; estilos consistentes; degradación elegante (Error Boundaries + mensajes si SatNOGS/backend caen).
- **DoD:** demo end-to-end funcionando offline con caché precargada; documentación completa; el error de validación está cuantificado y presentado.

### Semana 5 (buffer) — Defensa y presentación
- Preparar slides/demo, caso de estudio con datos reales, métricas de la validación.

## 10. Definición de "Listo" Global (Definition of Done)

- Backend sirve datos **reales y/o cacheados validados** contra SatNOGS, con resiliencia (cero requests bloqueantes).
- Todo el cómputo físico (órbitas, Doppler, link budget) vive en el backend; el frontend solo consume y presenta.
- Los endpoints nuevos siguen el estilo de `main.py` (JSON, manejo `try/except`, paginación donde aplique).
- Sin secretos hardcodeados; configuración por `.env`.
- Documentación al día: este archivo + README de cada carpeta.

## 11. Estado Actual del Repositorio (al iniciar la Fase 0)

- Backend FastAPI funcional como proxy (ver 5.2), con 2 bugs conocidos y sin resiliencia.
- **Frontend inexistente** (crear desde cero).
- Dependencias backend actuales (ver `backend/pyproject.toml`): `fastapi`, `httpx`, `python-dotenv`, `requests`, `uvicorn`. Se agregarán `skyfield` (y su dependencia `sgp4`).
- Datos de ejemplo y pruebas: `backend/requests/*.yml` (requests de Thunder Client) y respuestas capturadas en `backend/requests/.timeline/*.bodies/`.
- Áreas de conocimiento de referencia: `docs/Redes_Satelitales_Resumen.md` (contenido de la materia).
>>>>>>> Stashed changes
