"""Arma el sitio del estudio de la zona para publicar en GitHub Pages, protegido con clave.

Uso: python zonas/publicar_estudio.py            -> arma zonas/_sitio/ (no sube nada)
     python zonas/publicar_estudio.py --subir    -> además lo sube al repositorio REPO de la cuenta personal (elfrancho)

GitHub Pages gratuito no tiene páginas con contraseña. Acá las imágenes y los datos se suben CIFRADOS (AES-256-GCM) y la página
los descifra en el navegador con la clave: sin la clave, lo publicado son archivos ilegibles, con nombres que no dicen nada.
- Las claves están en zonas/_privado/claves.json (carpeta fuera de git), una por rol. Para cambiar una: editar ese archivo y volver a subir.
- El contenido se cifra con una llave fija (zonas/_privado/contenido.bin); cada clave, con PBKDF2-SHA256 (600.000 vueltas), abre una
  "cerradura" que guarda esa llave y el rol. Así varias claves abren lo mismo y la página sabe con cuál se entró.
- Registro de visitas: cada ingreso manda a GoatCounter un evento "estudio-zona/<rol>/<página>" (fecha, hora, navegador, sistema,
  pantalla y país; GoatCounter no guarda la IP). También anota los intentos con clave incorrecta. La pantalla de ingreso lo avisa.
- Lo que SÍ se ve desde afuera: que el sitio existe, cuántos archivos tiene y cuánto pesa cada uno.
- Las imágenes se pasan a WebP para que pesen menos. La de Bing NO se publica (sin fecha y sin permiso de redistribución).
"""
import base64, hashlib, hmac, io, json, os, re, secrets, shutil, subprocess, sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from PIL import Image
from rasterio.warp import transform as reproyectar

Image.MAX_IMAGE_PIXELS = None
AQUI = os.path.dirname(os.path.abspath(__file__))
SITIO = os.path.join(AQUI, "_sitio")
PRIVADO = os.path.join(AQUI, "_privado")
REPO = "elfrancho/estudio-zona"
VUELTAS = 600_000
CONTADOR = "elfrancho"   # GoatCounter: el mismo panel que el sitio de ríos; las visitas quedan bajo "estudio-zona/..."
VISTAS = [("p", "zona_precisa", "index.html", "Zona de estudio"), ("g", "zona_a_investigar", "contexto.html", "Zona amplia")]

ACCESO = """<div id="acceso" style="position:fixed;inset:0;z-index:50;background:#0e1418;display:flex;align-items:center;justify-content:center;padding:16px;overflow:auto">
 <form id="formClave" style="background:#151d23;border:1px solid #2a3840;border-radius:12px;padding:22px;max-width:380px;width:100%;font:15px/1.45 system-ui,sans-serif;color:#e8eef1">
  <h2 style="margin:0 0 6px;font-size:19px">Estudio de zona</h2>
  <p style="margin:0 0 14px;color:#9aabb4;font-size:14px">Material reservado. Escribí la clave que te pasaron para verlo.</p>
  <label for="clave" style="display:block;font-size:13px;color:#9aabb4;margin-bottom:4px">Clave</label>
  <div style="display:flex;gap:6px">
   <input id="clave" type="password" autocomplete="current-password" autocapitalize="none" autocorrect="off" spellcheck="false" autofocus required
          style="flex:1;min-width:0;padding:12px;border-radius:8px;border:1px solid #2a3840;background:#0e1418;color:#e8eef1;font:16px system-ui">
   <button type="button" id="verClave" aria-pressed="false" style="padding:0 12px;border-radius:8px;border:1px solid #2a3840;background:#1c272e;color:#e8eef1;font:13px system-ui;cursor:pointer">Ver</button>
  </div>
  <button id="entrar" style="margin-top:12px;width:100%;padding:12px;border:0;border-radius:8px;background:#4fd8ff;color:#06222c;font:600 16px system-ui;cursor:pointer">Entrar</button>
  <p id="errClave" role="alert" style="margin:10px 0 0;color:#ff8a8a;font-size:13.5px;min-height:20px"></p>
  <p style="margin:6px 0 0;color:#9aabb4;font-size:12px">El acceso queda registrado: fecha, hora, navegador y país.</p>
 </form>
</div>
<script>
(() => {
  const CERRADURAS = __CERRADURAS__, VUELTAS = __VUELTAS__, PRE = "__PRE__";
  const registrar = ev => { try { new Image().src = "https://__CONTADOR__.goatcounter.com/count?p=" + encodeURIComponent("estudio-zona/" + ev) + "&t=" + encodeURIComponent("Estudio de zona") + "&e=true&s=" + [screen.width, screen.height, devicePixelRatio || 1].join(",") + "&rnd=" + Math.random().toString(36).slice(2); } catch (e) {} };
  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const el = id => document.getElementById(id);
  let kAes, kMac; const cache = new Map();
  async function llaves(bits) {
    kAes = await crypto.subtle.importKey("raw", bits.slice(0, 32), "AES-GCM", false, ["decrypt"]);
    kMac = await crypto.subtle.importKey("raw", bits.slice(32, 64), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  }
  async function leer(ruta) {
    const firma = new Uint8Array(await crypto.subtle.sign("HMAC", kMac, new TextEncoder().encode(ruta)));
    const nombre = [...firma.slice(0, 10)].map(x => x.toString(16).padStart(2, "0")).join("");
    const r = await fetch("d/" + nombre + ".bin"); if (!r.ok) throw new Error("no está " + ruta);
    const buf = new Uint8Array(await r.arrayBuffer());
    return crypto.subtle.decrypt({ name: "AES-GCM", iv: buf.slice(0, 12) }, kAes, buf.slice(12));
  }
  // La vista pide cada imagen por acá: se baja cifrada, se descifra y recién entonces se muestra (la anterior queda a la vista mientras tanto).
  window.__src = async (img, ruta) => {
    const clave = ruta.startsWith("../zona_a_investigar/") ? "g/" + ruta.slice(21) : PRE + "/" + ruta;
    img.dataset.pide = clave;
    try {
      if (!cache.has(clave)) cache.set(clave, leer(clave).then(b => URL.createObjectURL(new Blob([b], { type: "image/webp" }))));
      const url = await cache.get(clave);
      if (img.dataset.pide === clave) img.src = url;
    } catch (e) { cache.delete(clave); if (img.dataset.pide === clave) img.dispatchEvent(new Event("error")); }
  };
  async function entrar(bits, rol, guardar) {
    await llaves(bits);
    window.__D = JSON.parse(new TextDecoder().decode(await leer(PRE + "/datos.json")));
    if (guardar) sessionStorage.setItem("k", btoa(String.fromCharCode(...new Uint8Array(bits))) + "|" + rol);
    registrar(rol + "/" + (PRE === "p" ? "zona-de-estudio" : "zona-amplia") + (guardar ? "/ingreso" : ""));
    el("acceso").remove(); window.__visor();
  }
  async function abrir(clave) {   // prueba la clave en cada cerradura; la que abre devuelve la llave de contenido y el rol
    const base = await crypto.subtle.importKey("raw", new TextEncoder().encode(clave), "PBKDF2", false, ["deriveKey"]);
    for (const c of CERRADURAS) {
      try {
        const k = await crypto.subtle.deriveKey({ name: "PBKDF2", hash: "SHA-256", salt: b64(c.s), iterations: VUELTAS }, base, { name: "AES-GCM", length: 256 }, false, ["decrypt"]);
        const w = b64(c.w), claro = new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: w.slice(0, 12) }, k, w.slice(12)));
        return [claro.slice(0, 64).buffer, new TextDecoder().decode(claro.slice(64))];
      } catch (e) {}
    }
    return null;
  }
  const previa = sessionStorage.getItem("k");
  if (previa) { const [k, rol] = previa.split("|"); entrar(b64(k).buffer, rol, false).catch(() => sessionStorage.removeItem("k")); }
  el("verClave").addEventListener("click", () => { const c = el("clave"), ver = c.type === "password"; c.type = ver ? "text" : "password"; el("verClave").textContent = ver ? "Ocultar" : "Ver"; el("verClave").setAttribute("aria-pressed", ver); c.focus(); });
  el("formClave").addEventListener("submit", async ev => {
    ev.preventDefault(); const err = el("errClave"), boton = el("entrar"), escrita = el("clave").value.trim();
    if (!window.crypto || !crypto.subtle) { err.textContent = "Este navegador no permite abrir el material. Probá con Chrome, Edge, Firefox o Safari actualizados."; return; }
    err.style.color = "#9aabb4"; err.textContent = "Comprobando la clave…"; boton.disabled = true; boton.style.opacity = .6;
    try {
      // las claves van en minúsculas: si el teclado puso una mayúscula, se prueba también sin ella
      const r = await abrir(escrita) || (escrita !== escrita.toLowerCase() ? await abrir(escrita.toLowerCase()) : null);
      if (!r) throw new Error("clave");
      err.textContent = "Abriendo…"; await entrar(r[0], r[1], true);
    } catch (e) {
      err.style.color = "#ff8a8a"; boton.disabled = false; boton.style.opacity = 1;
      if (e.message === "clave") { err.textContent = "Clave incorrecta. Revisá que no haya espacios ni letras cambiadas."; registrar("clave-incorrecta"); el("clave").select(); }
      else err.textContent = "La clave es correcta pero no se pudo cargar el material. Revisá la conexión y probá de nuevo.";
    }
  });
})();
</script>"""


def llaves():
    """Llave de contenido (fija, 64 bytes) y una cerradura por cada clave de zonas/_privado/claves.json.
    Cada cerradura guarda la llave de contenido y el rol, cifrados con esa clave: así varias claves abren lo mismo
    y la página sabe con cuál se entró (para el registro de visitas) sin que el rol quede a la vista."""
    k = open(os.path.join(PRIVADO, "contenido.bin"), "rb").read()
    cerraduras = []
    for u in json.load(open(os.path.join(PRIVADO, "claves.json"), encoding="utf-8"))["usuarios"]:
        sal, iv = secrets.token_bytes(16), secrets.token_bytes(12)
        ku = hashlib.pbkdf2_hmac("sha256", u["clave"].encode(), sal, VUELTAS, 32)
        cerraduras.append({"s": base64.b64encode(sal).decode(), "w": base64.b64encode(iv + AESGCM(ku).encrypt(iv, k + u["rol"].encode(), None)).decode()})
    secrets.SystemRandom().shuffle(cerraduras)
    return k, cerraduras


def webp(ruta):
    b = io.BytesIO()
    Image.open(ruta).convert("RGB").save(b, "WEBP", quality=82, method=4)
    return b.getvalue()


def main():
    bits, cerraduras = llaves()
    aes, mac = AESGCM(bits[:32]), bits[32:]
    shutil.rmtree(SITIO, ignore_errors=True)
    os.makedirs(os.path.join(SITIO, "d"))
    total = 0

    def guardar(ruta_logica, contenido):
        nonlocal total
        nombre = hmac.new(mac, ruta_logica.encode(), hashlib.sha256).digest()[:10].hex()
        iv = secrets.token_bytes(12)
        datos = iv + aes.encrypt(iv, contenido, None)
        open(os.path.join(SITIO, "d", nombre + ".bin"), "wb").write(datos)
        total += len(datos)

    plantilla = open(os.path.join(AQUI, "plantilla_vista.html"), encoding="utf-8").read()
    for pre, carpeta, pagina, titulo in VISTAS:
        zona = os.path.join(AQUI, carpeta)
        d = json.load(open(os.path.join(zona, "escenas.json"), encoding="utf-8"))
        d.pop("descartadas", None)
        rev = os.path.join(zona, "revisadas.json")
        quitar = json.load(open(rev, encoding="utf-8")).get("quitar", {}) if os.path.exists(rev) else {}
        d["escenas"] = [e for e in d["escenas"] if e["fecha"] not in quitar]
        ctx = os.path.join(zona, "contexto.json")
        if "contexto" not in d and os.path.exists(ctx):
            d["contexto"] = json.load(open(ctx, encoding="utf-8"))
        d["zona"] = titulo
        gx0, gy1, gres, gw, gh = d["grilla"]
        if "esquinas_lonlat" not in d:   # NO, NE, SE, SO: para dar coordenadas en la vista
            lo, la = reproyectar("EPSG:32720", "EPSG:4326", [gx0, gx0 + gw * gres, gx0 + gw * gres, gx0], [gy1, gy1, gy1 - gh * gres, gy1 - gh * gres])
            d["esquinas_lonlat"] = [[round(a, 7), round(b, 7)] for a, b in zip(lo, la)]
        d.setdefault("ancho_km", gw * gres / 1000)
        d.setdefault("alto_km", gh * gres / 1000)
        d.pop("nota", None)
        for e in d["escenas"]:
            if e.get("teselas"):   # se muestra en vivo desde el servidor del proveedor: no hay archivo que cifrar
                continue
            base = e.get("clave") or e["fecha"]
            for suf in ([""] + (["_pan"] if e.get("pan", e.get("resolucion_m", 9) <= 2) else [])):
                guardar(f"{pre}/img/{base}{suf}.jpg", webp(os.path.join(zona, "img", base + suf + ".jpg")))
        guardar(f"{pre}/datos.json", json.dumps(d, ensure_ascii=False).encode())
        html = plantilla.replace("const D = /*DATOS*/null;", "const D = window.__D;")
        html = html.replace("<title>Zona desde el satélite</title>", '<title>Estudio de zona</title>\n<meta name="robots" content="noindex,nofollow">')
        html = re.sub(r"<script>\n", "<script>\nwindow.__visor = function () {\n", html, count=1)
        html = html.replace("</script>\n</body>", "};\n</script>\n" + ACCESO.replace("__CERRADURAS__", json.dumps(cerraduras)).replace("__CONTADOR__", CONTADOR)
                            .replace("__VUELTAS__", str(VUELTAS)).replace("__PRE__", pre) + "\n</body>")
        otra = [v for v in VISTAS if v[0] != pre][0]
        html = html.replace("<!--ENLACE-->", f'<a class="lnk" href="{otra[2]}">{otra[3]} →</a>')
        ana = os.path.join(zona, "analisis.html")
        if os.path.exists(ana):
            html = html.replace("<!--ANALISIS-->", "")  # el texto de cambios va cifrado junto con los datos, no en la página
        open(os.path.join(SITIO, pagina), "w", encoding="utf-8").write(html)
        print(carpeta, "->", pagina, len(d["escenas"]), "imágenes")
    open(os.path.join(SITIO, ".nojekyll"), "w").close()
    open(os.path.join(SITIO, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n")
    print(f"sitio armado en {SITIO}: {len(os.listdir(os.path.join(SITIO, 'd')))} archivos cifrados, {total / 1e6:.0f} MB · claves en zonas/_privado/claves.json")
    if "--subir" in sys.argv:
        subir()


def subir():
    token = subprocess.run(["gh", "auth", "token", "--user", "elfrancho"], capture_output=True, text=True, check=True).stdout.strip()
    env = {**os.environ, "GH_TOKEN": token}
    if subprocess.run(["gh", "repo", "view", REPO], capture_output=True, env=env).returncode != 0:
        subprocess.run(["gh", "repo", "create", REPO, "--public", "--description", "Material de estudio (acceso con clave)"], check=True, env=env)
    url = f"https://x-access-token:{token}@github.com/{REPO}.git"

    def git(*a):
        r = subprocess.run(["git", "-C", SITIO, *a], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"git {a[0]} falló: " + (r.stderr + r.stdout).replace(token, "***"))
    # historia de un solo commit: cada publicación reemplaza todo (los archivos cifrados cambian enteros cada vez)
    git("init", "-q", "-b", "main")
    git("add", "-A")
    git("-c", "user.name=elfrancho", "-c", "user.email=elfrancho@users.noreply.github.com", "commit", "-q", "-m", "Publicación")
    git("push", "-q", "--force", url, "main")
    shutil.rmtree(os.path.join(SITIO, ".git"), ignore_errors=True)
    r = subprocess.run(["gh", "api", "-X", "POST", f"repos/{REPO}/pages", "-f", "source[branch]=main", "-f", "source[path]=/"], capture_output=True, text=True, env=env)
    print("subido ->", f"https://{REPO.split('/')[0]}.github.io/{REPO.split('/')[1]}/", "(Pages activado)" if r.returncode == 0 else "(Pages ya estaba activado o hay que activarlo a mano)")


if __name__ == "__main__":
    main()
