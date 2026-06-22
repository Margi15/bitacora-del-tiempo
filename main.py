"""
main.py - Orquestador principal de Bitácora del Tiempo
Ejecuta el flujo completo diario: investigación → guiones → captions → thumbnails

USO:
  python main.py              # Ejecutar flujo completo del día
  python main.py --step 1     # Solo investigación
  python main.py --step 2     # Solo generar guiones
  python main.py --step 3     # Solo captions
  python main.py --date 06-14 # Ejecutar para una fecha específica
  python main.py --list       # Ver eventos en la base de datos
"""

import argparse
import datetime
import json
import sys
import os
from pathlib import Path

# Agregar src al path
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR / "src"))


def print_banner():
    print("""
╔══════════════════════════════════════════╗
║       🗓️  BITÁCORA DEL TIEMPO           ║
║    Canal de YouTube Automatizado         ║
║    Historia diaria en video              ║
╚══════════════════════════════════════════╝
    """)


def step_1_research(month: int, day: int):
    """Paso 1: Buscar eventos históricos."""
    print("\n" + "=" * 50)
    print("PASO 1: 🔍 Investigación de eventos históricos")
    print("=" * 50)
    from research.fetch_events import run
    return run()


def step_2_scripts(month: int, day: int):
    """Paso 2: Generar guiones."""
    print("\n" + "=" * 50)
    print("PASO 2: 📝 Generación de guiones")
    print("=" * 50)
    from scripts.generate_scripts import run
    return run()


def step_3_thumbnails_prompts(month: int, day: int):
    """Paso 3: Generar prompts para thumbnails."""
    print("\n" + "=" * 50)
    print("PASO 3: 🖼️  Prompts para thumbnails")
    print("=" * 50)

    research_file = BASE_DIR / "src" / "research" / "daily" / f"{month:02d}-{day:02d}.json"
    if not research_file.exists():
        print("❌ No hay investigación. Ejecuta el Paso 1 primero.")
        return

    with open(research_file, "r", encoding="utf-8") as f:
        research = json.load(f)

    event = research.get("event")
    if not event:
        print("❌ Sin evento para hoy.")
        return

    # Cargar configuración de prompts de thumbnails
    config_file = BASE_DIR / "config" / "thumbnail_prompts.json"
    with open(config_file, "r", encoding="utf-8") as f:
        thumb_config = json.load(f)

    style = event.get("thumbnail_style", "dramatic_historical")
    base_prompt = thumb_config["styles"].get(style, thumb_config["styles"]["dramatic_historical"])

    short_prompt = thumb_config["short_prompt_template"].format(
        base_style=base_prompt,
        title=event.get("title", ""),
        year=event.get("year", ""),
        emotion=event.get("emotion", "impactante"),
        day=event.get("day", ""),
        month_name=research.get("date", {}).get("month_name_es", "")
    )

    long_prompt = thumb_config["long_prompt_template"].format(
        base_style=base_prompt,
        title=event.get("title", ""),
        year=event.get("year", ""),
        emotion=event.get("emotion", "impactante"),
        day=event.get("day", ""),
        month_name=research.get("date", {}).get("month_name_es", "")
    )

    # Guardar prompts
    thumbs_dir = BASE_DIR / "src" / "thumbnails"
    thumbs_dir.mkdir(exist_ok=True)

    with open(thumbs_dir / f"{month:02d}-{day:02d}_short_prompt.txt", "w", encoding="utf-8") as f:
        f.write(f"PROMPT PARA THUMBNAIL DE SHORT:\n\n{short_prompt}")

    with open(thumbs_dir / f"{month:02d}-{day:02d}_long_prompt.txt", "w", encoding="utf-8") as f:
        f.write(f"PROMPT PARA THUMBNAIL DE VIDEO LARGO:\n\n{long_prompt}")

    print(f"✅ Prompts de thumbnail guardados en src/thumbnails/")
    print(f"\n📱 SHORT (1080x1920):\n{short_prompt[:200]}...")
    print(f"\n🎥 VIDEO LARGO (1280x720):\n{long_prompt[:200]}...")


def step_4_youtube_upload_info(month: int, day: int):
    """Paso 4: Mostrar información para publicación en YouTube."""
    print("\n" + "=" * 50)
    print("PASO 4: 📤 Información para publicación en YouTube")
    print("=" * 50)

    meses_esp = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril",
        5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
        9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }

    captions_dir = BASE_DIR / "src" / "captions"
    short_caption_file = captions_dir / f"{month:02d}-{day:02d}_short.txt"
    long_caption_file = captions_dir / f"{month:02d}-{day:02d}_long.txt"

    print("\n📋 CHECKLIST DE PUBLICACIÓN:")
    print("-" * 40)

    # Short (9:00 AM)
    print("\n🕘 09:00 AM - YouTube Short:")
    print("   ✅ Formato: vertical 9:16 (1080x1920)")
    print("   ✅ Duración: 30-60 segundos")
    if short_caption_file.exists():
        print(f"   ✅ Caption: {short_caption_file}")
    else:
        print("   ❌ Caption no generado aún")
    thumb_short = BASE_DIR / "src" / "thumbnails" / f"{month:02d}-{day:02d}_short_prompt.txt"
    if thumb_short.exists():
        print(f"   ✅ Thumbnail prompt: {thumb_short}")

    # Video largo (12:00 PM)
    print("\n🕛 12:00 PM - Video largo:")
    print("   ✅ Formato: horizontal 16:9 (1280x720)")
    print("   ✅ Duración: 5-10 minutos")
    if long_caption_file.exists():
        print(f"   ✅ Caption: {long_caption_file}")
    else:
        print("   ❌ Caption no generado aún")

    # Config de YouTube
    config_file = BASE_DIR / "config" / "youtube.json"
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            yt_config = json.load(f)
        print(f"\n🎯 Canal configurado: {yt_config.get('channel_name', 'N/A')}")
        print(f"   API configurada: {'✅ Sí' if yt_config.get('api_key') != 'TU_API_KEY_AQUI' else '❌ Pendiente'}")


def list_events():
    """Lista todos los eventos en la base de datos."""
    events_file = BASE_DIR / "data" / "events.json"
    with open(events_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"\n📚 BASE DE DATOS - {data['metadata']['total_events']} eventos:\n")
    for event in data["events"]:
        print(f"  [{event['date']}] {event['year']} - {event['title']}")
        print(f"          Categoría: {event['category']} | Impacto: {event['impact']}")
        print()


def run_full_flow(month: int, day: int):
    """Ejecuta el flujo completo."""
    print_banner()
    print(f"🗓️  Ejecutando flujo para: {day:02d}/{month:02d}")

    step_1_research(month, day)
    step_2_scripts(month, day)
    step_3_thumbnails_prompts(month, day)
    step_4_youtube_upload_info(month, day)

    print("\n" + "=" * 50)
    print("✅ FLUJO COMPLETO FINALIZADO")
    print("=" * 50)
    print("\n📁 Archivos generados:")
    print(f"  • src/research/daily/{month:02d}-{day:02d}.json")
    print(f"  • src/scripts/daily/{month:02d}-{day:02d}_short.txt")
    print(f"  • src/scripts/daily/{month:02d}-{day:02d}_long_video.txt")
    print(f"  • src/captions/{month:02d}-{day:02d}_short.txt")
    print(f"  • src/captions/{month:02d}-{day:02d}_long.txt")
    print(f"  • src/thumbnails/{month:02d}-{day:02d}_short_prompt.txt")
    print(f"  • src/thumbnails/{month:02d}-{day:02d}_long_prompt.txt")
    print("\n🎬 ¡Listo para crear los videos!")


def main():
    parser = argparse.ArgumentParser(
        description="Bitácora del Tiempo - Sistema automatizado de videos de historia"
    )
    parser.add_argument("--step", type=int, choices=[1, 2, 3, 4],
                        help="Ejecutar solo un paso específico")
    parser.add_argument("--date", type=str,
                        help="Fecha específica en formato MM-DD (ej: 06-14)")
    parser.add_argument("--list", action="store_true",
                        help="Listar todos los eventos en la base de datos")

    args = parser.parse_args()

    # Listar eventos
    if args.list:
        list_events()
        return

    # Parsear fecha
    if args.date:
        try:
            parts = args.date.split("-")
            month, day = int(parts[0]), int(parts[1])
        except Exception:
            print("❌ Formato de fecha inválido. Usa MM-DD (ej: 06-14)")
            sys.exit(1)
    else:
        today = datetime.date.today()
        month, day = today.month, today.day

    # Ejecutar paso específico o flujo completo
    if args.step == 1:
        print_banner()
        step_1_research(month, day)
    elif args.step == 2:
        print_banner()
        step_2_scripts(month, day)
    elif args.step == 3:
        print_banner()
        step_3_thumbnails_prompts(month, day)
    elif args.step == 4:
        print_banner()
        step_4_youtube_upload_info(month, day)
    else:
        run_full_flow(month, day)


if __name__ == "__main__":
    main()
