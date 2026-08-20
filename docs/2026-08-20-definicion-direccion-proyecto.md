# Minuta de Reunión

- **Fecha:** 2026-08-20
- **Tema:** Definición de la dirección del proyecto final (Redes de Datos II)
- **Proyecto:** Sistema de Monitoreo de Telecomunicaciones Satelitales

## 1. Objetivo de la reunión

Analizar el estado actual del proyecto y seleccionar una dirección concreta para el trabajo final que resuelva un problema real y tenga una duración estimada de más de 3 semanas.

## 2. Análisis del estado actual del proyecto

### 2.1 Backend (FastAPI, `backend/main.py`)

Actúa como proxy REST inverso entre un frontend React y las APIs de SatNOGS:

- `GET /` → health check.
- `GET /satelite/{satelite_id}` → metadatos por UUID `sat_id` (DB API).
- `GET /satelites/{satelite_name}` → búsqueda por nombre, con caché LRU y paginación.
- `GET /observations/{satelite_id}` → observaciones por `sat_id` (Network API).
- `GET /observations/id/{id}` → observación puntual por ID.
- `GET /telemetry/{satelite_id}` → telemetría.

### 2.2 Problemas detectados

1. `/observations/id/{id}` falla con error 301: SatNOGS exige barra final (`/observations/{id}/`).
2. `/satelite/25544` (NORAD) devuelve `[]`: el endpoint espera el UUID (`XXXX-XXXX-XXXX-XXXX`), no el NORAD.
3. Varios handlers no tienen timeouts; hay llamadas `requests` síncronas dentro de handlers async que bloquean el event loop.
4. `/telemetry/{id}` está roto (TODO pendiente en el código; el recurso real devuelve 404).
5. La estrategia de resiliencia definida en la minuta `2026-08-05-resiliencia-backend-conectividad-limitada.md` (caché a disco, circuit breaker, refresher en background, prefetch) **no está implementada**.
6. **El frontend React no existe todavía**; solo está el backend.

### 2.3 Datos reales disponibles (verificados en respuestas capturadas en `backend/requests/.timeline/*.bodies/`)

- **Satélite:** `sat_id` (UUID), `norad_cat_id`, `name`, `status`, `launched`, `countries`, etc.
- **Observación:** `start`/`end` (ventana del pase), `station_name`, `station_lat/lng/alt`, `rise_azimuth`, `set_azimuth`, `max_altitude`, `observation_frequency`, bloque `transmitter_*` (`downlink_low`, `downlink_drift`, `mode`, `baud`) y **TLE embebida** (`tle0/1/2`).
- **Telemetría:** frames en hex, timestamp, NORAD, observador.

Los campos TLE y `transmitter_downlink_drift` son la base para cómputo orbital y de enlace.

## 3. Alternativas evaluadas

Se evaluaron cuatro direcciones posibles, todas construidas sobre el backend actual y alineadas con el documento de la materia (`docs/Redes_Satelitales_Resumen.md`):

### Alternativa A — NOC satelital: predicción de pases + calidad de enlace

- **Problema a resolver:** "¿qué satélite pasa por mi estación, cuándo, y con qué calidad lo captaré?".
- **Contenido:** propagación orbital (TLE/SGP4), predicción de ventanas AOS/LOS, corrección Doppler, link budget (FSL/CNR), ground track en mapa.
- **Validación:** contrastar predicciones contra el histórico real de observaciones de SatNOGS.
- **Duración estimada:** 3–4 semanas.

### Alternativa B — Simulador de acceso al medio (ALOHA/TDMA/CDMA/FDMA)

- **Problema a resolver:** "¿qué protocolo MAC conviene para un uplink satelital dada una carga?" (sección 4 del doc de la materia).
- **Contenido:** simulación por eventos discretos de ALOHA puro/ranurado, TDMA, FDMA y CDMA, parametrizada con datos reales (baud, frecuencia, nº de estaciones, latencia GEO ~250 ms).
- **Resultado:** gráficas comparativas de throughput/colisiones.
- **Duración estimada:** ~3 semanas.

### Alternativa C — Planificador de red VSAT / enlace de última milla

- **Problema a resolver:** diseñar una red VSAT hub-and-spoke (sección 5.3) dados sitios y banda (Ku/C).
- **Contenido:** cálculo de FSL, EIRP, CNR, disponibilidad por lluvia y mapas de cobertura; estaciones reales de SatNOGS como sitios candidatos.
- **Duración estimada:** ~3 semanas.

### Alternativa D — Combinación (A + B + fases de saneamiento)

- **Contenido:** arreglar backend + resiliencia, predicción de pases + Doppler + link budget, y simulador de acceso al medio.
- **Duración estimada:** 4+ semanas. Máximo impacto y mejor aprovechamiento de lo ya construido.

## 4. Decisiones tomadas

1. **Se selecciona la Alternativa A** como dirección del proyecto: **NOC Satelital — Predicción de pases + Calidad de enlace.**
2. **Se descarta la demodulación de radio real** (requeriría hardware SDR/antena y excede el alcance de Redes de Datos II); el proyecto se enfoca en predicción computacional, corrección de frecuencia y estimación de calidad de enlace.
3. **El frontend se crea desde cero** (opcionalmente reutilizando las vistas de la Alternativa D como base de librerías).
4. **El plan se documenta en `AGENTES.md`** como fuente de verdad para cualquier agente humano o IA que trabaje en el repo.
5. **La Fase 0 incluye el saneamiento del backend** (bugs conocidos) y la implementación de la resiliencia pendiente de la minuta del 05-08.

## 5. Caso de uso de referencia (ejemplo concreto)

"Un radioaficionado en Rosario quiere captar el pase del LUSAT esta noche" — el sistema:

1. Obtiene los metadatos y la TLE real del LUSAT (NORAD 20442) desde SatNOGS.
2. Propaga la órbita (movimiento medio 14.34 rev/día → período ~100 min → altura ~785 km → clasificación **LEO**).
3. Predice los pases para Rosario (tabla AOS/LOS, elevación/acimut máximos, duración).
4. Calcula la curva de corrección Doppler (nominal 437.125 MHz; en LEO el desplazamiento alcanza ~±10.8 kHz; el histórico real ya muestra +1350 Hz de corrimiento y 3088 Hz de drift instantáneo en la estación).
5. Estima el link budget por geometría del pase (ej. a 45° de elevación: distancia ~1055 km → FSL ≈ 145.7 dB) y responde si la señal podrá decodificarse según modo/baud reales.
6. Visualiza el ground track y el footprint en un mapa.
7. Valida la predicción contra pases históricos reales (ej. 18:30:51 → 18:38:05, elevación máx. 85°) y reporta métricas de error.

## 6. Próximos pasos

1. Documentar el plan detallado en `AGENTES.md` (realizado en esta misma sesión).
2. Iniciar la Fase 0: saneamiento del backend + resiliencia + scaffold del frontend.
3. Confirmar satélites del conjunto fijo a monitorear (pendiente de la minuta 2026-08-05).

## 7. Notas

- Los datos de ejemplo utilizados provienen de las respuestas reales capturadas en `backend/requests/.timeline/`.
- La definición de variables, esquemas y endpoints de predicción queda especificada en la sección 9 de `AGENTES.md`.

# Session de Opencode

```bash
opencode -s ses_fe0dd391fffe4EjXWDuiWr7XEa
```

