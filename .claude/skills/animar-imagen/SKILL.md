---
name: animar-imagen
description: Anima cualquier imagen o logo (zoom, rebote, flotar, giro 3D, latido, revelado…) y entrega SIEMPRE 3 ejemplos distintos sin alterar nunca los colores del logo. Úsala cuando pida animar un logo, una imagen, un intro/outro animado o un logo en movimiento para reels.
---

## Regla de oro
**Los colores del logo no se tocan jamás.** Solo se permiten movimientos (posición, escala,
rotación, recorte, aparición). Prohibido: filtros, tintes, degradados sobre el logo, cambios de
brillo, saturación o tono, y recolorear el fondo "para que combine" si eso modifica el logo.

## Pasos
1. Pide la imagen si no la tengo (PNG con fondo transparente es lo ideal).
2. Si no lo dije, usa formato vertical `1080x1920`, 4 s, fondo `auto` (el de la propia imagen,
   o blanco si es transparente). Pregunta solo si pido algo concreto (cuadrado 1080x1080, horizontal 1920x1080, color de fondo de marca).
3. Ejecuta:
   ```bash
   python3 .claude/skills/animar-imagen/scripts/animar.py RUTA_IMAGEN \
     --salida contenido/animaciones/AAAA-MM-DD-nombre [--estilos a,b,c] \
     [--formato 1080x1920] [--segundos 4] [--fondo auto|#RRGGBB|transparente]
   ```
   Sin `--estilos` elige 3 variados: uno de **entrada** (zoom, rebote, deslizar, rotar, revelar),
   uno de **bucle** (flotar, respirar, giro3d) y uno de **énfasis** (latido, sacudir).
   Si pido otras formas, cambia los estilos, pero siempre exactamente 3.
   **Escritura** (cuando pida que el logo "se escriba", "se forme" o aparezca letra a letra):
   `--estilos escribir,escribir-inverso,escribir-lineas --segundos 5`
   - `escribir`: se dibuja el símbolo y luego las letras una a una.
   - `escribir-inverso`: primero el texto letra a letra y al final el símbolo.
   - `escribir-lineas`: todas las líneas de texto a la vez mientras se dibuja el símbolo.
   Cada letra aparece entera con su color original: no hay fundidos que mezclen colores.
4. Comprueba que la salida dice `VERIFICACIÓN DE COLOR: OK`. Si sale AVISO, no entregues:
   revisa la imagen (bordes semitransparentes, fondo) y repite.
5. Entrega los 3 ejemplos: por cada uno, nombre del estilo, una línea de para qué sirve
   (intro, cierre de reel, story…) y los archivos:
   - `.mp4` → listo para Instagram/TikTok/YouTube.
   - `.mov` → sin pérdida y con transparencia (si fondo transparente), para montar en el editor.
   - `-portada.png` → fotograma fijo para revisar los colores.
6. No publiques nada sin mi confirmación.

## Nota técnica
El MP4 usa H.264 con espacio de color bt709 bien etiquetado y calidad alta (CRF 12) para que las
apps no desplacen los colores; el `.mov` (QuickTime Animation) es RGB sin pérdida: colores exactos al píxel.

## Texto animado sobre un fondo (invitaciones, recordatorios, eventos)
Cuando me pases un fondo + un texto para animar encima:
1. Copia el fondo a `contenido/animaciones/AAAA-MM-DD-tema/fondo.png` y escribe ahí un `guion.json`
   (ver ejemplo en `contenido/animaciones/2026-11-11-recordatorio-eudosia/guion.json`):
   reparte el texto en escenas cortas, nombres importantes con `GreatVibes`, el resto con
   `CormorantGaramond` (fuentes en `fuentes/`). Ajusta `caja` (proporciones x0,y0,x1,y1) a la zona libre del fondo.
2. `python3 .claude/skills/animar-imagen/scripts/animar_texto.py guion.json --salida <carpeta>`
   → 3 variantes: letra a letra, palabra a palabra, línea a línea con zoom lento del fondo.
   Para poner una foto encima (p. ej. retrato arriba), añade al guion `"imagenes": [{"archivo", "centro": [x,y], "alto"}]`.
   Si pido "solo 1 vídeo", usa `--solo palabras` (o el modo que pida): mi petición manda sobre la regla de 3.
3. El fondo no cambia de color nunca. Respeta el texto tal como lo dicto; si veo una posible errata
   (tildes, nombres), pregúntamelo en vez de corregirlo por mi cuenta.

### Mejorar un fondo pequeño o borroso
Si el fondo es pequeño (menos de 1080 px de ancho), mejóralo antes con superresolución:
`pip install opencv-contrib-python-headless`, descarga `EDSR_x4.pb`
(github.com/Saafke/EDSR_Tensorflow, carpeta models), `cv2.dnn_superres` x4 → redimensiona a 1080x1920 → enfoque suave
(unsharp: 1.35·img − 0.35·desenfoque σ=2). Mantiene los colores. Avisa de que no hace milagros con originales muy pequeños.
Para recortar retratos ovalados sobre fondo oscuro: umbral de brillo → caja del óvalo → máscara elíptica suavizada.

### Música (cuando pida sonido)
`python3 .claude/skills/animar-imagen/scripts/musica.py salida.wav --segundos N --estilo piano-arpegio|piano-acordes|guitarra`
Música original sintetizada (La m–Fa–Do–Sol, 66 bpm, tono sereno). Únela al vídeo con ffmpeg
(`-c:v copy -c:a aac -b:a 192k`, `afade` de salida en los últimos 3 s, `-t` = duración del vídeo).
Con 3 vídeos, pon un estilo distinto a cada uno. Si el fondo no es 9:16, usa su proporción en `formato` para no deformarlo.
