"""Arma la vista de la zona precisa: exportaciones de Google Earth Pro + recortes de la serie de 2 m (CBERS-4A), en un mismo encuadre.

Uso: python zonas/armar_zona_precisa.py
Lee zonas/zona_precisa/marco.json (marco en UTM 20S), google_earth/pasos/paso_NN.jpg (exportadas con "Guardar imagen", 8192x4416,
con el marco dibujado en magenta) y zonas/zona_a_investigar (serie de 2 m). Deja zonas/zona_precisa/img/, escenas.json,
contexto.json y vista.html.

- Cada exportación se ubica buscando las cuatro esquinas del marco magenta y se lleva a una grilla de 0,5 m por píxel.
- Fechas de Google: el selector de Google Earth Pro solo da mes y año (PASOS). El día sale de la barra inferior de Google Earth web,
  leída en un punto dentro de esta zona; puede diferir en un día de la de Earth Pro por el huso horario. Donde no se pudo cruzar,
  `dia_confirmado` es falso y no se informa altura del río.
- Solo se guardan las exportaciones cuya imagen cambia dentro del marco respecto del paso anterior, más viejo (correlación < 0,98). Una imagen puede combinar franjas de fechas distintas.
- La serie de 2 m se recorta y se agranda a la misma grilla: sirve para 2023-2026, donde Google no tiene imagen nueva en esta zona.
"""
import csv, json, math, os
import numpy as np
from PIL import Image
from rasterio.warp import transform as reproyectar

Image.MAX_IMAGE_PIXELS = None
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SAL = os.path.join(AQUI, "zona_precisa")
GRANDE = os.path.join(AQUI, "zona_a_investigar")
RES = 0.5
BAJA, ALTA = 2.36, 4.22
# paso -> (mes/año del selector de Earth Pro, fecha AAAA-MM-DD, día confirmado con la barra de Google Earth web)
PASOS = {1: ("12/2022", "2022-12-31", False), 2: ("12/2022", "2022-12-16", True), 3: ("12/2022", "2022-12-15", True),
         4: ("3/2022", "2022-04-01", True), 5: ("1/2022", "2022-01-30", True), 6: ("1/2022", "2022-01-27", True),
         7: ("1/2022", "2022-01-13", True), 8: ("1/2022", "2022-01-12", True), 9: ("12/2021", "2021-12-15", False),
         10: ("3/2021", "2021-04-01", False), 11: ("12/2020", "2020-12-28", False), 12: ("12/2020", "2020-12-21", False),
         13: ("12/2020", "2020-12-14", False), 14: ("12/2020", "2020-12-08", False), 15: ("11/2020", "2020-11-16", True),
         16: ("10/2020", "2020-10-28", True), 17: ("9/2020", "2020-09-27", False), 18: ("7/2020", "2020-07-08", True),
         19: ("4/2020", "2020-04-21", True), 20: ("4/2020", "2020-04-19", True), 21: ("12/2019", "2019-12-15", False),
         22: ("8/2019", "2019-08-11", True), 23: ("4/2019", "2019-04-12", True), 24: ("2/2019", "2019-02-22", False),
         25: ("12/2018", "2018-12-08", True)}
# Esri World Imagery (archivo Wayback): fechas posteriores a la última de Google, comprobadas con zonas/esri_versiones.py en el centro y
# las cuatro esquinas del marco. "release" es la versión del archivo que muestra esa foto; "correr_m" (este, abajo) es lo que hay que
# moverla para que calce con la serie de 2 m (medido por correlación). Se muestran en vivo desde el servidor de Esri: no se guardan.
ESRI = {"2024-02-02": {"release": 43291, "correr_m": (8, -6), "res": 0.46}, "2023-01-31": {"release": 39767, "correr_m": (6, -4), "res": 0.5}}
ESRI_URL = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{release}/{z}/{y}/{x}"
ESRI_Z = 18
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()


def estado(h):
    return None if h is None else "aguas bajas" if h < BAJA else "aguas altas" if h > ALTA else "aguas medias"


def esquinas(a):
    m = (a[..., 0] > 200) & (a[..., 1] < 90) & (a[..., 2] > 200)
    ys, xs = np.nonzero(m)
    s, d = xs + ys, xs - ys
    return [(int(xs[i]), int(ys[i])) for i in (s.argmin(), d.argmax(), s.argmax(), d.argmin())]  # NO, NE, SE, SO


def main():
    marco = json.load(open(os.path.join(SAL, "marco.json"), encoding="utf-8"))
    x0, y0, x1, y1 = marco["marco_utm"]
    W, H = int(round((x1 - x0) / RES)), int(round((y1 - y0) / RES))
    os.makedirs(os.path.join(SAL, "img"), exist_ok=True)
    sf = {r["fecha"]: float(r["valor"]) for r in csv.DictReader(open(os.path.join(RAIZ, "datos_ina", "parana_santa_fe_altura.csv"),
                                                                       encoding="utf-8")) if r["valor"]}
    escenas, previa = [], None
    for viejo in os.listdir(os.path.join(SAL, "img")):
        if viejo.endswith("_g.jpg"):
            os.remove(os.path.join(SAL, "img", viejo))
    # De la más vieja a la más nueva: el selector muestra en cada paso la última imagen disponible hasta esa fecha, así que
    # una imagen pertenece al paso MÁS VIEJO en el que aparece. Solo se guarda un paso si cambia respecto del paso anterior (más viejo).
    for n in sorted(PASOS, reverse=True):
        ruta = os.path.join(SAL, "google_earth", "pasos", f"paso_{n:02d}.jpg")
        if not os.path.exists(ruta):
            continue
        im = Image.open(ruta).convert("RGB")
        no, ne, se, so = esquinas(np.asarray(im).astype(int))
        m = 3  # se entra unos píxeles para no llevarse la línea magenta
        rec = im.transform((W, H), Image.QUAD, (no[0] + m, no[1] + m, so[0] + m, so[1] - m, se[0] - m, se[1] - m, ne[0] - m, ne[1] + m), Image.BICUBIC)
        firma = np.asarray(rec.convert("L").resize((160, 142))).astype("float32")
        firma = (firma - firma.mean()) / (firma.std() + 1e-6)
        mes, fecha, ok = PASOS[n]
        parecido = None if previa is None else float((firma * previa).mean())
        previa = firma
        if parecido is not None and parecido > 0.98:
            print(f"paso {n:02d} {mes}: igual al paso anterior (más viejo) dentro de la zona ({parecido:.3f}), no se guarda")
            continue
        clave = f"{fecha}_g"
        rec.save(os.path.join(SAL, "img", clave + ".jpg"), quality=90, optimize=True)
        mm, aa = mes.split("/")
        h = sf.get(fecha) if ok else None
        d = fecha[8:].lstrip("0") + " de " if ok else ""
        escenas.append({"fecha": fecha, "clave": clave, "etiqueta": f"{d}{MESES[int(mm) - 1]} de {aa}", "satelite": "Google Earth", "resolucion_m": 0.5,
                        "dia_confirmado": ok, "parana_sf_m": h, "estado": estado(h), "pan": False,
                        "nota": "" if ok else "día sin confirmar", "paso": n})
        print(f"paso {n:02d} {mes} -> {clave}", "" if parecido is None else f"(parecido con la anterior {parecido:.3f})")

    g = json.load(open(os.path.join(GRANDE, "escenas.json"), encoding="utf-8"))
    gx0, gy1, gres, gW, gH = g["grilla"]
    caja = ((x0 - gx0) / gres, (gy1 - y1) / gres, (x1 - gx0) / gres, (gy1 - y0) / gres)
    for e in g["escenas"]:
        ref = bool(e.get("referencia"))   # imagen de referencia de otra fuente (crecida de 2016): conserva su fuente, resolución y crédito
        for suf in ("", "_pan") if e.get("pan", True) else ("",):
            im = Image.open(os.path.join(GRANDE, "img", e["fecha"] + suf + ".jpg"))
            im.resize((W, H), Image.BICUBIC, box=caja).save(os.path.join(SAL, "img", f"{e['fecha']}_c{suf}.jpg"), quality=88, optimize=True)
        f = e["fecha"]
        escenas.append({"fecha": f, "clave": f + "_c", "etiqueta": f"{int(f[8:])} de {MESES[int(f[5:7]) - 1]} de {f[:4]}", "satelite": e["satelite"] if ref else "CBERS-4A",
                        "resolucion_m": e.get("resolucion_m", 2) if ref else 2, "dia_confirmado": True, "parana_sf_m": e["parana_sf_m"], "estado": e["estado"],
                        "pan": e.get("pan", True), "nota": "ubicación sin ajustar" if str(e.get("alineada")).startswith("no") else ""})
        if ref:
            escenas[-1]["credito"] = e.get("credito", "")
    for f, info in ESRI.items():   # matriz que lleva los píxeles del mosaico de teselas (Mercator) a la grilla de la vista (UTM)
        cx, cy = [x0, x1, x1, x0, (x0 + x1) / 2], [y1, y1, y0, y0, (y0 + y1) / 2]
        lo, la = reproyectar("EPSG:32720", "EPSG:4326", cx, cy)
        X = np.array([(a + 180) / 360 * 2 ** ESRI_Z * 256 for a in lo])
        Y = np.array([(1 - math.asinh(math.tan(math.radians(b))) / math.pi) / 2 * 2 ** ESRI_Z * 256 for b in la])
        tx0, tx1, ty0, ty1 = int(X.min() // 256), int(X.max() // 256), int(Y.min() // 256), int(Y.max() // 256)
        A = np.column_stack([X - tx0 * 256, Y - ty0 * 256, np.ones(5)])
        u = (np.array(cx) - x0) / RES + info["correr_m"][0] / RES
        v = (y1 - np.array(cy)) / RES + info["correr_m"][1] / RES
        (a, c, e_), (b, d, f_) = np.linalg.lstsq(A, u, rcond=None)[0], np.linalg.lstsq(A, v, rcond=None)[0]
        h = sf.get(f)
        escenas.append({"fecha": f, "clave": None, "etiqueta": f"{int(f[8:])} de {MESES[int(f[5:7]) - 1]} de {f[:4]}", "satelite": "Esri (Maxar)",
                        "resolucion_m": info["res"], "dia_confirmado": True, "parana_sf_m": h, "estado": estado(h), "pan": False, "nota": "en vivo desde Esri",
                        "credito": f"Imagen: Esri World Imagery · Maxar · captura {f[8:]}/{f[5:7]}/{f[:4]}",
                        "teselas": {"release": info["release"], "z": ESRI_Z, "tx0": tx0, "tx1": tx1, "ty0": ty0, "ty1": ty1,
                                    "url": ESRI_URL.replace("{release}", str(info["release"])), "m": [round(float(k), 6) for k in (a, b, c, d, e_, f_)]}})
    escenas.sort(key=lambda e: (e["fecha"], e["satelite"]), reverse=True)

    px = [[round((u - x0) / (x1 - x0), 5), round((y1 - v) / (y1 - y0), 5)] for u, v in marco["poligono_utm"]]
    lon, lat = reproyectar("EPSG:32720", "EPSG:4326", [x0, x1], [y0, y1])
    datos = {"zona": marco["zona"], "nota": marco["nota"], "fuente": "Google Earth Pro (imágenes © Google y sus proveedores, exportadas con «Guardar imagen», ≈0,4 m), "
             "Esri World Imagery (Maxar, ≈0,5 m, mostrada en vivo desde Esri con la fecha de captura que informa su archivo) "
             "y CBERS-4A WPM del INPE de Brasil (2 m, agrandada)", "resolucion_m": RES, "grilla": [x0, y1, RES, W, H],
             "bbox_lonlat": [round(lon[0], 6), round(lat[0], 6), round(lon[1], 6), round(lat[1], 6)], "ancho_km": (x1 - x0) / 1000, "alto_km": (y1 - y0) / 1000,
             "poligono_px": px, "criterio_alturas": {"bajas_menos_de": BAJA, "altas_mas_de": ALTA}, "escenas": escenas}
    # contexto alrededor: la serie de 2 m de la zona grande, ubicada detrás (coordenadas en píxeles de esta grilla)
    datos["fondo"] = {"x": round((gx0 - x0) / RES, 1), "y": round((y1 - gy1) / RES, 1), "w": round(gW * gres / RES, 1), "h": round(gH * gres / RES, 1),
                      "imagenes": [{"fecha": e["fecha"], "src": f"../zona_a_investigar/img/{e['fecha']}.jpg"} for e in g["escenas"]]}
    elo, ela = reproyectar("EPSG:32720", "EPSG:4326", [x0, x1, x1, x0], [y1, y1, y0, y0])
    datos["esquinas_lonlat"] = [[round(a, 7), round(b, 7)] for a, b in zip(elo, ela)]   # NO, NE, SE, SO: para dar coordenadas en la vista
    json.dump(datos, open(os.path.join(SAL, "escenas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    crudo = json.load(open(os.path.join(GRANDE, "osm_crudo.json"), encoding="utf-8"))
    lineas = []
    for el in crudo["elements"]:
        t = el.get("tags", {})
        if el["type"] != "way" or "geometry" not in el:
            continue
        tipo = ("agua" if "waterway" in t else "ruta" if t.get("highway") in ("primary", "secondary", "trunk", "tertiary")
                else "camino" if t.get("highway") in ("track", "path", "service") else "calle")
        xs, ys = reproyectar("EPSG:4326", "EPSG:32720", [p["lon"] for p in el["geometry"]], [p["lat"] for p in el["geometry"]])
        pts = [[round((x - x0) / RES, 1), round((y1 - y) / RES, 1)] for x, y in zip(xs, ys)]
        if any(0 <= p[0] <= W and 0 <= p[1] <= H for p in pts):
            lineas.append({"tipo": tipo, "nombre": t.get("name", ""), "pts": pts})
    json.dump({"fuente": "© colaboradores de OpenStreetMap (datos abiertos, licencia ODbL)", "lineas": lineas},
              open(os.path.join(SAL, "contexto.json"), "w", encoding="utf-8"), ensure_ascii=False)
    datos["contexto"] = json.load(open(os.path.join(SAL, "contexto.json"), encoding="utf-8"))
    pagina = open(os.path.join(AQUI, "plantilla_vista.html"), encoding="utf-8").read().replace("/*DATOS*/null", json.dumps(datos, ensure_ascii=False))
    ana = os.path.join(SAL, "analisis.html")
    if os.path.exists(ana):
        pagina = pagina.replace("<!--ANALISIS-->", open(ana, encoding="utf-8").read())
    open(os.path.join(SAL, "vista.html"), "w", encoding="utf-8").write(pagina)
    print(len(escenas), "imágenes en la vista:", sum(e["satelite"] == "Google Earth" for e in escenas), "de Google Earth y",
          sum(e["satelite"] == "CBERS-4A" for e in escenas), "de 2 m y", sum("teselas" in e for e in escenas), "de Esri ·", len(lineas), "líneas de contexto ·", W, "x", H, "px")


if __name__ == "__main__":
    main()
