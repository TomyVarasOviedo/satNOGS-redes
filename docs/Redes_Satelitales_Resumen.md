# Resumen Técnico: Redes Inalámbricas y Satelitales

## 1. Clasificación de Redes Inalámbricas
* **PAN (Personal Area Network):** Estándares Bluetooth y 802.15.3. Velocidad < 1 Mbps. Alcance corto. Comunicación punto a punto.
* **LAN (Local Area Network):** Estándar 802.11. Velocidad de 11 a 54 Mbps. Alcance medio. Redes de área local/empresariales.
* **MAN (Metropolitan Area Network):** Estándares 802.11, 802.16, 802.20. Velocidad 10-100+ Mbps. Alcance medio-largo. Enlaces de última milla.
* **WAN (Wide Area Network):** Estándares GSM, CDMA y Satélite. Velocidad 10 Kbps a 2 Mbps. Alcance largo.

## 2. Espectro y Propagación
Las propiedades físicas de las ondas de radio dependen directamente de su frecuencia operativa:
* **Bajas frecuencias:** Atraviesan obstáculos físicos eficientemente, pero sufren una atenuación de potencia drástica con el incremento de la distancia.
* **Altas frecuencias:** Propagación predominante en línea recta (Line of Sight - LOS); alta susceptibilidad a la reflexión en obstáculos.
* **Modos de propagación:** Superficial, troposférica, ionosférica, espacial y línea de visión.
* **Bandas Satelitales (Espectro SHF/EHF):** L (1 GHz), C (4 y 6 GHz), X, Ku (12 y 14 GHz), K, Ka (20 GHz).

## 3. Arquitectura y Fisiología de Redes Satelitales
* **Función central:** Recepción del enlace ascendente, amplificación de la señal y retransmisión al segmento terrestre.
* **Hardware espacial:** Arreglos de paneles solares, sistemas de antenas, cámaras de monitorización, almacenamiento de telemetría y datos, medidores de gases/nubes y múltiples transpondedores (Transponders).
* **Clasificación orbital:**
  * **LEO (Low Earth Orbit - Órbita Baja):** 640 - 1,600 km.
  * **MEO (Medium Earth Orbit - Órbita Media):** > 9,600 km.
  * **GEO (Geostationary Earth Orbit - Órbita Geoestacionaria):** 36,000 km.
  * **HEO (Highly Elliptical Orbit - Órbita Elíptica).**

## 4. Métodos de Multiplexación y Acceso al Medio (Uplink)
* **FDM (Frequency Division Multiplexing):** Asignación estática de bandas de frecuencia por estación.
* **TDM (Time Division Multiplexing):** Asignación de ranuras de tiempo (timeslots) específicas.
* **ALOHA (Puro/Ranurado):** Transmisiones aleatorias (puras) o encuadradas en ranuras temporales; susceptible a colisiones.
* **CDMA (Code Division Multiple Access):** Transmisión simultánea sobre el mismo canal físico utilizando secuencias de codificación ortogonales.
* **Otros protocolos de acceso:** GSM (FDM+TDM), MACA, CDPD, DQDB, FDDI, SPADE, ACTS, Binder, Crowther, Roberts.

[Falta de información: El material fuente enumera diversos protocolos de la capa de enlace (MAC), pero carece del modelo matemático de contención, las métricas de overhead introducidas y la latencia de propagación específica impuesta por las órbitas (ej. los ~250ms inherentes a enlaces GEO), limitándose a descripciones superficiales de una línea.]

## 5. Arquitectura de Enlaces Satelitales
### 5.1 Enlace SCPC (Single Channel Per Carrier)
* Topología punto a punto dedicada.
* Optimizado para servicios de misión crítica o en tiempo real. Soporta un ancho de banda de hasta 2 Mbps.
* **Cadena de RF y banda base:** MUX/De-MUX, MODEM, Up/Down Converters, Power Amplifier, LNA (Low Noise Amplifier) y OMT (Orthomode Transducer).

### 5.2 Enlace MCPC (Multiple Channel Per Carrier)
* Emplea multiplexación por división de frecuencias (FDM) para consolidar múltiples flujos lógicos sobre una única portadora de radiofrecuencia.

### 5.3 Redes VSAT (Very Small Aperture Terminals)
* **Topología:** Implementación típicamente centralizada (hub-and-spoke). Un nodo central (HUB) gestiona la orquestación del tráfico, la señalización y la asignación del ancho de banda del satélite.
* **Escalabilidad:** Alta densidad, soportando despliegues de hasta 1000 estaciones remotas.
* **Infraestructura en cliente:** Terminales con antenas de diámetro reducido (generalmente 1.3m; siempre menores a 2.4m), lo que facilita instalaciones de bajo costo operativo.
* **Rendimiento:** Velocidades documentadas en el rango de 56 a 64 kbps, permitiendo flujos de datos, voz y video.
* **Bandas operativas:** Mayoritariamente en bandas Ku y C, seleccionadas por su equilibrio óptimo entre la potencia de transmisión requerida y la sensibilidad en recepción.

[Matiz: Las tasas de transferencia documentadas en el texto original para terminales VSAT (56 a 64 kbps) son métricas legacy correspondientes a canales de voz comprimida o control; el hardware VSAT actual en bandas Ku y Ka entrega caudales de banda ancha asimétricos en el orden de los Mbps.]
