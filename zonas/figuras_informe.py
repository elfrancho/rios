"""Figuras rotuladas para el informe: evolución del sector sur en seis fechas, con flechas a lo que se describe en el texto.

Uso: python zonas/figuras_informe.py <carpeta de salida>
Cada panel es el mismo rectángulo de terreno (1400 x 1050 m) llevado a 2 m por píxel. Los rótulos se dibujan encima de una copia: los archivos
originales no se tocan. Las posiciones de los rótulos se pusieron a mano.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from recortar_pasos import recorte, SAL

CAJA = (735050, 6507100, 736450, 6508150)
MPP = 2.0
F20, F24, F18 = (ImageFont.truetype('arial.ttf', n) for n in (20, 24, 18))
AGUA, ARENA13, ARENA15, LOTEO = (735810, 6507566), (736178, 6507552), (736200, 6507390), (736200, 6507330)
# (carpeta, archivo, fecha, [(texto, punto UTM señalado, posición del texto en el panel)])
PANELES = [
    ("claves_sur", "k_02.jpg", "7 de enero de 2012", [("estanque con vegetación", AGUA, (30, 330))]),
    ("claves_sur", "k_03.jpg", "4 de enero de 2013", [("agua marrón claro", AGUA, (30, 330)), ("primera arena", ARENA13, (470, 150))]),
    ("claves_sur", "k_04.jpg", "14 de octubre de 2013", [("espejo de agua", AGUA, (30, 330)), ("arena", ARENA13, (470, 150)), ("embarcación", (735660, 6507847), (60, 70))]),
    ("claves_sur", "k_05.jpg", "15 de julio de 2015", [("espejo de agua", AGUA, (30, 400)), ("arena", ARENA15, (330, 470)), ("embarcación", (735514, 6507851), (60, 70))]),
    ("claves_sur", "k_07.jpg", "9 de diciembre de 2016", [("espejo de agua", (735600, 6507840), (30, 400)), ("loteo alteado", LOTEO, (330, 470)), ("embarcación", (735836, 6507511), (500, 200))]),
    ("pasos_sur", "paso_04.jpg", "16 de diciembre de 2022", [("espejo de agua", (735600, 6507840), (30, 400)), ("loteo con casas", LOTEO, (330, 470))]),
]


def main(salida):
    marco = json.load(open(os.path.join(SAL, "marco_sur.json"), encoding="utf-8"))["marco_utm"]
    os.makedirs(salida, exist_ok=True)
    piezas = []
    for carpeta, archivo, fecha, notas in PANELES:
        im, _ = recorte(os.path.join(SAL, "google_earth", carpeta, archivo), marco, CAJA, MPP)
        d = ImageDraw.Draw(im)
        for texto, (ux, uy), (tx, ty) in notas:
            px, py = (ux - CAJA[0]) / MPP, (CAJA[3] - uy) / MPP
            ancho = d.textlength(texto, font=F20)
            d.line([tx + ancho / 2, ty + 12, px, py], fill=(255, 255, 0), width=2)
            d.ellipse([px - 5, py - 5, px + 5, py + 5], outline=(255, 255, 0), width=2)
            d.rectangle([tx - 4, ty - 2, tx + ancho + 4, ty + 26], fill=(0, 0, 0))
            d.text((tx, ty), texto, fill=(255, 255, 0), font=F20)
        d.rectangle([0, 0, im.width, 34], fill=(0, 0, 0))
        d.text((8, 4), fecha, fill=(255, 255, 255), font=F24)
        d.rectangle([im.width - 130, im.height - 44, im.width, im.height], fill=(0, 0, 0))
        d.line([im.width - 115, im.height - 12, im.width - 15, im.height - 12], fill=(255, 255, 255), width=3)
        d.text((im.width - 115, im.height - 38), "200 m", fill=(255, 255, 255), font=F18)
        piezas.append(im)
    w, h = piezas[0].size
    sep = 6
    for nombre, grupo in (("sur_evolucion_a.jpg", piezas[:3]), ("sur_evolucion_b.jpg", piezas[3:])):
        hoja = Image.new("RGB", (len(grupo) * w + (len(grupo) - 1) * sep, h), (255, 255, 255))
        for i, p in enumerate(grupo):
            hoja.paste(p, (i * (w + sep), 0))
        hoja.save(os.path.join(salida, nombre), quality=90)
    print("ok", w, h)


if __name__ == "__main__":
    main(sys.argv[1])
