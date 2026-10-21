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
| `services/orbits.py` | Clasificación orbital, propagación SGP4 (skyfield), ground track, búsqueda de pases | PR #2 |
| `services/doppler.py` | Curva de frecuencia a sintonizar a lo largo de un pase | PR #3 |
| `services/linkbudget.py` | Distancia oblicua, FSL, CNR, Eb/N0 y margen | PR #3 |
| `services/validation.py` | Pases predichos frente a observaciones reales | PR #4 |
| `notebooks/analisis.ipynb` | Gráficos del documento y la demo (`uv sync --group notebook`) | PR #4 |

Endpoints:

| Endpoint | Descripción | Estado |
| ----- | ----- | ----- |
| `GET /satelites/{nombre}` · `GET /satelite/{sat_id}` | Búsqueda y metadatos | Existente |
| `GET /observations/{sat_id}` · `GET /observations/id/{id}` | Observaciones de SatNOGS Network | Existente |
| `GET /telemetry/{norad_id}` | Telemetría de SatNOGS DB (requiere token) | Existente |
| `GET /satellites/monitored` | Lista configurada | Existente |
| `GET /orbits/classify` | Período, altura y tipo (LEO/MEO/GEO/HEO) | PR #2 |
| `GET /predictions/passes` | AOS/LOS, elevación máxima, acimuts, duración (PR #2) y margen de enlace (PR #3) | PR #2 + #3 |
| `GET /predictions/groundtrack` | Punto subsatelital y geometría respecto de la estación | PR #2 |
| `GET /predictions/doppler` | Curva `f(t)` de un pase, corrimiento máximo y margen por punto | PR #3 |
| `GET /linkbudget` | FSL, distancia, CNR y margen con parámetros editables | PR #3 |
| `GET /validation/satellite` | Error de predicción contra observaciones reales | PR #4 |

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
- **Margen:** Eb/N0 menos el umbral del modo, para BER 10⁻⁵ en AWGN (Sklar, *Digital Communications*, 2.ª ed., §4.7–4.8). Coherentes BPSK/QPSK/OQPSK/MSK/GMSK: 9,6 dB. FSK/GFSK/AFSK no coherente: 13,4 dB. CW, FM, SSB y LoRa no tienen umbral. B = tasa de símbolos.
- **Pases:** AOS/LOS son los cruces exactos de la máscara de elevación (skyfield `find_events`, 10° por defecto). No se muestrea cada 30–60 s. Un pase cortado por la ventana se recorta y lleva `aos_clipped`/`los_clipped`; así se cubren el pase en curso y los GEO.
- **Validación:** cada observación real se predice con **el TLE embebido en esa observación** (`tle0/1/2`), desde su propia estación. La elevación máxima y los acimuts se comparan dentro de la ventana observada. AOS y LOS se comparan contra el pase completo a 0°, así que ese error incluye el recorte que hace el scheduler. El Doppler no se puede validar con SatNOGS (ver la sección siguiente).

## Lo que hay que saber de los datos de SatNOGS (verificado)

- **`db/satellites/?search=` se ignora:** devuelve el catálogo entero, unos 2800 satélites. Por eso el backend cachea el catálogo y filtra por `name`/`names`.
- **Filtros de la DB:** se filtra por `?sat_id=` o `?norad_cat_id=`. Los filtros `satellite__…` se ignoran.
- **`transmitter_downlink_drift` no es Doppler:** es la deriva del oscilador del transmisor en ppb. Se cumple `observation_frequency = downlink_low · (1 + drift/10⁹)`. SatNOGS no guarda el Doppler medido de cada observación.
- **`start`/`end`/`rise_azimuth`/`set_azimuth`/`max_altitude`:** describen la ventana que agendó el scheduler. Esa ventana sale del SGP4 de SatNOGS y suele quedar recortada por el horizonte de la estación. Los ángulos vienen redondeados a grados enteros, por eso el error de validación ronda ±0,5°.
- **Nombres de modo con sufijo de protocolo:** por ejemplo `GMSK USP`, `FSK AX.100 Mode 5` o `GFSK/BPSK`. Se normalizan con `linkbudget.base_mode()`.
- **`network/observations/`:** filtra con `?sat_id=&status=good&start=&end=`, todo en ISO UTC. Pagina con un cursor en el header `Link: rel="next"`, de a 25 y empezando por las más recientes. `fetch_with_cache(max_pages=N)` sigue ese cursor.
- **Nombres de los archivos de caché:** cambian los caracteres que Windows no acepta, como el `:` de las fechas ISO, por `-`.

## Fuentes de datos

- **SatNOGS Network API** (`https://network.satnogs.org/api`): `observations/`, con TLE embebido, estación, acimuts, `max_altitude`, `status` y bloque `transmitter_*`; y `stations/`.
- **SatNOGS DB API** (`https://db.satnogs.org/api`): `satellites/`, `transmitters/` y `telemetry/` (requiere token). Los datos son CC BY-SA 4.0: hay que citar la fuente.

## Estado y ramas

- `main`: documentación.
- `backend`: el backend FastAPI. Fase 0 (resiliencia, PR #1) mergeada. Las minutas de la Fase 0 y `docs/Redes_Satelitales_Resumen.md` viven ahí hasta que se mergee a `main`.
- PRs apilados sobre `backend`, a mergear en orden: #2 órbitas → #3 Doppler y enlace → #4 validación y notebook. Al mergear uno, el siguiente se rebasa a `backend`.
- `frontend`: scaffold de Vite sin usar. **Fuera del alcance** del prototipo según el documento del TFI.

## Ajustes pendientes en el documento del TFI (surgieron del código)

- **§4.5:** sacar la métrica "error de frecuencia Doppler". SatNOGS no guarda el Doppler medido. El Doppler se valida con física: forma de la curva, cruce por el nominal en el TCA y magnitud ≈ ±10 kHz.
- **§4.8:** AOS/LOS no se muestrean, se calculan exactos. La limitación por el paso de muestreo ya no aplica.
- **§4.5 y §9:** aclarar que coincidir con `start`/`end` de SatNOGS valida la implementación (el mismo SGP4), no la órbita real. La elevación máxima y los acimuts son la comparación útil, con redondeo de ±0,5°.
- **§3.7:** los umbrales y su fuente ya están documentados (arriba). El margen es optimista: EIRP 0 dBW por defecto y sin pérdidas extra.
- **§7:** la ISS es LEO porque se usa el límite habitual de < 2000 km, no el rango de 640–1600 km de la cátedra.
