"""Reel de los 30 mil seguidores de @elfrancho (03/11/2026): una isla que nace grano a grano con la forma de «30.000».

Va SIN voz (lo pidió Francisco: él le pone música al subirlo). La voz clonada (voz/b1..b3.wav, generar_voz.sh) solo marca
el ritmo: los tiempos de cada frase, estirados por LECTURA para que se alcancen a leer. Arma index.html y assets/ a partir de
fuentes/plantilla.html:
  - los puntos del banco (granos) muestreando el texto «30.000» con Barlow Condensed ExtraBold,
  - la playa y el borde mojado (PNG), las huellas de carpincho, ceibos y camalotes,
  - los tiempos de cada fase según la voz, y los subtítulos con los tiempos de faster-whisper.
Uso: python festejo30k/armar.py  (después: cd festejo30k && npx hyperframes render -o reel_30mil.mp4)
"""
import json, os, subprocess
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from faster_whisper import WhisperModel

AQUI = os.path.dirname(os.path.abspath(__file__))
W, H = 1080, 1920
CX, CY = 540, 1000          # centro del número
SR = 24000
ANTES, PAUSA, COLA = 0.5, 0.55, 2.8
LECTURA = 1.25      # sin voz, el texto necesita más tiempo que la voz
rng = np.random.default_rng(30000)

SUBS = [  # (en pantalla, lo que dice la voz)
    [("¿Sabés cómo nace una isla en el Paraná?", "¿Sabés cómo nace una isla en el Paraná?"), ("Grano a grano.", "Grano a grano."),
     ("El río trae la arena, el agua se frena,", "El río trae la arena, el agua se frena,"), ("y se forma un banco.", "y se forma un banco.")],
    [("Después llegan las plantas.", "Después llegan las plantas."), ("Y con las plantas, la vida.", "Y con las plantas, la vida.")],
    [("Esta cuenta nació igual:", "Esta cuenta nació igual:"), ("grano a grano, ustedes la fueron armando.", "grano a grano, ustedes la fueron armando."),
     ("Hoy somos 30.000.", "Hoy somos treinta mil."), ("Gracias por ser parte de esta isla.", "Gracias por ser parte de esta isla.")],
]


def leer(n):
    a, sr = sf.read(os.path.join(AQUI, "voz", f"b{n}.wav"), dtype="float32")
    if a.ndim > 1:
        a = a.mean(axis=1)
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a).astype("float32")
    voz = np.flatnonzero(np.abs(a) > 0.01)
    return a[max(voz[0] - 240, 0): voz[-1] + 2400]


def dilatar(m, r):
    img = Image.fromarray(m.astype("uint8") * 255)
    while r > 0:
        k = min(r, 10)
        img = img.filter(ImageFilter.MaxFilter(2 * k + 1))
        r -= k
    return np.asarray(img) > 127


def geometria():
    # «30» grande arriba y «MIL» abajo: dos islas
    img = Image.new("L", (W, H), 0)
    ruta = os.path.join(AQUI, "fuentes", "BarlowCondensed-ExtraBold.ttf")
    for texto, ancho, cy, aire in [("30", 560, 780, 0), ("MIL", 470, 1175, 34)]:   # aire: separación entre letras (px)
        f = ImageFont.truetype(ruta, 400)
        anchos = [f.getbbox(l)[2] - f.getbbox(l)[0] for l in texto] if aire else [f.getbbox(texto)[2] - f.getbbox(texto)[0]]
        k = (ancho - aire * (len(anchos) - 1)) / sum(anchos)
        f = ImageFont.truetype(ruta, int(400 * k))
        piezas = list(texto) if aire else [texto]
        cajas = [f.getbbox(l) for l in piezas]
        total = sum(c[2] - c[0] for c in cajas) + aire * (len(piezas) - 1)
        alto_ = max(c[3] for c in cajas) - min(c[1] for c in cajas)
        x = CX - total / 2
        for l, c in zip(piezas, cajas):
            ImageDraw.Draw(img).text((x - c[0], cy - alto_ / 2 - min(cc[1] for cc in cajas)), l, font=f, fill=255)
            x += c[2] - c[0] + aire
    num = np.asarray(img) > 127
    ys, xs = np.nonzero(num)
    abajo = ys.max()

    # distancia al borde (para que las plantas entren desde la orilla): erosiones sucesivas
    dist = np.zeros(num.shape, "float32")
    capa = Image.fromarray(num.astype("uint8") * 255)
    for k in range(1, 60):
        capa = capa.filter(ImageFilter.MinFilter(3))
        a = np.asarray(capa) > 127
        if not a.any():
            break
        dist[a] = k

    # granos: grilla triangular con algo de desorden
    paso = 10.5
    puntos = []
    for j, y in enumerate(np.arange(ys.min(), abajo + 1, paso * 0.866)):
        for x in np.arange(xs.min() + (paso / 2 if j % 2 else 0), xs.max() + 1, paso):
            px, py = x + rng.uniform(-2, 2), y + rng.uniform(-2, 2)
            if num[int(round(min(py, H - 1))), int(round(min(px, W - 1)))]:
                puntos.append([round(px, 1), round(py, 1)])
    puntos = np.array(puntos)
    d = np.array([dist[int(round(p[1])), int(round(p[0]))] for p in puntos])
    dn = d / max(d.max(), 1)

    # playa: el número dilatado más una barra de arena por debajo (para que las huellas sigan por la orilla)
    playa = dilatar(num, 13)
    barra = np.zeros_like(num)
    barra[abajo + 4: abajo + 52, 150: 930] = True
    playa |= barra
    mojado = dilatar(playa, 22)
    for nombre, m, color, blur in [("playa", playa, (226, 201, 150), 3), ("mojado", mojado & ~playa, (92, 66, 40), 9)]:
        a = Image.fromarray(m.astype("uint8") * 255).filter(ImageFilter.GaussianBlur(blur))
        rgba = Image.new("RGBA", (W, H), color + (0,))
        rgba.putalpha(a)
        rgba.save(os.path.join(AQUI, "assets", f"{nombre}.png"), optimize=True)

    # huellas de carpincho por la barra de arena, de izquierda a derecha (mano de 4 dedos y pata de 3)
    huellas = []
    yb = abajo + 30
    for k, x in enumerate(np.arange(170, 915, 30)):
        lado = 1 if k % 2 else -1
        huellas.append([round(float(x), 1), round(float(yb + lado * 11 + 3 * np.sin(k * 0.7)), 1), 4 if k % 4 < 2 else 3])

    # ceibos sobre la isla (lejos de la orilla) y camalotes flotando en el agua alrededor
    adentro = np.flatnonzero(dn > 0.35)
    ceibos = puntos[rng.choice(adentro, size=min(34, len(adentro)), replace=False)].round(1).tolist()
    lejos = dilatar(mojado, 40) & ~dilatar(mojado, 8)
    lejos[:520] = False
    lejos[1380:] = False
    cy_, cx_ = np.nonzero(lejos)
    elegidos = rng.choice(len(cx_), size=16, replace=False)
    camalotes = [[int(cx_[i]), int(cy_[i]), round(float(rng.uniform(0, 6.28)), 2)] for i in elegidos]

    granos = [[p[0], p[1], round(float(o), 3), round(float(rng.uniform()), 3), int(rng.integers(0, 4))]
              for p, o in zip(puntos, dn)]
    print(f"{len(granos)} granos, número de {xs.min()} a {xs.max()} x, {ys.min()} a {abajo} y")
    return {"granos": granos, "huellas": huellas, "ceibos": ceibos, "camalotes": camalotes,
            "abajo": int(abajo), "arriba": int(ys.min()), "izq": int(xs.min()), "der": int(xs.max())}


def main():
    bloques = [leer(n) for n in (1, 2, 3)]
    dur = [len(b) / SR for b in bloques]
    ini = [ANTES]
    for d in dur[:-1]:
        ini.append(round(ini[-1] + d + PAUSA, 3))
    total = round((ini[-1] + dur[-1]) * LECTURA + COLA, 2)
    modelo = WhisperModel("small", device="cpu", compute_type="int8")
    subs, frases = [], []
    for k, (b, t0b) in enumerate(zip(bloques, ini)):
        b16 = np.interp(np.arange(0, len(b), SR / 16000), np.arange(len(b)), b).astype("float32")
        segs, _ = modelo.transcribe(b16, language="es", word_timestamps=True)
        pal = [w for s in segs for w in s.words]
        print(f"b{k + 1}: {dur[k]:.1f} s · {' '.join(w.word.strip() for w in pal)}")
        habladas = sum(len(h.split()) for _, h in SUBS[k])
        cuenta = 0
        for j, (texto, hablado) in enumerate(SUBS[k]):
            n = len(hablado.split())
            i0 = min(int(round(cuenta * len(pal) / habladas)), len(pal) - 1)
            i1 = min(int(round((cuenta + n) * len(pal) / habladas)) - 1, len(pal) - 1)
            a, z = t0b + pal[i0].start, t0b + pal[i1].end
            if j + 1 < len(SUBS[k]):
                i2 = min(int(round((cuenta + n) * len(pal) / habladas)), len(pal) - 1)
                z = max(z, t0b + pal[i2].start - 0.05)
            else:
                z = z + 0.35
            cuenta += n
            frases.append((k, j, round(a * LECTURA, 2), round(z * LECTURA, 2)))
            subs.append((texto, a * LECTURA, z * LECTURA))

    f = {(k, j): (a, z) for k, j, a, z in frases}
    tiempos = {
        "total": total,
        "llegaIni": 1.7,                        # la arena empieza a asentarse enseguida (que el arranque no quede vacío)
        "contador": f[(0, 1)][0] - 0.2,          # «Grano a grano»: aparece el contador
        "llegaFin": f[(0, 3)][1] - 0.1,          # «y se forma un banco»: el banco completo
        "plantas": f[(1, 0)][0],                 # «Después llegan las plantas»
        "vida": f[(1, 1)][0],                    # «Y con las plantas, la vida»
        "b3": f[(2, 0)][0],
        "somos": f[(2, 2)][0],                   # «Hoy somos treinta mil»
        "gracias": f[(2, 3)][0],
    }
    print(json.dumps(tiempos))
    datos = geometria()
    datos["t"] = tiempos

    s = open(os.path.join(AQUI, "fuentes", "plantilla.html"), encoding="utf-8").read()
    s = s.replace("/*DATOS*/null", json.dumps(datos, separators=(",", ":")))
    s = s.replace("TOTAL_S", f"{total}")
    # el primero («¿Sabés cómo nace…?») y el último («Gracias…») no van: los dicen el título y el cartel grande
    filas = [f'      <div id="sub{i}" class="sub clip" data-start="{a:.2f}" data-duration="{z - a:.2f}" data-track-index="6"><span>{t}</span></div>'
             for i, (t, a, z) in enumerate(subs[1:-1])]
    s = s.replace("<!--SUBS-->", "\n".join(filas))
    s = s.replace("GRACIAS_S", f"{tiempos['gracias']:.2f}").replace("GRACIAS_D", f"{total - tiempos['gracias']:.2f}")
    open(os.path.join(AQUI, "index.html"), "w", encoding="utf-8").write(s)
    print(f"listo: {total:.1f} s")


if __name__ == "__main__":
    main()
