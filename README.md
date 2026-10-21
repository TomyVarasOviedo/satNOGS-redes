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

Fase 0 (proxy de SatNOGS con caché y resiliencia) hecha en la rama `backend`. Alcance, arquitectura y endpoints del prototipo en [`AGENTS.md`](AGENTS.md).
