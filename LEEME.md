# Ríos Iguazú – Paraná · contenido para @elfrancho

Estado al 25/10/2026. Proyecto personal de Francisco. Todo corre en la notebook **SFE-NB-001**.

## Qué hay y dónde

| Qué | Dónde | Cómo se regenera |
|---|---|---|
| Tablero interactivo 1980-hoy (Iguazú, Andresito, Posadas, Corrientes, Santa Fe) | `rios.html` | `python bajar_ina.py datos_ina` y después `python armar.py` |
| Tablero histórico del río Salado (Tostado, Recreo/Ruta 70 desde 1980, Laguna Setúbal, último año de 8 estaciones, Paraná en Santa Fe) | `salado.html` | `python bajar_salado.py` y después `python armar_salado.py` |
| Simulación interactiva "La ola del Paraná" (mapa con barra de tiempo; crecida actual, 2023, 2014, 2013, 1992 y 1983; color según nivel de cada puerto) | `ola.html` | `python armar_ola.py` (después de actualizar datos_ina) |
| **Las crecidas desde el espacio** (página web, 24/10/2026): cortina para comparar dos imágenes satelitales del mismo recuadro, con agua resaltada, altura del día y km² de agua. Paraná: 1992, 1998, 2010, 2016, bajante 2022, 2023 y hoy. Salado: abril y mayo de 2003, abril de 2016 y hoy. No hay Landsat de 1983 | `satelite.html` (web), `satelite\img\` y `satelite\escenas.json` (van al repo ya procesadas) | `python satelite\armar_imagenes.py [id ...]` SOLO en la notebook (rasterio); para sumar una crecida, agregar una fila a `EVENTOS` y correrlo; después `python publicar_web.py` |
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
| Reel "Corrientes, el octubre más alto en 46 años" (21/10/2026: 7,37 m vs 7,24 m de 1998; puntos de cada 21/10 desde 1980, Reconquista en alerta, Santa Fe a 1,45 m de la alerta; 31 s) | `historias\animacion\reel_record\` (+ `texto_reel.txt`) | `historias\animacion\armar_reel_record.py` (fecha fija en `HOY`; avisa si la lectura ya no coincide con el guion) |
| Reel "Corrientes, el octubre más alto en 46 años" versión 22/10 (barras simples con los octubres más altos desde 1980, +1,94 m en una semana, Puerto Iguazú vuelve a evacuación, Santa Fe a 1,42 m de la alerta; 28 s). Reemplaza al de `reel_record`, que no se publicó y usaba puntos (confusos) | `historias\animacion\reel_octubre\` (+ `texto_reel.txt`) | `historias\animacion\armar_reel_octubre.py` (fecha fija en `HOY`; avisa si la lectura ya no coincide) |
| Reel "¿Hay que asustarse?" (23/10/2026, 52 s, en primera persona y prudente: Corrientes sobre evacuación pero 1,61 m debajo de 1983; Santa Fe 3,98 vs alerta 5,30; pronóstico INA del 20/10 ~4,92 m el 3/11; 2016 y 1992; "atentos sí, pánico no"; Defensa Civil). Las fuentes de cada frase están en el docstring | `historias\animacion\reel_calma\` (+ `texto_reel.txt`) | `historias\animacion\armar_reel_calma.py` (avisa si algún número del guion ya no coincide) |
| Reel timelapse "¿Por qué abajo sube tan poquito?" (7 semanas en cámara rápida, datos horarios del SNIH; prueba del 19/10) | `historias\animacion\reel_timelapse\` | `python bajar_snih_horario.py` (deja `datos_snih\`) y después `historias\animacion\armar_reel_timelapse.py` |
| **Panorama del Salado** (carrusel 4:5 de 6 láminas, `carrusel_1..6.png` + `texto_carrusel.txt`, y versión de 2 historias; estética propia, tonos de agua barrosa: mapa esquemático de norte a sur con cada estación, y "3 datos": meses de Tostado sobre la alerta, cuánto bajó Recreo y Santo Tomé que sigue al Paraná, con correlación calculada 0,98). Los afluentes van en texto, sin dibujar dónde desembocan | `historias\extra\salado_panorama\` | `python historias\extra\salado_panorama\armar.py` (usa el CIM del día + `datos_salado`; toma medianas porque hay lecturas sueltas erróneas) |
| **Imágenes satelitales** (24/10/2026): 4 modelos de reel sin voz con Santa Fe desde el satélite (cortina bajante 2022 → hoy, "el agua que volvió" con km² de agua por NDWI, Landsat 27/06/1992 vs 21/09/2026, pantalla partida de la Setúbal). Fuente: Microsoft Planetary Computer, sin cuenta (Sentinel-2 L2A y Landsat C2 L2). Créditos obligatorios en el video | `historias\animacion\satelite\` (`escenas\*.npz`, `modelo_1..4.mp4`) | `buscar.py` (escenas sin nubes), `bajar.py` (alinea en grilla 9:16 de 15 m), `modelos.py` (arma los videos). Librerías: pystac-client, planetary-computer, rasterio |
| **Reel "Santa Fe desde el espacio"** (24/10/2026, 92 s, voz William): regla animada que explica la altura del río, bajante 2022 → hoy con cortina y agua resaltada, Landsat 1992, el Salado en 2003 (Landsat 7 del 15/04 y del 01/05, con nubes marcadas por qa_pixel y agua por MNDWI) y cierre "atentos, sin pánico". Fuentes en el docstring | `historias\animacion\satelite\reel_satelital.mp4` (+ `_mail.mp4` liviana y `texto_reel.txt`) | `bajar.py`, `bajar_2003.py`, `reel_satelital.py` |
| Historias sueltas (pronóstico INA, Día de la Madre con el chajá) | `historias\extra\` | HTML + Chrome headless (ver cada .html) |
| Historia promo de la web (video 14 s con la ola en un celular + flyer fijo, 20/10) | `historias\extra\promo_web\` | `node historias\animacion\capturar_ola.js ola.html historias\extra\promo_web\ola 36 0`, después `captura.js promo.html cuadros` + ffmpeg (ver comentario en `promo.html`; las fechas del mapa están fijas en el script) |
| Fotos de su Instagram usadas de fondo | `historias\fotos_ig\`, `historias\fondos\` | — |

## Parte diario: cómo está armado (rediseño del 21/10/2026)

Antes eran 4 historias iguales todos los días y cansaban. Ahora son 2:
- **Historia 1, la noticia del día.** El titular se arma solo con lo que pasó: un puerto que cruzó una marca, que se movió fuerte en un día o en la semana, que sigue en evacuación, o Santa Fe. Ese puerto queda como protagonista, con el número grande, y el resto va en lista. Si el protagonista repite el de ayer y no cruzó ninguna marca, pierde prioridad para que rote (`protagonista` en `estado.json`). El color sigue al protagonista: coral si está en evacuación, ámbar en alerta, verde si sube y azul si está quieto. La parte de abajo queda libre, con la foto, para pegar una encuesta.
- **Historia 2, rota según el día** (`ROTACION` en `parte_diario.py`): lunes y jueves la onda (gráfico, también en video); martes y viernes la escala de cada puerto ("¿Cuánto falta para la alerta?"); miércoles y domingo el dato del día; sábado el río Salado (si el CIM falla, sale el dato). El formato "historia" (puntos del mismo día desde 1980) existe pero quedó fuera de la rotación el 21/10: a Francisco le resultó confuso.
- `mail.txt` lleva qué es cada historia y la **encuesta sugerida** del día; `enviar_parte.ps1` la pega en el mail.
- Copias de antes del rediseño: `historias\*.bak-20261021`.

## Sitio público

- **https://elfrancho.github.io/rios/** — portada con las crecidas desde el espacio, la ola, el Paraná desde 1980 y el Salado. Repo `elfrancho/rios` (cuenta personal de GitHub), carpeta local `web/`.
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
3. La voz es `en-AU-WilliamMultilingualNeural` (ritmo -6%, tono -4Hz) desde el 24/10/2026; antes, `es-MX-JorgeNeural`. El script trae la marca de tiempo de cada palabra; con eso se sincronizan la animación y los subtítulos.
4. Antes de mandarlo, revisar cuadros sueltos con ffmpeg y que ninguna frase llegue cortada (el script reintenta solo).
5. Herramientas usadas: Chrome, puppeteer-core (npm, en `animacion\`), ffmpeg, edge-tts, Pillow, PyMuPDF.

## Pendiente / ideas

- **Reels pedidos el 25/10/2026** (se arman con datos del día; si es domingo, los hidrómetros automáticos del SNIH en lugar de Prefectura):
  1. **«¿Qué significa "nivel de evacuación"?»**, con imágenes satelitales (probar radar Sentinel-1 si hay nubes). Recorre los puertos de Puerto Iguazú a Rosario, cada uno con su marca. Arranca con la frase elegida: «Estoy cansado de los títulos que asustan. Yo no te vengo a asustar: te traigo los datos oficiales y te los explico.» Hay que decir que es la marca para evacuar las zonas más bajas, no toda la ciudad (frase oficial de la Municipalidad de Reconquista del 24/10).
  2. **La costa de la Ruta 1** (de Rincón y Arroyo Leyes a Cayastá, Helvecia, Santa Rosa, San Javier y Reconquista): al este de la ruta, el sistema del Paraná (río San Javier, Setúbal); al oeste, el de los Saladillos. Lo pidió un seguidor. Falta confirmar las marcas de alerta y evacuación de San Javier (los diarios dicen 6 o 7 m) y qué estaciones hay en los Saladillos. Cayastá, Helvecia y Santa Rosa no tienen escala propia: aclararlo.
     **Estaciones del SNIH con datos al 25/10** (automáticas y sin validar; códigos para `LeerUltimosRegistros`, `codigo` "1" = altura): del lado del Paraná, Romang 13331 (río San Javier, 6,64 → 7,05 m del 15 al 25/10), Cayastá 13226 (3,74 → 4,27), Leyes RP1 13225 (6,38 → 6,69) y Setúbal La Guardia 13339 (3,57 → 4,05); del lado de los Saladillos, Saladillo Dulce en La Noria RP281 13218 (0,90 → 0,76, último dato del 22/10) y Saladillo Amargo en Vera Mujica RP281 13200 (0,94 → 0,80). San Javier 13227, Helvecia 13204, Santa Rosa 13229, Saladero Cabal 13228, los dos de la RP39 (13230 y 13212) y San Justo 13325 no devolvieron datos recientes. Lista completa de estaciones: POST `Filtros.aspx/LeerEstaciones`. Cada escala tiene su propio cero: comparar subidas, no alturas. Falta bibliografía de la cuenca (laguna San Pedro, El Capón).

- El INA tenía que publicar el pronóstico nuevo el 23/10 y al cierre de esa tarde no había salido. El próximo informe semanal sale el miércoles 28/10.
- En el reel satelital, la frase "el Salado viene bajando" quedó general: en Santo Tomé sube porque lo frena el Paraná. En lo próximo, separar los tramos.
- Metricool: pasar la zona horaria de la marca de Madrid a Argentina (lo tiene que hacer él o autorizarlo).
- Ideas de reels: "cuánta agua es" (37.000 m³/s ≈ 15 piletas olímpicas por segundo); el río "tiene fin de semana" (Itaipú); la bajante 2020-22 fue más larga que la de 1944; crecidas de otros puertos (Corrientes, Rosario) desde el satélite; el radar (Sentinel-1) para días nublados.
- Quedaron sin mandar: el reel de los 107 m corregido y la historia del chajá.
