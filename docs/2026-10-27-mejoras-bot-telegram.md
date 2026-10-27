# Minuta: Mejoras del bot de Telegram

| Campo | Valor |
|-------|-------|
| Fecha | 2026-10-27 |
| Tema | mejoras-bot-telegram |
| Lenguajes | Python 3.11 |
| Frameworks/Libs | python-telegram-bot 22.8, httpx 0.28.1, python-dotenv 1.2.4, pytest 9.2.0, pytest-asyncio 1.4.1 |
| Herramientas | uv 0.11.32, FastAPI (backend existente) |
| Versiones clave | Python 3.11.2 |
| Estado final | exito |

## Contexto
Complementa `docs/2026-10-27-integracion-telegram.md`. Registra los cambios posteriores: resolución estricta de nombres y rediseño visual de todos los mensajes. No se modificó la selección de pases, la deduplicación ni el backend.

## Decisiones
- Nombre exacto primero y ambigüedad como error: evita elegir un satélite arbitrario cuando la búsqueda devuelve varios.
- Probar el nombre completo antes de separar días: hay satélites como `NOAA 18` o `AOBA-VELOX 3` que terminan en número.
- Mantener `/agenda` agrupada por satélite y agregar fecha por fila: evita confundir pases antes y después de medianoche.
- Presentación híbrida “consola”: tags `<code>`, tablas `<pre>`, veredicto en texto y footer de fuente; Telegram no permite colores ni fuentes.
- Cortar por bloques `\n\n` solo en mensajes con etiquetas: no partir `<pre>`/`<code>`; el texto plano conserva el corte por líneas.
- Hora local principal; UTC explícito en la alerta de pase y zona horaria en los listados.

## Complicaciones y soluciones
- **Problema**: un nombre como `x` devolvía varios satélites y el bot usaba el primero sin avisar.
  **Solucion**: `resolve_sat_id` distingue coincidencia exacta/parcial y lanza `AmbiguousSatellite` con hasta cinco nombres.
- **Problema**: `_split_args` interpretaba el último número como días, rompiendo nombres como `NOAA 18`.
  **Solucion**: `_resolve_name_and_days` prueba primero el nombre completo como coincidencia exacta; si no existe, separa el número como días.
- **Problema**: los mensajes con tablas largas podían cortarse dentro de `<pre>`.
  **Solucion**: `chunk()` corta por bloques `\n\n` cuando hay etiquetas; deja el fallback por líneas para texto sin HTML.
- **Problema**: la agenda de 24 h cruza medianoche y solo mostraba horas.
  **Solucion**: se agregó la fecha local a cada fila.
- **Problema**: `/proximo` y `/tle` solo recibían la primera palabra de nombres con espacios.
  **Solucion**: `_args_name` une todos los argumentos.

## Cambios realizados
- `bot/api.py`: `SatelliteNotFound`, `AmbiguousSatellite`, `_name_preview` y `resolve_sat_id(..., exact_only=False)`; acepta exacta única o parcial única, y falla ante múltiples coincidencias.
- `bot/main.py`: `_args_name` y `_resolve_name_and_days`; `/pases` usa el parser nombre/días; `/proximo` y `/tle` aceptan nombres con espacios.
- `bot/messages.py`: tags `PASS`/`AGENDA`/`TLE`/`TEST`/`NORMAL`/`ERROR`; alerta de pase con franja AOS→TCA→LOS, rango local/UTC, `SINTONÍA`, `ENLACE` y `DECODABLE`/`SIN MARGEN`; `/pases` y `/agenda` con ledger `<pre>` y encabezado por satélite; `/tle` con tabla orbital y aviso de TLE; ayuda, test, normal y error unificados; footer de fuente.
- `bot/tests/test_api.py`: ambigüedad, inexistente, parcial única y `exact_only`.
- `bot/tests/test_main_helpers.py`: nombre completo con número, fallback a días, solo dígito y ambigüedad.
- `bot/tests/test_messages.py`: mayúsculas de veredicto, fecha en agenda, footer de fuente y corte por bloques.

## Pendientes
- Probar con token y chat de Telegram reales.
- Actualizar `AGENTS.md`, el TFI y el `README.md`: Telegram sigue figurando fuera de alcance en `AGENTS.md`.

## Notas tecnicas
**Diferencias con `2026-10-27-integracion-telegram.md`:**
- Comandos actuales: `/start`, `/help`, `/pases [sat] [días]`, `/proximo [sat]`, `/agenda`, `/tle [sat]`, `/test [5|10]`, `/stop`.
- `/pases`: si el último argumento es número, primero busca el nombre completo exacto; si no existe, ese número son días. Un único número implica días sin filtro de nombre.
- `resolve_sat_id`: exacta única gana; sin exacta, parcial única se acepta; varias exactas o varias parciales son ambigüedad; sin resultados es `SatelliteNotFound`.
- Formato: `<code>PASS</code> · <b>sat</b> · Pasa en N min`; ledger `FECHA PASE ELEV MARGEN`; footer `● live · ◐ caché · ○ caché vencida`; stale agrega `<blockquote>`.
- Variables no documentadas antes: `CHAT_ID_FILE` (default `bot/chat_id.txt`), `TEST_SCAN_SECONDS` (5, 1–60), `TEST_LEAD_MIN` (default `ALERT_LEAD_MIN`).
- Clamps: `ALERT_LEAD_MIN>=1`; `PASS_SCAN_INTERVAL_MIN` entre 1 y lead; `AGENDA_HOUR_UTC` 0–23; `TLE_MAX_AGE_DAYS>=0`; `MIN_ELEVATION_DEG` 0–90; `TZ` inválida cae a UTC.
- Sin `TELEGRAM_CHAT_ID`, el bot guarda el último chat en `chat_id.txt`; precedencia env > archivo > último chat.
- Tests: `cd bot && uv run pytest -q` → 46 passed. `uv run python main.py --demo` verificado con backend real, sin token de Telegram.
