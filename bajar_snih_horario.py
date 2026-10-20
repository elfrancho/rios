r"""Baja las alturas "a tiempo útil" (dato crudo del sensor, cada 30 min a 4 h) del SNIH.

Uso: python bajar_snih_horario.py [desde AAAA-MM-DD]   -> datos_snih\<clave>.csv (fecha_hora,altura_m)
Son datos sin validar: se descartan los saltos sueltos (un valor que se aparta mucho de sus dos vecinos).
"""
import csv, datetime as dt, json, os, sys, urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
URL = "https://snih.hidricosargentina.gob.ar/MuestraDatos.aspx/LeerUltimosRegistros"
# clave -> (código de estación SNIH, salto máximo creíble entre lecturas vecinas, en m)
ESTACIONES = {"andresito": (13448, 1.5), "puerto_iguazu": (13446, 2.0), "corrientes": (13805, 0.3),
              "goya": (13887, 0.3), "setubal": (13339, 0.2), "rosario": (13311, 0.2)}


def bajar(codigo, desde, hasta):
    body = json.dumps({"fechaDesde": desde, "fechaHasta": hasta, "estacion": str(codigo), "codigo": "1"}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        filas = json.load(r)["d"].get("Mediciones") or []
    out = []
    for x in filas:
        ms = int(x["FechaHora"].split("(")[1].split(")")[0].split("-")[0].split("+")[0])
        v = x["Mediciones"][0].get("Valor")
        if v is not None and v > -900:
            out.append((dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=ms) - dt.timedelta(hours=3), v))
    return sorted(out)


def limpiar(serie, salto):
    """Saca valores que saltan respecto de los dos vecinos y vuelven (picos de un solo registro)."""
    ok = [serie[0]] if serie else []
    for i in range(1, len(serie) - 1):
        a, b, c = serie[i - 1][1], serie[i][1], serie[i + 1][1]
        if abs(b - a) > salto and abs(b - c) > salto and abs(a - c) <= salto:
            continue
        ok.append(serie[i])
    return ok + serie[-1:] if len(serie) > 1 else ok


def main():
    desde = sys.argv[1] if len(sys.argv) > 1 else "2026-09-01"
    hasta = dt.date.today().isoformat()
    os.makedirs(os.path.join(AQUI, "datos_snih"), exist_ok=True)
    for clave, (codigo, salto) in ESTACIONES.items():
        crudo = bajar(codigo, desde, hasta)
        serie = limpiar(crudo, salto)
        with open(os.path.join(AQUI, "datos_snih", f"{clave}.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fecha_hora", "altura_m"])
            w.writerows([(t.isoformat(timespec="minutes"), v) for t, v in serie])
        print(f"{clave}: {len(serie)} lecturas ({len(crudo) - len(serie)} descartadas), "
              f"{serie[0][0]:%d/%m %H:%M} -> {serie[-1][0]:%d/%m %H:%M}")


if __name__ == "__main__":
    main()
