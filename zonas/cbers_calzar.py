"""Calza los recortes anteriores a 2020 (nivel L2, ubicación aproximada) contra una imagen CBERS-4A corregida sobre el terreno.

Uso: python zonas/cbers_calzar.py <carpeta cbers_anteriores> <referencia .png de 2 m> <carpeta de salida> <archivo> [<archivo> ...]

Método: se lleva la referencia a la resolución del recorte y se busca, por correlación de bordes (gradiente), el desplazamiento que mejor la
hace coincidir dentro del recorte con margen. Solo se corrige un corrimiento (sin giro ni cambio de escala). El resultado se lleva a la grilla
de 2 m de la serie (3000 x 2800 m) con interpolación bicúbica: el detalle real sigue siendo el del satélite de origen. Se anota el
desplazamiento aplicado y el puntaje de coincidencia (1 = perfecta). Un puntaje bajo indica que el calce debe revisarse a ojo.
"""
import json, os, sys
import cv2
import numpy as np
from PIL import Image

W, H = 1500, 1400   # grilla de 2 m de la serie


def bordes(a):
    a = cv2.GaussianBlur(a.astype("float32"), (0, 0), 1.5)
    gx, gy = cv2.Sobel(a, cv2.CV_32F, 1, 0), cv2.Sobel(a, cv2.CV_32F, 0, 1)
    return cv2.magnitude(gx, gy)


def main(origen, ref, salida, archivos):
    os.makedirs(salida, exist_ok=True)
    reg = {e.get("archivo"): e for e in json.load(open(os.path.join(origen, "registro.json"), encoding="utf-8"))["escenas"]}
    r2 = np.asarray(Image.open(ref).convert("L"))
    rj = os.path.join(salida, "calce.json")
    filas = json.load(open(rj, encoding="utf-8"))["escenas"] if os.path.exists(rj) else []
    for arch in archivos:
        e = reg[arch]
        mpp = e["metros_por_pixel"]
        im = np.asarray(Image.open(os.path.join(origen, arch)).convert("L"))
        tw, th = round(W * 2 / mpp), round(H * 2 / mpp)
        t = cv2.resize(r2, (tw, th), interpolation=cv2.INTER_AREA)
        m = cv2.matchTemplate(bordes(im), bordes(t), cv2.TM_CCOEFF_NORMED)
        _, score, _, (x, y) = cv2.minMaxLoc(m)
        x0, y0 = (im.shape[1] - tw) / 2, (im.shape[0] - th) / 2
        rec = cv2.resize(im[y:y + th, x:x + tw], (W, H), interpolation=cv2.INTER_CUBIC)
        nombre = arch.replace(".png", "_calzada.png")
        Image.fromarray(rec).save(os.path.join(salida, nombre))
        fila = {"archivo": nombre, "origen": arch, "id": e["id"], "fecha": e["fecha"], "hora_utc": e["hora_utc"], "metros_por_pixel_origen": mpp,
                "corrimiento_m": [round((x - x0) * mpp), round((y0 - y) * mpp)], "puntaje": round(float(score), 3)}
        filas = [f for f in filas if f["archivo"] != nombre] + [fila]
        print(arch, "corrimiento este/norte (m)", fila["corrimiento_m"], "puntaje", fila["puntaje"], flush=True)
    json.dump({"metodo": __doc__, "referencia": os.path.basename(ref), "escenas": sorted(filas, key=lambda f: f["fecha"])},
              open(rj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
