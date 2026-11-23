"""Superficie del espejo de agua del sector sur incluyendo la vegetación acuática contigua, con la orilla trazada a mano.

Uso: python zonas/medir_orilla.py <carpeta de salida>
Complementa a medir_espejos.py, que solo cuenta el agua libre (sin plantas flotantes ni vegetación de borde). En las fechas en que el agua
tiene vegetación encima, la orilla exterior se dibujó a mano sobre la exportación llevada a 1 m por píxel (vértices en píxeles de esa grilla:
x hacia el este, y hacia el sur, origen en la esquina noroeste de la caja). La superficie es el área del polígono. Qué parte de la vegetación
pertenece al espejo es una decisión de quien traza: el resultado es un máximo razonable, no una medida exacta.
"""
import json, os, sys
from PIL import ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from recortar_pasos import recorte, SAL

CAJA = (735050, 6507100, 736450, 6508150)
ORILLAS = [
    ("claves_sur", "k_05.jpg", "7/2015", [(447, 240), (490, 225), (527, 212), (545, 195), (580, 200), (620, 230), (660, 265), (690, 295), (730, 320),
        (760, 350), (785, 385), (790, 425), (770, 440), (775, 470), (800, 495), (820, 520), (822, 545), (828, 575), (835, 620), (830, 670), (815, 690),
        (795, 680), (770, 640), (745, 610), (705, 585), (695, 565), (720, 545), (745, 520), (748, 480), (735, 450), (700, 420), (670, 375), (640, 365),
        (610, 385), (585, 410), (565, 430), (560, 450), (530, 455), (505, 440), (500, 410), (520, 395), (490, 360), (450, 340), (410, 335), (385, 315),
        (375, 285), (395, 260), (420, 245)]),
    ("pasos_sur", "paso_01.jpg", "3/2025", [(170, 205), (215, 197), (250, 215), (290, 222), (350, 230), (375, 215), (400, 200),
        (445, 195), (500, 225), (540, 190), (580, 195), (625, 235), (665, 275), (690, 295), (735, 320), (770, 360), (795, 400), (795, 435), (770, 445),
        (780, 470), (840, 468), (868, 500), (850, 540), (848, 600), (835, 640), (832, 690), (815, 695), (790, 665), (740, 630), (700, 600), (683, 560),
        (700, 530), (735, 500), (752, 470), (735, 440), (700, 415), (660, 395), (630, 400), (615, 430), (575, 445), (520, 445), (495, 425), (465, 395),
        (430, 365), (405, 330), (380, 305), (370, 270), (340, 255), (290, 250), (255, 285), (240, 320), (215, 350), (190, 345), (195, 300), (172, 240)]),
]


def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def main(salida):
    marco = json.load(open(os.path.join(SAL, "marco_sur.json"), encoding="utf-8"))["marco_utm"]
    os.makedirs(salida, exist_ok=True)
    filas = []
    for carpeta, archivo, etiqueta, pol in ORILLAS:
        im, _ = recorte(os.path.join(SAL, "google_earth", carpeta, archivo), marco, CAJA, 1.0)
        a = area(pol)
        d = ImageDraw.Draw(im)
        d.line(pol + [pol[0]], fill=(0, 255, 255), width=3)
        rot = f"{etiqueta}: {a / 10000:.1f} ha con vegetación acuática"
        d.rectangle([0, 0, 14 + 12 * len(rot), 30], fill=(0, 0, 0))
        d.text((6, 6), rot, fill=(0, 255, 255), font_size=20)
        im.save(os.path.join(salida, f"sur_orilla_{etiqueta.replace('/', '-')}.jpg"), quality=88)
        filas.append({"fecha_selector": etiqueta, "archivo": f"{carpeta}/{archivo}", "superficie_m2": round(a), "superficie_ha": round(a / 10000, 2),
                      "vertices_px": pol})
        print(rot)
    json.dump({"metodo": __doc__, "caja_utm": CAJA, "mediciones": filas}, open(os.path.join(salida, "sur_orilla.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
