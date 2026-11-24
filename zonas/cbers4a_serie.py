"""Serie de imágenes CBERS-4A (cámara WPM: 2 m en blanco y negro, 8 m en color) de los dos sectores.

Uso:
  python zonas/cbers4a_serie.py revisar <carpeta>            recorre el archivo, guarda una vista chica de cada fecha y un listado
  python zonas/cbers4a_serie.py bajar <carpeta> <id> [<id>]  guarda el recorte de 2 m de las escenas indicadas

Fuente: satélite CBERS-4A (Brasil/China), catálogo público del INPE (https://data.inpe.br/bdc/stac/v1), sin cuenta. Se lee solo la ventana
de la zona, sin bajar la escena entera. Nivel L4 = corregida sobre el terreno; nivel L2 = ubicación aproximada (puede estar corrida decenas
de metros). Las escenas que el INPE entrega en UTM 21 Sur se llevan a UTM 20 Sur (remuestreo bilineal); las demás no se remuestrean.
El contraste de cada recorte se estira entre los percentiles 1 y 99,5: sirve para ver, no para comparar brillos entre fechas.
"""
import json, os, sys, time, urllib.request
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import from_bounds
from PIL import Image

CAJA = (734300, 6506400, 737300, 6509200)   # UTM 20S: los dos sectores y la ruta
STAC = "https://data.inpe.br/bdc/stac/v1"
UA = {"Content-Type": "application/json", "User-Agent": "geo-lookup/1.0"}
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_USERAGENT="geo-lookup/1.0", GDAL_HTTP_MAX_RETRY="3", GDAL_HTTP_RETRY_DELAY="5")


def ventana(url):
    with rasterio.Env(**ENV):
        with rasterio.open(url) as src:
            if src.crs.to_epsg() == 32720:
                return src.read(1, window=from_bounds(*CAJA, transform=src.transform), boundless=True).astype("float32"), False
            with WarpedVRT(src, crs="EPSG:32720", resampling=Resampling.bilinear) as v:
                w = from_bounds(*CAJA, transform=v.transform).round_offsets().round_lengths()
                if w.col_off < 0 or w.row_off < 0 or w.col_off + w.width > v.width or w.row_off + w.height > v.height:
                    return np.zeros((2, 2), "float32"), True
                return v.read(1, window=w).astype("float32"), True


def estirar(a):
    v = a[a > 0]
    lo, hi = np.percentile(v, (1, 99.5)) if v.size else (0, 1)
    return (np.clip((a - lo) / max(hi - lo, 1), 0, 1) * 255).astype("uint8")


def fecha(iid):
    f = iid.split("_")[3]
    return f"{f[:4]}-{f[4:6]}-{f[6:]}"


def revisar(salida):
    os.makedirs(os.path.join(salida, "vistas"), exist_ok=True)
    items = []
    for col in ("CB4A-WPM-L4-DN-1", "CB4A-WPM-L2-DN-1"):
        q = {"collections": [col], "intersects": {"type": "Point", "coordinates": [-60.515, -31.540]}, "limit": 200}
        d = json.load(urllib.request.urlopen(urllib.request.Request(STAC + "/search", data=json.dumps(q).encode(), headers=UA), timeout=120))
        items += [(col, f) for f in d["features"]]
    filas = []
    for col, f in sorted(items, key=lambda x: x[1]["id"]):
        iid = f["id"]
        try:
            rgb = [ventana(f["assets"][b]["href"])[0] for b in ("BAND3", "BAND2", "BAND1")]
            r = rgb[0]
            v = r[r > 0]
            fila = {"id": iid, "coleccion": col, "fecha": fecha(iid), "hora_utc": f["properties"]["datetime"][11:16],
                    "con_datos": round(float(v.size) / max(r.size, 1), 3)}
            if v.size > r.size * 0.95 and r.size > 100:
                fila.update(mediana=round(float(np.median(v))), p95=round(float(np.percentile(v, 95))), saturado=round(float(np.mean(r >= 1020)), 3))
                Image.fromarray(np.dstack([estirar(x) for x in rgb])).save(os.path.join(salida, "vistas", f"{fecha(iid)}_{iid.split('_')[-1]}_{iid.split('_')[4]}.jpg"), quality=85)
            filas.append(fila)
            print(fila, flush=True)
        except Exception as e:
            print(iid, "ERROR", repr(e)[:150], flush=True)
            filas.append({"id": iid, "coleccion": col, "fecha": fecha(iid), "error": repr(e)[:150]})
        json.dump({"metodo": __doc__, "caja_utm": CAJA, "escenas": filas}, open(os.path.join(salida, "revision.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("fin", len(filas))


def bajar(salida, ids):
    os.makedirs(salida, exist_ok=True)
    reg = os.path.join(salida, "registro.json")
    filas = json.load(open(reg, encoding="utf-8"))["escenas"] if os.path.exists(reg) else []
    for iid in ids:
        col = "CB4A-WPM-L4-DN-1" if iid.endswith("L4") else "CB4A-WPM-L2-DN-1"
        nombre = f"cbers4a_{fecha(iid)}_{iid.split('_')[-1]}_pan_2m.png"
        if os.path.exists(os.path.join(salida, nombre)):
            continue
        try:
            t = time.time()
            f = json.load(urllib.request.urlopen(urllib.request.Request(f"{STAC}/collections/{col}/items/{iid}", headers=UA), timeout=120))
            p, remuestreada = ventana(f["assets"]["BAND0"]["href"])
            if p.max() <= 0:
                print(iid, "sin banda de 2 m", flush=True); continue
            Image.fromarray(estirar(p)).save(os.path.join(salida, nombre))
            filas = [x for x in filas if x["id"] != iid] + [{"id": iid, "coleccion": col, "archivo": nombre, "fecha": fecha(iid), "hora_utc": f["properties"]["datetime"][11:19],
                      "nivel": iid.split("_")[-1], "remuestreada_de_utm21": remuestreada, "origen": f["assets"]["BAND0"]["href"],
                      "caja_utm_20s": CAJA, "metros_por_pixel": 2, "tamano_px": [int(p.shape[1]), int(p.shape[0])]}]
            json.dump({"metodo": __doc__, "escenas": sorted(filas, key=lambda x: x["fecha"])}, open(reg, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(iid, p.shape, round(time.time() - t), "s", flush=True)
        except Exception as e:
            print(iid, "ERROR", repr(e)[:200], flush=True)
    print("fin")


if __name__ == "__main__":
    if sys.argv[1] == "revisar":
        revisar(sys.argv[2])
    else:
        bajar(sys.argv[2], sys.argv[3:])
