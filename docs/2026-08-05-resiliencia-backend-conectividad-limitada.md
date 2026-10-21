# Minuta de Reunión

- **Fecha:** 2026-08-05
- **Tema:** Resiliencia del backend ante conectividad limitada
- **Proyecto:** Sistema de Monitoreo de Telecomunicaciones Satelitales (Redes de Datos II)

## 1. Objetivo de la reunión
Analizar el proyecto y definir estrategias para que el backend funcione correctamente en un entorno donde la conectividad a internet es intermitente/lenta.

## 2. Análisis del funcionamiento actual
- Backend FastAPI (backend/main.py) actúa como proxy REST inverso entre el frontend React y la API de SatNOGS.
- Dos APIs consumidas:
  - DB API (db.satnogs.org/api): metadatos de satélites → /satelite/{id}, /satelites/{nombre}
  - Network API (network.satnogs.org/api): observaciones y telemetría → /observations/{sat_id}, /observations/id/{id}, /telemetry/{sat_id}
- Puntos débiles detectados:
  1. Cada request dispara una llamada HTTP en vivo a SatNOGS, sin caché.
  2. No hay timeouts: SatNOGS colgado puede dejar la petición pendiente por minutos.
  3. Sin reintentos ni degradación elegante: fallo = error crudo para el usuario.
  4. Llamadas síncronas (requests) dentro de handlers async bloquean el event loop.
  5. El frontend no podría distinguir datos reales de datos cacheados/viejos.
- Bug existente: /telemetry/{id} arma la URL NetworkURL/{id}/telemetry, que no coincide con el recurso real de telemetría de SatNOGS (confirmado por un TODO).

## 3. Decisiones tomadas
1. **Conectividad del runtime:** intermitente/lenta → precarga + refresco en background.
2. **Persistencia de caché:** archivos JSON por endpoint.
3. **Alcance de datos:** conjunto fijo de satélites (dataset concreto precargado).

## 4. Plan de implementación acordado
Estrategia: el backend responde casi siempre desde el caché local (0 tráfico); un refresco en background actualiza los datos cuando hay señal.

1. backend/config.py — lista fija de satélites a monitorear (fuente de verdad).
2. backend/utils/cache.py — CacheManager: get/set/key_for, archivos JSON por endpoint bajo CACHE_DIR, TTL por entrada, escritura atómica.
3. backend/services/satnogs.py — fetch_with_cache: sirve caché fresca → llama a SatNOGS con timeout + reintentos con backoff → actualiza caché → si falla y hay caché vieja, sirve stale → si no hay nada, error limpio. Circuit breaker.
4. backend/main.py — refactor de endpoints al servicio con TTLs por tipo de dato (metadatos: horas/días; observaciones: minutos). Headers X-Source y X-Cache-Age. Lifespan arranca el refresco.
5. backend/services/refresher.py — thread en background que refresca los satélites configurados cuando hay conectividad, respetando TTL y circuit breaker.
6. backend/scripts/prefetch.py — precarga con buena internet; el CACHE_DIR se copia al equipo con mala red.
7. .env — nuevas variables: CACHE_DIR, REQUEST_TIMEOUT, RETRY_*, CIRCUIT_*, REFRESH_INTERVAL, DEFAULT_TTL_*.
8. .gitignore — decidir si se versiona backend/cache/ para distribuir la precarga.
9. Corregir el endpoint /telemetry/{id} hacia el recurso real.

## 5. Notas
- Sin dependencias nuevas pesadas (JSON + stdlib; reintentos vía urllib3.Retry de requests).
- Secretos permanecen en .env (ya gitignoreado).
- Pendientes: definir la lista concreta de satélites del conjunto fijo.
