"""Búsqueda de hallazgos en las series diarias (INA). Imprime un informe de texto."""
import csv, datetime as dt, math, statistics as stt, sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
D = "datos_ina/"
EST = ["iguazu_andresito", "iguazu_puerto_iguazu", "parana_posadas", "parana_corrientes", "parana_santa_fe"]
CORTO = dict(zip(EST, ["Andresito", "Pto Iguazú", "Posadas", "Corrientes", "Santa Fe"]))
NIV = {"iguazu_puerto_iguazu": (25, 28, 9.4), "parana_corrientes": (6.5, 7, 1.83), "parana_santa_fe": (5.3, 5.7, 2.0),
       "iguazu_andresito": (10.5, 13.5, 0.16)}


def leer(k, var="altura"):
    try:
        return {dt.date.fromisoformat(r["fecha"]): float(r["valor"]) for r in csv.DictReader(open(f"{D}{k}_{var}.csv"))}
    except FileNotFoundError:
        return {}


A = {k: leer(k) for k in EST}
Q = {k: leer(k, "caudal") for k in EST}
ULT = max(A["parana_corrientes"])


def picos(s, ventana=60, desde=None):
    """Máximos locales (el mayor valor en ±ventana días), ordenados de mayor a menor."""
    ds = sorted(d for d in s if desde is None or d >= desde)
    out = []
    for d in ds:
        v = s[d]
        ok = all(s.get(d + dt.timedelta(days=j), -1e9) <= v for j in range(-ventana, ventana + 1) if j)
        if ok and not any(abs((d - p).days) <= ventana for p, _ in out):
            out.append((d, v))
    return sorted(out, key=lambda x: -x[1])


def titulo(t):
    print("\n" + "=" * 8, t, "=" * 8)


titulo("1. Récords históricos (toda la serie disponible)")
for k in EST:
    s = A[k]
    p = picos(s)[:6]
    print(f"{CORTO[k]:11s} desde {min(s).year}: " + " | ".join(f"{d:%d/%m/%Y} {v:.2f}" for d, v in p))
    mn = sorted(s.items(), key=lambda x: x[1])[:1]
    print(f"{'':11s} mínimo: {mn[0][0]:%d/%m/%Y} {mn[0][1]:.2f}")

titulo("2. Crecida actual: dónde se ubica")
for k in EST:
    s = A[k]
    hoy = s[ULT]
    hace7 = s.get(ULT - dt.timedelta(days=7))
    hace30 = s.get(ULT - dt.timedelta(days=30))
    mayor = sum(1 for v in s.values() if v > hoy) / len(s) * 100
    anios_sup = sorted({d.year for d, v in s.items() if v >= hoy})
    print(f"{CORTO[k]:11s} {ULT:%d/%m}: {hoy:.2f} m (hace 7 d {hace7}, hace 30 d {hace30}); "
          f"solo el {mayor:.1f}% de los días de la historia estuvo más alto; años que lo superaron: {len(anios_sup)}"
          f" (últimos: {anios_sup[-6:]})")

titulo("3. Demora Iguazú→Corrientes→Santa Fe por década (correlación de variaciones semanales)")


def variacion(s, n=7):
    return {d: v - s[d - dt.timedelta(days=n)] for d, v in s.items() if d - dt.timedelta(days=n) in s}


def mejor_lag(a, b, d0, d1):
    best = None
    for lag in range(0, 41):
        xs, ys = [], []
        for d, v in a.items():
            if d0 <= d < d1:
                w = b.get(d + dt.timedelta(days=lag))
                if w is not None:
                    xs.append(v); ys.append(w)
        if len(xs) < 300:
            return None
        r = stt.correlation(xs, ys)
        if best is None or r > best[1]:
            best = (lag, r)
    return best


vpi, vco, vsf = (variacion(A[k]) for k in ("iguazu_puerto_iguazu", "parana_corrientes", "parana_santa_fe"))
for d0 in range(1970, 2030, 10):
    a, b = dt.date(d0, 1, 1), dt.date(d0 + 10, 1, 1)
    l1, l2 = mejor_lag(vpi, vco, a, b), mejor_lag(vco, vsf, a, b)
    print(f"{d0}s: Pto Iguazú→Corrientes {l1[0] if l1 else '-'} d (r={l1[1]:.2f})" if l1 else f"{d0}s: -", end="")
    print(f" | Corrientes→Santa Fe {l2[0]} d (r={l2[1]:.2f})" if l2 else "")

titulo("4. Ciclo semanal (efecto de la operación de represas: menos generación el fin de semana)")
for k in EST:
    s = A[k]
    dif = defaultdict(list)
    for d, v in s.items():
        if d.year < 1995:
            continue
        # anomalía contra la media centrada de 7 días: saca la tendencia y deja el ciclo semanal
        win = [s.get(d + dt.timedelta(days=j)) for j in range(-3, 4)]
        if None in win:
            continue
        dif[d.weekday()].append(v - sum(win) / 7)
    dias = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
    print(f"{CORTO[k]:11s} " + "  ".join(f"{dias[i]} {stt.mean(dif[i])*100:+5.1f}cm" for i in range(7)))
for k in ("iguazu_puerto_iguazu", "iguazu_andresito", "parana_posadas", "parana_corrientes"):
    s = A[k]
    dif = defaultdict(list)
    for d, v in s.items():
        if d.year < 1980 or d.year > 1984:
            continue
        win = [s.get(d + dt.timedelta(days=j)) for j in range(-3, 4)]
        if None in win:
            continue
        dif[d.weekday()].append(v - sum(win) / 7)
    if dif:
        print(f"{CORTO[k]:11s} 1980-84 (antes de Itaipú) " + "  ".join(f"{i} {stt.mean(dif[i])*100:+5.1f}" for i in range(7)))

titulo("5. Bajantes: días por debajo del nivel de aguas bajas, por año (Corrientes y Santa Fe)")
for k in ("parana_corrientes", "parana_santa_fe"):
    s = A[k]
    lim = NIV[k][2]
    por = defaultdict(int)
    for d, v in s.items():
        if v < lim:
            por[d.year] += 1
    top = sorted(por.items(), key=lambda x: -x[1])[:8]
    print(f"{CORTO[k]} (< {lim} m): " + ", ".join(f"{y}: {n} d" for y, n in top))
    mins = sorted(((d, v) for d, v in s.items()), key=lambda x: x[1])
    vistos, lista = set(), []
    for d, v in mins:
        if d.year not in vistos:
            vistos.add(d.year); lista.append((d, v))
        if len(lista) == 6:
            break
    print(f"   mínimos por año: " + " | ".join(f"{d:%d/%m/%Y} {v:.2f}" for d, v in lista))

titulo("6. ¿En qué mes ocurre el máximo anual? (1980-2025)")
for k in EST:
    s = A[k]
    meses = defaultdict(int)
    for y in range(1980, 2026):
        vals = [(d, v) for d, v in s.items() if d.year == y]
        if len(vals) > 300:
            meses[max(vals, key=lambda x: x[1])[0].month] += 1
    print(f"{CORTO[k]:11s} " + " ".join(f"{m:02d}:{meses[m]}" for m in range(1, 13)))

titulo("7. Velocidad: mayor subida en 24 h y en 7 días (desde 1980)")
for k in EST:
    s = A[k]
    s1 = max(((d, v - s[d - dt.timedelta(days=1)]) for d, v in s.items() if d.year >= 1980 and d - dt.timedelta(days=1) in s), key=lambda x: x[1])
    s7 = max(((d, v - s[d - dt.timedelta(days=7)]) for d, v in s.items() if d.year >= 1980 and d - dt.timedelta(days=7) in s), key=lambda x: x[1])
    print(f"{CORTO[k]:11s} 24 h: +{s1[1]:.2f} m ({s1[0]:%d/%m/%Y}) | 7 días: +{s7[1]:.2f} m ({s7[0]:%d/%m/%Y})")

titulo("8. Grandes crecidas del Iguazú y qué pasó aguas abajo (picos de Pto Iguazú > 30 m desde 1980)")
pi = A["iguazu_puerto_iguazu"]
for d, v in sorted(picos(pi, 20, dt.date(1980, 1, 1))):
    if v < 30:
        continue
    def resp(k, desde, hasta):
        s = A[k]
        base = s.get(d - dt.timedelta(days=1))
        vent = [(d + dt.timedelta(days=j), s.get(d + dt.timedelta(days=j))) for j in range(desde, hasta)]
        vent = [x for x in vent if x[1] is not None]
        if not vent or base is None:
            return "s/d"
        m = max(vent, key=lambda x: x[1])
        return f"{base:.2f}→{m[1]:.2f} ({(m[0]-d).days:+d} d)"
    qd = Q["iguazu_puerto_iguazu"].get(d) or Q["iguazu_andresito"].get(d)
    print(f"{d:%d/%m/%Y} Pto Iguazú {v:.2f} m" + (f", caudal Iguazú ≈{qd:,.0f} m³/s" if qd else "") +
          f" | Corrientes {resp('parana_corrientes', 0, 25)} | Santa Fe {resp('parana_santa_fe', 0, 40)}")

titulo("9. Datos sospechosos")
for k in EST:
    s = A[k]
    ds = sorted(d for d in s if d.year >= 1980)
    # días repetidos idénticos muchos días seguidos (escala sin leer)
    racha, mejor, ini = 1, (1, None), ds[0]
    for a, b in zip(ds, ds[1:]):
        if (b - a).days == 1 and s[a] == s[b]:
            racha += 1
            if racha > mejor[0]:
                mejor = (racha, b)
        else:
            racha = 1
    # picos aislados: sube y baja más de X en un día
    lim = 2.5 if "iguazu" in k else 0.5
    spikes = [(d, s[d]) for d in ds if d - dt.timedelta(1) in s and d + dt.timedelta(1) in s
              and s[d] - s[d - dt.timedelta(1)] > lim and s[d] - s[d + dt.timedelta(1)] > lim]
    huecos = sum(1 for a, b in zip(ds, ds[1:]) if (b - a).days > 1)
    print(f"{CORTO[k]:11s} mayor racha de valor idéntico: {mejor[0]} días (hasta {mejor[1]}); "
          f"picos de 1 día: {len(spikes)} {spikes[:4]}; huecos: {huecos}")

titulo("10. Promedio por década (altura media) y caudal medio")
for k in ("parana_corrientes", "parana_santa_fe", "iguazu_puerto_iguazu"):
    s, q = A[k], Q[k]
    fila = []
    for d0 in range(1900, 2030, 10):
        v = [x for d, x in s.items() if d0 <= d.year < d0 + 10]
        w = [x for d, x in q.items() if d0 <= d.year < d0 + 10]
        if len(v) > 1000:
            fila.append(f"{d0}s {stt.mean(v):.2f}" + (f"/{stt.mean(w)/1000:.1f}k" if len(w) > 1000 else ""))
    print(f"{CORTO[k]:11s} " + " | ".join(fila))

titulo("11. Aporte del Iguazú al caudal de Corrientes (días con dato de ambos)")
qi = {**Q["iguazu_puerto_iguazu"]}
for d, v in Q["iguazu_andresito"].items():
    qi.setdefault(d, v)
qc = Q["parana_corrientes"]
com = [d for d in qi if d in qc and d.year >= 1994]
r = [qi[d] / qc[d] for d in com if qc[d] > 0]
print(f"días: {len(com)}; aporte medio {stt.mean(r)*100:.0f}%, mediana {stt.median(r)*100:.0f}%, máximo {max(r)*100:.0f}%")
qmed_i, qmed_c = stt.mean(qi[d] for d in com), stt.mean(qc[d] for d in com)
print(f"caudal medio Iguazú {qmed_i:,.0f} m³/s vs Corrientes {qmed_c:,.0f} m³/s")
mx = max(com, key=lambda d: qi[d])
print(f"máximo Iguazú {qi[mx]:,.0f} m³/s el {mx}; ese día Corrientes {qc[mx]:,.0f} m³/s")
