#!/usr/bin/env python3
"""Anima un texto por escenas sobre una imagen de fondo (invitaciones, recordatorios, citas).

El fondo NUNCA cambia de color: solo se escala para ajustarlo al formato (y, en la variante
"lineas", un zoom muy lento). El texto se dibuja encima.

Uso: python3 animar_texto.py guion.json --salida carpeta/
Genera siempre 3 variantes: 1-letra (máquina de escribir), 2-palabras (palabras que suben
suavemente), 3-lineas (líneas con fundido + zoom lento del fondo).
"""
import warnings; warnings.filterwarnings("ignore")
import json, os, subprocess, sys, argparse
from PIL import Image, ImageDraw, ImageFont

FPS = 30
FEAT = ["lnum"]   # números modernos (1 no parece I)
DIR_FUENTES = os.path.join(os.path.dirname(__file__), "..", "fuentes")

def fuente(nombre, tam, peso=None):
    f = ImageFont.truetype(os.path.join(DIR_FUENTES, nombre), tam)
    if peso:
        try: f.set_variation_by_axes([peso])
        except Exception: pass
    return f

def hex2rgb(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def partir(texto, f, ancho):
    lineas = []
    for parrafo in texto.split("\n"):
        actual = ""
        for w in parrafo.split():
            prueba = (actual + " " + w).strip()
            if f.getlength(prueba, features=FEAT) <= ancho or not actual: actual = prueba
            else: lineas.append(actual); actual = w
        lineas.append(actual)
    return lineas

def maquetar(escena, caja):
    """Devuelve lista de líneas: (texto, fuente, color, x, y) centradas en la caja."""
    x0, y0, x1, y1 = caja; bloques = []; alto = 0
    for b in escena["bloques"]:
        f = fuente(b["fuente"], b["tam"], b.get("peso"))
        ls = partir(b["texto"], f, x1 - x0)
        lh = int(b["tam"] * b.get("interlineado", 1.25))
        bloques.append((ls, f, hex2rgb(b["color"]), lh, b.get("espacio", 30)))
        alto += lh * len(ls) + b.get("espacio", 30)
    alto -= bloques[-1][4]
    y = y0 + (y1 - y0 - alto) / 2; out = []
    for ls, f, c, lh, esp in bloques:
        for l in ls:
            asc = f.getmetrics()[0]
            out.append((l, f, c, (x0 + x1) / 2 - f.getlength(l, features=FEAT) / 2, y + (lh - asc) / 2 + asc * .1))
            y += lh
        y += esp
    return out

def unidades(lineas, modo):
    """Trocea en unidades (letras, palabras o líneas) con su posición."""
    u = []
    for texto, f, c, x, y in lineas:
        if modo == "lineas": u.append((texto, f, c, x, y)); continue
        trozos = list(texto) if modo == "letra" else [w + " " for w in texto.split(" ")]
        pre = ""
        for t in trozos:
            u.append((t, f, c, x + f.getlength(pre, features=FEAT), y)); pre += t
    return u

VEL = {"letra": .045, "palabras": .22, "lineas": .7}   # segundos entre unidades
FUNDIDO = {"letra": .08, "palabras": .6, "lineas": 1.0}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("guion"); ap.add_argument("--salida", required=True)
    ap.add_argument("--solo", help="genera solo una variante: letra|palabras|lineas")
    a = ap.parse_args()
    g = json.load(open(a.guion)); base = os.path.dirname(os.path.abspath(a.guion))
    W, H = g.get("formato", [1080, 1920])
    fondo0 = Image.open(os.path.join(base, g["fondo"])).convert("RGB")
    fondo = fondo0.resize((W, H), Image.LANCZOS)
    caja = [int(v * (W if i % 2 == 0 else H)) for i, v in enumerate(g["caja"])]
    os.makedirs(a.salida, exist_ok=True)
    modos = [a.solo] if a.solo else ["letra", "palabras", "lineas"]
    for n, modo in enumerate(modos, 1):
        # Programación temporal de cada escena
        plan, t = [], .6
        for esc in g["escenas"]:
            us = unidades(maquetar(esc, caja), modo)
            dur_escr = len(us) * VEL[modo] * esc.get("velocidad", 1)
            fin = t + dur_escr + FUNDIDO[modo] + esc.get("pausa", 2.5)
            plan.append((t, fin, us, esc.get("velocidad", 1), esc.get("final", False)))
            t = fin + .8
        total = plan[-1][1] + (0 if plan[-1][4] else 0)
        nf = int(total * FPS)
        ruta = os.path.join(a.salida, f"{g['nombre']}-{n}-{modo}.mp4")
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-preset", "medium",
            "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-vf", "scale=out_color_matrix=bt709", "-movflags", "+faststart", ruta], stdin=subprocess.PIPE)
        for i in range(nf):
            tt = i / FPS
            if modo == "lineas":   # zoom lento del fondo (solo geometría)
                k = 1 + .06 * tt / total; cw, ch = W / k, H / k
                bg = fondo.crop(((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2)).resize((W, H), Image.BICUBIC)
            else: bg = fondo
            capa = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(capa)
            for k_esc, (t0, t1, us, vel, final) in enumerate(plan):
                es_ultima = k_esc == len(plan) - 1
                if tt < t0 or (tt > t1 + .8 and not es_ultima): continue
                salida = 1 if es_ultima else max(0, 1 - (tt - t1) / .8)
                for j, (txt, f, c, x, y) in enumerate(us):
                    ta = t0 + j * VEL[modo] * vel
                    al = min(1, max(0, (tt - ta) / FUNDIDO[modo]))
                    if al <= 0: break
                    dy = (1 - al) ** 2 * 18 if modo == "palabras" else 0
                    d.text((x, y + dy), txt, font=f, features=FEAT, fill=(*c, round(255 * al * salida)))
            img = bg.convert("RGBA"); img.alpha_composite(capa)
            p.stdin.write(img.convert("RGB").tobytes())
            if i == nf - 1: img.convert("RGB").save(ruta.replace(".mp4", "-final.png"))
        p.stdin.close(); p.wait()
        print(f"Variante {n} ({modo}): {ruta}  ({total:.1f} s)")

if __name__ == "__main__":
    main()
