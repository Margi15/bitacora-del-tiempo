"""
generate_scripts.py - Generador de guiones para Bitácora del Tiempo
Crea guiones para YouTube Shorts y Videos largos usando plantillas.
"""

import json
import datetime
import anthropic
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "src" / "scripts" / "daily"
SHORTS_DIR = BASE_DIR / "src" / "shorts"
VIDEOS_DIR = BASE_DIR / "src" / "videos"


def load_templates() -> dict:
    """Carga las plantillas de guiones."""
    with open(DATA_DIR / "templates.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_daily_research(month: int, day: int) -> dict:
    """Carga la investigación del día."""
    research_file = BASE_DIR / "src" / "research" / "daily" / f"{month:02d}-{day:02d}.json"
    if not research_file.exists():
        raise FileNotFoundError(f"No hay investigación para {month:02d}-{day:02d}. Ejecuta fetch_events.py primero.")
    with open(research_file, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_short_script_with_claude(event: dict, templates: dict, month_name: str) -> str:
    """Usa la API de Claude para generar un guion de Short personalizado."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    short_template = templates["short_template"]

    prompt = f"""Eres el guionista del canal de YouTube "Bitácora del Tiempo", especializado en historia.

Crea un guion para un YouTube Short (30-60 segundos) sobre este evento histórico:

EVENTO: {event.get('title', '')}
FECHA: {event.get('day', '')} de {month_name} de {event.get('year', '')}
DESCRIPCIÓN CORTA: {event.get('short_desc', '')}
DESCRIPCIÓN LARGA: {event.get('long_desc', '')}
DATO CURIOSO: {event.get('fun_fact', '')}
EMOCIÓN: {event.get('emotion', 'impactante')}

ESTRUCTURA OBLIGATORIA:
1. HOOK (0-5 seg): Pregunta sorprendente que empiece con "¿Sabías que..."
2. CONTEXTO (5-25 seg): 3 frases cortas e impactantes (máx 15 palabras cada una)
3. DATO IMPACTANTE (25-35 seg): El dato más sorprendente del evento
4. CTA (35-40 seg): "Suscríbete 🔔 para más historias que la escuela no te enseñó"

REGLAS:
- Lenguaje coloquial pero educado, como si le hablaras a un amigo
- Máxima emoción y drama apropiado al evento
- Incluir emojis relevantes
- El español debe ser neutro (para toda Latinoamérica y España)
- Máximo 150 palabras en total

Devuelve SOLO el guion con los títulos de sección claramente marcados."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_long_script_with_claude(event: dict, templates: dict, month_name: str) -> str:
    """Usa Claude para generar un guion de video largo (5-10 minutos)."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = f"""Eres el guionista senior del canal de YouTube "Bitácora del Tiempo",
especializado en hacer historia entretenida y accesible.

Crea un guion detallado para un video de YouTube de 5-10 minutos sobre este evento:

EVENTO: {event.get('title', '')}
FECHA: {event.get('day', '')} de {month_name} de {event.get('year', '')}
DESCRIPCIÓN CORTA: {event.get('short_desc', '')}
DESCRIPCIÓN COMPLETA: {event.get('long_desc', '')}
DATO CURIOSO: {event.get('fun_fact', '')}
CATEGORÍA: {event.get('category', '')}
REGIÓN: {event.get('region', '')}
EMOCIÓN CLAVE: {event.get('emotion', 'impactante')}

ESTRUCTURA OBLIGATORIA (incluye timestamps aproximados):
00:00 - INTRO/HOOK (30 seg): Arranque impactante con el gancho del evento
00:30 - CONTEXTO HISTÓRICO (2-3 min): El mundo antes del evento, causas, actores
03:00 - EL EVENTO DEL DÍA (3-5 min): Descripción detallada, cronología, testimonios
07:00 - CONSECUENCIAS (1-2 min): Impacto inmediato y a largo plazo
08:30 - EL DATO SECRETO (60 seg): El dato que nadie sabe
09:30 - OUTRO/CTA (30 seg): Despedida y llamado a suscribirse

REGLAS:
- Narrativa cinematográfica: como si fuera un documental de Netflix
- Incluye notas de dirección entre [corchetes] para el editor
- Lenguaje accesible pero apasionado
- Español neutro latinoamericano
- Incluir preguntas retóricas para mantener al espectador enganchado
- Al menos una frase por minuto que haga que el espectador quiera seguir viendo

Devuelve el guion completo con todas las secciones claramente marcadas."""

    message = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text


def generate_fallback_short_script(event: dict, templates: dict, month_name: str) -> str:
    """Genera guion de Short usando plantillas (sin API de Claude)."""
    template = templates["short_template"]["full_script_template"]

    context_lines = event.get("long_desc", "").split(". ")
    c1 = context_lines[0] + "." if len(context_lines) > 0 else ""
    c2 = context_lines[1] + "." if len(context_lines) > 1 else ""
    c3 = context_lines[2] + "." if len(context_lines) > 2 else ""

    script = template.replace("{day}", str(event.get("day", "")))
    script = script.replace("{month_name}", month_name)
    script = script.replace("{year}", str(event.get("year", "")))
    script = script.replace("{short_desc}", event.get("short_desc", ""))
    script = script.replace("{hook_emoji}", event.get("hashtags", [""])[0] if event.get("hashtags") else "")
    script = script.replace("{context_line_1}", c1)
    script = script.replace("{context_line_2}", c2)
    script = script.replace("{context_line_3}", c3)
    script = script.replace("{fun_fact}", event.get("fun_fact", ""))

    return script


def save_script(content: str, script_type: str, month: int, day: int) -> Path:
    """Guarda un guion generado."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)

    filename = SCRIPTS_DIR / f"{month:02d}-{day:02d}_{script_type}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"💾 Guion guardado: {filename}")
    return filename


def generate_caption(event: dict, script_type: str, templates: dict, month_name: str) -> str:
    """Genera el caption/descripción para YouTube."""
    if script_type == "short":
        tmpl = templates["caption_templates"]["short_caption"]["template"]
    else:
        tmpl = templates["caption_templates"]["long_caption"]["template"]

    long_desc = event.get("long_desc", "")
    sentences = long_desc.split(". ")
    para1 = ". ".join(sentences[:3]) + "." if len(sentences) >= 3 else long_desc
    para2 = ". ".join(sentences[3:6]) + "." if len(sentences) >= 6 else ""

    caption = tmpl.replace("{day}", str(event.get("day", "")))
    caption = caption.replace("{month_name}", month_name)
    caption = caption.replace("{year}", str(event.get("year", "")))
    caption = caption.replace("{short_desc}", event.get("short_desc", ""))
    caption = caption.replace("{hook_emoji}", "🗓️")
    caption = caption.replace("{fun_fact}", event.get("fun_fact", ""))
    caption = caption.replace("{long_desc_paragraph_1}", para1)
    caption = caption.replace("{long_desc_paragraph_2}", para2)
    caption = caption.replace("{hashtags}", " ".join(event.get("hashtags", [])))

    return caption


def run():
    """Función principal de generación de guiones."""
    today = datetime.date.today()
    month = today.month
    day = today.day

    meses_esp = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    month_name = meses_esp[month]

    print(f"\n📝 Bitácora del Tiempo - Generador de Guiones")
    print(f"📅 Fecha: {day} de {month_name}")
    print("-" * 50)

    # 1. Cargar datos
    templates = load_templates()
    try:
        research = load_daily_research(month, day)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    event = research.get("event")
    if not event:
        print("❌ No se encontró evento para hoy.")
        return

    # 2. Generar guion de Short
    print("\n🎬 Generando guion de YouTube Short...")
    use_claude = bool(os.environ.get("ANTHROPIC_API_KEY"))

    if use_claude:
        short_script = generate_short_script_with_claude(event, templates, month_name)
        long_script = generate_long_script_with_claude(event, templates, month_name)
    else:
        print("⚠️  Sin API key de Claude, usando plantillas locales")
        short_script = generate_fallback_short_script(event, templates, month_name)
        long_script = f"[Video largo - Configura ANTHROPIC_API_KEY para generación automática]\n\nEvento: {event.get('title')}\n\n{event.get('long_desc')}"

    # 3. Guardar guiones
    save_script(short_script, "short", month, day)
    save_script(long_script, "long_video", month, day)

    # 4. Generar captions
    print("\n📋 Generando captions...")
    short_caption = generate_caption(event, "short", templates, month_name)
    long_caption = generate_caption(event, "long", templates, month_name)

    captions_dir = BASE_DIR / "src" / "captions"
    captions_dir.mkdir(exist_ok=True)
    with open(captions_dir / f"{month:02d}-{day:02d}_short.txt", "w", encoding="utf-8") as f:
        f.write(short_caption)
    with open(captions_dir / f"{month:02d}-{day:02d}_long.txt", "w", encoding="utf-8") as f:
        f.write(long_caption)

    print(f"\n✅ Guiones generados exitosamente.")
    print(f"   📱 Short: src/scripts/daily/{month:02d}-{day:02d}_short.txt")
    print(f"   🎥 Video largo: src/scripts/daily/{month:02d}-{day:02d}_long_video.txt")
    print(f"   📋 Captions: src/captions/{month:02d}-{day:02d}_*.txt")


if __name__ == "__main__":
    run()
