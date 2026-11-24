"""Recortes en blanco y negro de los satélites brasileños anteriores al CBERS-4A, para la serie 2008-2019 de los dos sectores.

Uso: python zonas/cbers_anteriores.py <carpeta de salida> [hasta_año]

Fuentes (catálogo público del INPE, https://data.inpe.br/bdc/stac/v1, sin cuenta):
  CBERS-2B, cámara HRC: 2,7 m por píxel, blanco y negro, 2007-2010.
  CBERS-4, cámara PAN: 5 m por píxel, blanco y negro, desde 2015.
Entre 2010 y 2014 el catálogo no tiene imágenes finas de la zona.
Solo hay nivel L2 (ubicación aproximada: la imagen puede estar corrida cientos de metros), por eso se recorta con 1500 m de margen
alrededor de la caja de trabajo y no se remuestrea salvo que la escena venga en UTM 21 Sur. Se usa la huella real de cada escena, no su caja.
El contraste se estira entre los percentiles 1 y 99,5.
"""
import json, os, sys, time, urllib.request
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds
from PIL import Image

CAJA = (734300, 6506400, 737300, 6509200)
M = 1500
LON, LAT = -60.515, -31.540
STAC = "https://data.inpe.br/bdc/stac/v1"
UA = {"Content-Type": "application/json", "User-Agent": "geo-lookup/1.0"}
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_USERAGENT="geo-lookup/1.0", GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="5")
COLECCIONES = (("CB2B-HRC-L2-DN-1", "hrc_2.7m"), ("CB4-PAN5M-L2-DN-1", "pan_5m"))


def dentro(geom):
    r = (geom["coordinates"] if geom["type"] == "Polygon" else geom["coordinates"][0])[0]
    c = False
    for i in range(len(r)):
        x1, y1 = r[i][:2]; x2, y2 = r[i - 1][:2]
        if (y1 > LAT) != (y2 > LAT) and LON < (x2 - x1) * (LAT - y1) / (y2 - y1) + x1:
            c = not c
    return c


def ventana(url):
    c = (CAJA[0] - M, CAJA[1] - M, CAJA[2] + M, CAJA[3] + M)
    with rasterio.Env(**ENV):
        with rasterio.open(url) as src:
            if src.crs.to_epsg() == 32720:
                return src.read(1, window=from_bounds(*c, transform=src.transform), boundless=True).astype("float32"), src.res[0], False
            with WarpedVRT(src, crs="EPSG:32720", resampling=Resampling.bilinear) as v:
                w = from_bounds(*c, transform=v.transform).round_offsets().round_lengths()
                if w.col_off < 0 or w.row_off < 0 or w.col_off + w.width > v.width or w.row_off + w.height > v.height:
                    return np.zeros((2, 2), "float32"), v.res[0], True
                return v.read(1, window=w).astype("float32"), v.res[0], True


def estirar(a):
    v = a[a > 0]
    lo, hi = np.percentile(v, (1, 99.5)) if v.size else (0, 1)
    return (np.clip((a - lo) / max(hi - lo, 1), 0, 1) * 255).astype("uint8")


def main(salida, hasta):
    os.makedirs(salida, exist_ok=True)
    reg = os.path.join(salida, "registro.json")
    filas = json.load(open(reg, encoding="utf-8"))["escenas"] if os.path.exists(reg) else []
    hechos = {x["id"] for x in filas}
    for col, sufijo in COLECCIONES:
        q = {"collections": [col], "intersects": {"type": "Point", "coordinates": [LON, LAT]}, "limit": 500}
        d = json.load(urllib.request.urlopen(urllib.request.Request(STAC + "/search", data=json.dumps(q).encode(), headers=UA), timeout=120))
        for f in sorted(d["features"], key=lambda f: f["properties"]["datetime"]):
            iid, fe = f["id"], f["properties"]["datetime"][:10]
            if iid in hechos or int(fe[:4]) > hasta or not dentro(f["geometry"]):
                continue
            try:
                t = time.time()
                clave = next(k for k, a in sorted(f["assets"].items()) if a["href"].lower().endswith(".tif"))
                a, res, rem = ventana(f["assets"][clave]["href"])
                datos = float(np.mean(a > 0))
                fila = {"id": iid, "coleccion": col, "fecha": fe, "hora_utc": f["properties"]["datetime"][11:19], "con_datos": round(datos, 3),
                        "metros_por_pixel": round(float(res), 2), "remuestreada_de_utm21": rem, "origen": f["assets"][clave]["href"],
                        "caja_utm_20s_con_margen": [CAJA[0] - M, CAJA[1] - M, CAJA[2] + M, CAJA[3] + M]}
                if datos > 0.9:
                    fila["archivo"] = f"cbers_{fe}_{sufijo}_{'_'.join(iid.split('_')[-3:])}.png"
                    fila["saturado"] = round(float(np.mean(a >= a.max())), 3)
                    Image.fromarray(estirar(a)).save(os.path.join(salida, fila["archivo"]))
                filas.append(fila)
                json.dump({"metodo": __doc__, "escenas": filas}, open(reg, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                print(iid, fe, a.shape, "datos", round(datos, 2), round(time.time() - t), "s", flush=True)
            except Exception as e:
                print(iid, "ERROR", repr(e)[:160], flush=True)
    print("fin")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2019)
