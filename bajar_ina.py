"""Baja series diarias de altura (y caudal si existe) del sistema de alerta del INA (API pública a5).

Uso: python bajar_ina.py <carpeta_salida>
Por estación guarda <clave>_altura.csv (fecha,valor) y, si hay, <clave>_caudal.csv.
También escribe estaciones.json con niveles de alerta / evacuación / aguas bajas.
"""
import csv, json, sys, urllib.request
from collections import defaultdict

API = "https://alerta.ina.gob.ar/a5/obs/puntual"
ESTACIONES = {  # clave: id de estación en el INA (escalas de Prefectura)
    "iguazu_andresito": 8,
    "iguazu_puerto_iguazu": 9,
    "parana_posadas": 14,
    "parana_corrientes": 19,
    "parana_santa_fe": 30,
    "parana_goya": 23,
    "parana_reconquista": 24,
    "parana_la_paz": 26,
    "parana_rosario": 34,
}
DESDE, HASTA = "1900-01-01", "2100-01-01"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=600) as r:
        d = json.load(r)
    return d["rows"] if isinstance(d, dict) and "rows" in d else d


def observaciones(serie_id):
    return get(f"{API}/series/{serie_id}/observaciones?timestart={DESDE}&timeend={HASTA}&format=json")


def dia(ts):
    # timestart viene en UTC; el día hidrológico argentino arranca 03:00 UTC (00:00 local)
    from datetime import datetime, timedelta
    t = datetime.fromisoformat(ts.replace("Z", "+00:00")) - timedelta(hours=3)
    return t.date().isoformat()


def diario(obs):
    acc = defaultdict(list)
    for o in obs:
        v = o.get("valor")
        if v is not None:
            acc[dia(o["timestart"])].append(float(v))
    return {d: round(sum(v) / len(v), 3) for d, v in acc.items()}


def guardar(path, serie):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["fecha", "valor"])
        for d in sorted(serie):
            w.writerow([d, serie[d]])


def main():
    salida = sys.argv[1]
    meta = {}
    for clave, est_id in ESTACIONES.items():
        series = get(f"{API}/series?estacion_id={est_id}&format=json")
        por_var = defaultdict(list)
        for s in series:
            if (s.get("procedimiento") or {}).get("id") in (None, 1, 2):  # medición directa o curva de gasto (no simulados ni pronósticos)
                por_var[s["var"]["id"]].append(s["id"])
        e = series[0]["estacion"] if series else {}
        meta[clave] = {k: e.get(k) for k in ("nombre", "rio", "nivel_alerta", "nivel_evacuacion",
                                               "nivel_aguas_bajas", "cero_ign")}
        # altura: media diaria (var 39) completada con lecturas instantáneas (var 2) promediadas por día
        altura = {}
        for sid in por_var.get(2, []):
            altura.update(diario(observaciones(sid)))
        for sid in por_var.get(39, []):
            altura.update(diario(observaciones(sid)))  # la media diaria oficial pisa a la calculada
        guardar(f"{salida}/{clave}_altura.csv", altura)
        caudal = {}
        for sid in por_var.get(4, []) + por_var.get(40, []):
            caudal.update(diario(observaciones(sid)))
        if caudal:
            guardar(f"{salida}/{clave}_caudal.csv", caudal)
        dias = sorted(altura)
        print(f"{clave}: altura {len(altura)} días ({dias[0] if dias else '-'} a {dias[-1] if dias else '-'}),"
              f" caudal {len(caudal)} días", file=sys.stderr)
    with open(f"{salida}/estaciones.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
