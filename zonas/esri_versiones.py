"""Qué fotos de alta resolución tiene Esri World Imagery (archivo Wayback) sobre una zona, con su fecha de captura.

Uso: python zonas/esri_versiones.py zonas/zona_precisa      -> escribe <zona>/esri_versiones.json
Consulta el servicio público de metadatos de Esri (sin cuenta) en cinco puntos de la zona: centro y cuatro esquinas del marco.
Para cada fecha de captura distinta guarda la versión del archivo en la que aparece, la resolución y el proveedor.
La fecha es la que informa Esri (campo SRC_DATE2); no se baja ninguna imagen.
"""
import datetime as dt, json, os, sys, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from rasterio.warp import transform

CONFIG = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"


def pedir(url, t=25):
    for intento in range(3):
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=t))
        except Exception:
            if intento == 2:
                raise


def consulta(base, lon, lat):
    q = urllib.parse.urlencode({"f": "json", "geometry": json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}),
                                "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                                "outFields": "SRC_DATE2,SRC_RES,NICE_NAME,NICE_DESC", "returnGeometry": "false"})
    for capa in (4, 3, 2, 1, 0, 5, 6):   # la capa 4 es la de mayor detalle en esta zona
        fs = pedir(f"{base}/{capa}/query?{q}").get("features") or []
        if fs:
            a = fs[0]["attributes"]
            f = (dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=a["SRC_DATE2"])).date().isoformat() if a.get("SRC_DATE2") else None
            return f, a.get("SRC_RES"), a.get("NICE_NAME"), a.get("NICE_DESC")
    return None


def main(zona):
    m = json.load(open(os.path.join(zona, "marco.json"), encoding="utf-8"))
    x0, y0, x1, y1 = m["marco_utm"]
    xs = [(x0 + x1) / 2, x0 + 60, x1 - 60, x1 - 60, x0 + 60]
    ys = [(y0 + y1) / 2, y1 - 60, y1 - 60, y0 + 60, y0 + 60]
    lon, lat = transform("EPSG:32720", "EPSG:4326", xs, ys)
    puntos = list(zip(["centro", "NO", "NE", "SE", "SO"], lon, lat))
    cfg = pedir(CONFIG)
    items = sorted(((int(k), v) for k, v in cfg.items()), key=lambda kv: kv[1]["itemTitle"])
    items = [it for it in items if it[1]["itemTitle"][-11:-7] >= "2022"]

    def una(it):
        num, v = it
        try:
            return num, v["itemTitle"][-11:-1], [consulta(v["metadataLayerUrl"], lo, la) for _, lo, la in puntos]
        except Exception as e:
            return num, v["itemTitle"][-11:-1], None

    with ThreadPoolExecutor(4) as p:
        res = list(p.map(una, items))
    fechas = {}
    for num, version, datos in res:
        if not datos or not datos[0]:
            continue
        f = datos[0][0]
        pareja = all(d and d[0] == f for d in datos)
        e = fechas.setdefault(f, {"fecha": f, "resolucion_m": datos[0][1], "producto": datos[0][2], "proveedor": datos[0][3], "versiones": [], "toda_la_zona": True})
        e["versiones"].append({"version": version, "release": num})
        e["toda_la_zona"] = e["toda_la_zona"] and pareja
    lista = sorted(fechas.values(), key=lambda e: e["fecha"], reverse=True)
    json.dump({"consultado": dt.date.today().isoformat(), "puntos": [[n, round(a, 6), round(b, 6)] for n, a, b in puntos], "fechas": lista,
               "sin_respuesta": [v for _, v, d in res if not d]}, open(os.path.join(zona, "esri_versiones.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for e in lista:
        print(e["fecha"], e["resolucion_m"], "m", e["producto"], "|", e["proveedor"], "| igual en las 4 esquinas:", e["toda_la_zona"],
              "| versiones", e["versiones"][0]["version"], "a", e["versiones"][-1]["version"], f"({len(e['versiones'])})", "| release", e["versiones"][-1]["release"])
    print("versiones sin respuesta:", sum(1 for _, _, d in res if not d), "de", len(res))


if __name__ == "__main__":
    main(sys.argv[1])
