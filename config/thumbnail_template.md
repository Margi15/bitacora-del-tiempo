# 🖼️ Template de Thumbnails — Bitácora del Tiempo

## Estilo Recomendado: DORADO ÉPICO (CTR 9.3/10)

---

## SHORTS (1080×1920) — Estilo Dorado Épico

### Paleta de colores
- Fondo: `#0d0a00` (negro cálido)
- Acento principal: `#F7C75A` (dorado)
- Acento secundario: `#8B6914` (ámbar oscuro)
- Texto: `#FFFFFF` (blanco)
- Alerta: `#C0392B` (rojo)

### Estructura de la imagen
```
┌─────────────────────────┐
│  📅 UN DÍA COMO HOY    │  ← Header dorado, 7px, tracking 2px
│                         │
│                         │
│        [IMAGEN]         │  ← Evento histórico (buscar en Wikimedia Commons)
│                         │
│  ━━━━━━━━━━━━━━━━━━━━  │  ← Línea separadora dorada
│        1 9 4 0          │  ← AÑO en grande, #F7C75A, 120px
│   CAÍDA DE PARIS        │  ← Título, blanco, 60px, MAYÚSCULAS
│      ¿Lo sabías?        │  ← Hook, dorado pequeño, 30px
│                         │
└─────────────────────────┘
```

### Prompt para Midjourney / DALL-E 3
```
Create a vertical YouTube Shorts thumbnail (1080x1920 pixels) for historical event: "{TITULO_EVENTO}" ({AÑO}).

Background: very dark warm black (#0d0a00), cinematic atmosphere.
At top: small golden badge text "UN DÍA COMO HOY" in Spanish.
Center: dramatic photorealistic scene or iconic symbol of the event, 
       moody cinematic lighting, golden hour tones, epic scale.
       NO text overlay on the image itself.
Gold decorative line separator.
Bottom area: space reserved for text overlay.

Style: cinematic documentary, dramatic shadows, gold and amber color grading,
       ultra high resolution, 8K quality, professional photography.
Mood: epic, historical, powerful.
NO watermarks, NO logos, NO text in the image (text will be added separately).
```

### Instrucciones Canva (paso a paso)
1. Nuevo diseño → `1080 × 1920 px`
2. Fondo: color `#0d0a00`
3. Buscar imagen del evento en **Unsplash** o **Wikimedia Commons**
4. Insertar imagen, cubrir pantalla completa
5. Overlay: rectángulo negro con **opacidad 65%**, tamaño completo
6. Overlay 2: rectángulo dorado (`#F7C75A`) con **opacidad 15%** en zona inferior
7. Texto superior: `"📅 UN DÍA COMO HOY"` — Montserrat SemiBold, 40px, `#F7C75A`, centrado
8. Línea: rectángulo delgado `#F7C75A`, 600px × 3px, centrado
9. Año: `"1 9 4 0"` — Montserrat Black, 160px, `#F7C75A`, centrado (espaciado de letra +50)
10. Título: `"CAÍDA DE PARIS"` — Montserrat Black, 80px, `#FFFFFF`, centrado
11. Hook: `"¿Lo sabías?"` — Montserrat Light Italic, 45px, `#F7C75A`, centrado
12. Exportar: PNG, 1080×1920

---

## VIDEOS LARGOS (1280×720) — Estilo Imagen de Fondo Full Bleed

### Estructura
```
┌─────────────────────────────────────────┐
│  🔴 UN DÍA COMO HOY    [esquina sup.]  │
│                                         │
│         [IMAGEN HISTÓRICA               │
│          FULL BLEED CON                 │
│          OVERLAY OSCURO 60%]            │
│                                         │
│  PARIS CAE ANTE LOS NAZIS              │ ← Texto blanco bold, sombra
│  ─────────────────                      │ ← Línea dorada 300px
│  14 DE JUNIO, 1940                      │ ← Fecha dorada pequeña
└─────────────────────────────────────────┘
  ↑ Imagen histórica de fondo en todo el ancho
  Texto en la mitad inferior con overlay oscuro
```

### Prompt para Midjourney / DALL-E 3
```
Create a horizontal YouTube thumbnail (1280x720 pixels) for: "{TITULO_EVENTO}" ({AÑO}).

FULL BLEED: Dramatic photorealistic historical scene filling the entire canvas.
Cinematic golden hour lighting, moody documentary atmosphere.
Strong dark vignette on lower third where text will be overlaid.
Top area: slightly darker for date badge overlay.

Overall style: documentary, cinematic, gold and amber tones, epic scale.
Ultra detailed, 8K quality, photorealistic historical photography style.
NO text anywhere in the image.
```

### Instrucciones Canva (paso a paso)
1. Nuevo diseño → `1280 × 720 px`
2. Buscar imagen histórica del evento en **Unsplash** o **Wikimedia Commons**
3. Insertar imagen → **cubrir todo el canvas** (ajustar a pantalla completa)
4. Overlay: rectángulo negro, opacidad **60%**, tamaño completo
5. Overlay extra: rectángulo negro, opacidad **80%** solo en el **tercio inferior** (para el texto)
6. Badge superior izq.: rectángulo `#C0392B` pequeño + texto `"UN DÍA COMO HOY"` blanco Montserrat Bold 18px
7. Título: máximo 5 palabras MAYÚSCULAS — Montserrat Black, 72px, `#FFFFFF`, con sombra
8. Línea dorada: `#F7C75A`, 2px de alto, 300px de ancho, bajo el título
9. Fecha: `"14 DE JUNIO, 1940"` — Montserrat SemiBold, 28px, `#F7C75A`
10. Exportar: PNG, 1280×720

---

## TEMPLATE VARIABLES (reemplazar por evento del día)

| Variable | Descripción | Ejemplo |
|---|---|---|
| `{TITULO_EVENTO}` | Título del evento (max 4 palabras) | "Caída de París" |
| `{AÑO}` | Año del evento | 1940 |
| `{DIA}` | Día del mes | 14 |
| `{MES_NOMBRE}` | Nombre del mes en español | JUNIO |
| `{FECHA_COMPLETA}` | Fecha formateada | 14 JUN 1940 |
| `{HOOK}` | Pregunta de curiosidad | "¿Lo sabías?" |
| `{EMOJI}` | Emoji representativo | 🏛️ ⚔️ 🚀 💥 |

---

## GUÍA RÁPIDA: Elegir el estilo según el evento

| Tipo de evento | Estilo recomendado | Colores |
|---|---|---|
| Guerras / invasiones | Dorado Épico | negro + dorado |
| Descubrimientos / logros | Choque Viral | negro + amarillo |
| Desastres naturales | Azul Dramático | azul + blanco |
| Revoluciones / caídas | Rojo Impacto | rojo + negro |
| Misterios / datos ocultos | Misterio Oscuro | negro + rojo oscuro |

---

## PROMPT UNIVERSAL (copiar y adaptar)

```
YouTube thumbnail for: "{TITULO_EVENTO}" ({AÑO}).
Style: dramatic, cinematic, high contrast.
Colors: dark background, {COLOR_PRINCIPAL} accents.
Mood: {EMOCION} (epic/tragic/triumphant/mysterious).
Composition: central focal point, dramatic lighting, documentary photography.
Text space: reserved at top for date, bottom for title.
Quality: 8K, ultra-detailed, professional.
```

---

*Generado para Bitácora del Tiempo (@BitácoraDelTiempoo)*
