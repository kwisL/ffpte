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

ESTILOS = dict(zoom=zoom, flotar=flotar, latido=latido, giro3d=giro3d, rebote=rebote,
               deslizar=deslizar, rotar=rotar, revelar=revelar, sacudir=sacudir, respirar=respirar)
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
        img = frame(logo, W, H, f(t), fondo)
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
