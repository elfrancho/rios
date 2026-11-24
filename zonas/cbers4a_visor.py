"""Arma, con los recortes CBERS-4A de 2 m ya bajados (ver cbers4a_serie.py), un visor HTML para recorrer las fechas y una hoja resumen.

Uso: python zonas/cbers4a_visor.py <carpeta con los recortes y registro.json> <carpeta de salida> [solo_L4 | <carpeta de calzadas>]
El visor es un único archivo, sin conexión a internet: las imágenes van adentro en JPEG. Los originales son los PNG de la carpeta de recortes.
"""
import base64, io, json, os, sys
from PIL import Image, ImageDraw, ImageFont

CALZ = None      # carpeta con las imágenes anteriores a 2020 ya calzadas (cbers_calzar.py)
EXCLUIR = {"cbers_2014-12-29_pan_5m_167_135_L2_calzada.png", "cbers_2009-12-31_hrc_2.7m_135_5_L2_calzada.png"}   # calce fallido / escena repetida
NOMBRE = "serie_cbers4a"
MESES = "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split()


def lindo(f):
    a, m, d = f.split("-")
    return f"{int(d)} de {MESES[int(m) - 1]} de {a}"


def main(origen, salida, solo_l4):
    esc = json.load(open(os.path.join(origen, "registro.json"), encoding="utf-8"))["escenas"]
    esc = [e for e in esc if os.path.exists(os.path.join(origen, e["archivo"])) and (not solo_l4 or e["nivel"] == "L4")]
    for e in esc:
        e["ruta"] = os.path.join(origen, e["archivo"])
        e["nota"] = "CBERS-4A, 2 m · " + ("ubicación corregida sobre el terreno" if e["nivel"] == "L4" else "ubicación aproximada (puede estar corrida decenas de metros)")
    if CALZ:
        for c in json.load(open(os.path.join(CALZ, "calce.json"), encoding="utf-8"))["escenas"]:
            if c["archivo"] in EXCLUIR:
                continue
            sat = "CBERS-2B, 2,7 m" if "hrc" in c["archivo"] else "CBERS-4, 5 m"
            esc.append({"fecha": c["fecha"], "hora_utc": c["hora_utc"], "id": c["id"], "nivel": "L2", "ruta": os.path.join(CALZ, c["archivo"]),
                        "nota": sat + " · calzada a mano contra la imagen de 2020 (corrimiento, sin giro)"})
    esc.sort(key=lambda e: e["fecha"])
    datos, minis = [], []
    f = ImageFont.truetype("arial.ttf", 26)
    for e in esc:
        im = Image.open(e["ruta"]).convert("L")
        b = io.BytesIO()
        im.save(b, "JPEG", quality=85)
        nota = e["nota"]
        datos.append({"f": lindo(e["fecha"]), "n": nota, "id": e["id"], "h": e["hora_utc"][:5], "src": "data:image/jpeg;base64," + base64.b64encode(b.getvalue()).decode()})
        m = im.resize((500, 467)).convert("RGB")
        d = ImageDraw.Draw(m)
        d.rectangle([0, 0, 500, 34], fill=(0, 0, 0))
        d.text((8, 3), lindo(e["fecha"]) + ("" if e["nivel"] == "L4" else " *"), fill=(255, 255, 255), font=f)
        minis.append(m)
    col = 4
    filas = -(-len(minis) // col)
    hoja = Image.new("RGB", (col * 506 - 6, filas * 473 - 6), (255, 255, 255))
    for i, m in enumerate(minis):
        hoja.paste(m, ((i % col) * 506, (i // col) * 473))
    hoja.save(os.path.join(salida, NOMBRE + "_hoja.jpg"), quality=85)
    html = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Serie CBERS</title><style>
body{margin:0;background:#111;color:#eee;font-family:Arial,Helvetica,sans-serif}
header{padding:10px 16px;display:flex;flex-wrap:wrap;gap:12px;align-items:center;position:sticky;top:0;background:#111;z-index:2}
h1{font-size:22px;margin:0;min-width:260px}button{font-size:20px;padding:6px 16px;background:#333;color:#eee;border:1px solid #666;border-radius:6px;cursor:pointer}
input[type=range]{flex:1;min-width:200px}small{color:#aaa;display:block;padding:0 16px 8px}
#marco{position:relative;max-width:1500px;margin:auto}#marco img{width:100%;display:block}
#esc{position:absolute;right:16px;bottom:14px;width:16.667%;border-bottom:4px solid #fff;color:#fff;text-align:center;font-size:15px;text-shadow:0 0 4px #000}
</style></head><body><header><button id="a">&#9664;</button><button id="p">&#9654; reproducir</button><button id="s">&#9654;</button>
<h1 id="t"></h1><input id="r" type="range" min="0" value="0"></header><small id="n"></small>
<div id="marco"><img id="i" alt=""><div id="esc">500 m</div></div>
<small>Satélites CBERS-2B (2,7 m), CBERS-4 (5 m) y CBERS-4A (2 m), Brasil/China, bandas en blanco y negro. Catálogo público del INPE. Todas llevadas a la misma grilla de 2 m: el detalle real es el de cada satélite. Norte arriba. Recorte de 3000 × 2800 m.
El contraste de cada fecha se ajustó por separado: sirve para ver formas, no para comparar brillos. Teclas: flechas izquierda y derecha.</small>
<script>const D=__DATOS__;let k=0,tm=null;const $=x=>document.getElementById(x);$('r').max=D.length-1;
function ver(j){k=(j+D.length)%D.length;$('i').src=D[k].src;$('t').textContent=D[k].f;$('n').textContent=(k+1)+' de '+D.length+' · '+D[k].h+' UTC · '+D[k].n+' · '+D[k].id;$('r').value=k}
$('a').onclick=()=>ver(k-1);$('s').onclick=()=>ver(k+1);$('r').oninput=e=>ver(+e.target.value);
$('p').onclick=()=>{if(tm){clearInterval(tm);tm=null;$('p').innerHTML='&#9654; reproducir'}else{tm=setInterval(()=>ver(k+1),900);$('p').innerHTML='&#10074;&#10074; pausar'}};
document.onkeydown=e=>{if(e.key==='ArrowLeft')ver(k-1);if(e.key==='ArrowRight')ver(k+1)};ver(0);</script></body></html>"""
    open(os.path.join(salida, NOMBRE + ".html"), "w", encoding="utf-8").write(html.replace("__DATOS__", json.dumps(datos, ensure_ascii=False)))
    print(len(esc), "fechas", round(os.path.getsize(os.path.join(salida, NOMBRE + ".html")) / 1e6, 1), "MB")


if __name__ == "__main__":
    if len(sys.argv) > 3 and sys.argv[3] != "solo_L4":
        CALZ, NOMBRE = sys.argv[3], "serie_cbers_2009_2026"
    main(sys.argv[1], sys.argv[2], len(sys.argv) > 3 and sys.argv[3] == "solo_L4")
