"""Superficie de arena clara expuesta sobre el loteo del sector sur el 15/7/2015, en un encuadre que la contiene entera, y huella del loteo en 2022.

Uso: python zonas/medir_alteo.py <carpeta de salida>
El borde se trazó a mano sobre la exportación llevada a 2 m por píxel (vértices en píxeles de esa grilla; origen en la esquina noroeste de la caja).
La superficie es el área del polígono. Margen estimado: ±10 %. La huella de 2022 es el contorno exterior de las calles del loteo; su esquina
oeste queda apenas fuera de la caja y se extrapoló.
"""
import json, os, sys
from PIL import ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from recortar_pasos import recorte, SAL

CAJA, MPP = (735700, 6506500, 737300, 6507900), 2.0
CASOS = [
    ("claves_sur", "k_05.jpg", "7/2015", "arena expuesta", [(215, 128), (470, 345), (455, 378), (345, 447), (262, 378), (240, 362), (190, 412), (52, 320),
                                                              (50, 300), (105, 245), (160, 185)]),
    ("pasos_sur", "paso_04.jpg", "12/2022", "huella del loteo", [(215, 128), (475, 352), (232, 592), (-10, 375)]),
]


def area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2 * MPP * MPP


def main(salida):
    marco = json.load(open(os.path.join(SAL, "marco_sur.json"), encoding="utf-8"))["marco_utm"]
    filas = []
    for carpeta, archivo, etiqueta, que, pol in CASOS:
        im, _ = recorte(os.path.join(SAL, "google_earth", carpeta, archivo), marco, CAJA, MPP)
        a = area(pol)
        d = ImageDraw.Draw(im)
        d.line(pol + [pol[0]], fill=(0, 255, 255), width=3)
        rot = f"{etiqueta}: {que}, {a / 10000:.0f} ha"
        d.rectangle([0, 0, 14 + 12 * len(rot), 30], fill=(0, 0, 0))
        d.text((6, 6), rot, fill=(0, 255, 255), font_size=20)
        im.save(os.path.join(salida, f"sur_alteo_{etiqueta.replace('/', '-')}.jpg"), quality=88)
        filas.append({"fecha_selector": etiqueta, "que": que, "archivo": f"{carpeta}/{archivo}", "superficie_ha": round(a / 10000, 1), "vertices_px": pol})
        print(rot)
    json.dump({"metodo": __doc__, "caja_utm": CAJA, "metros_por_pixel": MPP, "mediciones": filas},
              open(os.path.join(salida, "sur_alteo.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1])
