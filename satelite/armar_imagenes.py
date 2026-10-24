"""Imágenes satelitales de las crecidas para la página "Las crecidas desde el espacio" (satelite.html).

Se corre SOLO en la notebook (necesita rasterio, pystac-client y planetary-computer); GitHub publica las imágenes ya hechas.
Uso: python satelite/armar_imagenes.py [id ...]  -> satelite/img/<id>.jpg, satelite/img/<id>_agua.png y satelite/escenas.json

- Fuente: Microsoft Planetary Computer, sin cuenta. Sentinel-2 L2A (10 m, desde 2015) y Landsat Collection 2 nivel 2 (30 m).
  No hay Landsat utilizable de 1983 sobre Santa Fe en ese archivo.
- Todas las imágenes caen en la misma grilla (UTM 20 sur, recuadro vertical de 18 x 32 km, píxel de 15 m), así se superponen.
- Agua: MNDWI = (verde - infrarrojo de onda corta) / (verde + infrarrojo de onda corta) > 0,05, sin contar nubes ni sombras
  (Sentinel: banda SCL; Landsat: qa_pixel). Los km² son "agua visible dentro del recuadro", no el área total de la crecida.
- Alturas del día de cada imagen: Paraná en Santa Fe (datos_ina) y Salado en Recreo (datos_salado).
"""
import csv, datetime as dt, json, os, sys
import numpy as np, pystac_client, planetary_computer, rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform as reproyectar

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
IMG = os.path.join(AQUI, "img")
CRS, RES, ANCHO_M, ALTO_M = "EPSG:32720", 15, 18000, 32000
W, H = ANCHO_M // RES, ALTO_M // RES
SALIDA = (900, 1600)
MARCOS = {"parana": (-60.655, -31.615), "salado": (-60.725, -31.605)}  # Santa Fe y la Setúbal / el Salado y el oeste

# id, marco, título, fecha de la imagen, colección, plataforma (Landsat), nota
EVENTOS = [
    ("p1992", "parana", "Crecida de 1992", "1992-06-27", "landsat-c2-l2", "landsat-5", "5 días después del récord de Santa Fe: 7,43 m el 22/06/1992."),
    ("p1998", "parana", "El Niño 1997-98", "1998-06-28", "landsat-c2-l2", "landsat-5", "El pico fue de 7,26 m el 02/05/1998; no hay imagen sin nubes más cerca."),
    ("p2010", "parana", "Crecida de 2010", "2010-01-20", "landsat-c2-l2", "landsat-5", "Pico de 6,02 m el 10/02/2010."),
    ("p2016", "parana", "Crecida de 2015-16", "2016-01-23", "sentinel-2-l2a", None, "18 días después del pico: 6,60 m el 05/01/2016."),
    ("p2022", "parana", "Bajante de 2022", "2022-02-15", "sentinel-2-l2a", None, "La bajante más larga en décadas: la Setúbal casi seca."),
    ("p2023", "parana", "Crecida de 2023", "2023-12-12", "sentinel-2-l2a", None, "Pico de 5,45 m el 20/12/2023."),
    ("p2026", "parana", "Octubre de 2026", "2026-10-19", "sentinel-2-l2a", None, "La crecida de este año."),
    ("s2003a", "salado", "Salado, abril de 2003", "2003-04-15", "landsat-c2-l2", "landsat-7", "Dos semanas antes del pico: el Salado ya ocupaba su valle."),
    ("s2003b", "salado", "Salado, 1 de mayo de 2003", "2003-05-01", "landsat-c2-l2", "landsat-7",
     "Un día después del pico (7,88 m en Recreo el 30/04/2003, el más alto desde 1980). Las manchas blancas son nubes."),
    ("s2016", "salado", "Salado, abril de 2016", "2016-04-22", "sentinel-2-l2a", None, "Crecieron los dos ríos a la vez: el Salado tocó 6,79 m en Recreo el 13/04/2016."),
    ("s2026", "salado", "Salado, octubre de 2026", "2026-10-19", "sentinel-2-l2a", None, "Hoy el Salado baja aguas arriba; en Santo Tomé lo frena el Paraná."),
]
BANDAS = {"sentinel-2-l2a": ("B04", "B03", "B02", "B11", "SCL"), "landsat-c2-l2": ("red", "green", "blue", "swir16", "qa_pixel")}
CREDITO = {"sentinel-2-l2a": "Contiene datos modificados de Copernicus Sentinel", "landsat-c2-l2": "Landsat: USGS/NASA"}
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)


def grilla(centro):
    (cx,), (cy,) = reproyectar("EPSG:4326", CRS, [centro[0]], [centro[1]])
    return from_origin(cx - ANCHO_M / 2, cy + ALTO_M / 2, RES, RES)


def banda(items, clave, transf, metodo=Resampling.bilinear):
    out = np.zeros((H, W), dtype="float32")
    for it in items:
        with rasterio.open(it.assets[clave].href) as src, WarpedVRT(src, crs=CRS, transform=transf, width=W, height=H,
                                                                     resampling=metodo, nodata=0) as vrt:
            a = vrt.read(1).astype("float32")
        out = np.where((out == 0) & (a > 0), a, out)
    return out


def serie(ruta, col):
    return {r["fecha"]: float(r[col]) for r in csv.DictReader(open(ruta, encoding="utf-8")) if r[col]}


def cerca(s, fecha, dias=2):
    f = dt.date.fromisoformat(fecha)
    for k in sorted(range(-dias, dias + 1), key=abs):
        v = s.get((f + dt.timedelta(days=k)).isoformat())
        if v is not None:
            return round(v, 2)
    return None


def procesar(ev, sf, rc):
    eid, marco, titulo, fecha, col, plat, nota = ev
    transf = grilla(MARCOS[marco])
    items = [i for i in cat.search(collections=[col], intersects={"type": "Point", "coordinates": list(MARCOS[marco])},
                                   datetime=fecha).items() if not plat or i.properties.get("platform") == plat]
    # todos los cuadrantes de esa pasada que tocan el recuadro
    items += [i for i in cat.search(collections=[col], bbox=[-60.85, -31.78, -60.50, -31.45], datetime=fecha).items()
              if (not plat or i.properties.get("platform") == plat) and i.id not in {x.id for x in items}]
    r, g, b, sw = (banda(items, k, transf) for k in BANDAS[col][:4])
    qa = banda(items, BANDAS[col][4], transf, Resampling.nearest).astype("uint16")
    if col.startswith("sentinel"):
        nube = np.isin(qa, (3, 8, 9, 10))  # sombra, nube media, nube alta, cirro
    else:
        nube = (((qa >> 1) & 1) | ((qa >> 3) & 1) | ((qa >> 4) & 1)).astype(bool)
    valido = (g > 0) & (sw > 0)
    if valido.mean() < 0.9:  # pasadas de costado: el satélite no cubrió el recuadro
        raise RuntimeError(f"{eid}: la imagen del {fecha} cubre solo el {valido.mean():.0%} del recuadro")
    limpio = valido & ~nube
    rgb = np.dstack([np.clip((c - np.percentile(c[limpio], 2)) / (np.percentile(c[limpio], 98) - np.percentile(c[limpio], 2)), 0, 1) for c in (r, g, b)])
    rgb = (np.power(rgb, 0.85) * 255).astype("uint8")
    agua = ((g - sw) / np.maximum(g + sw, 1) > 0.05) & limpio
    Image.fromarray(rgb).resize(SALIDA, Image.LANCZOS).save(os.path.join(IMG, f"{eid}.jpg"), quality=82, optimize=True, progressive=True)
    m = Image.fromarray(agua.astype("uint8")).resize(SALIDA, Image.NEAREST)
    m.putpalette([0, 0, 0, 0, 200, 255] + [0, 0, 0] * 254)
    m.save(os.path.join(IMG, f"{eid}_agua.png"), transparency=0, optimize=True)
    km2 = round(float(agua.sum()) * RES * RES / 1e6, 1)
    out = {"id": eid, "marco": marco, "titulo": titulo, "fecha": fecha, "nota": nota, "agua_km2": km2,
           "nubes_pct": round(float(nube[valido].mean()) * 100), "parana_sf": cerca(sf, fecha), "salado_recreo": cerca(rc, fecha),
           "sensor": "Sentinel-2" if col.startswith("sentinel") else plat.replace("landsat-", "Landsat "), "credito": CREDITO[col],
           "escenas": [i.id for i in items]}
    print(eid, fecha, f"agua {km2} km² · nubes {out['nubes_pct']}% · SF {out['parana_sf']} · Recreo {out['salado_recreo']}")
    return out


def main():
    os.makedirs(IMG, exist_ok=True)
    sf = serie(os.path.join(RAIZ, "datos_ina", "parana_santa_fe_altura.csv"), "valor")
    rc = serie(os.path.join(RAIZ, "datos_salado", "recreo.csv"), "altura_m")
    ruta = os.path.join(AQUI, "escenas.json")
    previas = {e["id"]: e for e in json.load(open(ruta, encoding="utf-8"))} if os.path.exists(ruta) else {}
    pedidas = sys.argv[1:]
    for ev in EVENTOS:
        if not pedidas or ev[0] in pedidas:
            previas[ev[0]] = procesar(ev, sf, rc)
    orden = [e[0] for e in EVENTOS]
    json.dump([previas[i] for i in orden if i in previas], open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("listo:", ruta)


if __name__ == "__main__":
    main()
