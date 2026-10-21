"""Historia "Río Salado hoy": 8 estaciones de la red de alerta de la cuenca (Provincia de Santa Fe), publicada por el CIM-FICH (UNL).

Uso: python salado.py [carpeta_salida]   -> <carpeta>/parte_4.png  (por defecto partes/<hoy>/)
También lo llama parte_diario.py los sábados, como historia 2 del parte (parte_2.png).
Los datos son una lectura por día, tomada a las 00 h.
"""
import datetime as dt, html, json, os, re, subprocess, sys, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
URL = "https://fich.unl.edu.ar/cim/rios/salado/alturas"
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def num(x):
    try:
        return float(x.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def leer():
    t = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read().decode("utf-8", "replace")
    m = re.search(r"correspondientes a la fecha\s*(.*?)\s*\.", re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))))
    filas = []
    for fila in re.findall(r"<tr.*?</tr>", t, re.S):
        c = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<td.*?</td>", fila, re.S)]
        if len(c) >= 7 and num(c[2]) is not None:
            filas.append({"estacion": c[0], "rio": c[1], "altura": num(c[2]), "var": num(c[3]), "ant": num(c[5]), "alerta": num(c[6])})
    return (m.group(1) if m else ""), filas


def main(carpeta=None, nombre="parte_4.png"):
    fecha_txt, filas = leer()
    if not filas:
        raise RuntimeError("El CIM no devolvió datos del Salado")
    hoy = dt.date.today()
    carpeta = os.path.abspath(carpeta or os.path.join(AQUI, "partes", hoy.isoformat()))
    os.makedirs(carpeta, exist_ok=True)
    datos = {"fecha": f"{DIAS[hoy.weekday()]} {hoy:%d/%m}", "fecha_fuente": fecha_txt, "filas": filas}
    html_txt = open(os.path.join(AQUI, "plantilla_salado.html"), encoding="utf-8").read().replace("/*DATOS*/", json.dumps(datos, ensure_ascii=False))
    pagina = os.path.join(carpeta, "salado.html")
    open(pagina, "w", encoding="utf-8").write(html_txt)
    png = os.path.join(carpeta, nombre)
    chrome = next(c for c in CHROME if os.path.exists(c))
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    "--window-size=1080,1920", "--virtual-time-budget=3000", "--allow-file-access-from-files",
                    f"--screenshot={png}", "file:///" + pagina.replace("\\", "/")], check=True, capture_output=True)
    print("ok", png)
    return png


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
