# Mi entorno de trabajo con IA

Claude lee este archivo al empezar cada sesión. Mantenlo corto: aquí va lo que Claude
necesita saber siempre. El detalle vive en `contexto/`.

## Quién soy
Soy Kwis. Hago marketing con vídeos y fotos para empresas, y también creo contenido propio
para Instagram, TikTok y YouTube. Mi tono: cercano, directo, profesional y con humor.

## Cómo está organizada esta carpeta
- `contexto/` — **Pieza 1: contexto.** Negocio, servicios, clientes, voz de marca.
  - `contexto/negocio.md` — qué hago, oferta, precios, público.
  - `contexto/voz-de-marca.md` — cómo escribo y hablo.
  - `contexto/clientes/` — un archivo por cliente (`nombre-cliente.md`).
- `contenido/` — guiones, reels, publicaciones. Un archivo por pieza: `AAAA-MM-DD-tema.md`.
- `.claude/skills/` — **Pieza 2: capacidades.** Procesos repetibles que Claude sabe hacer.
- `memoria/` — **Pieza 3: memoria.** Decisiones y aprendizajes que deben sobrevivir entre sesiones.
- `.claude/settings.json` — **Pieza 4: reglas.** Permisos que Claude respeta siempre.

## Reglas de trabajo
- Responde en español.
- Antes de escribir contenido o hablar de un cliente, lee `contexto/voz-de-marca.md` y el archivo del cliente.
- Nunca envíes emails ni publiques nada sin mi confirmación.
- Cuando tomemos una decisión importante o aprendas algo de mí, añádelo a `memoria/decisiones.md` o `memoria/aprendizajes.md` (fecha + una línea).
- Si un proceso se repite 3 veces, propón convertirlo en una skill en `.claude/skills/`.
- Al terminar un trabajo, haz commit con un mensaje claro en español.
