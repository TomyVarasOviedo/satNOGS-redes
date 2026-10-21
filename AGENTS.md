# AGENTS.md

Contexto para cualquier agente (humano o IA) que trabaje en este repositorio. La fuente de verdad del alcance es el documento del TFI **"NOC Satelital como Servicio" (Grupo 3)**; este archivo resume lo que hace falta para escribir código.

## Qué es el proyecto

TFI de **Redes de Datos II** (Unidad 6: Redes Satelitales). Se propone un **NOC satelital ofrecido como servicio (SaaS)** para equipos chicos que operan CubeSats y no pueden sostener un centro de operaciones propio: universidades, startups y radioaficionados. El servicio les dice cuándo pueden comunicarse con su satélite, qué frecuencia sintonizar, si el enlace tendrá margen y si la telemetría está fuera de rango.

El foco del TFI es **demostrar que el servicio se puede vender**, con modelo de negocio, entrevistas y pitch. El código es un **prototipo demostrable**, no el producto. Si falta tiempo, se recorta del prototipo y nunca de la validación comercial.

## Alcance del prototipo

| Se construye (prototipo) | NO se construye (solo mockups y hoja de ruta) |
| ----- | ----- |
| Uno o dos satélites reales (LUSAT, ISS) y una estación de referencia | Satélites y estaciones por cliente |
| Agenda de pases con margen de enlace y curva Doppler | Panel web: no hay frontend |
| Validación de predicciones contra observaciones reales de SatNOGS | Alertas por correo o Telegram |
| Caché y tolerancia a fallas ante caídas de SatNOGS | Cuentas, multicliente, despliegue en la nube |
| Consulta por `/docs` de FastAPI y un notebook con gráficos | Demodulación de RF real (SDR o antena) |

La demo se hace desde `/docs` y desde `notebooks/analisis.ipynb`. Todo el cómputo científico vive en el backend; el notebook solo consume la API.

## Arquitectura (backend)

Python 3.11 + FastAPI, gestionado con `uv`. Corre desde `backend/`: `uv run uvicorn main:app`, `uv run pytest`.

| Módulo | Responsabilidad | Estado |
| ----- | ----- | ----- |
| `main.py` | App FastAPI y endpoints | Existente |
| `utils/config.py` | Config por variables de entorno, satélites monitoreados y estación de referencia | Existente |
| `utils/cache.py` | Caché en archivos JSON con TTL por entrada y escritura atómica | Existente |
| `services/satnogs.py` | Único punto de acceso a SatNOGS: `fetch_with_cache` (caché → retry con backoff → circuit breaker → stale) | Existente |
| `services/refresher.py`, `scripts/prefetch.py` | Refresco en background y precarga de caché para demos sin conexión | Existente |
| `services/orbits.py` | Clasificación orbital, propagación SGP4 (skyfield), ground track, búsqueda de pases | A construir |
| `services/doppler.py` | Curva de frecuencia a sintonizar a lo largo de un pase | A construir |
| `services/linkbudget.py` | Distancia oblicua, FSL, CNR y margen | A construir |
| `services/validation.py` | Pases predichos frente a observaciones reales | A construir |
| `notebooks/analisis.ipynb` | Gráficos del documento y la demo | A construir |

Endpoints:

| Endpoint | Descripción | Estado |
| ----- | ----- | ----- |
| `GET /satelites/{nombre}` · `GET /satelite/{sat_id}` | Búsqueda y metadatos | Existente |
| `GET /observations/{sat_id}` · `GET /observations/id/{id}` | Observaciones de SatNOGS Network | Existente |
| `GET /telemetry/{norad_id}` | Telemetría de SatNOGS DB (requiere token) | Existente |
| `GET /satellites/monitored` | Lista configurada | Existente |
| `GET /orbits/classify` | Período, altura y tipo (LEO/MEO/GEO/HEO) | A construir |
| `GET /predictions/passes` | AOS/LOS, elevación máxima, acimuts, duración y margen de enlace | A construir |
| `GET /predictions/doppler` | Curva `f(t)` de un pase y corrimiento máximo | A construir |
| `GET /linkbudget` | FSL, distancia, CNR y margen con parámetros editables | A construir |
| `GET /validation/satellite` | Error de predicción contra observaciones reales | A construir |

Cada respuesta lleva los headers `X-Source` (`live`/`cache`/`stale`) y `X-Cache-Age`. Los endpoints nuevos usan `fetch_with_cache` y `build_response` igual que los existentes.

## Convenciones

- **Nada de secretos en el código.** Tokens y URLs van en `backend/.env` (gitignoreado); `backend/.env.example` es la plantilla.
- **Las rutas y variables usan `satelite` sin tilde ni doble "l".** Mantenerlo para no romper compatibilidad.
- **Identificadores de SatNOGS:** DB usa `sat_id` (UUID `XXXX-XXXX-XXXX-XXXX`) y NORAD (`norad_cat_id`); Network filtra observaciones por `sat_id`. Verificá cada NORAD contra `db.satnogs.org/api/satellites/?norad_cat_id=` antes de agregarlo a la config.
- **Si falta el token,** el header `Authorization` no se envía: SatNOGS responde 401 a un token inválido incluso en endpoints públicos.
- **Los cálculos de órbita, Doppler y enlace llevan tests** contra casos conocidos (pytest en `backend/tests/`).
- **Comentarios solo cuando aportan algo no evidente,** por ejemplo una fórmula física con su fuente.
- **Las minutas de reuniones** van en `docs/` con el formato `YYYY-MM-DD-tema.md`.

## Fórmulas de referencia (marco teórico del TFI)

R = 6371 km, μ = 398 600,4418 km³/s², c = 299 792 458 m/s.

- **Altura desde TLE:** `T = 1440 / n` min (n = movimiento medio, rev/día); `a = (μ·(T/2π)²)^(1/3)`; `h = a − R`.
- **Distancia oblicua:** `d = −R·sin(E) + √(R²·sin²(E) + h² + 2·R·h)`.
- **Huella de cobertura:** `λ = arccos(R/(R+h)·cos(ε)) − ε`, con radio `R·λ`. Caso de prueba: h = 550 km, ε = 10° da ≈ 1670 km.
- **Doppler:** `Δf(t) = −f₀·v_r(t)/c`, con v_r positiva cuando el satélite se aleja. En LEO/UHF da ≈ ±10 kHz.
- **FSL (dB):** `20·log₁₀(d_km) + 20·log₁₀(f_MHz) + 32,44`. Casos de prueba: 437 MHz a 1000 km da ≈ 145 dB; a 36 000 km, ≈ 176 dB.
- **CNR (dB):** `EIRP − FSL + G_r + 228,6 − 10·log₁₀(T) − 10·log₁₀(B)`. EIRP va en dBW (dBm = dBW + 30). También `Eb/N₀ = CNR + 10·log₁₀(B/R_b)`.
- **Margen:** CNR menos el umbral de decodificación del modo y baud rate. Documentar la fuente de cada umbral.
- **Pases:** se muestrea cada 30–60 s con una máscara de elevación de 10° por defecto. El cruce ascendente es AOS y el descendente LOS.
- **Validación:** para cada observación real se predice el pase con **el TLE embebido en esa observación** (`tle0/1/2`) y se mide el error en AOS y LOS (s), en elevación máxima (°) y en Doppler (Hz, contra `transmitter_downlink_drift` y `observation_frequency`).

## Fuentes de datos

- **SatNOGS Network API** (`https://network.satnogs.org/api`): `observations/`, con TLE embebido, estación, acimuts, `max_altitude`, `status` y bloque `transmitter_*`; y `stations/`.
- **SatNOGS DB API** (`https://db.satnogs.org/api`): `satellites/`, `transmitters/` y `telemetry/` (requiere token). Los datos son CC BY-SA 4.0: hay que citar la fuente.

## Estado y ramas

- `main`: documentación.
- `backend`: el backend FastAPI con resiliencia (Fase 0 hecha). Las minutas de la Fase 0 y `docs/Redes_Satelitales_Resumen.md` viven ahí hasta que se mergee a `main`.
- `frontend`: scaffold de Vite sin usar. **Fuera del alcance** del prototipo según el documento del TFI.
