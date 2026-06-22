"""
script_writer.py — Guiones virales con Gemini Flash
Hooks de tensión, pausas [PAUSA], CTA que invite a comentar.
"""

import os
import json
import random
import requests
import datetime
import logging
from typing import Optional

log = logging.getLogger(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

HOOK_STYLES = [
    "tensión_narrativa",   # "Nadie lo vio venir..."
    "dato_imposible",      # "Lo que nadie te contó..."
    "pregunta_provocadora",# "¿Y si te dijera que...?"
    "escena_vívida",       # Descripción sensorial del momento
    "contradicción",       # "El héroe era el villano"
    "número_impactante",   # "En 72 horas todo cambió"
    "nombre_propio",       # Arranca con el protagonista haciendo algo
    "final_primero",       # Revela el final, luego explica
    "comparación_actual",  # Conecta con algo que el espectador conoce
    "secreto_revelado",    # "Esto se mantuvo oculto por décadas"
]

SYSTEM_PROMPT = """Eres el guionista viral más efectivo de YouTube Shorts en español latino.
Tu especialidad: historias históricas que generan 90%+ de retención.

REGLAS ABSOLUTAS:
1. NUNCA empieces con la fecha: "El 22 de junio de 1978..." → PROHIBIDO
2. SIEMPRE arranca con tensión narrativa, pregunta o imagen mental
3. Usa [PAUSA] donde el oyente necesita un momento para asimilar
4. Usa [SUSPENSO] antes de revelar datos impactantes
5. El CTA al final pide una OPINIÓN o REACCIÓN, nunca "suscríbete"
6. Duración exacta: 55-60 segundos a velocidad 1.1x (≈145 palabras en español)
7. Sin emojis en el guion de narración
8. Tono: conversacional, íntimo, como si contaras un secreto

ESTRUCTURA:
- Hook (5s): imagen mental o pregunta que engancha
- Contexto (10s): quién, dónde, situación real
- Giro (20s): el evento histórico con detalles sensoriales
- Impacto (15s): qué cambió para siempre en el mundo
- CTA (8s): pregunta que invita a comentar
"""

def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY no configurada")
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.85,
            "maxOutputTokens": 1024,
            "topP": 0.95,
        },
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
    }
    
    r = requests.post(
        f"{GEMINI_URL}?key={GEMINI_API_KEY}",
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    
    candidates = data.get("candidates", [])
    if not candidates:
        raise ValueError(f"Gemini sin candidatos: {data}")
    
    text = candidates[0]["content"]["parts"][0]["text"]
    return text.strip()


def _get_historical_event(event_date: Optional[str] = None) -> dict:
    """Obtiene evento histórico de Wikipedia 'On This Day'."""
    if event_date:
        dt = datetime.datetime.strptime(event_date, "%Y-%m-%d")
    else:
        dt = datetime.datetime.utcnow()
    
    month, day = dt.month, dt.day
    url = f"https://en.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}"
    headers = {"User-Agent": "BitacoraBot/2.0 (kuralens.official@gmail.com)", "Accept": "application/json"}
    
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    events = r.json().get("events", [])
    
    if not events:
        raise ValueError(f"Sin eventos para {month}/{day}")
    
    # Preferir eventos con imágenes
    with_images = [e for e in events if e.get("pages") and 
                   any(p.get("originalimage") for p in e["pages"])]
    pool = with_images if with_images else events
    
    # Preferir eventos más impactantes (historia > 50 años)
    old_events = [e for e in pool if e.get("year", 9999) <= 1980]
    chosen = random.choice(old_events if old_events else pool)
    
    page = chosen["pages"][0] if chosen.get("pages") else {}
    img_url = None
    if page.get("originalimage"):
        img_url = page["originalimage"]["source"]
    
    return {
        "year": chosen.get("year"),
        "text": chosen.get("text", ""),
        "title": page.get("title", "").replace("_", " "),
        "extract": page.get("extract", ""),
        "image_url": img_url,
        "month": month,
        "day": day,
    }


def _generate_script(event: dict, style: str) -> dict:
    """Genera guion viral para el evento dado."""
    prompt = f"""Evento histórico:
Año: {event['year']}
Tema: {event['text']}
Título: {event['title']}
Contexto: {event['extract'][:500]}
Fecha: {event['month']}/{event['day']}

Estilo de hook: {style}

Genera un guion para YouTube Shorts siguiendo exactamente la estructura. 
Responde en JSON con estos campos:
{{
  "hook": "primeras 2-3 oraciones que enganchan (sin fecha)",
  "narration": "guion completo de 140-150 palabras con [PAUSA] y [SUSPENSO]",
  "cta": "pregunta final que invita a comentar",
  "yt_title": "título YouTube ≤70 chars con emoji inicial",
  "yt_description": "descripción 150 palabras con hashtags al final",
  "tags": ["tag1","tag2","tag3","tag4","tag5","tag6","tag7"],
  "image_query": "término de búsqueda en inglés para Wikimedia Commons",
  "fb_caption": "caption para Facebook 2-3 oraciones + pregunta + hashtags"
}}

El campo "narration" debe tener exactamente 140-155 palabras. Verifica el conteo."""
    
    raw = _call_gemini(prompt)
    
    # Extraer JSON
    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]
    
    data = json.loads(raw.strip())
    data["year"] = event["year"]
    data["title"] = event["title"]
    data["event_image_url"] = event.get("image_url")
    
    return data


def generate_script_and_metadata(event_date=None) -> dict:
    """Punto de entrada principal. Retorna todo lo necesario para el pipeline."""
    event = _get_historical_event(event_date)
    style = random.choice(HOOK_STYLES)
    
    last_error = None
    for attempt in range(3):
        try:
            script = _generate_script(event, style)
            log.info(f"Guion generado: estilo={style} año={event['year']}")
            return script
        except json.JSONDecodeError as e:
            log.warning(f"JSON parse error intento {attempt+1}: {e}")
            last_error = e
        except Exception as e:
            log.warning(f"Error guion intento {attempt+1}: {e}")
            last_error = e
    
    # Fallback hardcoded
    log.error(f"Fallback hardcoded. Último error: {last_error}")
    return _hardcoded_fallback(event)


def _hardcoded_fallback(event: dict) -> dict:
    year = event.get("year", "????")
    title = event.get("title", "Evento histórico")
    text = event.get("text", title)
    
    narration = (
        f"Nadie lo sabía. [PAUSA] Mientras el mundo seguía su rutina, "
        f"algo estaba a punto de cambiar todo. [SUSPENSO] "
        f"En {year}, {text}. "
        f"Lo que ocurrió después no estaba en ningún libro de historia. "
        f"Este momento redefinió lo que creíamos posible. "
        f"Hoy, décadas después, todavía sentimos sus consecuencias. "
        f"¿Lo sabías? Comenta qué te enseñaron sobre esto."
    )
    
    return {
        "year": year,
        "title": title,
        "hook": f"Nadie lo sabía. Mientras el mundo seguía su rutina...",
        "narration": narration,
        "cta": "¿Lo sabías? Comenta qué te enseñaron sobre esto.",
        "yt_title": f"🕰️ {year}: {title[:50]}",
        "yt_description": (
            f"En {year}, {text}\n\n"
            "Bitácora del Tiempo — Historia que nadie te contó.\n\n"
            "#historia #curiosidades #shorts #bitacoradeltiempo"
        ),
        "tags": ["historia", "curiosidades", "shorts", "efemérides", "viral", title.lower(), str(year)],
        "image_query": title,
        "event_image_url": event.get("image_url"),
        "fb_caption": f"¿Sabías que en {year} ocurrió esto? {text} 👇 Comenta.",
    }
