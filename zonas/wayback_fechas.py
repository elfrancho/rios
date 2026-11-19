"""Qué fotos de alta resolución hay en un punto según el archivo Esri World Imagery Wayback (gratis, sin cuenta).

Uso: python zonas/wayback_fechas.py <lon> <lat> [desde_año]
Cada versión del mapa base de Esri trae, por lugar, la fecha real de captura (SRC_DATE2), la resolución (SRC_RES) y el proveedor.
Lista las fechas de captura distintas, de la más nueva a la más vieja, y en qué versión del archivo aparece cada una.
"""
import json, sys, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

CONFIG = "https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json"


def pedir(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(req, timeout=40))


def consulta(item, lon, lat):
    num, v = item
    q = urllib.parse.urlencode({"f": "json", "geometry": json.dumps({"x": lon, "y": lat, "spatialReference": {"wkid": 4326}}),
                                "geometryType": "esriGeometryPoint", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects",
                                "outFields": "SRC_DATE2,SRC_RES,SRC_ACC,NICE_NAME,NICE_DESC,SAMP_RES", "returnGeometry": "false"})
    for capa in (0, 1, 2, 3):  # 0 = el zoom más cercano
        for intento in range(3):
            try:
                r = pedir(f"{v['metadataLayerUrl']}/{capa}/query?{q}")
                break
            except Exception as e:
                r = None
                err = str(e)[:80]
                time.sleep(2)
        if r is None:
            return num, v, {"error": err}
        if r.get("features"):
            return num, v, r["features"][0]["attributes"]
    return num, v, None


def main():
    lon, lat = float(sys.argv[1]), float(sys.argv[2])
    desde = int(sys.argv[3]) if len(sys.argv) > 3 else 2019
    cfg = pedir(CONFIG)
    with ThreadPoolExecutor(3) as pool:
        res = list(pool.map(lambda it: consulta(it, lon, lat), [it for it in cfg.items() if int(it[1]['itemTitle'][-11:-7]) >= desde]))
    porfecha = {}
    for num, v, at in res:
        if not at or "error" in at or not at.get("SRC_DATE2"):
            continue
        import datetime as dt
        f = (dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=at["SRC_DATE2"])).date().isoformat()
        e = porfecha.setdefault(f, {"res": at.get("SRC_RES"), "prov": at.get("NICE_NAME"), "desc": at.get("NICE_DESC"), "versiones": []})
        e["versiones"].append((v["itemTitle"][-11:-1], num))
    for f in sorted(porfecha, reverse=True):
        if int(f[:4]) < desde:
            continue
        e = porfecha[f]
        vs = sorted(e["versiones"])
        print(f, f"{e['res']} m", e["prov"], "|", e["desc"], "| en", len(vs), "versiones, primera", vs[0][0], "release", vs[0][1])
    print(len(cfg), "versiones consultadas;", sum(1 for _, _, at in res if at and "error" in at), "con error")


if __name__ == "__main__":
    main()
