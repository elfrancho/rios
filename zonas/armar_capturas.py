"""Vista para recorrer las capturas de Google Earth de un lugar. Uso: python zonas/armar_capturas.py <carpeta con AAAA-MM-DD.jpg> "<título>"

Cada archivo se llama como la fecha que mostraba la barra inferior de Google Earth ("Más antigua - dd/mm/aaaa") al capturar.
Agrega la altura del Paraná en el puerto de Santa Fe de ese día (datos_ina) y arma vista.html en la misma carpeta.
Las capturas son vistas de pantalla de Google Earth (imágenes © Google y sus proveedores): uso de estudio, citando la fuente.
"""
import csv, json, os, re, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
BAJA, ALTA = 2.36, 4.22

PAGINA = """<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITULO__</title><style>
body{margin:0;background:#0e1418;color:#e8eef1;font:15px/1.45 system-ui,"Segoe UI",sans-serif}
header{padding:10px 16px;border-bottom:1px solid #2a3840}h1{font-size:17px;margin:0}header span{color:#93a4ad;font-size:13px}
.barra{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:8px 16px}
.barra button{background:#172026;border:1px solid #2a3840;color:#e8eef1;border-radius:6px;padding:6px 10px;font:inherit;cursor:pointer}
.barra button.on{background:#4fd8ff;color:#06222c}.fecha{font-size:20px;font-weight:700;margin-right:8px}.dato{color:#93a4ad;font-size:13px}.dato b{color:#e8eef1}
#fechas{display:flex;flex-wrap:wrap;gap:6px;padding:0 16px 8px}#fechas button{background:#172026;border:1px solid #2a3840;color:#e8eef1;border-radius:6px;padding:3px 8px;font:13px system-ui;cursor:pointer}
#fechas button.activa{border-color:#4fd8ff;background:#24343e}#fechas button.fijada{box-shadow:inset 0 -3px 0 #ffb347}
#marco{overflow:hidden;margin:0 16px;border:1px solid #2a3840}#marco img{display:block;width:100%;margin-top:-21.2%;margin-bottom:-4%}
p{margin:8px 16px;color:#93a4ad;font-size:12.5px;max-width:100ch}kbd{background:#24343e;border-radius:3px;padding:0 5px;color:#e8eef1}
</style></head><body>
<header><h1>__TITULO__</h1><span id="sub"></span></header>
<div class="barra"><span class="fecha" id="fecha"></span><span class="dato" id="dato"></span><span style="flex:1"></span>
<button id="nueva">▲ más nueva</button><button id="vieja">▼ más vieja</button><button id="fijar">Fijar para comparar</button><button id="alt">⇄ Alternar</button></div>
<div id="fechas"></div><div id="marco"><img id="foto" alt=""></div>
<p><kbd>↑</kbd> <kbd>↓</kbd> cambian de fecha · <kbd>F</kbd> fija una fecha y <kbd>espacio</kbd> alterna entre esa y la que estás viendo.
Capturas de pantalla de Google Earth (imágenes © Google y sus proveedores), todas con el mismo encuadre: centro __CENTRO__, unos 0,6 m por píxel.
La fecha es la que mostraba la barra inferior de Google Earth al capturar; un 31/12 suele indicar que solo se conoce el año.
Altura: Paraná en el puerto de Santa Fe ese día (INA). Aguas bajas: menos de 2,36 m; aguas altas: más de 4,22 m.</p>
<script>
const E=__DATOS__,$=i=>document.getElementById(i);let i=0,fij=null,prev=null;
const larga=f=>new Date(f+"T12:00:00").toLocaleDateString("es-AR",{day:"numeric",month:"long",year:"numeric"});
$("sub").textContent=E.length+" fechas · de la más nueva a la más vieja";
E.forEach((e,k)=>{const b=document.createElement("button");b.textContent=e.f.slice(8)+"/"+e.f.slice(5,7)+"/"+e.f.slice(0,4);b.onclick=()=>ir(k);e.b=b;$("fechas").append(b)});
function ir(k){i=Math.max(0,Math.min(E.length-1,k));const e=E[i];$("foto").src=e.f+".jpg";$("fecha").textContent=larga(e.f);
$("dato").innerHTML="Paraná en Santa Fe <b>"+(e.h==null?"sin dato":e.h.toFixed(2).replace(".",",")+" m")+"</b>"+(e.e?" ("+e.e+")":"")+(e.n?" · "+e.n:"");
E.forEach((x,j)=>{x.b.classList.toggle("activa",j===i);x.b.classList.toggle("fijada",j===fij)})}
function alt(){if(fij==null)return;if(i!==fij){prev=i;ir(fij)}else if(prev!=null)ir(prev)}
$("nueva").onclick=()=>ir(i-1);$("vieja").onclick=()=>ir(i+1);$("alt").onclick=alt;
$("fijar").onclick=()=>{fij=fij===i?null:i;$("fijar").classList.toggle("on",fij!=null);ir(i)};
addEventListener("keydown",v=>{const k=v.key.toLowerCase();if(k==="arrowup"||k==="arrowleft")ir(i-1);else if(k==="arrowdown"||k==="arrowright")ir(i+1);else if(k==="f")$("fijar").click();else if(k===" ")alt();else return;v.preventDefault()});
ir(0);
</script></body></html>"""


def main(carpeta, titulo, centro=""):
    sf = {r["fecha"]: float(r["valor"]) for r in csv.DictReader(open(os.path.join(RAIZ, "datos_ina", "parana_santa_fe_altura.csv"),
                                                                       encoding="utf-8")) if r["valor"]}
    notas = json.load(open(os.path.join(carpeta, "notas.json"), encoding="utf-8")) if os.path.exists(os.path.join(carpeta, "notas.json")) else {}
    datos = []
    for a in sorted(os.listdir(carpeta), reverse=True):
        m = re.fullmatch(r"(\d{4}-\d\d-\d\d)\.jpg", a)
        if m:
            f = m.group(1)
            h = sf.get(f)
            datos.append({"f": f, "h": h, "e": None if h is None else "aguas bajas" if h < BAJA else "aguas altas" if h > ALTA else "aguas medias",
                          "n": notas.get(f, "")})
    open(os.path.join(carpeta, "vista.html"), "w", encoding="utf-8").write(
        PAGINA.replace("__TITULO__", titulo).replace("__CENTRO__", centro).replace("__DATOS__", json.dumps(datos, ensure_ascii=False)))
    for d in datos:
        print(d["f"], d["h"], d["e"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
