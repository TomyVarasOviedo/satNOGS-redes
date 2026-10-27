# Minuta: Integración de bot de Telegram

| Campo | Valor |
|-------|-------|
| Fecha | 2026-10-27 |
| Tema | integracion-telegram |
| Lenguajes | Python 3.11 |
| Frameworks/Libs | python-telegram-bot 22.8 (job-queue), httpx 0.28.1, python-dotenv 1.2.4, pytest 9.2.0, pytest-asyncio 1.4.1 |
| Herramientas | uv 0.11.32, FastAPI (backend existente) |
| Versiones clave | Python 3.11.2 |
| Estado final | exito |

## Contexto
Se agregó un bot de Telegram aislado en `bot/` para ofrecer alertas y reportes del NOC sin modificar el backend. Consume la API FastAPI existente por HTTP y puede ejecutarse como proceso independiente.

## Decisiones
- Bot standalone en `bot/`, sin importar `backend/`: si no se termina, el backend sigue funcionando igual.
- Long polling en vez de webhook: funciona en localhost sin URL pública ni despliegue.
- Resolver `sat_id` desde `/satellites/monitored` + `/satelites/{nombre}`: una sola fuente de verdad, sin duplicar configuración.
- MVP de alertas: pase inminente T-15 con Doppler, agenda diaria y TLE viejo; se descartaron validación semanal y telemetría para no inflar el prototipo.
- Mensajes HTML con chunking a 4000 caracteres y deduplicación en JSON: robusto sin base de datos ni dependencias extra.

## Complicaciones y soluciones
- **Problema**: `/satellites/monitored` solo devuelve NORAD y nombre, no `sat_id`.
  **Solucion**: resolver por búsqueda exacta en `/satelites/{nombre}`, con fallback al primer resultado.
- **Problema**: `--demo` propagaba `ApiError` y terminaba con traceback si el backend estaba caído.
  **Solucion**: capturar `ApiError` y salir con mensaje limpio.
- **Problema**: `pyproject.toml` referenciaba un `README.md` inexistente en `bot/`.
  **Solucion**: quitar `readme` para no crear documentación no pedida.
- **Problema**: warning de pytest-asyncio por scope del event loop.
  **Solucion**: `asyncio_default_fixture_loop_scope = "function"` en `pyproject.toml`.

## Cambios realizados
- `bot/config.py`: configuración por variables de entorno y zona horaria.
- `bot/api.py`: cliente HTTP de la API y resolución de `sat_id`.
- `bot/state.py`: deduplicación persistente con escritura atómica.
- `bot/messages.py`: formateo HTML de alertas, agenda, órbitas y errores.
- `bot/alerts.py`: lógica pura de selección y `AlertService` con jobs.
- `bot/main.py`: handlers de PTB, JobQueue, `--demo` y cierre del cliente.
- `bot/tests/`: 23 tests offline (API, alertas, mensajes, estado y servicio).
- `bot/pyproject.toml`, `bot/.python-version`, `bot/.env.example`, `bot/uv.lock`: proyecto uv aislado.
- `.gitignore`: agregado `bot/state.json`.

## Pendientes
- Copiar `bot/.env.example` a `bot/.env` y cargar `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`.
- Actualizar `AGENTS.md` y el TFI: Telegram figuraba en "NO se construye".
- Actualizar el `README.md` raíz con la carpeta `bot/` y cómo ejecutarla.
- Probar con el backend real y un token de Telegram válido.

## Notas tecnicas
- Comandos: `/start`, `/help`, `/pases [sat] [días]`, `/proximo [sat]`, `/agenda`, `/tle [sat]`.
- Endpoints usados: `/satellites/monitored`, `/satelites/{nombre}`, `/predictions/passes`, `/predictions/doppler`, `/orbits/classify`.
- Ejecutar: `cd bot && cp .env.example .env && uv sync && uv run python main.py`.
- Demo sin token: `uv run python main.py --demo` (requiere backend levantado).
- Variables: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `BACKEND_URL`, `ALERT_LEAD_MIN=15`, `PASS_SCAN_INTERVAL_MIN=5`, `AGENDA_HOUR_UTC=9`, `TLE_MAX_AGE_DAYS=7`, `MIN_ELEVATION_DEG=10`, `TZ`, `STATE_PATH`.
- Dedup: `pass:{sat_id}:{aos}`, `agenda:{fecha}`, `tle:{sat_id}:{fecha}`; poda a 3 días.
