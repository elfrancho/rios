"""Serie de imágenes de 2 m de una zona marcada en el Marcador de la Setúbal, de hoy hacia atrás (para ver objetos chicos).

Se corre SOLO en la notebook (rasterio). Uso:
  python zonas/armar_zona_cbers.py <marcas.json bajado con ArtifactData> "<parte del nombre de la zona>" [--max N] [--bateria 25]
-> zonas/<zona>/img/<fecha>.jpg (color, 2 m), <fecha>_pan.jpg (blanco y negro, lo más nítido), zonas/<zona>/escenas.json y vista.html
Se puede cortar y volver a correr: sigue donde quedó. Se frena solo si la batería baja del mínimo.

- Fuente: satélite CBERS-4A (China-Brasil), cámara WPM: pancromática de 2 m y color de 8 m. Catálogo público del INPE de Brasil,
  https://data.inpe.br/bdc/stac/v1 (colecciones CB4A-WPM-L4-DN-1, ortorrectificada, y CB4A-WPM-L2-DN-1), sin cuenta. Hay desde 2020:
  el satélite se lanzó en diciembre de 2019. La fecha y la hora de cada imagen son las del catálogo (UTC; ~13:45 = ~10:45 de Argentina).
- Color de 2 m: el color de 8 m se agranda y se le aplica el detalle de la pancromática (método Brovey, con el infrarrojo en la
  intensidad porque la pancromática también lo ve). El detalle fino es real (pancromática); el color de cada objeto chico es aproximado.
- Las imágenes vienen con errores de ubicación de decenas de metros: cada una se alinea con la primera (correlación de fase) y se
  guarda cuánto se corrió. Si no se pudo alinear, queda marcada.
- Nubes: no hay máscara oficial. Se descarta si más del 15 % del encuadre es muy brillante o está saturado en azul; el resto se revisa a ojo
  (campo `brillo`). Los valores son cuentas del sensor, no reflectancia: el contraste se ajusta en cada imagen.
- Agua: NDWI = (verde - infrarrojo) / (verde + infrarrojo) > 0, a 8 m. `agua_ha` son las hectáreas DENTRO del polígono (aproximado).
- Altura del Paraná en el puerto de Santa Fe ese día (datos_ina). Aguas bajas / medias / altas: debajo de 2,36 m, entre medio o
  arriba de 4,22 m (cuartos inferior y superior de todo el registro 1925-hoy).
"""
import argparse, csv, ctypes, datetime as dt, json, os, re, time, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np, rasterio
from PIL import Image
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import transform as reproyectar
from rasterio.windows import Window

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
CRS, RES, PAD = "EPSG:32720", 2, 100   # PAD: píxeles de más alrededor para poder alinear (200 m)
BAJA, ALTA = 2.36, 4.22
STAC = "https://data.inpe.br/bdc/stac/v1/search"
os.environ.setdefault("GDAL_DISABLE_READDIR_ON_OPEN", "EMPTY_DIR")
os.environ.setdefault("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", ".tif")
os.environ.setdefault("GDAL_HTTP_MERGE_CONSECUTIVE_RANGES", "YES")
os.environ.setdefault("GDAL_HTTP_MAX_RETRY", "3")
os.environ.setdefault("GDAL_HTTP_RETRY_DELAY", "5")


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def bateria():
    class S(ctypes.Structure):
        _fields_ = [("ac", ctypes.c_byte), ("flag", ctypes.c_byte), ("pct", ctypes.c_byte), ("r", ctypes.c_byte),
                    ("life", ctypes.c_ulong), ("full", ctypes.c_ulong)]
    s = S()
    ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(s))
    return 100 if s.ac == 1 else s.pct & 0xFF


def buscar(col, bbox):
    cuerpo = json.dumps({"collections": [col], "bbox": bbox, "datetime": "2019-12-01T00:00:00Z/2030-01-01T00:00:00Z", "limit": 500}).encode()
    req = urllib.request.Request(STAC, data=cuerpo, headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=90))["features"]


def leer(href, x0, y1, ancho, alto, escala=1, hilos=1):
    """Recorte [x0, y1] de ancho x alto píxeles de 2 m. escala=4 para las bandas de 8 m (se devuelven agrandadas a 2 m)."""
    def trozo(f0, f1):
        with rasterio.open(href) as s:
            c0, r0 = (x0 - s.transform.c) / s.res[0], (s.transform.f - y1) / s.res[1]
            w = Window(c0, r0 + f0 / escala, ancho / escala, (f1 - f0) / escala)
            return s.read(1, window=w, out_shape=(f1 - f0, ancho), boundless=True, fill_value=0,
                          resampling=Resampling.bilinear if escala > 1 else Resampling.nearest)
    if hilos == 1:
        return trozo(0, alto).astype("float32")
    cortes = np.linspace(0, alto, hilos + 1).astype(int)
    cortes = (cortes // 4) * 4
    cortes[-1] = alto
    with ThreadPoolExecutor(hilos) as p:
        return np.vstack(list(p.map(lambda i: trozo(cortes[i], cortes[i + 1]), range(hilos)))).astype("float32")


def corrimiento(ref, img):
    """Cuántos píxeles hay que mover img para que calce con ref (correlación de fase sobre los bordes)."""
    def prep(a):
        gy, gx = np.gradient(a)
        g = np.hypot(gx, gy)
        g = (g - g.mean()) / (g.std() + 1e-6)
        return g * np.outer(np.hanning(a.shape[0]), np.hanning(a.shape[1]))
    A, B = np.fft.fft2(prep(ref)), np.fft.fft2(prep(img))
    R = A * np.conj(B)
    c = np.abs(np.fft.ifft2(R / (np.abs(R) + 1e-9)))
    i, j = np.unravel_index(np.argmax(c), c.shape)
    dy, dx = (i if i < c.shape[0] / 2 else i - c.shape[0]), (j if j < c.shape[1] / 2 else j - c.shape[1])
    return int(dy), int(dx), float(c.max() / (c.mean() + 1e-9))


def estirar(canales):
    """Resta la bruma (1 % más oscuro de cada canal) y aplica la misma ganancia a los tres."""
    ok = canales[0] > 0
    cs = [np.clip(c - np.percentile(c[ok], 1), 0, None) for c in canales]
    tope = np.percentile(np.mean(cs, axis=0)[ok], 99.7) * 1.15 + 1e-6
    return [np.clip(c / tope, 0, 1) ** 0.75 for c in cs]


def estado(h):
    return None if h is None else "aguas bajas" if h < BAJA else "aguas altas" if h > ALTA else "aguas medias"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("marcas"), ap.add_argument("nombre")
    ap.add_argument("--max", type=int, default=0), ap.add_argument("--bateria", type=int, default=25), ap.add_argument("--salida")
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
    mx, my = max(200, (max(px) - min(px)) * 0.10), max(200, (max(py) - min(py)) * 0.10)
    x0, y1 = np.floor((min(px) - mx) / 8) * 8, np.ceil((max(py) + my) / 8) * 8
    W, H = int(np.ceil((max(px) + mx - x0) / 8) * 4), int(np.ceil((y1 - (min(py) - my)) / 8) * 4)
    lon, lat = reproyectar(CRS, "EPSG:4326", [x0, x0 + W * RES], [y1 - H * RES, y1])
    plon, plat = reproyectar(CRS, "EPSG:4326", px, py)
    dentro = rasterize([({"type": "Polygon", "coordinates": [list(zip(px, py))]}, 1)], out_shape=(H, W),
                       transform=from_origin(x0, y1, RES, RES)).astype(bool)
    print(f"Zona «{z['nombre']}»: encuadre {W * RES / 1000:.2f} x {H * RES / 1000:.2f} km a {RES} m ({W} x {H} px)", flush=True)

    sal = a.salida or os.path.join(AQUI, slug(z["nombre"]))
    img = os.path.join(sal, "img")
    os.makedirs(img, exist_ok=True)
    ruta = os.path.join(sal, "escenas.json")
    prev = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}
    mismo = prev.get("grilla") == [x0, y1, RES, W, H]
    escenas = {e["fecha"]: e for e in prev.get("escenas", [])} if mismo else {}
    descartadas = prev.get("descartadas", {}) if mismo else {}
    refruta = os.path.join(sal, "referencia.npy")
    ref = np.load(refruta) if mismo and os.path.exists(refruta) else None
    sf = {r["fecha"]: float(r["valor"]) for r in csv.DictReader(open(os.path.join(RAIZ, "datos_ina", "parana_santa_fe_altura.csv"),
                                                                       encoding="utf-8")) if r["valor"]}

    def guardar():
        json.dump({"zona": z["nombre"], "nota": z.get("nota", ""), "generado": dt.datetime.now().isoformat(timespec="seconds"),
                   "fuente": "CBERS-4A WPM (INPE, Brasil): pancromática de 2 m + color de 8 m", "resolucion_m": RES,
                   "grilla": [x0, y1, RES, W, H], "bbox_lonlat": [round(lon[0], 6), round(lat[0], 6), round(lon[1], 6), round(lat[1], 6)],
                   "ancho_km": W * RES / 1000, "alto_km": H * RES / 1000,
                   "poligono_lonlat": [[round(u, 6), round(v, 6)] for u, v in zip(plon, plat)],
                   "poligono_px": [[round((u - x0) / RES / W, 5), round((y1 - v) / RES / H, 5)] for u, v in zip(px, py)],
                   "poligono_ha": round(float(dentro.sum()) * RES * RES / 1e4, 1), "criterio_alturas": {"bajas_menos_de": BAJA, "altas_mas_de": ALTA},
                   "escenas": [escenas[f] for f in sorted(escenas, reverse=True)], "descartadas": descartadas},
                  open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    bbox = [lon[0], lat[0], lon[1], lat[1]]
    pasadas = {}
    for col in ("CB4A-WPM-L4-DN-1", "CB4A-WPM-L2-DN-1"):  # primero la ortorrectificada
        for it in buscar(col, bbox):
            pasadas.setdefault(it["properties"]["datetime"][:10], []).append(it)
    fechas = sorted(pasadas, reverse=True)
    print(len(fechas), "fechas en el catálogo entre", fechas[-1], "y", fechas[0], flush=True)
    X0, Y1, WP, HP = x0 - PAD * RES, y1 + PAD * RES, W + 2 * PAD, H + 2 * PAD
    hechas = 0
    # la referencia para alinear tiene que ser una ortorrectificada (L4): hasta tener una, se prueban primero esas
    primero = [f for f in fechas if pasadas[f][0]["id"].endswith("L4")] if ref is None else []
    for f in primero + fechas:
        if ref is None and not pasadas[f][0]["id"].endswith("L4"):
            continue
        if f in escenas or f in descartadas:
            continue
        if a.max and hechas >= a.max:
            break
        if bateria() < a.bateria:
            print(f"Batería en {bateria()} %: freno acá. Volvé a correrlo con el cargador y sigue donde quedó.", flush=True)
            break
        t0 = time.time()
        try:
            elegido = None
            for it in pasadas[f]:
                azul = leer(it["assets"]["BAND1"]["href"], X0, Y1, WP, HP, 4)
                if (azul > 0).mean() > 0.995:
                    elegido = it
                    break
            if elegido is None:
                descartadas[f] = "la pasada no cubre el encuadre entero"
                print(" ", f, "descartada:", descartadas[f], flush=True)
                guardar()
                continue
            med = float(np.median(azul[azul > 0]))
            brillo = float(((azul > med * 1.8) | (azul > 450)).mean())   # 450 de 1023: nube o saturado
            if brillo > 0.15:
                descartadas[f] = f"nubes: {brillo:.0%} del encuadre muy brillante"
                print(" ", f, "descartada:", descartadas[f], flush=True)
                guardar()
                continue
            A = elegido["assets"]
            with ThreadPoolExecutor(3) as p:
                verde, rojo, nir = p.map(lambda k: leer(A[k]["href"], X0, Y1, WP, HP, 4), ("BAND2", "BAND3", "BAND4"))
            pan = leer(A["BAND0"]["href"], X0, Y1, WP, HP, 1, hilos=6)
        except Exception as e:  # una fecha que falla no corta la serie; se reintenta en la próxima corrida
            print(" ", f, "ERROR, se saltea:", type(e).__name__, str(e)[:150], flush=True)
            continue
        if (pan > 0).mean() < 0.995:
            descartadas[f] = "la pancromática no cubre el encuadre entero"
            print(" ", f, "descartada:", descartadas[f], flush=True)
            guardar()
            continue
        dy = dx = 0
        alineada = "referencia"
        if ref is None:
            ref = pan
            np.save(refruta, ref)
        else:
            dy, dx, pico = corrimiento(ref, pan)
            if max(abs(dy), abs(dx)) <= PAD and pico > 8:
                alineada = "sí"
            else:
                alineada, dy, dx = f"no (pico {pico:.0f})", 0, 0
        corte = (slice(PAD - dy, PAD - dy + H), slice(PAD - dx, PAD - dx + W))
        pan, azul, verde, rojo, nir = (c[corte] for c in (pan, azul, verde, rojo, nir))
        razon = pan / ((azul + verde + rojo + nir) / 4 + 1e-3)
        r, v, b = estirar([rojo * razon, verde * razon, azul * razon])
        Image.fromarray((np.dstack([r, v, b]) * 255).astype("uint8")).save(os.path.join(img, f + ".jpg"), quality=90, optimize=True)
        Image.fromarray((estirar([pan])[0] * 255).astype("uint8")).save(os.path.join(img, f + "_pan.jpg"), quality=90, optimize=True)
        agua = (verde - nir) / np.maximum(verde + nir, 1e-3) > 0
        h = sf.get(f)
        escenas[f] = {"fecha": f, "hora_utc": elegido["properties"]["datetime"][11:16], "satelite": "CBERS-4A WPM", "resolucion_m": RES,
                      "nivel": elegido["id"][-2:], "id": elegido["id"], "brillo": round(brillo, 3), "alineada": alineada,
                      "corrida_m": [dx * RES, dy * RES], "parana_sf_m": h, "estado": estado(h),
                      "agua_ha": round(float((agua & dentro).sum()) * RES * RES / 1e4, 1)}
        hechas += 1
        print(f, elegido["id"][-2:], f"SF {h} m · agua {escenas[f]['agua_ha']} ha · brillo {brillo:.1%} · alineada {alineada} "
              f"({dx * RES}, {dy * RES} m) · {time.time() - t0:.0f} s · batería {bateria()} %", flush=True)
        guardar()
    guardar()
    plantilla = os.path.join(AQUI, "plantilla_vista.html")
    datos = json.load(open(ruta, encoding="utf-8"))
    datos.pop("descartadas")
    open(os.path.join(sal, "vista.html"), "w", encoding="utf-8").write(
        open(plantilla, encoding="utf-8").read().replace("/*DATOS*/null", json.dumps(datos, ensure_ascii=False)))
    print("listo:", len(escenas), "imágenes,", len(descartadas), "fechas descartadas ->", os.path.join(sal, "vista.html"), flush=True)


if __name__ == "__main__":
    main()
