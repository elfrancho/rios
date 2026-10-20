"""Baja alturas diarias de la base hidrológica nacional (SNIH / BDHI), año por año.

Uso: python bajar_snih.py <carpeta_salida> <codigo_estacion> <nombre> [anio_desde]
Guarda <nombre>.csv con columnas fecha,altura_m,validado.
"""
import csv, datetime, json, sys, time, urllib.request

BASE = "https://snih.hidricosargentina.gob.ar/MuestraDatos.aspx/LeerDatosHistoricos"


def pedir(estacion, desde, hasta, validados):
    body = json.dumps({"fechaDesde": desde, "fechaHasta": hasta, "estacion": estacion,
                       "codigo": 1, "validados": validados}).encode()
    req = urllib.request.Request(BASE, data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    for intento in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)["d"].get("Mediciones") or []
        except Exception as e:  # red inestable: reintento con espera creciente
            print("  reintento", intento + 1, e, file=sys.stderr)
            time.sleep(2 ** (intento + 1))
    return []


def fecha(ms_txt):
    ms = int(ms_txt.split("(")[1].split(")")[0].split("-")[0].split("+")[0])
    # El servidor manda medianoche/hora local de Argentina (UTC-3): corrijo para no correr el día
    return (datetime.datetime(1970, 1, 1) + datetime.timedelta(milliseconds=ms) - datetime.timedelta(hours=3)).date()


def main():
    salida, estacion, nombre = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    desde = int(sys.argv[4]) if len(sys.argv) > 4 else 1980
    hoy = datetime.date.today()
    datos = {}  # fecha -> (lista de alturas, validado)
    for anio in range(desde, hoy.year + 1):
        a, b = f"{anio}-01-01", (f"{anio}-12-31" if anio < hoy.year else hoy.isoformat())
        n = 0
        # primero lo validado; después lo no validado solo para días que falten
        for validados in (True, False):
            for m in pedir(estacion, a, b, validados):
                v = m.get("Medicion")
                if v is None or v <= -999:
                    continue
                d = fecha(m["FechaHora"])
                prev = datos.get(d)
                if prev and prev[1] and not validados:
                    continue
                if prev is None or prev[1] == validados:
                    datos.setdefault(d, ([], validados))[0].append(v)
                    n += 1
        print(f"{nombre} {anio}: {n} lecturas", file=sys.stderr)
    with open(f"{salida}/{nombre}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fecha", "altura_m", "validado"])
        for d in sorted(datos):
            vals, val = datos[d]
            w.writerow([d.isoformat(), round(sum(vals) / len(vals), 2), int(val)])
    print(f"{nombre}: {len(datos)} días guardados", file=sys.stderr)


if __name__ == "__main__":
    main()
