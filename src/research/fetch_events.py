"""
fetch_events.py - Buscador de eventos históricos para Bitácora del Tiempo
Busca eventos del día actual usando Wikipedia API y la base de datos local.
"""

import json
import datetime
import requests
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def get_today():
    """Devuelve mes y día de hoy."""
    today = datetime.date.today()
    return today.month, today.day, today.strftime("%d"), today.strftime("%B")


def get_spanish_month(month_num: int) -> str:
    """Convierte número de mes a nombre en español."""
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    return meses.get(month_num, "")


def load_local_events(month: int, day: int) -> list:
    """Carga eventos de la base de datos local que coincidan con la fecha."""
    events_file = DATA_DIR / "events.json"
    with open(events_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    date_key = f"{month:02d}-{day:02d}"
    matching = [
        e for e in data["events"]
        if e["date"] == date_key
    ]
    return matching


def fetch_wikipedia_events(month: int, day: int) -> list:
    """
    Busca eventos del día en la Wikipedia en español.
    Devuelve lista de eventos con título y descripción.
    """
    month_str = f"{month:02d}"
    day_str = f"{day:02d}"

    # Wikipedia API - Eventos del día
    url = "https://es.wikipedia.org/api/rest_v1/feed/onthisday/events/{}/{}"
    try:
        response = requests.get(
            url.format(month_str, day_str),
            headers={"User-Agent": "BitacoraDelTiempo/1.0"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            events = []
            for item in data.get("events", [])[:10]:  # Top 10 eventos
                events.append({
                    "year": item.get("year"),
                    "title": item.get("text", ""),
                    "pages": [p.get("title", "") for p in item.get("pages", [])[:3]]
                })
            return events
    except Exception as e:
        print(f"Error fetching Wikipedia: {e}")
    return []


def select_best_event(local_events: list, wiki_events: list) -> dict:
    """
    Selecciona el mejor evento para el día.
    Prioriza eventos locales (ya tienen todo el formato).
    """
    if local_events:
        # Usar el evento local si existe
        print(f"✅ Evento local encontrado: {local_events[0]['title']}")
        return {"source": "local", "event": local_events[0]}

    if wiki_events:
        # Usar Wikipedia como respaldo
        print(f"🌐 Usando evento de Wikipedia: {wiki_events[0]['title']}")
        return {"source": "wikipedia", "event": wiki_events[0]}

    return {"source": "none", "event": None}


def save_daily_research(result: dict, month: int, day: int):
    """Guarda el resultado de la búsqueda en un archivo del día."""
    research_dir = BASE_DIR / "src" / "research" / "daily"
    research_dir.mkdir(exist_ok=True)

    filename = research_dir / f"{month:02d}-{day:02d}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"📁 Investigación guardada en: {filename}")
    return filename


def run():
    """Función principal de búsqueda."""
    month, day, day_str, month_eng = get_today()
    month_esp = get_spanish_month(month)

    print(f"\n🗓️ Bitácora del Tiempo - Búsqueda de eventos")
    print(f"📅 Fecha: {day} de {month_esp}")
    print("-" * 50)

    # 1. Buscar en base de datos local
    print("🔍 Buscando en base de datos local...")
    local_events = load_local_events(month, day)

    # 2. Buscar en Wikipedia
    print("🌐 Consultando Wikipedia en español...")
    wiki_events = fetch_wikipedia_events(month, day)

    # 3. Seleccionar el mejor evento
    result = select_best_event(local_events, wiki_events)
    result["date"] = {"month": month, "day": day, "month_name_es": month_esp}
    result["all_wiki_events"] = wiki_events

    # 4. Guardar resultado
    output_file = save_daily_research(result, month, day)

    print("\n✅ Búsqueda completada.")
    if result["event"]:
        print(f"📰 Evento seleccionado: {result['event'].get('title', 'N/A')}")

    return result


if __name__ == "__main__":
    run()
