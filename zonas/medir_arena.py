"""Mide la superficie de arena clara expuesta en el sector sur, en las fechas en que el relleno todavía no tiene vegetación ni casas.

Uso: python zonas/medir_arena.py <carpeta de salida>
Método: exportación llevada a grilla UTM de 1 m por píxel; se cuenta como arena todo píxel muy claro (los tres colores por encima de un umbral
por fecha, sobre la imagen suavizada), en manchas de más de media hectárea, dentro del polígono del loteo y su entorno. Se guarda la imagen con el
contorno para revisarlo a ojo. Las nubes también son claras: hay que descartarlas mirando el contorno. Sirve solo mientras la arena está desnuda.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from recortar_pasos import recorte, SAL

CAJA = (735050, 6507100, 736450, 6508150)
FECHAS = [("k_02.jpg", "1/2012", 175), ("k_03.jpg", "1/2013", 175), ("k_04.jpg", "10/2013", 175), ("k_05.jpg", "7/2015", 175), ("k_07.jpg", "12/2016", 175)]


def manchas(m, minimo):
    """Deja solo las manchas conectadas de al menos `minimo` píxeles (recorrido por filas, sin librerías extra)."""
    im = Image.fromarray((m * 255).astype("uint8")).convert("RGB")
    sal = np.zeros(m.shape, bool)
    a = np.asarray(im)[..., 0].copy()
    ys, xs = np.nonzero(a[::8, ::8] > 127)
    for y, x in zip(ys * 8, xs * 8):
        if np.asarray(im)[y, x].tolist() != [255, 255, 255]:
            continue
        ImageDraw.floodfill(im, (int(x), int(y)), (255, 0, 0))
        b = np.asarray(im)
        esta = (b[..., 0] == 255) & (b[..., 1] == 0)
        if esta.sum() >= minimo:
            sal |= esta
        ImageDraw.floodfill(im, (int(x), int(y)), (0, 0, 0))
    return sal


def main(salida):
    marco = json.load(open(os.path.join(SAL, "marco_sur.json"), encoding="utf-8"))["marco_utm"]
    os.makedirs(salida, exist_ok=True)
    filas, piezas = [], []
    for archivo, etiqueta, umbral in FECHAS:
        im, _ = recorte(os.path.join(SAL, "google_earth", "claves_sur", archivo), marco, CAJA, 1.0)
        s = np.asarray(im.filter(ImageFilter.GaussianBlur(4))).astype(int)
        m = manchas(s.min(axis=2) > umbral, 5000)
        area = int(m.sum())
        total = Image.fromarray((m * 255).astype("uint8"))
        borde = ImageChops.subtract(total.filter(ImageFilter.MaxFilter(5)), total)
        vista = Image.composite(Image.new("RGB", im.size, (255, 0, 255)), im, borde)
        d = ImageDraw.Draw(vista)
        rot = f"{etiqueta}: arena {area / 10000:.1f} ha"
        d.rectangle([0, 0, 14 + 13 * len(rot), 30], fill=(0, 0, 0))
        d.text((6, 6), rot, fill=(255, 255, 0), font_size=20)
        piezas.append(vista.resize((im.width // 2, im.height // 2), Image.LANCZOS))
        filas.append({"fecha_selector": etiqueta, "archivo": "claves_sur/" + archivo, "arena_m2": area, "arena_ha": round(area / 10000, 2), "umbral": umbral})
        print(rot, flush=True)
    w, h = piezas[0].size
    hoja = Image.new("RGB", (len(piezas) * w, h))
    for i, p in enumerate(piezas):
        hoja.paste(p, (i * w, 0))
    hoja.save(os.path.join(salida, "sur_arena_contornos.jpg"), quality=88)
    json.dump({"metodo": __doc__, "caja_utm": CAJA, "mediciones": filas}, open(os.path.join(salida, "sur_arena.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
