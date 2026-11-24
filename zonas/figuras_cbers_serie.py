"""Figuras del anexo E del informe: serie en blanco y negro de los satélites CBERS (2009-2026).

Uso: python zonas/figuras_cbers_serie.py <carpeta de salida>
Parte de los recortes de cbers4a_serie.py (CBERS-4A, 2 m) y de los calzados por cbers_calzar.py (CBERS-2B de 2,7 m y CBERS-4 de 5 m).
Todos están en la misma grilla: 3000 x 2800 m, norte arriba.
"""
import os, sys
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
A4 = os.path.join(AQUI, "zona_precisa", "cbers4a")
CAL = os.path.join(AQUI, "zona_precisa", "cbers_anteriores", "calzadas")
F = ImageFont.truetype("arial.ttf", 30)
ANTES = [(os.path.join(CAL, "cbers_2009-09-13_hrc_2.7m_135_4_L2_calzada.png"), "13 de septiembre de 2009 · CBERS-2B, 2,7 m"),
         (os.path.join(CAL, "cbers_2009-12-31_hrc_2.7m_135_4_L2_calzada.png"), "31 de diciembre de 2009 · CBERS-2B, 2,7 m")]
SERIE = [(os.path.join(CAL, "cbers_2015-01-24_pan_5m_167_135_L2_calzada.png"), "24 ene 2015 · CBERS-4, 5 m"),
         (os.path.join(CAL, "cbers_2016-09-13_pan_5m_167_135_L2_calzada.png"), "13 sep 2016 · CBERS-4, 5 m"),
         (os.path.join(CAL, "cbers_2017-12-25_pan_5m_167_135_L2_calzada.png"), "25 dic 2017 · CBERS-4, 5 m"),
         (os.path.join(CAL, "cbers_2018-12-24_pan_5m_167_135_L2_calzada.png"), "24 dic 2018 · CBERS-4, 5 m"),
         (os.path.join(A4, "cbers4a_2020-02-12_L4_pan_2m.png"), "12 feb 2020 · CBERS-4A, 2 m"),
         (os.path.join(A4, "cbers4a_2022-08-30_L4_pan_2m.png"), "30 ago 2022 · CBERS-4A, 2 m"),
         (os.path.join(A4, "cbers4a_2024-01-08_L2_pan_2m.png"), "8 ene 2024 · CBERS-4A, 2 m"),
         (os.path.join(A4, "cbers4a_2026-09-26_L4_pan_2m.png"), "26 sep 2026 · CBERS-4A, 2 m")]


def pieza(ruta, texto, ancho):
    im = Image.open(ruta).convert("RGB")
    mpp = 3000 / ancho
    im = im.resize((ancho, round(im.height * ancho / im.width)), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 44], fill=(0, 0, 0))
    d.text((10, 5), texto, fill=(255, 255, 255), font=F)
    x1, y = im.width - 24, im.height - 22
    d.line([x1 - 500 / mpp, y, x1, y], fill=(255, 255, 255), width=5)
    d.text((x1 - 500 / mpp, y - 40), "500 m", fill=(255, 255, 255), font=F)
    return im


def hoja(piezas, col, sep=8):
    w, h = piezas[0].size
    filas = -(-len(piezas) // col)
    s = Image.new("RGB", (col * w + (col - 1) * sep, filas * h + (filas - 1) * sep), (255, 255, 255))
    for i, p in enumerate(piezas):
        s.paste(p, ((i % col) * (w + sep), (i // col) * (h + sep)))
    return s


def main(salida):
    hoja([pieza(r, t, 1200) for r, t in ANTES], 2).save(os.path.join(salida, "cbers_2009.jpg"), quality=88)
    hoja([pieza(r, t, 900) for r, t in SERIE[:4]], 2).save(os.path.join(salida, "cbers_serie_a.jpg"), quality=88)
    hoja([pieza(r, t, 900) for r, t in SERIE[4:]], 2).save(os.path.join(salida, "cbers_serie_b.jpg"), quality=88)
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1])
