"""Recorta un mismo rectángulo de terreno de todas las exportaciones de Google Earth Pro y arma una hoja para compararlas.

Uso: python zonas/recortar_pasos.py <norte|sur|claves> <x0> <y0> <x1> <y1> <metros_por_pixel> <salida.jpg> [pasos separados por coma]
Las coordenadas son UTM 20S (EPSG:32720). Cada exportación se ubica por las cuatro esquinas de su recuadro magenta
(transformación proyectiva), así que también sirve para terreno que queda fuera del recuadro.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw

Image.MAX_IMAGE_PIXELS = None
AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = os.path.join(AQUI, "zona_precisa")
sys.path.insert(0, AQUI)
from armar_zona_precisa import esquinas, PASOS


def proyectiva(origen, destino):
    """Matriz 3x3 que lleva los puntos de `origen` a los de `destino` (cuatro pares)."""
    A, b = [], []
    for (x, y), (u, v) in zip(origen, destino):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
        b += [u, v]
    h = np.linalg.solve(np.array(A, float), np.array(b, float))
    return np.append(h, 1).reshape(3, 3)


def recorte(ruta, marco, caja, mpp):
    """Devuelve el rectángulo `caja` (x0, y0, x1, y1 en UTM) de la exportación `ruta`, a `mpp` metros por píxel."""
    mx0, my0, mx1, my1 = marco
    im = Image.open(ruta).convert("RGB")
    no, ne, se, so = esquinas(np.asarray(im).astype(int))
    H = proyectiva([(mx0, my1), (mx1, my1), (mx1, my0), (mx0, my0)], [no, ne, se, so])   # UTM -> píxel de la exportación
    x0, y0, x1, y1 = caja

    def px(x, y):
        u, v, w = H @ np.array([x, y, 1.0])
        return u / w, v / w
    q = px(x0, y1) + px(x0, y0) + px(x1, y0) + px(x1, y1)   # NO, SO, SE, NE: orden de Image.QUAD
    W, Hh = int(round((x1 - x0) / mpp)), int(round((y1 - y0) / mpp))
    dentro = all(0 <= q[i] <= im.width and 0 <= q[i + 1] <= im.height for i in range(0, 8, 2))
    return im.transform((W, Hh), Image.QUAD, q, Image.BICUBIC), dentro


def main():
    cual, x0, y0, x1, y1, mpp, salida = sys.argv[1], *map(float, sys.argv[2:7]), sys.argv[7]
    solo = [int(n) for n in sys.argv[8].split(",")] if len(sys.argv) > 8 else None
    marco = json.load(open(os.path.join(SAL, "marco.json" if cual == "norte" else "marco_sur.json"), encoding="utf-8"))["marco_utm"]
    nombre = {"norte": "pasos", "sur": "pasos_sur", "claves": "claves_sur"}[cual]   # claves: fechas elegidas del recuadro sur (k_NN.jpg)
    carpeta = os.path.join(SAL, "google_earth", nombre)
    etiquetas = json.load(open(os.path.join(SAL, "google_earth", nombre + ".json"), encoding="utf-8")) if cual != "norte" else {}
    piezas = []
    for n in sorted(os.listdir(carpeta)):
        num = int(n.split("_")[1][:2])
        if solo and num not in solo:
            continue
        r, dentro = recorte(os.path.join(carpeta, n), marco, (x0, y0, x1, y1), mpp)
        rot = (f"paso {num}: " + (PASOS[num][0] if cual == "norte" else etiquetas.get(str(num), "?"))) + ("" if dentro else " (incompleto)")
        d = ImageDraw.Draw(r)
        d.rectangle([0, 0, 8 + 7 * len(rot), 16], fill=(0, 0, 0))
        d.text((4, 2), rot, fill=(255, 255, 0))
        piezas.append(r)
    col = min(len(piezas), 5 if len(piezas) > 6 else 3)
    fil = -(-len(piezas) // col)
    w, h = piezas[0].size
    hoja = Image.new("RGB", (col * w, fil * h))
    for i, p in enumerate(piezas):
        hoja.paste(p, ((i % col) * w, (i // col) * h))
    hoja.save(salida, quality=88)
    print(len(piezas), "recortes de", w, "x", h, "->", salida, hoja.size)


if __name__ == "__main__":
    main()
