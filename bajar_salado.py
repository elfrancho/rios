"""Baja la historia del río Salado (Santa Fe) y deja datos_salado/<clave>.csv (fecha,altura_m,fuente).

Fuentes:
- Base Hidrológica Integrada (SNIH), datos validados: Recreo/Ruta 70 (desde 1980), Tostado (desde 2004),
  Laguna Setúbal en La Guardia (desde 1992). Llegan hasta la última validación (hoy, junio 2026).
- CIM-FICH (UNL), red de alerta provincial: último año de las 8 estaciones, hasta hoy.
Para unir las dos fuentes en Recreo y Tostado se compara el tramo en común: si la diferencia mediana supera
5 cm se avisa y se guarda el CIM aparte, para no mezclar escalas distintas.
Uso: python bajar_salado.py
"""
import csv, datetime as dt, html, json, os, re, statistics, urllib.request
from collections import defaultdict

AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = os.path.join(AQUI, "datos_salado")
UA = {"User-Agent": "Mozilla/5.0"}
SNIH = {"recreo": 13216, "tostado": 13343, "setubal": 13339}
CIM = {"tostado": 1, "calchaqui": 2, "san_justo": 3, "emilia": 4, "recreo": 5, "santo_tome": 6, "cululu": 7, "paso_piedras": 52}


def snih(codigo, desde=1980):
    out = defaultdict(list)
    url = "https://snih.hidricosargentina.gob.ar/MuestraDatos.aspx/LeerDatosHistoricos"
    for a in range(desde, dt.date.today().year + 1, 5):
        body = json.dumps({"fechaDesde": f"{a}-01-01", "fechaHasta": f"{a + 4}-12-31", "estacion": codigo, "codigo": 1, "validados": True}).encode()
        req = urllib.request.Request(url, data=body, headers={**UA, "Content-Type": "application/json"})
        for m in json.load(urllib.request.urlopen(req, timeout=300))["d"].get("Mediciones") or []:
            if m["Medicion"] is None or m["Medicion"] <= -999:
                continue
            ms = int(m["FechaHora"].split("(")[1].split(")")[0].split("-")[0].split("+")[0])
            d = (dt.datetime(1970, 1, 1) + dt.timedelta(milliseconds=ms) - dt.timedelta(hours=3)).date()
            out[d].append(m["Medicion"])
    return {d: round(sum(v) / len(v), 3) for d, v in out.items()}


def cim(i):
    t = urllib.request.urlopen(urllib.request.Request(f"https://fich.unl.edu.ar/cim/rios/historico/{i}", headers=UA), timeout=120).read().decode("utf-8", "replace")
    out = defaultdict(list)
    for fila in re.findall(r"<tr.*?</tr>", t, re.S):
        c = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", x))).strip() for x in re.findall(r"<td.*?</td>", fila, re.S)]
        if len(c) >= 3 and re.match(r"\d\d/\d\d/\d{4}", c[0]):
            try:
                out[dt.datetime.strptime(c[0], "%d/%m/%Y").date()].append(float(c[2].replace(",", ".")))
            except ValueError:
                pass
    return {d: round(sum(v) / len(v), 3) for d, v in out.items()}


def guardar(clave, serie):
    with open(os.path.join(SAL, f"{clave}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fecha", "altura_m", "fuente"])
        for d in sorted(serie):
            w.writerow([d.isoformat(), serie[d][0], serie[d][1]])


def main():
    os.makedirs(SAL, exist_ok=True)
    largas = {k: snih(c, 1980 if k == "recreo" else 1990) for k, c in SNIH.items()}
    anio = {k: cim(i) for k, i in CIM.items()}
    for k in set(largas) | set(anio):
        serie = {d: (v, "SNIH") for d, v in largas.get(k, {}).items()}
        a = anio.get(k, {})
        if serie and a:
            comun = [d for d in a if d in largas[k]]
            dif = statistics.median(a[d] - largas[k][d] for d in comun) if comun else None
            if dif is None or abs(dif) > 0.05:
                print(f"{k}: CIM y SNIH no coinciden (diferencia mediana {dif}); el CIM queda aparte como {k}_cim")
                guardar(f"{k}_cim", {d: (v, "CIM") for d, v in a.items()})
                a = {}
            else:
                print(f"{k}: {len(comun)} días en común, diferencia mediana {dif:+.3f} m -> se unen")
        for d, v in a.items():
            if d not in serie:
                serie[d] = (v, "CIM")
        guardar(k, serie)
        ds = sorted(serie)
        print(f"{k:13s} {len(ds):6d} días  {ds[0]} a {ds[-1]}")


if __name__ == "__main__":
    main()
