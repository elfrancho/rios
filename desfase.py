"""Estima cuántos días tarda una variación en pasar de un puerto a otro (correlación cruzada).

Usa la variación semanal de altura (altura de hoy menos la de 7 días antes), que resalta las
crecidas y saca la estacionalidad lenta. Para cada par busca el corrimiento (0-60 días) con
mayor correlación. Imprime el resultado y lo guarda en datos_ina/desfases.json.
"""
import csv, datetime, json, math

D = "datos_ina/"
PARES = [("iguazu_puerto_iguazu", "parana_corrientes"), ("iguazu_andresito", "parana_corrientes"),
         ("parana_posadas", "parana_corrientes"), ("parana_corrientes", "parana_santa_fe"),
         ("iguazu_puerto_iguazu", "parana_santa_fe")]


def leer(clave, var="altura"):
    return {datetime.date.fromisoformat(r["fecha"]): float(r["valor"])
            for r in csv.DictReader(open(f"{D}{clave}_{var}.csv"))}


def variacion(s, n=7):
    return {d: v - s[d - datetime.timedelta(days=n)] for d, v in s.items()
            if d.year >= 1980 and d - datetime.timedelta(days=n) in s}


def corr(a, b, lag):
    xs, ys = [], []
    for d, v in a.items():
        w = b.get(d + datetime.timedelta(days=lag))
        if w is not None:
            xs.append(v); ys.append(w)
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs)); sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sxy / (sx * sy)


res = {}
for o, d in PARES:
    a, b = variacion(leer(o)), variacion(leer(d))
    curva = [(lag, corr(a, b, lag)) for lag in range(0, 61)]
    lag, r = max(curva, key=lambda x: x[1])
    res[f"{o}->{d}"] = {"dias": lag, "correlacion": round(r, 3)}
    print(f"{o:22s} -> {d:18s}: {lag:2d} días (correlación {r:.2f})")
json.dump(res, open(D + "desfases.json", "w"), indent=1)
