"""Figuras del informe hechas con las exportaciones de Google Earth Pro del 23/11/2026 (reemplazan a las capturas de pantalla de Google Earth web).

Uso: python zonas/figuras_exportadas_2014_2018.py <carpeta de salida>
Exportaciones: «Guardar imagen», resolución máxima (8192x5559), sin título, leyenda, escala ni brújula, con el recuadro magenta del sector.
El día de cada imagen se leyó en la línea de tiempo de Google Earth Pro acercada hasta mostrar día y hora (hora local, UTC-3: «22/6/2015 21:00»
corresponde al 23/6/2015 en hora universal, que es la fecha que da Google Earth web).
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from recortar_pasos import recorte, SAL

GE = os.path.join(SAL, "google_earth")
F = ImageFont.truetype("arial.ttf", 30)
NORTE = [("2014-04-23", "23 de abril de 2014"), ("2015-06-23", "23 de junio de 2015"), ("2015-07-15", "15 de julio de 2015"),
         ("2016-12-09", "9 de diciembre de 2016"), ("2018-06-29", "29 de junio de 2018")]
CAJA_N, MPP_N = (736050, 6507950, 736550, 6508325), 0.5
CAJA_S, MPP_S = (735250, 6507350, 736050, 6507950), 0.8
DET_S = (735628, 6507869)   # centro del recorte de detalle del 7/3/2014 (ubicado a ojo)


def rotulo(im, texto, metros, mpp):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 44], fill=(0, 0, 0))
    d.text((10, 5), texto, fill=(255, 255, 255), font=F)
    x1, y = im.width - 24, im.height - 22
    d.line([x1 - metros / mpp, y, x1, y], fill=(255, 255, 255), width=5)
    d.text((x1 - metros / mpp, y - 40), f"{metros} m", fill=(255, 255, 255), font=F)
    return im


def hoja(piezas, col, sep=8):
    w, h = piezas[0].size
    filas = -(-len(piezas) // col)
    s = Image.new("RGB", (col * w + (col - 1) * sep, filas * h + (filas - 1) * sep), (255, 255, 255))
    for i, p in enumerate(piezas):
        s.paste(p, ((i % col) * (w + sep), (i // col) * (h + sep)))
    return s


def main(salida):
    mn = json.load(open(os.path.join(SAL, "marco.json"), encoding="utf-8"))["marco_utm"]
    ms = json.load(open(os.path.join(SAL, "marco_sur.json"), encoding="utf-8"))["marco_utm"]
    piezas = [rotulo(recorte(os.path.join(GE, "claves_norte", f"n_{f}.jpg"), mn, CAJA_N, MPP_N)[0], t, 100, MPP_N) for f, t in NORTE]
    hoja(piezas, 3).save(os.path.join(salida, "norte_2014_2018.jpg"), quality=88)
    ruta = os.path.join(GE, "claves_sur_2014", "s_2014-03-07.jpg")
    a = rotulo(recorte(ruta, ms, CAJA_S, MPP_S)[0], "7 de marzo de 2014", 100, MPP_S)
    cx, cy = DET_S
    b = recorte(ruta, ms, (cx - 100, cy - 75, cx + 100, cy + 75), 0.2)[0]
    b = rotulo(b, "7 de marzo de 2014 · detalle", 20, 0.2)
    hoja([a, b], 2).save(os.path.join(salida, "sur_2014.jpg"), quality=88)
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1])
