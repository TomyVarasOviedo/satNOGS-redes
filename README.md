# Sistema de Monitoreo de Telecomunicaciones Satelitales

Proyecto final para la asignatura **Redes de Datos II**.

## Descripción

Sistema de monitoreo satelital que funciona como un "Dashboard de Gestión de Redes", estableciendo una analogía entre la monitorización de infraestructura terrestre (routers, switches, enlaces WAN) y la infraestructura aeroespacial (satélites de órbita baja - LEO). Interactúa con la red global y abierta de estaciones terrenas **SatNOGS** para explorar conceptos de comunicaciones inalámbricas, análisis de tráfico y arquitecturas de red distribuidas.

## Tecnologías

- **Backend:** Python + FastAPI, skyfield/sgp4 para propagación orbital
- **Demostración:** interfaz `/docs` de FastAPI y notebook Jupyter (el panel web queda como mockup)

## Estructura del Proyecto

```text
📦 Raíz del Proyecto
 ┣ 📂 backend/
 ┃ ┗ 📜 (Lógica del servidor Python)
 ┣ 📂 frontend/
 ┃ ┗ 📜 (Aplicación ReactJS)
 ┗ 📜 AGENTS.md (contexto del proyecto para humanos y agentes)
```

## Buenas Prácticas

- Separación de responsabilidades (SoC): el Frontend solo presenta datos, la lógica vive en el Backend.
- Arquitectura RESTful inversa: el Backend actúa como middleware entre el Frontend y la API de SatNOGS.
- Gestión de secretos: configuración mediante variables de entorno (`.env`), sin hardcoding.
- Componentización y reutilización en React.
- Resiliencia y clean code: manejo estructurado de errores y degradación elegante ante fallos.

## Estado

Prototipo completo: pases, Doppler, margen de enlace y validación contra SatNOGS. Cómo correrlo y guion de la demo en [`backend/README.md`](backend/README.md); alcance y arquitectura en [`AGENTS.md`](AGENTS.md).
