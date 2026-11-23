"""Recortes de detalle del objeto alargado que aparece en el agua, con las coordenadas del centro de cada recorte.

Uso: python zonas/detalle_objeto.py <carpeta de salida>
Cada recorte mide 140 x 105 m y se saca de la exportación original a 0,25 m por píxel (la imagen original tiene ≈0,45 m por píxel:
el recorte está agrandado, no tiene más detalle que el original). Las posiciones se ubicaron a ojo sobre cada exportación.
"""
import json, os, sys
from PIL import Image, ImageDraw
from rasterio.warp import transform as reproyectar

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from recortar_pasos import recorte, SAL

# (sector, carpeta, archivo, fecha del selector, centro UTM 20S)
CASOS = [
    ("sur", "claves_sur", "k_04.jpg", "10/2013", (735660, 6507847)),
    ("sur", "claves_sur", "k_05.jpg", "7/2015", (735514, 6507851)),
    ("sur", "claves_sur", "k_07.jpg", "12/2016", (735836, 6507511)),
    ("sur", "claves_sur", "k_08.jpg", "5/2017", (735311, 6507891)),
    ("sur", "claves_sur", "k_09.jpg", "12/2018", (735844, 6507541)),
    ("norte", "pasos", "paso_20.jpg", "4/2020", (736268, 6508160)),
    ("norte", "pasos", "paso_18.jpg", "7/2020", (736320, 6508255)),
    ("norte", "pasos", "paso_16.jpg", "10/2020", (736262, 6508145)),
    ("norte", "pasos", "paso_15.jpg", "11/2020", (736262, 6508145)),
]
ANCHO, ALTO, MPP = 140, 105, 0.25


def main(salida):
    os.makedirs(salida, exist_ok=True)
    marcos = {s: json.load(open(os.path.join(SAL, m), encoding="utf-8"))["marco_utm"] for s, m in (("sur", "marco_sur.json"), ("norte", "marco.json"))}
    piezas, filas = [], []
    for sector, carpeta, archivo, fecha, (cx, cy) in CASOS:
        caja = (cx - ANCHO / 2, cy - ALTO / 2, cx + ANCHO / 2, cy + ALTO / 2)
        im, dentro = recorte(os.path.join(SAL, "google_earth", carpeta, archivo), marcos[sector], caja, MPP)
        lon, lat = reproyectar("EPSG:32720", "EPSG:4326", [cx], [cy])
        d = ImageDraw.Draw(im)
        rot = f"{fecha} · centro {abs(lat[0]):.5f}° S, {abs(lon[0]):.5f}° O"
        d.rectangle([0, 0, im.width, 24], fill=(0, 0, 0))
        d.text((6, 4), rot, fill=(255, 255, 0), font_size=15)
        d.line([im.width - 20 - 20 / MPP, im.height - 14, im.width - 20, im.height - 14], fill=(255, 255, 255), width=3)   # escala: 20 m
        d.text((im.width - 20 - 20 / MPP, im.height - 34), "20 m", fill=(255, 255, 255), font_size=14)
        im.save(os.path.join(salida, f"detalle_{sector}_{fecha.replace('/', '-')}.jpg"), quality=90)
        piezas.append(im)
        filas.append({"sector": sector, "fecha_selector": fecha, "archivo": f"{carpeta}/{archivo}", "centro_utm": [cx, cy],
                      "centro_lat": round(lat[0], 6), "centro_lon": round(lon[0], 6), "completo": dentro})
    col = 3
    w, h = piezas[0].size
    hoja = Image.new("RGB", (col * w, -(-len(piezas) // col) * h), (255, 255, 255))
    for i, p in enumerate(piezas):
        hoja.paste(p, ((i % col) * w, (i // col) * h))
    hoja.save(os.path.join(salida, "detalle_hoja.jpg"), quality=90)
    json.dump({"metodo": __doc__, "recortes": filas}, open(os.path.join(salida, "detalle.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(len(piezas), "recortes ->", salida)


if __name__ == "__main__":
    main(sys.argv[1])
