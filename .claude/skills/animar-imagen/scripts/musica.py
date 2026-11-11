#!/usr/bin/env python3
"""Genera música instrumental suave y original (piano o guitarra sintetizados) para animaciones.

Uso: python3 musica.py salida.wav --segundos 36 --estilo piano-arpegio|piano-acordes|guitarra
Progresión tranquila y emotiva (La menor - Fa - Do - Sol), 66 bpm, con reverberación y fundido final.
"""
import argparse, wave
import numpy as np

SR = 44100
def nota(n): return 440 * 2 ** ((n - 69) / 12)   # número MIDI -> Hz

def piano(f, dur, vel=.5):
    t = np.arange(int(SR * dur)) / SR; s = np.zeros_like(t)
    for k, amp in enumerate([1, .45, .25, .12, .07, .04], 1):
        fk = f * k * np.sqrt(1 + .0004 * k * k)               # leve inarmonicidad de cuerda
        s += amp * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.2 + k * .9))
    ataque = np.minimum(1, t / .005)
    return vel * s * ataque

def guitarra(f, dur, vel=.5):                                  # Karplus-Strong (cuerda pulsada)
    n = int(SR * dur); p = int(SR / f)
    buf = np.random.uniform(-1, 1, p); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = .996 * .5 * (buf[i % p] + buf[(i + 1) % p])
    return vel * out

PROG = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]   # Am F C G
BAJOS = [45, 41, 36, 43]
MELODIA = [76, 74, 72, 71, 72, None, 69, 72, 74, 76, 74, None, 72, 71, 69, None]

def componer(estilo, segundos):
    beat = 60 / 66; L = int(SR * (segundos + 4)); mix = np.zeros(L)
    def poner(s, t):
        i = int(t * SR); j = min(L, i + len(s)); mix[i:j] += s[:j - i]
    inst = guitarra if estilo == "guitarra" else piano
    t, c = .2, 0
    while t < segundos:
        acorde = PROG[c % 4]; bajo = BAJOS[c % 4]
        poner(inst(nota(bajo), 4, .55), t)
        if estilo == "piano-acordes":
            for n in acorde: poner(piano(nota(n + 12), 4, .22), t + .02)
            m = MELODIA[(c * 2) % 16], MELODIA[(c * 2 + 1) % 16]
            for k, n in enumerate(m):
                if n: poner(piano(nota(n), 3, .3), t + k * 2 * beat)
        else:
            patron = [0, 1, 2, 1, 0 + 12 - 12, 2, 1, 2] if estilo == "guitarra" else [0, 1, 2, 1 + 3, 2, 1, 2 + 3, 1]
            arp = acorde + [n + 12 for n in acorde]
            for k in range(8):
                idx = patron[k] % len(arp)
                poner(inst(nota(arp[idx] + (12 if estilo != "guitarra" else 0)), 3, .2), t + k * beat / 2)
        t += 4 * beat; c += 1
    # Reverberación: convolución con cola de ruido decreciente
    ir_t = np.arange(int(SR * 2.2)) / SR
    ir = np.random.randn(len(ir_t)) * np.exp(-ir_t * 3); ir[0] = 1
    nfft = 1 << int(np.ceil(np.log2(L + len(ir))))
    wet = np.fft.irfft(np.fft.rfft(mix, nfft) * np.fft.rfft(ir, nfft), nfft)[:L]
    out = mix * .7 + wet / np.max(np.abs(wet)) * np.max(np.abs(mix)) * .35
    out = out[:int(SR * segundos)]
    fade = int(SR * 3); out[-fade:] *= np.linspace(1, 0, fade)
    out[:int(SR * .5)] *= np.linspace(0, 1, int(SR * .5))
    return out / np.max(np.abs(out)) * .8

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("salida")
    ap.add_argument("--segundos", type=float, required=True)
    ap.add_argument("--estilo", default="piano-arpegio", choices=["piano-arpegio", "piano-acordes", "guitarra"])
    a = ap.parse_args()
    s = componer(a.estilo, a.segundos)
    est = np.stack([s, np.roll(s, 220) * .95], 1)            # estéreo suave
    with wave.open(a.salida, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((est * 32767).astype(np.int16).tobytes())

if __name__ == "__main__":
    main()
