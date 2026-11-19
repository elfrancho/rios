"""Imagen de referencia con el río crecido: 23/01/2016, Paraná a 6,30 m en Santa Fe (el pico de esa crecida fue 6,60 m el 05/01/2016).

Uso: python zonas/armar_referencia.py     (solo en la notebook: rasterio, pystac-client, planetary-computer)
Agrega la fecha a zonas/zona_a_investigar (img/2016-01-23.jpg, img/2016-01-23_pan.jpg y una entrada en escenas.json). Después hay que
correr zonas/armar_zona_precisa.py y zonas/armar_vista.py para que aparezca en las dos vistas.

- Detalle: CBERS-4, cámara PAN de 5 m (pancromática), del catálogo público del INPE de Brasil (colección CB4-PAN5M-L2-DN-1).
- Color: Sentinel-2 L2A del mismo día (10 m, 1 % de nubes), de Microsoft Planetary Computer. Las dos pasaron con minutos de diferencia.
- La imagen en color es el color de Sentinel-2 con el detalle de la pancromática (método Brovey); la de blanco y negro es la
  pancromática sola. En las dos, cada píxel real son 5 m, agrandados a la grilla de 2 m del resto de la serie.
- Ubicación: la pancromática viene sin ortorrectificar; se alinea con la de Sentinel-2 del mismo día (correlación de fase) y después
  se intenta llevar las dos al marco de la serie de 2 m comparando con su fecha de aguas más altas. Lo que se corrió queda guardado.
"""
import csv, json, os
import numpy as np, pystac_client, planetary_computer, rasterio, urllib.request
from PIL import Image
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT
from armar_zona_cbers import corrimiento, estirar, leer, estado

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ZONA = os.path.join(AQUI, "zona_a_investigar")
FECHA, PAD = "2016-01-23", 300          # PAD: 300 px de 2 m = 600 m de más alrededor, para poder alinear
SERIE_ALTA = "2023-12-08"               # la fecha de aguas más altas de la serie de 2 m (5,30 m), para llevarla a su marco
CRS = "EPSG:32720"


def stac_inpe(col):
    cuerpo = json.dumps({"collections": [col], "bbox": BBOX, "datetime": f"{FECHA}T00:00:00Z/{FECHA}T23:59:59Z", "limit": 20}).encode()
    req = urllib.request.Request("https://data.inpe.br/bdc/stac/v1/search", data=cuerpo, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=90))["features"]


d = json.load(open(os.path.join(ZONA, "escenas.json"), encoding="utf-8"))
x0, y1, RES, W, H = d["grilla"]
BBOX = d["bbox_lonlat"]
X0, Y1, WP, HP = x0 - PAD * RES, y1 + PAD * RES, W + 2 * PAD, H + 2 * PAD
T = from_origin(X0, Y1, RES, RES)

# --- pancromática de 5 m (se lee ya agrandada a la grilla de 2 m)
pans = stac_inpe("CB4-PAN5M-L2-DN-1")
pan, pan_id = None, None
for it in pans:
    a = leer(it["assets"]["BAND1"]["href"], X0, Y1, WP, HP, 2.5, hilos=4)
    print("pancromática", it["id"], "cubre", round(float((a > 0).mean()), 3))
    if (a > 0).mean() > 0.995:
        pan, pan_id = a, it["id"]
        break
if pan is None:
    print("la pancromática de 5 m no cubre el encuadre: se usa solo Sentinel-2 (10 m)")

# --- color de Sentinel-2 del mismo día
cat = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
s2 = list(cat.search(collections=["sentinel-2-l2a"], bbox=BBOX, datetime=FECHA).items())
print("Sentinel-2:", [(i.id, i.properties.get("eo:cloud_cover")) for i in s2])


def banda(clave):
    out = np.zeros((HP, WP), dtype="float32")
    for it in s2:
        with rasterio.open(planetary_computer.sign(it.assets[clave].href.split("?")[0])) as src, WarpedVRT(
                src, crs=CRS, transform=T, width=WP, height=HP, resampling=Resampling.cubic, nodata=0) as vrt:
            a = vrt.read(1).astype("float32")
        out = np.where((out == 0) & (a > 0), a, out)
    base = 1000 if float(s2[0].properties.get("s2:processing_baseline", "0")) >= 4 else 0
    return np.clip((out - base) / 10000, 0, None)


r, g, b = banda("B04"), banda("B03"), banda("B02")
print("Sentinel-2 cubre", round(float((r > 0).mean()), 3))
inten = (r + g + b) / 3

# --- 1) pancromática sobre Sentinel-2 (mismo día: la altura del agua es la misma)
dy = dx = 0
if pan is not None:
    dy, dx, pico = corrimiento(inten, pan)
    print(f"pancromática respecto de Sentinel-2: {dx * RES} m en x, {dy * RES} m en y · pico {pico:.0f}")
    if max(abs(dy), abs(dx)) > PAD - 5 or pico < 8:
        raise SystemExit("no se pudo alinear la pancromática con Sentinel-2")
    pan = np.roll(np.roll(pan, dy, axis=0), dx, axis=1)
guia = pan if pan is not None else inten   # con qué se compara contra la serie

# --- 2) las dos al marco de la serie de 2 m (si la correlación con la fecha de aguas más altas es firme)
corte = (slice(PAD, PAD + H), slice(PAD, PAD + W))
serie = np.asarray(Image.open(os.path.join(ZONA, "img", SERIE_ALTA + "_pan.jpg")).convert("L")).astype("float32")
sy, sx, pico2 = corrimiento(serie, guia[corte])
a_serie = max(abs(sy), abs(sx)) * RES <= 40 and pico2 >= 12
print(f"respecto de la serie de 2 m ({SERIE_ALTA}): {sx * RES} m en x, {sy * RES} m en y · pico {pico2:.0f} ->", "se aplica" if a_serie else "NO se aplica")
if not a_serie:
    sy = sx = 0
corte = (slice(PAD - sy, PAD - sy + H), slice(PAD - sx, PAD - sx + W))
r, g, b, inten = (c[corte] for c in (r, g, b, inten))
pan = pan[corte] if pan is not None else None

# --- color con el detalle de la pancromática
if pan is not None:
    ok = (pan > 0) & (inten > 0)
    gan, des = np.polyfit(pan[ok][::7], inten[ok][::7], 1)      # la pancromática llevada a la escala de brillo de Sentinel-2
    razon = np.clip((pan * gan + des) / np.maximum(inten, 1e-3), 0.4, 2.5)
else:
    razon = 1
cr, cg, cb = estirar([r * razon, g * razon, b * razon])
Image.fromarray((np.dstack([cr, cg, cb]) * 255).astype("uint8")).save(os.path.join(ZONA, "img", FECHA + ".jpg"), quality=90, optimize=True)
if pan is not None:
    Image.fromarray((estirar([pan])[0] * 255).astype("uint8")).save(os.path.join(ZONA, "img", FECHA + "_pan.jpg"), quality=90, optimize=True)

sf = {x["fecha"]: float(x["valor"]) for x in csv.DictReader(open(os.path.join(RAIZ, "datos_ina", "parana_santa_fe_altura.csv"), encoding="utf-8")) if x["valor"]}
h = sf.get(FECHA)
entrada = {"fecha": FECHA, "hora_utc": s2[0].properties["datetime"][11:16], "satelite": "", "resolucion_m": 5 if pan is not None else 10, "id": pan_id or s2[0].id,
           "satelite_vista": "Crecida 2016 · CBERS-4 y Sentinel-2" if pan is not None else "Crecida 2016 · Sentinel-2", "referencia": True, "pan": pan is not None,
           "credito": ("Imagen: CBERS-4 PAN · INPE (Brasil), con color de Sentinel-2 · ESA/Copernicus · 23/01/2016" if pan is not None
                       else "Imagen: Sentinel-2 · ESA/Copernicus · 23/01/2016 · 10 m por píxel"),
           "color_de": [i.id for i in s2], "alineada": "sí" if a_serie else "sí (con Sentinel-2; sin llevar al marco de la serie)",
           "corrida_m": [(dx + sx) * RES, (dy + sy) * RES], "parana_sf_m": h, "estado": estado(h), "brillo": 0, "agua_ha": None}
entrada["satelite"] = entrada.pop("satelite_vista")
d["escenas"] = sorted([e for e in d["escenas"] if e["fecha"] != FECHA] + [entrada], key=lambda e: e["fecha"], reverse=True)
json.dump(d, open(os.path.join(ZONA, "escenas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("listo:", FECHA, "Paraná en Santa Fe", h, "m ·", entrada["estado"], "· corrida total", entrada["corrida_m"], "m")
