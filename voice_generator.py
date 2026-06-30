"""
voice_generator.py — Generación de voz con edge-tts + gTTS como fallback
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


def _preprocess_text_plain(text: str) -> str:
    """Convierte marcadores a texto limpio (para gTTS o edge-tts sin SSML)."""
    # [PAUSA] y [SUSPENSO] → coma + espacio (pausa natural)
    text = re.sub(r'\[PAUSA\]', ', ', text)
    text = re.sub(r'\[SUSPENSO\]', '... ', text)
    # Limpiar otros marcadores
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


async def _generate_edge_tts(text: str, output_path: str):
    """Genera audio con edge-tts usando texto plano (sin SSML para evitar 403)."""
    import edge_tts

    plain = _preprocess_text_plain(text)

    communicate = edge_tts.Communicate(
        text=plain,
        voice=VOICE,
        rate=RATE,
        volume=VOLUME,
    )
    await communicate.save(output_path)


def _generate_gtts(text: str, output_path: str):
    """Fallback: genera audio con gTTS (Google TTS, no requiere token)."""
    from gtts import gTTS

    plain = _preprocess_text_plain(text)
    # Detectar idioma desde la voz (es-MX → es)
    lang = VOICE.split("-")[0] if VOICE else "es"

    tts = gTTS(text=plain, lang=lang, slow=False)
    mp3_path = output_path.replace(".wav", "_gtts.mp3").replace(".mp3", "_gtts.mp3")
    tts.save(mp3_path)

    # Convertir a WAV con ffmpeg
    cmd = ["ffmpeg", "-y", "-i", mp3_path, output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    try:
        os.remove(mp3_path)
    except Exception:
        pass

    if result.returncode != 0:
        raise RuntimeError(f"gTTS ffmpeg conversion failed: {result.stderr.decode()}")


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
        return input_path


def generate_voice(text: str, output_path: str) -> str:
    """
    Genera narración de voz. Intenta edge-tts primero, gTTS como fallback.

    Args:
        text: Texto con marcadores [PAUSA] y [SUSPENSO]
        output_path: Ruta donde guardar el audio .wav

    Returns:
        Ruta al archivo de audio generado
    """
    output_path = str(output_path)
    raw_path = output_path.replace(".wav", "_raw.mp3")

    log.info(f"Generando voz: {len(text)} chars → {output_path}")

    # Intentar edge-tts primero
    edge_ok = False
    try:
        asyncio.run(_generate_edge_tts(text, raw_path))
        if os.path.exists(raw_path) and os.path.getsize(raw_path) > 1000:
            edge_ok = True
            log.info("edge-tts OK")
        else:
            log.warning("edge-tts generó archivo vacío")
    except Exception as e:
        log.warning(f"edge-tts falló ({e}), usando gTTS como fallback")

    if edge_ok:
        # Normalizar y convertir a WAV
        normalized = _normalize_audio(raw_path, output_path)
        if normalized != output_path:
            cmd = ["ffmpeg", "-y", "-i", raw_path, output_path]
            subprocess.run(cmd, capture_output=True, timeout=30)
        try:
            os.remove(raw_path)
        except Exception:
            pass
    else:
        # Fallback: gTTS
        log.info("Usando gTTS como fallback")
        _generate_gtts(text, output_path)

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        size = os.path.getsize(output_path)
        log.info(f"Audio OK: {size/1024:.1f}KB")
        return output_path

    raise RuntimeError(f"TTS no generó audio válido en {output_path}")
