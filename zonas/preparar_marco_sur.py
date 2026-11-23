"""Prepara la ampliación de la zona de estudio hacia el sur (23/11/2026). Uso: python zonas/preparar_marco_sur.py

La zona de estudio pasa a ser la unión de «esta es la zona precisa a estudiar» y «nueva zona precisa» (Marcador de la Setúbal).
Las exportaciones de Google Earth Pro que ya había (google_earth/pasos, marco.json) cubren la parte norte; para la parte sur se
exporta de nuevo con otro recuadro magenta. Deja en zonas/zona_precisa:
- marco_sur.json y google_earth/marco_sur.kml: recuadro de las exportaciones nuevas (van a google_earth/pasos_sur/)
- union.json: encuadre de la vista unida y los dos polígonos
"""
import json, os
import numpy as np
from rasterio.warp import transform as reproyectar

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
SAL = os.path.join(AQUI, "zona_precisa")
MARGEN = 50   # metros alrededor de la zona nueva

d = json.load(open(os.path.join(RAIZ, "mapa", "bajadas", "mapa", "marcas.json"), encoding="utf-8"))
d = d.get("data", d)
g = json.load(open(os.path.join(RAIZ, "setubal", "reel", "amplia.json"), encoding="utf-8"))
z = [i for i in d["items"] if i["tipo"] == "zona" and i["nombre"].lower() == "nueva zona precisa"][0]
px = [g["x0"] + fx * g["ancho_m"] for fx, _ in z["pts"]]
py = [g["y0"] - fy * g["alto_m"] for _, fy in z["pts"]]
norte = json.load(open(os.path.join(SAL, "marco.json"), encoding="utf-8"))
nx0, ny0, nx1, ny1 = norte["marco_utm"]

# encuadre de la vista unida, en metros enteros pares (la grilla es de 0,5 m)
ux0 = float(np.floor(min(nx0, min(px) - MARGEN) / 2) * 2)
ux1 = float(np.ceil(max(nx1, max(px) + MARGEN) / 2) * 2)
uy0 = float(np.floor(min(ny0, min(py) - MARGEN) / 2) * 2)
uy1 = float(np.ceil(max(ny1, max(py) + MARGEN) / 2) * 2)
# recuadro sur: todo el ancho de la unión y, de alto, lo que entra en una exportación (≈1800 m a 0,41 m por píxel) con margen
sx0, sx1, sy0, sy1 = ux0, ux1, uy0, uy0 + 1610.0


def lonlat(xs, ys):
    lo, la = reproyectar("EPSG:32720", "EPSG:4326", xs, ys)
    return [[round(a, 7), round(b, 7)] for a, b in zip(lo, la)]


centro = lonlat([(sx0 + sx1) / 2], [(sy0 + sy1) / 2])[0]
json.dump({"zona": z["nombre"], "marco_utm": [sx0, sy0, sx1, sy1], "crs": "EPSG:32720", "centro_lonlat": centro},
          open(os.path.join(SAL, "marco_sur.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"zona": "Zona de estudio", "marco_utm": [ux0, uy0, ux1, uy1], "crs": "EPSG:32720",
           "poligonos_utm": [{"nombre": norte["zona"], "pts": norte["poligono_utm"]},
                             {"nombre": z["nombre"], "pts": [[round(a, 3), round(b, 3)] for a, b in zip(px, py)]}],
           "nota": "Unión de la zona de estudio original y de su ampliación hacia el sudoeste (marcadas por Pancho)."},
          open(os.path.join(SAL, "union.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
esq = lonlat([sx0, sx1, sx1, sx0, sx0], [sy1, sy1, sy0, sy0, sy1])
coords = " ".join(f"{a:.7f},{b:.7f},0" for a, b in esq)
kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Marco zona sur</name>
<Style id="m"><LineStyle><color>ffff00ff</color><width>2</width></LineStyle><PolyStyle><fill>0</fill></PolyStyle></Style>
<Placemark><name>Marco sur</name><styleUrl>#m</styleUrl>
<LookAt><longitude>{centro[0]}</longitude><latitude>{centro[1]}</latitude><altitude>0</altitude><heading>0</heading><tilt>0</tilt><range>2500</range></LookAt>
<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>
</Document></kml>"""
open(os.path.join(SAL, "google_earth", "marco_sur.kml"), "w", encoding="utf-8").write(kml)
os.makedirs(os.path.join(SAL, "google_earth", "pasos_sur"), exist_ok=True)
print("unión:", [ux0, uy0, ux1, uy1], f"{ux1 - ux0:.0f} x {uy1 - uy0:.0f} m ->", int((ux1 - ux0) * 2), "x", int((uy1 - uy0) * 2), "px")
print("marco sur:", [sx0, sy0, sx1, sy1], "centro", centro)
