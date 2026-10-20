"""Arma rios.html (un solo archivo, funciona sin internet) a partir de los CSV bajados.

Para actualizar con datos nuevos:
    python bajar_ina.py datos_ina      (≈1 min)
    python desfase.py                  (opcional, recalcula demoras)
    python armar.py
"""
import csv, datetime, json, os

AQUI = os.path.dirname(os.path.abspath(__file__))
DESDE = datetime.date(1980, 1, 1)
ESTACIONES = ["iguazu_andresito", "iguazu_puerto_iguazu", "parana_posadas", "parana_corrientes", "parana_santa_fe"]


def leer(path, col):
    if not os.path.exists(path):
        return {}
    return {datetime.date.fromisoformat(r["fecha"]): float(r[col]) for r in csv.DictReader(open(path, encoding="utf-8"))}


def main():
    meta = json.load(open(f"{AQUI}/datos_ina/estaciones.json", encoding="utf-8"))
    desf = json.load(open(f"{AQUI}/datos_ina/desfases.json", encoding="utf-8"))
    hasta = DESDE
    series, completados = {}, {}
    for k in ESTACIONES:
        alt = leer(f"{AQUI}/datos_ina/{k}_altura.csv", "valor")
        nac = leer(f"{AQUI}/datos/{k}.csv", "altura_m")  # base nacional: solo rellena días que falten
        faltan = [d for d in nac if d not in alt and d >= DESDE]
        for d in faltan:
            alt[d] = nac[d]
        completados[k] = len(faltan)
        cau = leer(f"{AQUI}/datos_ina/{k}_caudal.csv", "valor")
        series[k] = (alt, cau)
        hasta = max([hasta] + list(alt))
    n = (hasta - DESDE).days + 1
    datos = {"desde": DESDE.isoformat(), "dias": n, "estaciones": {}, "desfases": desf,
             "generado": datetime.date.today().isoformat()}
    for k, (alt, cau) in series.items():
        a = [alt.get(DESDE + datetime.timedelta(days=i)) for i in range(n)]
        c = [cau.get(DESDE + datetime.timedelta(days=i)) for i in range(n)]
        datos["estaciones"][k] = {
            **meta[k],
            "altura": [None if v is None else round(v, 2) for v in a],
            "caudal": [None if v is None else round(v) for v in c] if any(v is not None for v in c) else None,
        }
    plantilla = open(f"{AQUI}/plantilla.html", encoding="utf-8").read()
    lib = open(f"{AQUI}/lib/echarts.min.js", encoding="utf-8").read()
    html = (plantilla.replace("/*ECHARTS*/", lib)
            .replace("/*DATOS*/", json.dumps(datos, ensure_ascii=False, separators=(",", ":"))))
    open(f"{AQUI}/rios.html", "w", encoding="utf-8").write(html)
    print(f"rios.html: {n} días ({DESDE} a {hasta}), {len(html)/1e6:.1f} MB; días completados con base nacional: {completados}")


if __name__ == "__main__":
    main()
