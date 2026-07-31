# Documento de Definición del Proyecto (AGENTES)

## 1. Propósito del Proyecto

El presente proyecto tiene como objetivo principal diseñar e implementar un sistema de monitoreo de telecomunicaciones satelitales, concebido como trabajo final para la asignatura Redes de Datos II. 

El sistema funcionará como un avanzado "Dashboard de Gestión de Redes", estableciendo una analogía directa entre la monitorización de infraestructura terrestre (routers, switches, enlaces WAN) y la infraestructura aeroespacial (satélites de órbita baja - LEO). Al interactuar con la red global y abierta de estaciones terrenas **SatNOGS**, el proyecto permite explorar de manera práctica, visual y dinámica los conceptos de comunicaciones inalámbricas, análisis de tráfico y arquitecturas de red distribuidas.

A través de esta plataforma, se busca proveer una interfaz que facilite la comprensión de los desafíos inherentes a las transmisiones espaciales (como las ventanas de visibilidad, el efecto Doppler y la calidad del enlace). El sistema actuará como una capa de abstracción que consumirá, limpiará y presentará la información de la red satelital de forma que sea relevante para el estudio de las redes de datos modernas.

## 2. Tecnologías Empleadas

Para garantizar un desarrollo ágil, eficiente y alineado con los estándares actuales del mercado, la arquitectura del proyecto se divide en dos tecnologías principales:

*   **Backend:** Python (Ideal para procesamiento de datos, interconexión ágil con APIs externas y lógica de red).
*   **Frontend:** ReactJS (Librería robusta para construir interfaces de usuario reactivas, modulares y de alto rendimiento).

## 3. Directrices y Buenas Prácticas (Best Practices)

El ciclo de desarrollo e implementación de ambas capas del sistema deberá regirse estrictamente por las siguientes mejores prácticas de la industria:

*   **Separación de Responsabilidades (SoC):** El Frontend actuará única y exclusivamente como una capa de presentación (UI) y consumo de datos. Toda lógica de negocio, autenticación con servicios de terceros, formateo de metadatos, control de peticiones y sanitización de respuestas debe ocurrir de forma aislada en el Backend.
*   **Arquitectura RESTful Inversa:** El Backend en Python actuará como un "middleware" o API de paso. La comunicación entre el Frontend local y el Backend local se realizará mediante endpoints REST limpios, protegiendo al Frontend de la complejidad o latencia de la API original.
*   **Gestión de Secretos y Configuración:** Las credenciales, *tokens* de acceso a la API, puertos y URIs de conexión nunca se incluirán de forma estática en el código fuente (zero hardcoding). Se requerirá el uso de variables de entorno (`.env`) independientes para cada entorno.
*   **Componentización y Reusabilidad:** El ecosistema de ReactJS se estructurará mediante componentes funcionales aislados y reutilizables. Se debe priorizar un manejo de estado predecible y eficiente.
*   **Resiliencia y Clean Code:** Se implementará un manejo estructurado de errores (`try/except` robustos en Python, *Error Boundaries* en React), garantizando que si la red de origen experimenta caídas, el sistema muestre un estado de degradación elegante y no un fallo crítico. Se exige código limpio, variables descriptivas y modularidad.

## 4. Estructura del Proyecto

El repositorio del proyecto mantendrá un desacoplamiento absoluto. Para ello, el código fuente se estructurará en dos directorios principales en la raíz del proyecto. Ningún dominio debe cruzar las fronteras de su carpeta designada:

```text
📦 Raíz del Proyecto
 ┣ 📂 Backend/
 ┃ ┗ 📜 (Contendrá exclusivamente la lógica del servidor Python, manejadores de rutas, 
 ┃      servicios de conexión, entornos virtuales y configuración del servidor).
 ┣ 📂 Frontend/
 ┃ ┗ 📜 (Contendrá exclusivamente la aplicación ReactJS, componentes de interfaz visual, 
 ┃      vistas, hojas de estilo y empaquetadores como Vite o Webpack).
 ┗ 📜 AGENTES.md (Documento de definición arquitectónica)
```

> *Nota: La definición estricta de las variables, los esquemas de datos a consumir y los endpoints específicos a invocar desde la red SatNOGS se determinarán en la fase de refinamiento técnico, una vez que la estructura base del repositorio esté consolidada.
