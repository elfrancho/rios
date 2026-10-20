"""Verificaciones de los hallazgos de analisis.py."""
import csv, datetime as dt, statistics as stt, sys, json, urllib.request
from collections import defaultdict
sys.stdout.reconfigure(encoding="utf-8")
D = "datos_ina/"


def leer(k, var="altura"):
    return {dt.date.fromisoformat(r["fecha"]): float(r["valor"]) for r in csv.DictReader(open(f"{D}{k}_{var}.csv"))}


A = {k: leer(k) for k in ["iguazu_andresito", "iguazu_puerto_iguazu", "parana_corrientes", "parana_santa_fe", "parana_posadas"]}

print("== Series de caudal en el INA (qué son)")
for est in (8, 9):
    req = urllib.request.Request(f"https://alerta.ina.gob.ar/a5/obs/puntual/series?estacion_id={est}&format=json", headers={"User-Agent": "Mozilla/5.0"})
    for s in json.load(urllib.request.urlopen(req, timeout=120))["rows"]:
        if s["var"]["id"] in (4, 40):
            print(est, s["id"], s["var"]["nombre"], "|", s["procedimiento"]["nombre"], "| estación", s["estacion"]["nombre"], s["estacion"]["rio"])
qa, qp = leer("iguazu_andresito", "caudal"), leer("iguazu_puerto_iguazu", "caudal")
for nom, q in (("Andresito", qa), ("Pto Iguazú", qp)):
    v = list(q.values())
    ult = sorted(q)[-5:]
    print(f"{nom}: {min(q)}..{max(q)} media {stt.mean(v):,.0f} mediana {stt.median(v):,.0f}; últimos: " + ", ".join(f"{d} {q[d]:,.0f}" for d in ult))
com = [d for d in qa if d in qp]
print("días en común Andresito/PtoIguazú:", len(com), "relación mediana PI/Andresito", round(stt.median(qp[d] / qa[d] for d in com if qa[d] > 0), 2))
for d in [dt.date(2014, 6, 10), dt.date(2023, 10, 30), dt.date(2023, 11, 6), dt.date(2026, 10, 16)]:
    print(d, "Andresito h", A["iguazu_andresito"].get(d), "Q", qa.get(d), "| PI h", A["iguazu_puerto_iguazu"].get(d), "Q", qp.get(d))

print("\n== Respuesta en Santa Fe a grandes crecidas del Iguazú (ventana 90 días)")
for d in [dt.date(1983, 7, 13), dt.date(1992, 5, 31), dt.date(1997, 2, 4), dt.date(2013, 6, 26), dt.date(2014, 6, 10), dt.date(2023, 10, 30)]:
    out = []
    for k, n in (("parana_corrientes", 60), ("parana_santa_fe", 90)):
        s = A[k]
        base = s[d - dt.timedelta(days=1)]
        vent = [(d + dt.timedelta(days=j), s.get(d + dt.timedelta(days=j))) for j in range(0, n)]
        m = max((x for x in vent if x[1] is not None), key=lambda x: x[1])
        # primer día en que subió 20 cm sobre la base
        arr = next(((x[0] - d).days for x in vent if x[1] is not None and x[1] - base >= 0.2), None)
        out.append(f"{k.split('_')[1]} {base:.2f}→{m[1]:.2f} pico {(m[0]-d).days:+d} d (empieza a subir +{arr} d)")
    print(f"{d} PI {A['iguazu_puerto_iguazu'][d]:.2f} Andresito {A['iguazu_andresito'].get(d)} | " + " | ".join(out))

print("\n== Ciclo semanal en Puerto Iguazú por período (cm respecto de la media móvil de 7 días)")
s = A["iguazu_puerto_iguazu"]
for a, b in ((1966, 1975), (1976, 1983), (1984, 1990), (1991, 2000), (2001, 2010), (2011, 2020), (2021, 2026)):
    dif = defaultdict(list)
    for d, v in s.items():
        if a <= d.year <= b:
            w = [s.get(d + dt.timedelta(days=j)) for j in range(-3, 4)]
            if None not in w:
                dif[d.weekday()].append(v - sum(w) / 7)
    if dif:
        vals = [stt.mean(dif[i]) * 100 for i in range(7)]
        print(f"{a}-{b}: " + " ".join(f"{x:+5.0f}" for x in vals) + f"   amplitud {max(vals)-min(vals):.0f} cm   (lun..dom)")

print("\n== Crecida actual, últimos 21 días")
for k in A:
    s = A[k]
    ult = sorted(s)[-21:]
    print(k[:22].ljust(22), " ".join(f"{s[d]:.2f}" for d in ult))
