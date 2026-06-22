"""
voice_generator.py — Generación de voz con edge-tts (Kokoro no disponible en cloud)
Voz: es-MX-JorgeNeural | Velocidad: +10% | Pausas en [PAUSA] y [SUSPENSO]
"""

import os
import re
import asyncio
import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

VOICE = os.environ.get("TTS_VOICE", "es-MX-JorgeNeural")
RATE = os.environ.get("TTS_RATE", "+10%")
VOLUME = os.environ.get("TTS_VOLUME", "+0%")


def _preprocess_text(text: str) -> str:
    """
    Convierte marcadores [PAUSA] y [SUSPENSO] en pausas SSML.
    edge-tts acepta SSML nativo.
    """
    # [PAUSA] → pausa corta 600ms
    text = re.sub(r'\[PAUSA\]', '<break time="600ms"/>', text)
    # [SUSPENSO] → pausa más larga 1000ms
    text = re.sub(r'\[SUSPENSO\]', '<break time="1000ms"/>', text)
    # Limpiar otros marcadores que puedan haber quedado
    text = re.sub(r'\[.*?\]', '', text)
    
    # Envolver en SSML
    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='es-MX'>
<prosody rate='{RATE}' volume='{VOLUME}'>
{text}
</prosody>
</speak>"""
    return ssml


async def _generate_edge_tts(text: str, output_path: str):
    """Genera audio con edge-tts."""
    import edge_tts
    
    ssml = _preprocess_text(text)
    
    communicate = edge_tts.Communicate(
        text=ssml,
        voice=VOICE,
        rate=RATE,
        volume=VOLUME,
    )
    
    # edge-tts puede fallar con SSML directo, intentar con texto plano si falla
    try:
        await communicate.save(output_path)
    except Exception:
        # Fallback: texto plano sin SSML
        plain = re.sub(r'<[^>]+>', ' ', ssml)
        plain = re.sub(r'\s+', ' ', plain).strip()
        communicate2 = edge_tts.Communicate(text=plain, voice=VOICE, rate=RATE)
        await communicate2.save(output_path)


def _normalize_audio(input_path: str, output_path: str) -> str:
    """Normaliza audio con ffmpeg para volumen consistente."""
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ar", "44100",
        "-ac", "1",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=60)
    if result.returncode == 0:
        return output_path
    else:
        log.warning(f"ffmpeg normalize falló: {result.stderr.decode()}")
        return input_path  # Usar sin normalizar


def generate_voice(text: str, output_path: str) -> str:
    """
    Genera narración de voz para el guion dado.
    
    Args:
        text: Texto con marcadores [PAUSA] y [SUSPENSO]
        output_path: Ruta donde guardar el audio .wav
    
    Returns:
        Ruta al archivo de audio generado
    """
    output_path = str(output_path)
    raw_path = output_path.replace(".wav", "_raw.mp3")
    
    log.info(f"Generando voz: {len(text)} chars → {output_path}")
    
    # Generar con edge-tts
    asyncio.run(_generate_edge_tts(text, raw_path))
    
    # Normalizar y convertir a WAV
    if os.path.exists(raw_path) and os.path.getsize(raw_path) > 1000:
        normalized = _normalize_audio(raw_path, output_path)
        if normalized != output_path:
            # ffmpeg falló, convertir sin normalizar
            cmd = ["ffmpeg", "-y", "-i", raw_path, output_path]
            subprocess.run(cmd, capture_output=True, timeout=30)
        
        # Limpiar temporal
        try:
            os.remove(raw_path)
        except Exception:
            pass
        
        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            log.info(f"Audio OK: {size/1024:.1f}KB")
            return output_path
    
    raise RuntimeError(f"edge-tts no generó audio válido en {raw_path}")
