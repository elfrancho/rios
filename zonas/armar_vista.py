"""Rearma la vista de una zona sin volver a bajar nada. Uso: python zonas/armar_vista.py zonas/<zona>

Lee escenas.json y, si existen en la carpeta de la zona:
- revisadas.json: {"quitar": {"AAAA-MM-DD": "motivo"}, "notas": {"AAAA-MM-DD": "texto corto"}} (lo que se descarta o se anota mirando a ojo)
- analisis.html: texto con los cambios observados, que va al pie de la vista
Además arma hoja_de_contacto.jpg con todas las fechas en miniatura.
"""
import json, os, sys
from PIL import Image, ImageDraw
from rasterio.warp import transform as reproyectar

AQUI = os.path.dirname(os.path.abspath(__file__))


def esquinas(x0, y1, res, ancho, alto):
    """Longitud y latitud de las cuatro esquinas de la grilla (NO, NE, SE, SO): la vista las usa para dar coordenadas."""
    lo, la = reproyectar("EPSG:32720", "EPSG:4326", [x0, x0 + ancho * res, x0 + ancho * res, x0], [y1, y1, y1 - alto * res, y1 - alto * res])
    return [[round(a, 7), round(b, 7)] for a, b in zip(lo, la)]


def main(sal):
    d = json.load(open(os.path.join(sal, "escenas.json"), encoding="utf-8"))
    d.pop("descartadas", None)
    rev = json.load(open(os.path.join(sal, "revisadas.json"), encoding="utf-8")) if os.path.exists(os.path.join(sal, "revisadas.json")) else {}
    d["escenas"] = [dict(e, nota=rev.get("notas", {}).get(e["fecha"], "")) for e in d["escenas"] if e["fecha"] not in rev.get("quitar", {})]
    d["esquinas_lonlat"] = esquinas(*d["grilla"])
    d.setdefault("ancho_km", d["grilla"][3] * d["grilla"][2] / 1000)
    d.setdefault("alto_km", d["grilla"][4] * d["grilla"][2] / 1000)
    for e in d["escenas"]:
        e.setdefault("pan", True)
    ext = os.path.join(sal, "extras.json")  # imágenes de otras fuentes, sin fecha comprobable: van primero y aparte
    if os.path.exists(ext):
        d["escenas"] = json.load(open(ext, encoding="utf-8"))["escenas"] + d["escenas"]
    ctx = os.path.join(sal, "contexto.json")
    d["contexto"] = json.load(open(ctx, encoding="utf-8")) if os.path.exists(ctx) else None
    pagina = open(os.path.join(AQUI, "plantilla_vista.html"), encoding="utf-8").read().replace("/*DATOS*/null", json.dumps(d, ensure_ascii=False))
    ruta = os.path.join(sal, "analisis.html")
    if os.path.exists(ruta):
        pagina = pagina.replace("<!--ANALISIS-->", open(ruta, encoding="utf-8").read())
    open(os.path.join(sal, "vista.html"), "w", encoding="utf-8").write(pagina)
    todas = json.load(open(os.path.join(sal, "escenas.json"), encoding="utf-8"))["escenas"]
    aw = 390
    ah = round(aw * d["grilla"][4] / d["grilla"][3])
    col = 6
    hoja = Image.new("RGB", (aw * col, (ah + 18) * -(-len(todas) // col)), "black")
    dib = ImageDraw.Draw(hoja)
    for k, e in enumerate(todas):
        x, y = (k % col) * aw, (k // col) * (ah + 18)
        hoja.paste(Image.open(os.path.join(sal, "img", e["fecha"] + ".jpg")).resize((aw, ah)), (x, y + 18))
        dib.text((x + 4, y + 3), f"{e['fecha']} {e.get('nivel', '') or ''} SF {e['parana_sf_m']} m {'NO ALIN' if str(e.get('alineada')).startswith('no') else ''}", fill="white")
    hoja.save(os.path.join(sal, "hoja_de_contacto.jpg"), quality=80)
    print(len(d["escenas"]), "en la vista,", len(todas), "en la hoja de contacto")


if __name__ == "__main__":
    main(sys.argv[1])
