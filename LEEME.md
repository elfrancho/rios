# Ríos Iguazú – Paraná · contenido para @elfrancho

Estado al 19/10/2026, 13 h. Proyecto personal de Francisco. Todo corre en la notebook **SFE-NB-001**.

## Qué hay y dónde

| Qué | Dónde | Cómo se regenera |
|---|---|---|
| Tablero interactivo 1980-hoy (Iguazú, Andresito, Posadas, Corrientes, Santa Fe) | `rios.html` | `python bajar_ina.py datos_ina` y después `python armar.py` |
| Tablero histórico del río Salado (Tostado, Recreo/Ruta 70 desde 1980, Laguna Setúbal, último año de 8 estaciones, Paraná en Santa Fe) | `salado.html` | `python bajar_salado.py` y después `python armar_salado.py` |
| Simulación interactiva "La ola del Paraná" (mapa con barra de tiempo; crecida actual, 2023, 2014, 2013, 1992 y 1983; color según nivel de cada puerto) | `ola.html` | `python armar_ola.py` (después de actualizar datos_ina) |
| Datos diarios del INA, y de la base nacional (SNIH) para completar huecos | `datos_ina\`, `datos\` | `bajar_ina.py`, `bajar_snih.py` |
| Hallazgos del análisis histórico (récords, bajante, ciclo semanal de Itaipú, demoras) | `analisis_salida.txt`, `analisis2_salida.txt` | `analisis.py`, `analisis2.py` |
| Carrusel 4:5 y 9 historias del 16/10 | `historias\png_carrusel\`, `historias\png\` | `historias\armar_historias.py` |
| **Parte diario** (2 historias desde el 21/10/2026) | `historias\partes\<fecha>\` | `historias\parte_diario.py [--formato X] [--sin-video]`; lo envía `enviar_parte.ps1` |
| **Historia del río Salado** (8 estaciones, red de alerta provincial vía CIM-FICH, lectura 00 h; sale los sábados como historia 2 del parte) | `historias\partes\<fecha>\parte_4.png` | `historias\salado.py [carpeta]` |
| **Aviso de la noche** (1 historia, solo con novedad) | `historias\partes\<fecha>\aviso.png` | `historias\aviso_noche.py`; lo envía `enviar_aviso.ps1` |
| Historial propio de lecturas de Prefectura | `datos_prefectura\lecturas.csv` | se completa en cada parte |
| Reel "El viaje del agua" (crecida 2013, voz de Jorge) | `historias\animacion\reel\` | `historias\animacion\armar_reel.py` |
| Reel "107 metros" (desnivel Iguazú → Santa Fe) | `historias\animacion\reel_107\` | `historias\animacion\armar_reel_107.py` |
| Reel "¿Agua negativa?" (−0,23 m en Santa Fe, 2022: el cero no es el fondo; 30 s) | `historias\animacion\reel_cero\` | `historias\animacion\armar_reel_cero.py` (toma la última lectura de Santa Fe; avisa si el guion ya no coincide) |
| Reel timelapse "¿Por qué abajo sube tan poquito?" (7 semanas en cámara rápida, datos horarios del SNIH; prueba del 19/10) | `historias\animacion\reel_timelapse\` | `python bajar_snih_horario.py` (deja `datos_snih\`) y después `historias\animacion\armar_reel_timelapse.py` |
| Historias sueltas (pronóstico INA, Día de la Madre con el chajá) | `historias\extra\` | HTML + Chrome headless (ver cada .html) |
| Historia promo de la web (video 14 s con la ola en un celular + flyer fijo, 20/10) | `historias\extra\promo_web\` | `node historias\animacion\capturar_ola.js ola.html historias\extra\promo_web\ola 36 0`, después `captura.js promo.html cuadros` + ffmpeg (ver comentario en `promo.html`; las fechas del mapa están fijas en el script) |
| Fotos de su Instagram usadas de fondo | `historias\fotos_ig\`, `historias\fondos\` | — |

## Parte diario: cómo está armado (rediseño del 21/10/2026)

Antes eran 4 historias iguales todos los días y cansaban. Ahora son 2:
- **Historia 1, la noticia del día.** El titular se arma solo con lo que pasó: un puerto que cruzó una marca, que se movió fuerte en un día o en la semana, que sigue en evacuación, o Santa Fe. Ese puerto queda como protagonista, con el número grande, y el resto va en lista. Si el protagonista repite el de ayer y no cruzó ninguna marca, pierde prioridad para que rote (`protagonista` en `estado.json`). El color sigue al protagonista: coral si está en evacuación, ámbar en alerta, verde si sube y azul si está quieto. La parte de abajo queda libre, con la foto, para pegar una encuesta.
- **Historia 2, rota según el día** (`ROTACION` en `parte_diario.py`): lunes y viernes la onda (gráfico, también en video); martes la escala de cada puerto ("¿Cuánto falta para la alerta?"); miércoles y domingo "¿Es mucho para un 21 de octubre?" (el mismo día desde 1980, Santa Fe y Corrientes); jueves el dato del día; sábado el río Salado (si el CIM falla, sale el dato).
- `mail.txt` lleva qué es cada historia y la **encuesta sugerida** del día; `enviar_parte.ps1` la pega en el mail.
- Copias de antes del rediseño: `historias\*.bak-20261021`.

## Sitio público

- **https://elfrancho.github.io/rios/** — portada con la ola, el Paraná desde 1980 y el Salado. Repo `elfrancho/rios` (cuenta personal de GitHub), carpeta local `web/`.
- **Desde el 20/10/2026 se actualiza sola cada hora en GitHub** (`.github/workflows/web.yml`), aunque la notebook esté apagada: baja INA y Salado, arma y publica; si una fuente falla, publica con los últimos datos del repo y commitea los datos nuevos. Esta carpeta `rios\` es el repo (las historias quedan afuera por `.gitignore`).
- `python publicar_web.py` sube cambios de plantillas/scripts (y pide una actualización); `--local` arma `web\` para revisar sin publicar. El parte de las 13:00 lo sigue llamando al final.
- Para tocar el workflow hace falta el permiso `workflow` en el token de elfrancho (ya otorgado el 20/10).
- Revisión en celular y PC: `node historias\animacion\capturar_web.js http://localhost:8765/web <carpeta>` (emula un celular de 390 px y una PC de 1440 px, y avisa si algo se sale del ancho). Imagen para compartir el link: `og.png` (se genera desde `og.html`).
- Foto de perfil (`perfil.jpg`, bajada de su Instagram) y botón "Seguime en Instagram" en la portada; chip con foto y @elfrancho arriba de cada página.
- Bloque "¿Te sirve?" para aportes: se activa completando `CAFECITO` y/o `ALIAS` arriba de `publicar_web.py`; vacíos, no se muestra.
- Visitas: GoatCounter, panel en https://elfrancho.goatcounter.com (cuenta de francho14@, por hora/día, referencias, celular/PC, export CSV de cada visita). La portada muestra "👀 N visitas" sumando las 4 páginas (el TOTAL de GoatCounter tarda en actualizarse). El script se inserta antes del ÚLTIMO `</body>`: ECharts trae ese texto adentro y romperlo deja los gráficos en blanco (pasó el 20/10).
- Estilo único oscuro en las 4 páginas (paleta de la portada); copia de las plantillas viejas en `respaldo_estilos\`.
- `gh` tiene dos cuentas: la activa es **grupobca** (trabajo) y no hay que cambiarla; el sitio usa el token de **elfrancho** solo para el push.

## Tareas programadas (Windows)

- **Parte del rio (elfrancho):** todos los días a las 13:00. Arma 3 historias con la lectura de las 12 de Prefectura y las manda por mail a francho14@gmail.com. El "desde ayer" y "en la semana" se calculan contra la lectura de Prefectura más cercana a 24 h / 7 días antes (historial propio); el INA solo completa huecos, porque publica una sola lectura diaria (00 h). Si el INA no responde, el parte sale igual. La historia 2 sale además animada (`parte_2.mp4`, 15 s, la graba `animacion\captura.js` con la plantilla en modo `#2v`); si el video falla, el mail sale solo con las imágenes y el log dice "sin video".
- **Aviso del rio (elfrancho):** todos los días a las 20:30. Compara con el parte del mediodía (`estado.json`) y manda 1 historia solo si un puerto cambió de nivel, se movió 15 cm o más (1,5 m en Puerto Iguazú) o el INA publicó un pronóstico nuevo.
- Si la notebook está apagada a esa hora, la tarea corre cuando se prende. Los envíos y errores quedan en `historias\partes\envios.log`.

## Cómo hacer un reel nuevo

1. Copiar `armar_reel_107.py` y `plantilla_reel_107.html` como base.
2. En `GUION`, cada frase lleva sus "anclas": la palabra que dispara un momento de la animación.
3. La voz es siempre `es-MX-JorgeNeural`. El script trae la marca de tiempo de cada palabra; con eso se sincronizan la animación y los subtítulos.
4. Antes de mandarlo, revisar cuadros sueltos con ffmpeg y que ninguna frase llegue cortada (el script reintenta solo).
5. Herramientas usadas: Chrome, puppeteer-core (npm, en `animacion\`), ffmpeg, edge-tts, Pillow, PyMuPDF.

## Pendiente / ideas

- **Martes 20/10:** el INA publica el pronóstico nuevo por puerto. Hacer una historia de actualización; el aviso de la noche avisa que salió.
- **Miércoles 21/10:** informe semanal del INA.
- Revisar las métricas de los dos reels desde su Instagram (ver la memoria de la asesoría de Instagram).
- Quedaron sin mandar por mail: el reel de los 107 m corregido y la historia del chajá. Preguntarle si los quiere.
- Ideas de curiosidades para reels: "cuánta agua es": 37.000 m³/s ≈ 15 piletas olímpicas por segundo; el río "tiene fin de semana" (Itaipú); la bajante 2020-22 fue más larga que la de 1944; antes y después con sus fotos.
- Lecturas al 19/10 12 h: Corrientes 7,10 m (sobre evacuación), Goya 5,40, Reconquista 4,87, Santa Fe 3,77, Rosario 3,49, Puerto Iguazú 29,60 (bajando).
