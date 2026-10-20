"""Arma ola.html: simulación interactiva de cómo baja una crecida por el Iguazú y el Paraná (mapa + barra de tiempo).

Uso: python bajar_ina.py ... (datos al día) y después  python armar_ola.py
Cada puerto se pinta según su propio "nivel": 0 = normal (mediana 1980-2025), 1 = alerta, 2 = evacuación,
-1 = aguas bajas (niveles de Prefectura). Así se comparan puertos con ceros distintos. Entre puertos el color
se interpola: no hay medición ahí.
Posadas queda afuera: desde Yacyretá su altura la regula el embalse.
"""
import csv, datetime as dt, json, os, statistics

AQUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(AQUI, "datos_ina")
# clave, nombre, lon, lat (punto para dibujar sobre el río esquemático)
PUERTOS = [
    ("iguazu_andresito", "Andresito", -53.99, -25.60),
    ("iguazu_puerto_iguazu", "Puerto Iguazú", -54.59, -25.59),
    ("parana_corrientes", "Corrientes", -58.83, -27.47),
    ("parana_goya", "Goya", -59.20, -29.10),
    ("parana_reconquista", "Reconquista", -59.45, -29.62),
    ("parana_la_paz", "La Paz", -59.64, -30.74),
    ("parana_santa_fe", "Santa Fe", -60.60, -31.66),
    ("parana_rosario", "Rosario", -60.64, -32.95),
]
EVENTOS = [  # id, título, desde, hasta (None = hasta el último dato)
    ("actual", "Crecida actual (2026)", "2026-09-15", None),
    ("2023", "Crecida de 2023", "2023-10-01", "2024-02-15"),
    ("2014", "Crecida de 2014", "2014-05-25", "2014-09-15"),
    ("2013", "Crecida de 2013", "2013-06-01", "2013-09-10"),
    ("1992", "Crecida de 1992", "1992-05-01", "1992-09-15"),
    ("1983", "Gran crecida de 1983", "1983-04-01", "1983-10-15"),
]


def serie(k):
    return {dt.date.fromisoformat(r["fecha"]): float(r["valor"]) for r in csv.DictReader(open(os.path.join(D, f"{k}_altura.csv"), encoding="utf-8"))}


def main():
    meta = json.load(open(os.path.join(D, "estaciones.json"), encoding="utf-8"))
    S = {k: serie(k) for k, *_ in PUERTOS}
    puertos = []
    for k, nombre, lon, lat in PUERTOS:
        m = meta[k]
        normal = statistics.median(v for d, v in S[k].items() if 1980 <= d.year <= 2025)
        puertos.append({"k": k, "nombre": nombre, "lon": lon, "lat": lat, "normal": round(normal, 2),
                        "alerta": m["nivel_alerta"], "evac": m["nivel_evacuacion"], "bajas": m["nivel_aguas_bajas"]})
    ultimo = min(max(S[k]) for k, *_ in PUERTOS)
    eventos = []
    for eid, titulo, a, b in EVENTOS:
        a = dt.date.fromisoformat(a)
        b = dt.date.fromisoformat(b) if b else ultimo
        n = (b - a).days + 1
        datos = {}
        for k, *_ in PUERTOS:
            arr, ult = [], None
            for i in range(n):
                v = S[k].get(a + dt.timedelta(days=i))
                arr.append(round(v, 2) if v is not None else None)
            datos[k] = arr
        picos = {k: max(((v, i) for i, v in enumerate(datos[k]) if v is not None), default=None) for k in datos}
        eventos.append({"id": eid, "titulo": titulo, "desde": a.isoformat(), "dias": n, "datos": datos,
                        "picos": {k: [p[0], (a + dt.timedelta(days=p[1])).isoformat()] for k, p in picos.items() if p}})
        print(f"{titulo:24s} {a} a {b} ({n} días) picos: " + ", ".join(f"{p['nombre']} {picos[p['k']][0]:.2f}" for p in puertos if picos[p['k']]))
    html = open(os.path.join(AQUI, "plantilla_ola.html"), encoding="utf-8").read().replace(
        "/*DATOS*/", json.dumps({"puertos": puertos, "eventos": eventos, "actualizado": ultimo.isoformat()}, ensure_ascii=False, separators=(",", ":")))
    open(os.path.join(AQUI, "ola.html"), "w", encoding="utf-8").write(html)
    print("ola.html listo,", round(len(html) / 1e3), "KB; normales:", {p["nombre"]: p["normal"] for p in puertos})


if __name__ == "__main__":
    main()
