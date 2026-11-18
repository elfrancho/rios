"""Serie de imágenes satelitales de una zona marcada por Francisco en el Marcador de la Setúbal, de hoy hacia atrás.

Se corre SOLO en la notebook (rasterio, pystac-client, planetary-computer).
Uso: python zonas/armar_zona.py <marcas.json bajado con ArtifactData> "<parte del nombre de la zona>" [--desde 2020-01-01] [--max N] [--salida carpeta]
-> zonas/<zona>/img/<fecha>.jpg (color natural), <fecha>_fc.jpg (falso color), <fecha>_agua.png, zonas/<zona>/escenas.json y vista.html

- Fuente: Sentinel-2 L2A (ESA/Copernicus), bajado de Microsoft Planetary Computer, sin cuenta. 10 m por píxel (el infrarrojo de onda
  corta es de 20 m). Pasa cada 5 días o menos; la fecha de cada imagen es la del catálogo (hora UTC, ~14 h = ~11 h de Argentina).
- Encuadre: el rectángulo que contiene al polígono más un margen del 15 %, el mismo para todas las fechas (grilla UTM 20S).
- Se descarta una fecha si la imagen no cubre el encuadre entero o si la clasificación de escena (SCL) marca nubes o sombras en más
  del 2 % del encuadre. La bruma fina puede escaparse: se guarda `brillo` (parte del encuadre con azul > 0,15) para revisar a ojo.
- Color natural: rojo, verde y azul con el mismo estiramiento en todas las fechas. Falso color: onda corta, infrarrojo cercano y rojo
  (el agua se ve casi negra, la vegetación verde, la arena y el suelo desnudo claros).
- Agua: MNDWI = (verde - onda corta) / (verde + onda corta) > 0. `agua_ha` son las hectáreas de agua DENTRO del polígono.
- Altura del Paraná en el puerto de Santa Fe ese día (datos_ina/parana_santa_fe_altura.csv). Aguas bajas / medias / altas: debajo de
  2,36 m, entre medio, o arriba de 4,22 m (cuartos inferior y superior de todo el registro 1925-hoy).
"""
import argparse, csv, datetime as dt, json, os, re, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pystac_client, planetary_computer, rasterio, rasterio.errors
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform as reproyectar

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
CRS = "EPSG:32720"
BAJA, ALTA = 2.36, 4.22
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def leer(href, T, W, H, metodo):
    # Planetary Computer a veces contesta 403 al rato de firmar: se reintenta con una firma nueva
    for intento in range(4):
        try:
            with rasterio.open(planetary_computer.sign(href.split("?")[0])) as src, WarpedVRT(
                    src, crs=CRS, transform=T, width=W, height=H, resampling=metodo, nodata=0) as vrt:
                return vrt.read(1).astype("float32")
        except rasterio.errors.RasterioIOError:
            if intento == 3:
                raise
            time.sleep(8 * (intento + 1))


def banda(items, clave, G, metodo=Resampling.bilinear):
    T, W, H = G
    out = np.zeros((H, W), dtype="float32")
    for it in items:
        a = leer(it.assets[clave].href, T, W, H, metodo)
        out = np.where((out == 0) & (a > 0), a, out)
    return out


def estado(h):
    return None if h is None else "aguas bajas" if h < BAJA else "aguas altas" if h > ALTA else "aguas medias"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("marcas"), ap.add_argument("nombre")
    ap.add_argument("--desde", default="2020-01-01"), ap.add_argument("--max", type=int, default=0), ap.add_argument("--salida")
    a = ap.parse_args()

    d = json.load(open(a.marcas, encoding="utf-8"))
    d = d.get("data", d)
    zonas = [i for i in d["items"] if i["tipo"] == "zona" and a.nombre.lower() in i["nombre"].lower()]
    if len(zonas) != 1:
        raise SystemExit(f"Con «{a.nombre}» hay {len(zonas)} zonas: {[z['nombre'] for z in zonas]}")
    z = zonas[0]
    g = json.load(open(os.path.join(RAIZ, "setubal", "reel", "amplia.json"), encoding="utf-8"))
    px = [g["x0"] + fx * g["ancho_m"] for fx, _ in z["pts"]]
    py = [g["y0"] - fy * g["alto_m"] for _, fy in z["pts"]]
    if len(px) == 2:  # zona marcada con dos esquinas
        px, py = [px[0], px[1], px[1], px[0]], [py[0], py[0], py[1], py[1]]
    mx, my = max(300, (max(px) - min(px)) * 0.15), max(300, (max(py) - min(py)) * 0.15)
    res = 10 if max(max(px) - min(px) + 2 * mx, max(py) - min(py) + 2 * my) <= 25000 else 20
    x0, y1 = np.floor((min(px) - mx) / res) * res, np.ceil((max(py) + my) / res) * res
    W, H = int(np.ceil((max(px) + mx - x0) / res)), int(np.ceil((y1 - (min(py) - my)) / res))
    T = from_origin(x0, y1, res, res)
    G = (T, W, H)
    lon, lat = reproyectar(CRS, "EPSG:4326", [x0, x0 + W * res], [y1 - H * res, y1])
    plon, plat = reproyectar(CRS, "EPSG:4326", px, py)
    dentro = rasterize([({"type": "Polygon", "coordinates": [list(zip(px, py))]}, 1)], out_shape=(H, W), transform=T).astype(bool)
    print(f"Zona «{z['nombre']}»: encuadre {W * res / 1000:.2f} x {H * res / 1000:.2f} km a {res} m ({W} x {H} px), "
          f"polígono {dentro.sum() * res * res / 1e4:.0f} ha")

    sal = a.salida or os.path.join(AQUI, slug(z["nombre"]))
    img = os.path.join(sal, "img")
    os.makedirs(img, exist_ok=True)
    ruta = os.path.join(sal, "escenas.json")
    prev = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}
    mismo = prev.get("grilla") == [x0, y1, res, W, H]
    escenas = {e["fecha"]: e for e in prev.get("escenas", [])} if mismo else {}
    descartadas = prev.get("descartadas", {}) if mismo else {}
    sf = {r["fecha"]: float(r["valor"]) for r in csv.DictReader(open(os.path.join(RAIZ, "datos_ina", "parana_santa_fe_altura.csv"),
                                                                       encoding="utf-8")) if r["valor"]}

    def guardar():
        json.dump({"zona": z["nombre"], "nota": z.get("nota", ""), "generado": dt.datetime.now().isoformat(timespec="seconds"),
                   "fuente": "Sentinel-2 L2A (ESA/Copernicus) vía Microsoft Planetary Computer", "resolucion_m": res,
                   "grilla": [x0, y1, res, W, H], "bbox_lonlat": [round(lon[0], 6), round(lat[0], 6), round(lon[1], 6), round(lat[1], 6)],
                   "poligono_lonlat": [[round(u, 6), round(v, 6)] for u, v in zip(plon, plat)],
                   "poligono_px": [[round((u - x0) / res / W, 5), round((y1 - v) / res / H, 5)] for u, v in zip(px, py)],
                   "poligono_ha": round(float(dentro.sum()) * res * res / 1e4, 1), "criterio_alturas": {"bajas_menos_de": BAJA, "altas_mas_de": ALTA},
                   "escenas": [escenas[f] for f in sorted(escenas, reverse=True)], "descartadas": descartadas},
                  open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    hoy = dt.date.today().isoformat()
    pasadas = {}
    for it in cat.search(collections=["sentinel-2-l2a"], bbox=[lon[0], lat[0], lon[1], lat[1]], datetime=f"{a.desde}/{hoy}",
                         query={"eo:cloud_cover": {"lt": 85}}).items():
        pasadas.setdefault(it.properties["datetime"][:10], []).append(it)
    fechas = sorted(pasadas, reverse=True)  # de la más nueva a la más vieja
    print(len(fechas), "pasadas en el catálogo entre", fechas[-1], "y", fechas[0])
    hechas = 0
    with ThreadPoolExecutor(5) as pool:
        for f in fechas:
            if f in escenas or f in descartadas:
                continue
            if a.max and hechas >= a.max:
                break
            its = pasadas[f]
            try:
                scl = banda(its, "SCL", G, Resampling.nearest)
                valido = scl > 0
                nube = np.isin(scl, (3, 8, 9, 10)) & valido
                if valido.mean() < 0.995 or nube.mean() > 0.02:
                    descartadas[f] = f"cubre {valido.mean():.0%}, nubes o sombras {nube.mean():.1%}"
                    print(" ", f, "descartada:", descartadas[f])
                    guardar()
                    continue
                base = 1000 if float(its[0].properties.get("s2:processing_baseline", "0")) >= 4 else 0
                r, v, b, nir, sw = pool.map(lambda k: (banda(its, k, G) - base) / 10000, ("B04", "B03", "B02", "B08", "B11"))
            except Exception as e:  # una fecha que falla no corta la serie; se reintenta en la próxima corrida
                print(" ", f, "ERROR, se saltea:", type(e).__name__, str(e)[:120])
                continue
            brillo = float((b > 0.15).mean())
            if brillo > 0.25:
                descartadas[f] = f"muy brillante ({brillo:.0%}): nubes o bruma sin marcar"
                print(" ", f, "descartada:", descartadas[f])
                guardar()
                continue
            agua = ((v - sw) / np.maximum(v + sw, 1e-4) > 0) & valido & ~nube
            rgb = np.dstack([np.clip(c / 0.22, 0, 1) for c in (r, v, b)])
            Image.fromarray((np.power(rgb, 0.75) * 255).astype("uint8")).save(os.path.join(img, f + ".jpg"), quality=88, optimize=True)
            fc = np.dstack([np.clip(sw / 0.35, 0, 1), np.clip(nir / 0.45, 0, 1), np.clip(r / 0.22, 0, 1)])
            Image.fromarray((np.power(fc, 0.8) * 255).astype("uint8")).save(os.path.join(img, f + "_fc.jpg"), quality=88, optimize=True)
            m = Image.fromarray(agua.astype("uint8"))
            m.putpalette([0, 0, 0, 0, 200, 255] + [0, 0, 0] * 254)
            m.save(os.path.join(img, f + "_agua.png"), transparency=0, optimize=True)
            h = sf.get(f)
            escenas[f] = {"fecha": f, "hora_utc": its[0].properties["datetime"][11:16], "satelite": its[0].properties["platform"],
                          "ids": [i.id for i in its], "nubes_encuadre": round(float(nube.mean()), 4), "brillo": round(brillo, 3),
                          "parana_sf_m": h, "estado": estado(h), "agua_ha": round(float((agua & dentro).sum()) * res * res / 1e4, 1),
                          "agua_encuadre_ha": round(float(agua.sum()) * res * res / 1e4, 1)}
            hechas += 1
            print(f, escenas[f]["satelite"], f"SF {h} m · agua en la zona {escenas[f]['agua_ha']} ha · brillo {brillo:.1%}")
            guardar()
    guardar()
    datos = json.load(open(ruta, encoding="utf-8"))
    datos.pop("descartadas")
    pagina = open(os.path.join(AQUI, "plantilla_vista.html"), encoding="utf-8").read().replace("/*DATOS*/null", json.dumps(datos, ensure_ascii=False))
    open(os.path.join(sal, "vista.html"), "w", encoding="utf-8").write(pagina)
    print("listo:", len(escenas), "imágenes,", len(descartadas), "fechas descartadas ->", os.path.join(sal, "vista.html"))


if __name__ == "__main__":
    main()
