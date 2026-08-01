# Documento de Definición del Proyecto (AGENTES)

## 1. Propósito del Proyecto

Dashboard de monitoreo de telecomunicaciones satelitales para la asignatura **Redes de Datos II** (Unidad N° 6: Redes Satelitales y Nuevas Tecnologías Inalámbricas). El sistema establece la analogía entre la monitorización de infraestructura terrestre (routers, switches, enlaces WAN) y la infraestructura aeroespacial (satélites de órbita baja - LEO), consumiendo la red global y abierta de estaciones terrenas **SatNOGS**.

Funcionalidades principales:

*   **Buscador de satélites** por nombre (catálogo de la SatNOGS DB).
*   **Ficha del satélite** al seleccionarlo: frecuencia de transmisión (uplink/downlink), modo de modulación, baud rate y temperatura de su última observación.
*   **Mapa 2D** con la posición del satélite según su última observación, la estación terrena receptora y su huella de cobertura (*footprint*).
*   **Botón educativo animado** que explica, paso a paso, cómo SatNOGS obtiene los datos: satélite → estación terrena → cliente SatNOGS → Network/DB → nuestra API → dashboard.

El sistema actúa como una capa de abstracción que consume, limpia y presenta la información de la red satelital de forma relevante para el estudio de las redes de datos modernas, facilitando la comprensión de los desafíos inherentes a las transmisiones espaciales (ventanas de visibilidad, efecto Doppler y calidad del enlace).

## 2. Tecnologías Empleadas

*   **Backend:** Python + FastAPI (actúa como *middleware* entre el Frontend y las APIs de SatNOGS). Propagación orbital con `skyfield`/`sgp4` para calcular la posición sub-satélite. Caché en memoria de respuestas para reducir latencia.
*   **Frontend:** ReactJS + Vite. Mapa 2D con MapLibre (o Leaflet). Componentes funcionales reutilizables y manejo de estado predecible y eficiente.

## 3. Directrices y Buenas Prácticas (Best Practices)

El ciclo de desarrollo e implementación de ambas capas del sistema deberá regirse estrictamente por las siguientes mejores prácticas de la industria:

*   **Separación de Responsabilidades (SoC):** El Frontend actuará única y exclusivamente como una capa de presentación (UI) y consumo de datos. Toda lógica de negocio, autenticación con servicios de terceros, formateo de metadatos, control de peticiones y sanitización de respuestas debe ocurrir de forma aislada en el Backend.
*   **Arquitectura RESTful Inversa:** El Backend en Python actuará como un "middleware" o API de paso. La comunicación entre el Frontend local y el Backend local se realizará mediante endpoints REST limpios, protegiendo al Frontend de la complejidad o latencia de la API original.
*   **Gestión de Secretos y Configuración:** Las credenciales, *tokens* de acceso a la API, puertos y URIs de conexión nunca se incluirán de forma estática en el código fuente (zero hardcoding). Se requerirá el uso de variables de entorno (`.env`) independientes para cada entorno.
*   **Componentización y Reusabilidad:** El ecosistema de ReactJS se estructurará mediante componentes funcionales aislados y reutilizables. Se debe priorizar un manejo de estado predecible y eficiente.
*   **Resiliencia y Clean Code:** Se implementará un manejo estructurado de errores (`try/except` robustos en Python, *Error Boundaries* en React), garantizando que si la red de origen experimenta caídas, el sistema muestre un estado de degradación elegante y no un fallo crítico. Se exige código limpio, variables descriptivas y modularidad.

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

El repositorio del proyecto mantendrá un desacoplamiento absoluto. Para ello, el código fuente se estructurará en dos directorios principales en la raíz del proyecto. Ningún dominio debe cruzar las fronteras de su carpeta designada:

```text
📦 Raíz del Proyecto
 ┣ 📂 Backend/
 ┃ ┗ 📜 (Contendrá exclusivamente la lógica del servidor Python, manejadores de rutas,
 ┃      servicios de conexión a SatNOGS, propagación orbital, entornos virtuales y
 ┃      configuración del servidor).
 ┣ 📂 Frontend/
 ┃ ┗ 📜 (Contendrá exclusivamente la aplicación ReactJS, componentes de interfaz visual,
 ┃      vistas, mapa 2D, hojas de estilo y empaquetadores como Vite o Webpack).
 ┗ 📜 AGENTES.md (Documento de definición arquitectónica)
```
