"""Arma salado.html (un solo archivo, funciona sin internet) con la historia del río Salado.

Para actualizar:  python bajar_salado.py  y después  python armar_salado.py
Niveles de alerta técnica: los de la red provincial que publica el CIM-FICH (se leen en el momento);
Paraná en Santa Fe: alerta y evacuación de Prefectura (datos_ina/estaciones.json).
"""
import csv, datetime as dt, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "historias"))
DESDE = dt.date(1980, 1, 1)
CLAVES = ["tostado", "san_justo", "emilia", "recreo", "santo_tome", "setubal"]
CIM_NOMBRE = {"tostado": "Tostado", "san_justo": "San Justo", "emilia": "Emilia", "recreo": "Recreo", "santo_tome": "Santo Tomé"}


def leer(path, col):
    return {dt.date.fromisoformat(r["fecha"]): float(r[col]) for r in csv.DictReader(open(path, encoding="utf-8"))} if os.path.exists(path) else {}


def main():
    series = {k: leer(os.path.join(AQUI, "datos_salado", f"{k}.csv"), "altura_m") for k in CLAVES}
    series["parana_sf"] = leer(os.path.join(AQUI, "datos_ina", "parana_santa_fe_altura.csv"), "valor")
    hasta = max(max(s) for s in series.values() if s)
    n = (hasta - DESDE).days + 1
    niveles = {}
    try:
        import salado
        _, filas = salado.leer()
        for k, nom in CIM_NOMBRE.items():
            f = next((x for x in filas if x["estacion"].startswith(nom)), None)
            if f and f["alerta"] is not None:
                niveles[k] = [["alerta técnica", f["alerta"], "alerta"]]
    except Exception as e:
        print("sin niveles de alerta del CIM:", e)
    meta = json.load(open(os.path.join(AQUI, "datos_ina", "estaciones.json"), encoding="utf-8")).get("parana_santa_fe", {})
    niveles["parana_sf"] = [["alerta", meta.get("nivel_alerta", 5.3), "alerta"], ["evacuación", meta.get("nivel_evacuacion", 5.7), "evac"]]
    datos = {"desde": DESDE.isoformat(), "dias": n, "niveles": niveles,
             "s": {k: [None if (DESDE + dt.timedelta(days=i)) not in s else round(s[DESDE + dt.timedelta(days=i)], 2) for i in range(n)]
                   for k, s in series.items() if s}}
    html = (open(os.path.join(AQUI, "plantilla_salado.html"), encoding="utf-8").read()
            .replace("/*ECHARTS*/", open(os.path.join(AQUI, "lib", "echarts.min.js"), encoding="utf-8").read())
            .replace("/*DATOS*/", json.dumps(datos, separators=(",", ":"))))
    open(os.path.join(AQUI, "salado.html"), "w", encoding="utf-8").write(html)
    print(f"salado.html: {n} días ({DESDE} a {hasta}), {len(html) / 1e6:.1f} MB, niveles: {list(niveles)}")


if __name__ == "__main__":
    main()
