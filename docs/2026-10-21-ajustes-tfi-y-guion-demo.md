# Ajustes al documento del TFI y guion de la demo

- **Fecha:** 2026-10-21
- **Estado:** el prototipo está completo en `main`, con los PRs #1 a #5 mergeados y 73 tests pasando.

Hay tres partes:
1. qué cambiar en el documento "NOC Satelital como Servicio", sección por sección;
2. qué hacer el día de la demo;
3. el guion de la demo.

---

## 1. Ajustes al documento del TFI

Salieron de construir el prototipo con datos reales. Para cada uno va la sección, qué dice hoy y qué proponemos. Los textos sugeridos se pueden pegar tal cual.

### §3.7 Presupuesto de enlace: los umbrales ya tienen fuente

Cierra el pendiente del §7 "documentar de dónde salen los umbrales". Texto sugerido para agregar al final del §3.7:

> Los umbrales de decodificación son el Eb/N0 necesario para una tasa de error de bit de 10⁻⁵ en un canal con ruido blanco gaussiano (Sklar, 2001, §4.7–4.8):
> - BPSK, QPSK, OQPSK, MSK y GMSK (coherentes): 9,6 dB.
> - FSK, GFSK y AFSK (no coherentes): 13,4 dB.
>
> Para AFSK, que son tonos de audio sobre FM, es una simplificación. Los modos analógicos (CW, FM, SSB) no tienen umbral digital. El ancho de banda de ruido se toma igual a la tasa de símbolos. Por defecto el margen se calcula con un EIRP de 0 dBW (1 W isotrópico), una antena receptora de 12 dBi, 500 K de temperatura de sistema y sin pérdidas adicionales, todo configurable. Por eso es una estimación optimista.

Agregar a Referencias: *Sklar, B. (2001). Digital communications: Fundamentals and applications (2.ª ed.). Prentice Hall.*

### §4.5 Estrategia de validación: sacar la métrica "error de frecuencia Doppler"

**Hoy dice:** la tabla incluye "Error de frecuencia Doppler (Hz) — deriva máxima informada por el transmisor y diferencia entre frecuencia nominal y observada".

**El problema:** SatNOGS **no guarda el Doppler medido** de cada observación.
- **El campo `transmitter_downlink_drift`** es la deriva del oscilador del satélite, en partes por mil millones (ppb). No es Doppler.
- **La prueba:** en una observación real de LUSAT, `observation_frequency` = 437 125 000 · (1 + 3088·10⁻⁹) = 437 126 350 Hz, exactamente el valor publicado.

**Texto sugerido** para reemplazar esa fila y agregar debajo de la tabla:

> El Doppler no se valida contra SatNOGS, porque la plataforma no publica la frecuencia medida durante el pase. La diferencia entre la frecuencia nominal y la observada corresponde a la deriva del oscilador del transmisor. El Doppler predicho se verifica con la física:
> - la curva empieza por encima de la nominal;
> - la cruza en el punto de máxima aproximación;
> - termina por debajo, con un corrimiento del orden de ±10 kHz en UHF para LEO.

**También en §4.5 y §5.7: qué valida realmente la comparación.** Texto sugerido:

> Los instantes de inicio y fin y los acimuts de SatNOGS describen la ventana que agendó su planificador. Esa ventana surge de su propia predicción SGP4 y muchas estaciones la recortan con su horizonte. Coincidir con ellos valida la implementación del cálculo, no la órbita real. Por eso la elevación máxima y los acimuts se comparan dentro de la ventana observada. Como SatNOGS los publica redondeados a grados enteros, el error esperable ronda ±0,5°.

### §4.8 Supuestos y limitaciones: los pases ya no se muestrean

**Hoy dice:** "Los pases se calculan muestreando la posición cada 30 a 60 segundos, por lo que la resolución de AOS y LOS está acotada por ese paso".

**Texto sugerido:**

> AOS y LOS se calculan como los instantes exactos en que la elevación cruza la máscara, buscando la raíz con skyfield (`find_events`). Su precisión ya no depende de un paso de muestreo. El error que queda viene de la antigüedad del TLE.

Hay que hacer el mismo cambio en el §5.5, donde dice "propaga la posición cada 30 a 60 segundos".

### §5.8 Organización del repositorio: todo está construido

- En la tabla de módulos, cambiar "A construir" por "Construido" en `orbits.py`, `doppler.py`, `linkbudget.py`, `validation.py` y el notebook. El notebook vive en `backend/notebooks/analisis.ipynb`.
- En la tabla de endpoints, agregar `GET /predictions/groundtrack`, que devuelve el punto subsatelital y la geometría respecto de la estación.

### §7 Pendientes: dos que ya se pueden cerrar

- **Umbrales de decodificación:** resuelto, ver §3.7 arriba.
- **La ISS está por debajo del rango LEO de la cátedra.** Texto sugerido:

> El sistema clasifica como LEO toda órbita por debajo de 2000 km, que es la definición habitual. El rango de 640 a 1600 km de la cátedra dejaría afuera a la ISS (~420 km) y a muchos CubeSats.

### Nueva §9 Prototipo: resultados para pegar

Todos los gráficos salen del notebook (`backend/notebooks/analisis.ipynb`).

**Órbita de LUSAT** (`/orbits/classify`):
- LEO, con período de 100,4 min y altura de 785 km;
- inclinación de 98,9°;
- huella de 2084 km de radio para una máscara de 10°.

**Agenda de pases sobre la Universidad de Belgrano** (`/predictions/passes`): 8 pases de LUSAT en 2 días. El mejor llega a 76° de elevación, con 29,7 dB de margen en el TCA y 20,4 dB en la máscara.

**Doppler** (`/predictions/doppler`), en un pase de LUSAT de 23°:
- la frecuencia va de +7,3 kHz a −7,3 kHz sobre 437,150 MHz;
- cruza la nominal en el TCA;
- la variación más rápida es de −43,8 Hz/s, en el centro del pase.

**Validación contra observaciones reales** (`/validation/satellite`, 7 días):

| Satélite | Observaciones | Elevación máx. (\|error\| medio / máximo) | Acimut de subida | Acimut de puesta |
| ----- | ----- | ----- | ----- | ----- |
| ISS | 100 | 0,26° / 0,95° | 0,24° / 0,53° | 0,26° / 0,55° |
| LUSAT | 2 | 0,38° / 0,41° | 0,29° / 0,43° | 0,11° / 0,15° |

Lectura sugerida para el documento:

> Los errores de geometría se distribuyen de manera uniforme entre ±0,5°, que es justamente la firma del redondeo a grados enteros de SatNOGS. Es decir, el error de predicción no se distingue de la resolución de la referencia. La diferencia de 100 a 450 s en el inicio y el fin no es error de predicción: corresponde a estaciones que agendan solo parte del pase.

**Prueba de resiliencia:** con la red cortada, todos los endpoints de la demo responden desde la caché local, con `X-Source: cache` o `stale`.

---

## 2. Aviso: qué hacer el día de la demo

**La caché de la validación se renueva por día.** La clave lleva la fecha UTC, así que la caché que esté commiteada hoy no sirve para validar sin conexión otro día. Por eso, **el mismo día de la demo y con buena conexión**:

```bash
./backend/scripts/preparar_demo.sh
```

Esto hace cuatro cosas:
1. instala las dependencias y corre los tests;
2. precarga la caché de los satélites;
3. llama a cada endpoint que se muestra en la demo;
4. vuelve a ejecutar el notebook, para que los gráficos tengan los pases de ese día.

Después, **con el wifi cortado**, verificar que todo sale de la caché:

```bash
./backend/scripts/preparar_demo.sh --offline
```

Tiene que listar todos los endpoints con `200` y `cache` o `stale`. Si alguno falla, la demo sin conexión no va a andar en ese paso.

Si alguien usa Windows, el script se corre desde Git Bash.

---

## 3. Guion de la demo (~4 minutos, punto 4 del pitch)

Antes de empezar, dejar abiertos:
- el backend (`cd backend && uv run uvicorn main:app`);
- el navegador en `http://127.0.0.1:8000/docs`;
- el notebook en JupyterLab, ya ejecutado (`uv run --group notebook jupyter lab notebooks/analisis.ipynb`).

| Tiempo | Qué se muestra | Qué se dice |
| ----- | ----- | ----- |
| 0:00 | `/docs`, `GET /predictions/passes`, `sat_id = ZDPY-4221-9426-0630-5344` (LUSAT), Execute | "Esta es la agenda de contactos del operador: cuándo pasa LUSAT sobre la estación de la UB en los próximos dos días, cuánto dura cada pase, a qué elevación llega y con cuánto margen de enlace. Un margen positivo quiere decir que se puede decodificar." |
| 0:45 | En la respuesta, un pase alto y su `link.margin_at_tca_db` frente a `margin_at_aos_db` | "El margen es mejor en el centro del pase, cuando el satélite está más cerca. Sobre la máscara de 10° la distancia oblicua llega a más de 2000 km y se pierde señal." |
| 1:15 | Notebook, gráfico Doppler | "La frecuencia a sintonizar cambia durante todo el pase: empieza 7 kHz arriba, cruza la nominal en el punto de máxima aproximación y termina 7 kHz abajo. Sin corregir esto, el receptor pierde la señal." |
| 1:45 | Notebook, margen a lo largo del pase | "Este es el margen minuto a minuto contra el umbral de decodificación de BPSK a 1200 baudios." |
| 2:15 | `/docs`, `GET /validation/satellite`, `sat_id = XSKZ-5603-1870-9019-3066` (ISS), o el histograma del notebook | "¿Podemos confiar en la predicción? La comparamos contra 100 observaciones reales de la red SatNOGS de la última semana. El error de elevación y de acimut queda por debajo de 1°, al nivel del redondeo de la propia referencia." |
| 3:00 | Cortar el wifi, repetir `GET /predictions/passes`, mostrar el header `x-source: cache` | "SatNOGS es una red de voluntarios y se puede caer. El servicio sigue respondiendo desde su caché y avisa de dónde sale cada dato." |
| 3:30 | Mockups del panel y de la alerta | "Esto es lo que se ve hoy por la API. Así lo vería el cliente en el producto: el panel con sus satélites y una alerta en el teléfono cuando un pase viene sin margen." |

**Plan B:**
- **Si `/docs` no responde:** usar las salidas guardadas en el notebook.
- **Si no hay pases de LUSAT en la ventana:** usar la ISS con `sat_id = XSKZ-5603-1870-9019-3066`.
- **Si el pase de Doppler ya ocurrió durante la demo:** el endpoint toma siempre el próximo.
