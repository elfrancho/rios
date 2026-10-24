"""Arma la web pública https://elfrancho.github.io/rios/ (repo elfrancho/rios, cuenta personal de GitHub).

Desde el 20/10/2026 la web se actualiza sola cada hora en GitHub (.github/workflows/web.yml): baja datos del INA y del
Salado, arma las páginas y las publica, aunque la notebook esté apagada. Esta carpeta es el repo con el código.

Uso:
- python publicar_web.py            (en la notebook) sube a GitHub los cambios de plantillas/scripts y pide una
                                     actualización ya mismo. No cambia la cuenta activa de gh (la de trabajo, grupobca):
                                     usa el token de elfrancho solo para el push y no lo guarda.
- python publicar_web.py --armar    (lo usa GitHub) arma web/ con los datos que haya, sin bajar ni publicar.
- python publicar_web.py --local    arma web/ bajando datos, para revisar en la notebook sin publicar.
"""
import datetime as dt, json, os, shutil, subprocess, sys, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(AQUI, "web")
REPO = "elfrancho/rios"
PY = sys.executable
ARG = dt.timezone(dt.timedelta(hours=-3))  # Argentina, sin horario de verano
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


# Bloque "Colaborá" de la portada: se muestra solo lo que tenga valor. Cafecito: el usuario de cafecito.app.
CAFECITO = "elfrancho"
ALIAS = "pancho.isla"


# Contador de visitas (GoatCounter, sin cookies). Código del sitio: el "MICODIGO" de MICODIGO.goatcounter.com. Vacío = sin contador.
# En GoatCounter > Settings hay que activar "Allow adding visitor counts on your website" para que se vea el número público.
GOATCOUNTER = "elfrancho"
CONTADOR_DESDE = "20/10/2026"


def contador_script():
    if not GOATCOUNTER:
        return ""
    # Registra solo la ruta (sin "?v=..." ni barra final) para que una página no se parta en varias filas
    return ('<script>window.goatcounter = { path: function () { return location.pathname.replace(/\\/$/, "") || "/"; } };</script>\n'
            f'<script data-goatcounter="https://{GOATCOUNTER}.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>\n')


def visitas_api():
    """Total de visitas desde CONTADOR_DESDE, pedido al panel de GoatCounter con la llave de solo lectura.
    En GitHub la llave está en el secreto GOATCOUNTER_TOKEN; sin llave (o si falla) devuelve None."""
    token = os.environ.get("GOATCOUNTER_TOKEN")
    if not (GOATCOUNTER and token):
        return None
    d, m, a = CONTADOR_DESDE.split("/")
    fin = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00:00Z")
    url = f"https://{GOATCOUNTER}.goatcounter.com/api/v0/stats/total?start={a}-{m}-{d}T00:00:00Z&end={fin}"
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return int(json.load(r)["total"])
    except urllib.error.HTTPError as e:
        print("sin total de visitas del panel:", e.code, e.read()[:300].decode("utf-8", "replace"))
    except Exception as e:
        print("sin total de visitas del panel:", type(e).__name__)
    return None


def contador_portada():
    if not GOATCOUNTER:
        return ""
    n = visitas_api()
    if n:  # número del panel, al día con la última actualización (cada hora)
        return f'<div id="visitas">👀 {n:,} visitas desde el {CONTADOR_DESDE}</div>'.replace(",", ".")
    # Suma página por página: el total del sitio (TOTAL.json) en GoatCounter se actualiza con mucha demora.
    return ('<div id="visitas" hidden></div><script>Promise.all(["/rios", "/rios/ola.html", "/rios/parana.html", "/rios/salado.html", "/rios/satelite.html"]'
            '.map(p => fetch("https://' + GOATCOUNTER + '.goatcounter.com/counter/" + encodeURIComponent(p) + ".json")'
            '.then(r => r.ok ? r.json() : { count: "0" }).then(j => +String(j.count).replace(/\\D/g, "")).catch(() => 0)))'
            '.then(v => { const n = v.reduce((a, b) => a + b, 0); if (!n) return; const e = document.getElementById("visitas");'
            ' e.textContent = "👀 " + n.toLocaleString("es-AR") + " visitas desde el ' + CONTADOR_DESDE + '"; e.hidden = false; });</script>')


def con_contador(html):
    # el último </body>: ECharts (incrustado) trae ese texto adentro de su código
    i = html.rfind("</body>")
    return html[:i] + contador_script() + html[i:]


def colaborar():
    if not (CAFECITO or ALIAS):
        return ""
    ops = []
    if CAFECITO:
        ops.append(f'<a class="cafe" href="https://cafecito.app/{CAFECITO}" target="_blank" rel="noopener">☕ Invitame un cafecito</a>')
    if ALIAS:
        ops.append(f'<button type="button" onclick="navigator.clipboard.writeText(\'{ALIAS}\');this.lastChild.textContent=\' ¡copiado!\'">'
                   f'Alias: <b>{ALIAS}</b><span></span></button>')
    return ('<section class="colaborar"><h2>¿Te sirve?</h2><p>Esto lo hago a pulmón, en mis ratos libres. '
            'Si querés darme una mano para que siga, cualquier aporte suma.</p><div class="opciones">' + "".join(ops) + "</div></section>")


def correr(args, **kw):
    print("·", " ".join(args[:3]))
    return subprocess.run(args, check=True, cwd=AQUI, **kw)


def armar():
    correr([PY, "armar.py"])
    correr([PY, "armar_salado.py"])
    correr([PY, "armar_ola.py"])
    shutil.rmtree(WEB, ignore_errors=True)
    os.makedirs(WEB)
    for origen, destino in [("rios.html", "parana.html"), ("salado.html", "salado.html"), ("ola.html", "ola.html")]:
        html = open(os.path.join(AQUI, origen), encoding="utf-8").read()
        open(os.path.join(WEB, destino), "w", encoding="utf-8").write(con_contador(html))
    # crecidas desde el espacio: imágenes ya procesadas en la notebook (satelite/armar_imagenes.py); acá solo se copian
    shutil.copytree(os.path.join(AQUI, "satelite", "img"), os.path.join(WEB, "satelite"))
    escenas = [{k: v for k, v in e.items() if k != "escenas"} for e in json.load(open(os.path.join(AQUI, "satelite", "escenas.json"), encoding="utf-8"))]
    html = open(os.path.join(AQUI, "plantilla_satelite.html"), encoding="utf-8").read().replace("/*ESCENAS*/", json.dumps(escenas, ensure_ascii=False))
    open(os.path.join(WEB, "satelite.html"), "w", encoding="utf-8").write(con_contador(html))
    shutil.copy(os.path.join(AQUI, "og.png"), os.path.join(WEB, "og.png"))
    shutil.copy(os.path.join(AQUI, "perfil.jpg"), os.path.join(WEB, "perfil.jpg"))
    hoy = dt.datetime.now(ARG)
    fecha = f"{DIAS[hoy.weekday()]} {hoy.day} de {MESES[hoy.month - 1]} de {hoy.year}, {hoy:%H:%M} h"
    portada = open(os.path.join(AQUI, "plantilla_portada.html"), encoding="utf-8").read().replace("/*FECHA*/", fecha).replace("<!--COLABORAR-->", colaborar())
    portada = portada.replace("<!--VISITAS-->", contador_portada())
    open(os.path.join(WEB, "index.html"), "w", encoding="utf-8").write(con_contador(portada))
    open(os.path.join(WEB, ".nojekyll"), "w").close()
    print(f"web/ armada ({fecha})")


def subir():
    """Sube el código a GitHub. Los datos los mantiene GitHub (los commitea cada hora), así que se toman de allá."""
    token = subprocess.run(["gh", "auth", "token", "--user", "elfrancho"], capture_output=True, text=True, check=True).stdout.strip()
    url = f"https://x-access-token:{token}@github.com/{REPO}.git"

    def git(*a, check=True):
        r = subprocess.run(["git", "-C", AQUI, *a], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(f"git {a[0]} falló: " + (r.stderr + r.stdout).replace(token, "***"))
        return r

    git("fetch", "-q", url, "main")
    git("checkout", "FETCH_HEAD", "--", "datos_ina", "datos_salado")
    git("add", "-A")
    if git("diff", "--cached", "--quiet", check=False).returncode != 0:
        git("commit", "-q", "-m", f"Cambios desde la notebook {dt.datetime.now(ARG):%d/%m/%Y %H:%M}")
    git("rebase", "-q", "FETCH_HEAD")
    if git("rev-parse", "HEAD").stdout == git("rev-parse", "FETCH_HEAD").stdout:
        # sin cambios de código: igual pide una actualización ya mismo
        r = subprocess.run(["gh", "api", "-X", "POST", f"repos/{REPO}/actions/workflows/web.yml/dispatches", "-f", "ref=main"],
                           capture_output=True, text=True, env={**os.environ, "GH_TOKEN": token})
        print("sin cambios de código; actualización pedida" if r.returncode == 0 else "no se pudo pedir la actualización")
        return
    git("push", "-q", url, "HEAD:main")
    print("subido: GitHub arma y publica en un par de minutos -> https://elfrancho.github.io/rios/")


def main():
    if "--armar" in sys.argv:
        armar()
    elif "--local" in sys.argv:
        correr([PY, "bajar_ina.py", "datos_ina"])
        correr([PY, "bajar_salado.py"])
        armar()
    else:
        subir()


if __name__ == "__main__":
    main()
