# Backend — NOC Satelital (prototipo)

FastAPI que consume SatNOGS con caché y tolerancia a fallas, y calcula pases, Doppler, margen de enlace y validación. Alcance y convenciones: [`AGENTS.md`](../AGENTS.md) en `main`.

## Correr

```bash
cd backend
cp .env.example .env          # tokens opcionales; sin token funciona todo salvo /telemetry
uv sync
uv run uvicorn main:app       # http://127.0.0.1:8000/docs
uv run pytest                 # tests, sin red
```

Notebook con los gráficos del documento: `uv sync --group notebook`, con el backend corriendo, `uv run --group notebook jupyter lab notebooks/analisis.ipynb`.

## Endpoints

| Endpoint | Qué devuelve |
| ----- | ----- |
| `GET /orbits/classify?sat_id=` | Tipo de órbita, período, altura, huella, antigüedad del TLE |
| `GET /predictions/passes?sat_id=&days=2` | Pases AOS/TCA/LOS con margen de enlace en AOS y TCA |
| `GET /predictions/doppler?sat_id=` | Curva de frecuencia a sintonizar del próximo pase, con margen por punto |
| `GET /predictions/groundtrack?sat_id=` | Punto subsatelital y geometría respecto de la estación |
| `GET /linkbudget?freq_hz=&distance_km=` | Calculadora: FSL, CNR, Eb/N0, margen |
| `GET /validation/satellite?sat_id=&days=7` | Error de predicción frente a observaciones reales |
| `GET /satelites/{nombre}`, `/satelite/{sat_id}`, `/observations/...`, `/telemetry/{norad}` | Proxy de SatNOGS |

Sin `lat`/`lng`/`alt` se usa la estación de referencia (`STATION_*` en `.env`, por defecto Universidad de Belgrano). Toda respuesta trae `X-Source` (`live`/`cache`/`stale`) y `X-Cache-Age`.

`sat_id` de ejemplo: LUSAT `ZDPY-4221-9426-0630-5344`, ISS `XSKZ-5603-1870-9019-3066` (buscar otros con `/satelites/{nombre}`).

## Guion de la demo (TFI §6.4)

1. En `/docs`, `GET /predictions/passes` con LUSAT: agenda y margen de enlace.
2. En el notebook, la curva Doppler y el margen a lo largo del pase.
3. `GET /validation/satellite` con la ISS: error frente a SatNOGS.
4. Cortar la conexión: las respuestas siguen saliendo de `cache/` con `X-Source: cache`/`stale`.

Para la demo sin conexión, correr antes `uv run python scripts/prefetch.py` con buena conexión y llamar una vez cada endpoint a mostrar: la caché queda en `backend/cache/`.
