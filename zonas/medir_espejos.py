"""Mide la superficie de un espejo de agua en las exportaciones de Google Earth Pro, fecha por fecha.

Uso: python zonas/medir_espejos.py <sur|norte> <carpeta de salida>
Método: cada exportación se lleva a una grilla UTM de 1 m por píxel (recortar_pasos.recorte). Desde uno o más puntos semilla puestos a mano
dentro del agua se marca todo lo que está conectado y tiene un color parecido (tolerancia por fecha, sobre la imagen suavizada).
La superficie es la cantidad de píxeles marcados (1 píxel = 1 m²). Se guarda una imagen por fecha con el contorno dibujado para revisarlo a ojo:
el número solo vale si el contorno sigue la orilla. No distingue agua de vegetación flotante ni de sombra de nubes.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from recortar_pasos import recorte, SAL

A, B, C = (735810, 6507566), (735593, 6507840), (735255, 6507880)   # lóbulo sudeste, lóbulo central, laguna circular del noroeste
N1, N2 = (736322, 6508245), (736334, 6508351)   # espejo del sector norte: tramo original y prolongación
CASOS = {
    "sur": {"caja": (735050, 6507100, 736450, 6508150), "marco": "marco_sur.json", "fechas": [
        # (carpeta, archivo, etiqueta, semillas, tolerancia)
        ("claves_sur", "k_02.jpg", "1/2012", [A], 9),
        ("claves_sur", "k_03.jpg", "1/2013", [A], 40),
        ("claves_sur", "k_04.jpg", "10/2013", [A], 40),
        ("claves_sur", "k_05.jpg", "7/2015", [A, B], 40),
        ("claves_sur", "k_07.jpg", "12/2016", [A, B], 22),
        ("claves_sur", "k_08.jpg", "5/2017", [A, B], 40),
        ("claves_sur", "k_09.jpg", "12/2018", [A, B], 40),
        # 4/2019 (k_10.jpg) no se mide: el agua tiene oleaje y reflejos y el contorno automático no sigue la orilla
        ("pasos_sur", "paso_04.jpg", "12/2022", [A, B, C], 40),
        ("pasos_sur", "paso_01.jpg", "3/2025", [A, B, C], 24),
    ]},
    "norte": {"caja": (736000, 6508050, 736600, 6508700), "marco": "marco.json", "fechas": [
        ("pasos", "paso_20.jpg", "4/2020", [N1], 35),
        ("pasos", "paso_18.jpg", "7/2020", [N1], 20),
        ("pasos", "paso_13.jpg", "12/2020", [N1], 35),
        ("pasos", "paso_07.jpg", "1/2022", [N1, N2], 35),
        ("pasos", "paso_03.jpg", "12/2022", [N1, N2], 18),
    ]},
}


def medir(cual, salida):
    caso = CASOS[cual]
    x0, y0, x1, y1 = caso["caja"]
    marco = json.load(open(os.path.join(SAL, caso["marco"]), encoding="utf-8"))["marco_utm"]
    os.makedirs(salida, exist_ok=True)
    filas, piezas = [], []
    for carpeta, archivo, etiqueta, semillas, tol in caso["fechas"]:
        im, _ = recorte(os.path.join(SAL, "google_earth", carpeta, archivo), marco, caso["caja"], 1.0)
        suave = im.filter(ImageFilter.GaussianBlur(3))
        total = Image.new("L", im.size, 0)
        for sx, sy in semillas:
            p = (int(sx - x0), int(y1 - sy))
            lienzo = suave.copy()
            ImageDraw.floodfill(lienzo, p, (255, 0, 255), thresh=tol)
            m = np.all(np.asarray(lienzo) == (255, 0, 255), axis=2)
            total = ImageChops.lighter(total, Image.fromarray((m * 255).astype("uint8")))
        total = total.filter(ImageFilter.MaxFilter(7)).filter(ImageFilter.MinFilter(7))   # cierra huecos chicos (olas, reflejos)
        area = int((np.asarray(total) > 127).sum())
        borde = ImageChops.subtract(total.filter(ImageFilter.MaxFilter(5)), total)
        vista = Image.composite(Image.new("RGB", im.size, (255, 255, 0)), im, borde)
        d = ImageDraw.Draw(vista)
        for sx, sy in semillas:
            d.ellipse([sx - x0 - 5, y1 - sy - 5, sx - x0 + 5, y1 - sy + 5], outline=(255, 0, 0), width=2)
        rot = f"{etiqueta}: {area / 10000:.1f} ha"
        d.rectangle([0, 0, 14 + 13 * len(rot), 30], fill=(0, 0, 0))
        d.text((6, 6), rot, fill=(255, 255, 0), font_size=20)
        vista.save(os.path.join(salida, f"{cual}_{etiqueta.replace('/', '-')}.jpg"), quality=88)
        piezas.append(vista.resize((im.width // 2, im.height // 2), Image.LANCZOS))
        filas.append({"fecha_selector": etiqueta, "archivo": f"{carpeta}/{archivo}", "superficie_m2": area, "superficie_ha": round(area / 10000, 2),
                      "semillas_utm": semillas, "tolerancia": tol})
        print(rot, flush=True)
    col = 5
    w, h = piezas[0].size
    hoja = Image.new("RGB", (col * w, -(-len(piezas) // col) * h))
    for i, p in enumerate(piezas):
        hoja.paste(p, ((i % col) * w, (i // col) * h))
    hoja.save(os.path.join(salida, f"{cual}_contornos.jpg"), quality=88)
    json.dump({"metodo": __doc__, "caja_utm": caso["caja"], "mediciones": filas}, open(os.path.join(salida, f"{cual}_superficies.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    medir(sys.argv[1], sys.argv[2])
