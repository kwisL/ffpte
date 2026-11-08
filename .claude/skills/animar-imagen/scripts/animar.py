#!/usr/bin/env python3
"""Anima una imagen/logo con movimientos que NUNCA alteran sus colores.

Solo se usan transformaciones geométricas (posición, escala, rotación, recorte)
y opacidad sobre fondo. No hay filtros, tintes, brillo, saturación ni cambio de tono.

Uso:
  python3 animar.py LOGO.png --salida carpeta/ [--estilos rebote,flotar,giro3d]
         [--fondo auto|#RRGGBB|transparente] [--formato 1080x1920] [--segundos 4]
Siempre genera 3 ejemplos (MP4 para redes + MOV sin pérdida con transparencia).
"""
import warnings; warnings.filterwarnings("ignore", category=DeprecationWarning)
import argparse, math, os, random, subprocess, sys
from collections import Counter
from PIL import Image

FPS = 30

def ease_out_back(t, s=1.70158):
    t -= 1
    return t * t * ((s + 1) * t + s) + 1

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_in_out(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)

def ease_out_bounce(t):
    n, d = 7.5625, 2.75
    if t < 1 / d: return n * t * t
    if t < 2 / d: t -= 1.5 / d; return n * t * t + .75
    if t < 2.5 / d: t -= 2.25 / d; return n * t * t + .9375
    t -= 2.625 / d; return n * t * t + .984375

# Cada estilo devuelve (dx, dy, escala_x, escala_y, rotacion_grados, opacidad, recorte_0a1)
def zoom(t):      e = ease_out_back(min(t / .5, 1)); return 0, 0, e, e, 0, min(t / .2, 1), 1
def flotar(t):    return 0, math.sin(t * 2 * math.pi) * .04, 1, 1, math.sin(t * 2 * math.pi) * 2, 1, 1
def latido(t):
    p = (t * 2) % 1; k = 1 + .08 * math.exp(-8 * p) * math.sin(p * math.pi * 3) ** 2
    return 0, 0, k, k, 0, 1, 1
def giro3d(t):    c = math.cos(ease_in_out(min(t / .7, 1)) * 2 * math.pi); return 0, 0, abs(c) or .001, 1, 0, 1, 1
def rebote(t):    return 0, -(1 - ease_out_bounce(min(t / .6, 1))) * .8, 1, 1, 0, 1, 1
def deslizar(t):  e = ease_out_cubic(min(t / .5, 1)); return (1 - e) * -1.2, 0, 1, 1, 0, e, 1
def rotar(t):     e = ease_out_back(min(t / .6, 1)); return 0, 0, e, e, (1 - e) * -180, min(t / .2, 1), 1
def revelar(t):   return 0, 0, 1, 1, 0, 1, ease_in_out(min(t / .6, 1))
def sacudir(t):
    a = .03 * math.exp(-5 * (t % .5) * 2) * math.sin(t * 60)
    return a, 0, 1, 1, a * 100, 1, 1
def respirar(t):  k = 1 + .05 * math.sin(t * 2 * math.pi); return 0, 0, k, k, 0, 1, 1

# --- Estilos de ESCRITURA: las piezas del logo aparecen una a una (letra a letra) ---
# Cada píxel recibe un "momento de aparición"; nunca se mezcla ni se modifica su color.
def _componentes(mask):
    import numpy as np
    from collections import deque
    h, w = mask.shape; lab = np.zeros((h, w), np.int32); n = 0
    for y0, x0 in zip(*np.nonzero(mask)):
        if lab[y0, x0]: continue
        n += 1; lab[y0, x0] = n; q = deque([(y0, x0)])
        while q:
            y, x = q.popleft()
            for yy, xx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1),(y-1,x-1),(y-1,x+1),(y+1,x-1),(y+1,x+1)):
                if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not lab[yy, xx]:
                    lab[yy, xx] = n; q.append((yy, xx))
    return lab, n

def mapa_escritura(logo, variante):
    import numpy as np
    a = np.array(logo.getchannel("A")) > 0
    # dilatar 2px para unir bordes suavizados y tildes/puntos a su letra
    d = a.copy()
    for _ in range(2):
        d = d | np.roll(d, 1, 0) | np.roll(d, -1, 0) | np.roll(d, 1, 1) | np.roll(d, -1, 1)
    lab, n = _componentes(d)
    piezas = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        piezas.append(dict(id=i, y0=ys.min(), y1=ys.max(), x0=xs.min(), x1=xs.max()))
    alturas = sorted(p["y1"] - p["y0"] for p in piezas)
    med = alturas[len(alturas) // 2]
    hmax = max(p["y1"] - p["y0"] for p in piezas)
    simbolo = [p for p in piezas if p["y1"] - p["y0"] > .6 * hmax]
    letras = [p for p in piezas if p not in simbolo]
    # agrupar letras en líneas por su centro vertical
    letras.sort(key=lambda p: (p["y0"] + p["y1"]) / 2)
    lineas = []
    for p in letras:
        c = (p["y0"] + p["y1"]) / 2
        if lineas and abs(c - lineas[-1][-1]["c"]) < med * .6: lineas[-1].append(p)
        else: lineas.append([p])
        p["c"] = c
    for l in lineas: l.sort(key=lambda p: p["x0"])
    T = np.full(a.shape, np.inf)
    def letras_en(t0, t1, paralelo=False):
        if paralelo:
            for l in lineas:
                for k, p in enumerate(l): T[lab == p["id"]] = t0 + (t1 - t0) * k / len(l)
        else:
            seq = [p for l in lineas for p in l]
            for k, p in enumerate(seq): T[lab == p["id"]] = t0 + (t1 - t0) * k / len(seq)
    def simbolo_en(t0, t1):
        simbolo.sort(key=lambda p: p["y0"])
        for k, p in enumerate(simbolo):
            m = lab == p["id"]; ys = np.nonzero(m)[0]
            a0 = t0 + (t1 - t0) * k / (len(simbolo) + 1); a1 = a0 + (t1 - t0) * 2 / (len(simbolo) + 1)
            yy = np.arange(a.shape[0])[:, None] * np.ones_like(m)
            T[m] = a0 + (a1 - a0) * (yy[m] - ys.min()) / max(1, ys.max() - ys.min())
    if variante == "escribir":           simbolo_en(0, .25); letras_en(.28, .75)
    elif variante == "escribir-inverso": letras_en(0, .5); simbolo_en(.52, .75)
    else:                                simbolo_en(0, .6); letras_en(.1, .6, paralelo=True)
    T[~a] = np.inf
    return T

ESCRITURA = ["escribir", "escribir-inverso", "escribir-lineas"]

ESTILOS = dict(zoom=zoom, flotar=flotar, latido=latido, giro3d=giro3d, rebote=rebote,
               deslizar=deslizar, rotar=rotar, revelar=revelar, sacudir=sacudir, respirar=respirar,
               **{e: None for e in ESCRITURA})
# Grupos: entrada / bucle / énfasis -> por defecto se elige uno de cada para variedad
GRUPOS = [["zoom", "rebote", "deslizar", "rotar", "revelar"],
          ["flotar", "respirar", "giro3d"],
          ["latido", "sacudir"]]

def color_fondo(img):
    w, h = img.size; px = img.load()
    esquinas = [px[x, y] for x, y in [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]]
    if all(p[3] < 10 for p in esquinas): return (255, 255, 255)
    return Counter(p[:3] for p in esquinas).most_common(1)[0][0]

def colores_logo(img, n=8):
    px = [p[:3] for p in img.getdata() if p[3] == 255]
    return [c for c, k in Counter(px).most_common(n) if k > len(px) * .01]

def frame(logo, W, H, estado, fondo):
    dx, dy, sx, sy, rot, op, rec = estado
    lw, lh = logo.size
    tw, th = max(1, round(lw * abs(sx))), max(1, round(lh * abs(sy)))
    # NEAREST cuando no hay escala: píxeles idénticos al original
    m = Image.NEAREST if (tw, th) == (lw, lh) else Image.LANCZOS
    capa = logo.resize((tw, th), m) if (tw, th) != (lw, lh) else logo.copy()
    if rec < 1:
        a = capa.getchannel("A"); cut = round(tw * rec)
        a.paste(0, (cut, 0, tw, th)); capa.putalpha(a)
    if rot: capa = capa.rotate(rot, Image.BICUBIC, expand=True)
    if op < 1:
        capa.putalpha(capa.getchannel("A").point(lambda v: round(v * op)))
    lienzo = Image.new("RGBA", (W, H), (0, 0, 0, 0) if fondo is None else (*fondo, 255))
    x = round(W / 2 - capa.width / 2 + dx * W); y = round(H / 2 - capa.height / 2 + dy * H)
    lienzo.alpha_composite(capa, (x, y)) if -capa.width < x < W and -capa.height < y < H else None
    return lienzo

def render(logo, estilo, W, H, seg, fondo, base):
    n = int(seg * FPS); f = ESTILOS[estilo]
    if estilo in ESCRITURA:
        import numpy as np
        T = mapa_escritura(logo, estilo); base_px = np.array(logo); fijo = lambda e: e
        def f(t): return t
        def frame_escr(t):
            px = base_px.copy(); px[..., 3] = np.where(T <= t, px[..., 3], 0)
            capa = Image.fromarray(px, "RGBA")
            lienzo = Image.new("RGBA", (W, H), (0, 0, 0, 0) if fondo is None else (*fondo, 255))
            lienzo.alpha_composite(capa, ((W - capa.width) // 2, (H - capa.height) // 2))
            return lienzo
    mp4 = base + ".mp4"; mov = base + ".mov"
    bg = fondo or (255, 255, 255)
    p1 = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "12", "-preset", "slow",
        "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-color_range", "tv", "-vf", "scale=out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int",
        "-movflags", "+faststart", mp4], stdin=subprocess.PIPE)
    p2 = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "qtrle", mov], stdin=subprocess.PIPE)
    ultimo = None
    for i in range(n):
        t = i / n
        img = frame_escr(t) if estilo in ESCRITURA else frame(logo, W, H, f(t), fondo)
        p2.stdin.write(img.tobytes())
        sol = Image.new("RGBA", (W, H), (*bg, 255)); sol.alpha_composite(img)
        p1.stdin.write(sol.tobytes()); ultimo = img
    for p in (p1, p2): p.stdin.close(); p.wait()
    frame(logo, W, H, (0, 0, 1, 1, 0, 1, 1), fondo).save(base + "-portada.png")
    return mp4, mov

def verificar(logo, W, H, fondo, colores):
    """Comprueba que el fotograma en reposo contiene EXACTAMENTE los colores del logo."""
    img = frame(logo, W, H, (0, 0, 1, 1, 0, 1, 1), fondo)
    presentes = set(p[:3] for p in img.getdata())
    return [c for c in colores if c not in presentes]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imagen"); ap.add_argument("--salida", default="animaciones")
    ap.add_argument("--estilos", help="3 estilos separados por coma: " + ",".join(ESTILOS))
    ap.add_argument("--fondo", default="auto"); ap.add_argument("--formato", default="1080x1920")
    ap.add_argument("--segundos", type=float, default=4); ap.add_argument("--semilla", type=int)
    a = ap.parse_args()
    random.seed(a.semilla)
    W, H = map(int, a.formato.lower().split("x"))
    logo = Image.open(a.imagen).convert("RGBA")
    fondo = None if a.fondo == "transparente" else color_fondo(logo) if a.fondo == "auto" \
        else tuple(int(a.fondo.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
    # Escala el logo al 60% del lado menor UNA sola vez (sin tocar colores)
    k = min(W, H) * .6 / max(logo.size)
    if abs(k - 1) > .01: logo = logo.resize((round(logo.width * k), round(logo.height * k)), Image.LANCZOS)
    colores = colores_logo(Image.open(a.imagen).convert("RGBA"))
    estilos = a.estilos.split(",") if a.estilos else [random.choice(g) for g in GRUPOS]
    if len(estilos) != 3 or any(e not in ESTILOS for e in estilos):
        sys.exit(f"Necesito exactamente 3 estilos válidos: {', '.join(ESTILOS)}")
    os.makedirs(a.salida, exist_ok=True)
    nombre = os.path.splitext(os.path.basename(a.imagen))[0]
    for i, e in enumerate(estilos, 1):
        mp4, mov = render(logo, e, W, H, a.segundos, fondo, os.path.join(a.salida, f"{nombre}-{i}-{e}"))
        print(f"Ejemplo {i} ({e}): {mp4} | {mov}")
    falta = verificar(logo, W, H, fondo, colores)
    print("Colores del logo:", ", ".join("#%02X%02X%02X" % c for c in colores))
    print("VERIFICACIÓN DE COLOR:", "OK — todos los colores intactos" if not falta
          else "AVISO — no aparecen exactos: " + ", ".join("#%02X%02X%02X" % c for c in falta))

if __name__ == "__main__":
    main()
