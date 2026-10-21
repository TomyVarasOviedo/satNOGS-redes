# Minuta de Reunión

- **Fecha:** 2026-09-10
- **Tema:** Implementación Fase 0 - Backend con resiliencia y saneamiento
- **Proyecto:** Sistema de Monitoreo de Telecomunicaciones Satelitales (Redes de Datos II)

## 1. Objetivo de la reunión

Implementar la Fase 0 completa del plan definido en `AGENTES.md` y la minuta `2026-08-05-resiliencia-backend-conectividad-limitada.md`: saneamiento del backend, implementación de la estrategia de resiliencia (caché a disco, circuit breaker, refresher en background, prefetch) y corrección de bugs conocidos.

## 2. Estado previo (backend/main.py original)

- Backend FastAPI funcionando como proxy REST inverso a APIs de SatNOGS
- 6 endpoints: `/`, `/satelite/{id}`, `/satelites/{nombre}`, `/observations/{sat_id}`, `/observations/id/{id}`, `/telemetry/{sat_id}`
- Caché LRU en memoria solo en `/satelites/{nombre}` y `/telemetry/{sat_id}`
- **Problemas detectados:**
  1. `/observations/id/{id}` falla con 301 (falta barra final en URL)
  2. `/telemetry/{id}` rota (endpoint incorrecto, TODO en código)
  3. Sin timeouts en requests a SatNOGS
  4. Sin reintentos ni circuit breaker
  5. Sin caché persistente a disco
  6. Sin headers para identificar origen de datos (live/cache/stale)
  7. Frontend inexistente

## 3. Implementación realizada

### 3.1 Configuración y variables de entorno (`backend/.env`, `backend/utils/config.py`)

**Nuevas variables en `.env`:**

```env
CACHE_DIR=./cache
REQUEST_TIMEOUT=10
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=0.5
RETRY_BACKOFF_MAX=30
CIRCUIT_FAILURE_THRESHOLD=5
CIRCUIT_RECOVERY_TIMEOUT=60
REFRESH_INTERVAL=300
DEFAULT_TTL_METADATA=86400
DEFAULT_TTL_OBSERVATIONS=300
DEFAULT_TTL_TELEMETRY=600
SATELLITES_TO_MONITOR=25544,20442,40012,43529,32784
```

**En `config.py`:**

- `RESILIENCE_CONFIG` con todos los parámetros parseados
- `SATELLITES_TO_MONITOR`: lista fija de 5 satélites (ISS, LUSAT, NOAA 18, METEOR-M2, FUNCUBE-1) con NORAD ID y nombre

### 3.2 CacheManager (`backend/utils/cache.py`)

- Clase `CacheManager` con persistencia en archivos JSON
- Métodos: `get()`, `set()`, `delete()`, `clear()`, `_key_for()`, `_cache_path()`
- TTL configurable por entrada
- Escritura atómica (archivo `.tmp` + `rename`)
- Retorna tupla: `(data, source, cache_age)` donde source ∈ {`cache`, `stale`, `live`, `error`}

### 3.3 Servicio SatNOGS (`backend/services/satnogs.py`)

- **CircuitBreaker**: estado closed/half-open/open, threshold 5 fallos, recovery 60s
- **fetch_with_retry()**: timeout 10s, 3 reintentos con backoff exponencial (0.5s, 1s, 2s... máx 30s), `follow_redirects=True`
- **fetch_with_cache()**: flujo completo
  1. Intenta caché fresca → retorna `(data, "cache", age)`
  2. Si stale o miss: verifica circuit breaker
  3. Si open y hay caché vieja → retorna `(data, "stale", age)`
  4. Si open y sin caché → error limpio
  5. Llama a SatNOGS con retry → guarda en caché → retorna `(data, "live", 0)`
  6. Si falla y hay caché → retorna `(data, "stale", age)`
  7. Si falla sin caché → propaga error

### 3.4 Refresher en background (`backend/services/refresher.py`)

- Hilo daemon separado (threading + asyncio.run por ciclo)
- Intervalo configurable (`REFRESH_INTERVAL=300s`)
- Para cada satélite de `SATELLITES_TO_MONITOR`:
  1. Obtiene `sat_id` vía NORAD desde DB API
  2. Refresca metadata (TTL 24h)
  3. Refresca observations (TTL 5min)
- Respeta circuit breaker y TTLs
- Logging estructurado

### 3.5 Script de prefetch (`backend/scripts/prefetch.py`)

- Script standalone para poblar caché con buena conectividad
- Itera `SATELLITES_TO_MONITOR`, obtiene `sat_id`, precarga metadata + observations
- Uso: `python scripts/prefetch.py` → genera `backend/cache/*.json`
- El directorio `cache/` se puede copiar a entorno sin internet

### 3.6 Refactor `backend/main.py`

- **Lifespan**: arranca/para refresher al inicio/fin
- **build_response()**: helper que inyecta headers `X-Source` y `X-Cache-Age`
- **Todos los endpoints** migrados a `fetch_with_cache()` con TTLs apropiados:
  - `/satelite/{id}` → metadata TTL 24h
  - `/satelites/{nombre}` → search TTL 24h (mantiene LRU memoria + caché disco)
  - `/observations/{sat_id}` → observations TTL 5min
  - `/observations/id/{id}` → observation TTL 5min (**fix 301**: URL con `/` final)
  - `/telemetry/{norad_id}` → telemetry TTL 10min (**fix**: endpoint DB API correcto)
- **Nuevo endpoint**: `/satellites/monitored` → lista configurada
- Headers en todas las respuestas: `X-Source: cache|live|stale|error`, `X-Cache-Age: segundos`

## 4. Problemas encontrados y soluciones

| Problema | Causa | Solución |
|----------|-------|----------|
| ISS (NORAD 25542) y FUNCUBE-1 (NORAD 32784) no tienen `sat_id` en DB API | Esos satélites no están catalogados en db.satnogs.org | Quedan en lista monitoreada pero se saltan en refresher/prefetch (warning log). Se pueden reemplazar por otros con `sat_id` válido. |
| `RuntimeWarning: coroutine 'fetch_with_cache' was never awaited` en refresher | Primera versión usaba `threading` sin `asyncio.run()` | Refactor a `asyncio.run(self._refresh_all())` y métodos `async` |
| `ModuleNotFoundError` al ejecutar desde raíz | Python no encuentra módulos locales | Ejecutar desde `backend/` o usar `sys.path.insert(0, ...)` en scripts |
| Cache crece indefinidamente | Sin política de limpieza automática | `CacheManager.clear()` manual; se puede agregar job de limpieza por TTL vencido en futuras fases |

## 5. Verificación funcional

```bash
# Precarga de caché
cd backend && python scripts/prefetch.py
# → 3/5 satélites cacheados (LUSAT, NOAA 18, METEOR-M2)

# Levantar servidor
cd backend && python -m uvicorn main:app --host 0.0.0.0 --port 8000

# Verificar headers
curl -I http://localhost:8000/satelite/ZDPY-4221-9426-0630-5344
# → x-source: cache, x-cache-age: 501

curl -I http://localhost:8000/observations/ZDPY-4221-9426-0630-5344
# → x-source: live/cache, x-cache-age: 0/202

curl -I http://localhost:8000/telemetry/20442
# → x-source: cache, x-cache-age: 295

# Verificar fix 301
curl -I "http://localhost:8000/observations/id/12345"
# → 200 OK (antes 301/500)
```

## 6. Archivos creados/modificados

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `backend/.env` | Modificado | Variables de resiliencia |
| `backend/utils/config.py` | Modificado | `RESILIENCE_CONFIG`, `SATELLITES_TO_MONITOR` |
| `backend/utils/cache.py` | Nuevo | `CacheManager` |
| `backend/services/satnogs.py` | Nuevo | `fetch_with_cache`, `CircuitBreaker` |
| `backend/services/refresher.py` | Nuevo | `Refresher` background |
| `backend/scripts/prefetch.py` | Nuevo | Script precarga |
| `backend/main.py` | Refactor completo | Lifespan, headers, endpoints migrados |

## 7. Definition of Done Fase 0 (cumplido)

- ✅ Backend levanta con/sin internet sirviendo caché
- ✅ Cada endpoint devuelve headers `X-Source` y `X-Cache-Age`
- ✅ Timeouts y reintentos en todas las llamadas externas
- ✅ Circuit breaker funcional
- ✅ Refresher background cada 5 min
- ✅ Script prefetch operativo
- ✅ Bugs corregidos: `/observations/id/{id}` (301), `/telemetry/{id}` (404)
- ✅ Caché persistente JSON con TTL y escritura atómica

## 8. Próximos pasos (Fase 1)

1. Agregar dependencia `skyfield` para propagación orbital
2. Implementar `backend/services/orbits.py` (clasificación, propagación SGP4, ground track, pases AOS/LOS)
3. Nuevos endpoints: `/orbits/classify`, `/predictions/passes`, `/predictions/groundtrack`
4. Frontend: scaffold Vite + React + vistas placeholder

## 9. Notas

- Caché actual: 8 archivos JSON (~1.8 MB) en `backend/cache/`
- 3 de 5 satélites configurados tienen `sat_id` válido y datos cacheados
- ISS y FUNCUBE-1 requieren revisión: buscar satélites alternativos con `sat_id` en DB API
- Sin dependencias externas nuevas pesadas (solo stdlib + httpx/fastapi existentes)

# Opencode Session

```bash
opencode -s ses_f74c1b862ffeayusresxxk3PCt
```

