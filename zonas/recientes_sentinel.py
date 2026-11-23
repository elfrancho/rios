"""Recortes en color de Sentinel-2 (10 m) de los dos sectores en las fechas más recientes, para ver el estado del agua.

Uso: python zonas/recientes_sentinel.py <carpeta de salida> <fecha AAAA-MM-DD> [más fechas]
Fuente: Sentinel-2 L2A (ESA/Copernicus), catálogo público Earth Search (https://earth-search.aws.element84.com/v1), sin cuenta. Se lee la
imagen en color ya preparada por el proveedor («visual») en la grilla original UTM 20 Sur, sin remuestrear. Cada píxel mide 10 m: sirve para
ver agua, arena y nubes, no objetos chicos. Se guarda el identificador y la hora de cada escena.
"""
import json, os, sys, urllib.request
import rasterio
from rasterio.windows import from_bounds
from PIL import Image

CAJA = (734300, 6506400, 737300, 6509200)   # UTM 20S: los dos sectores y la ruta
URL = "https://earth-search.aws.element84.com/v1/search"


def buscar(fecha):
    q = {"collections": ["sentinel-2-l2a"], "intersects": {"type": "Point", "coordinates": [-60.515, -31.540]},
         "datetime": f"{fecha}T00:00:00Z/{fecha}T23:59:59Z", "limit": 5}
    r = urllib.request.Request(URL, data=json.dumps(q).encode(), headers={"Content-Type": "application/json", "User-Agent": "geo-lookup/1.0"})
    return json.load(urllib.request.urlopen(r, timeout=60))["features"]


def main(salida, fechas):
    os.makedirs(salida, exist_ok=True)
    filas = []
    for fecha in fechas:
        for f in buscar(fecha)[:1]:
            with rasterio.open(f["assets"]["visual"]["href"]) as src:
                assert src.crs.to_epsg() == 32720, src.crs
                a = src.read(window=from_bounds(*CAJA, transform=src.transform))
            im = Image.fromarray(a.transpose(1, 2, 0))
            im.save(os.path.join(salida, f"sentinel_{fecha}.png"))
            filas.append({"fecha": fecha, "hora_utc": f["properties"]["datetime"][11:16], "id": f["id"], "nubes_escena_pct": f["properties"].get("eo:cloud_cover"),
                          "caja_utm": CAJA, "tamano_px": im.size})
            print(fecha, f["id"], im.size, flush=True)
    json.dump({"metodo": __doc__, "escenas": filas}, open(os.path.join(salida, "sentinel_recientes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
