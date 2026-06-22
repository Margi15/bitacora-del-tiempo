"""
video_generator.py — Genera YouTube Shorts 1080x1920, ~58s
Estilo: imagen histórica REAL + overlay negro 50% + texto blanco con sombra
Efectos: Ken Burns zoom 1.0→1.08, fade entre secciones, música ambiente 15%
"""

import os
import re
import time
import logging
import textwrap
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeAudioClip,
    concatenate_videoclips, VideoFileClip,
)
from moviepy.audio.AudioClip import AudioArrayClip

log = logging.getLogger(__name__)

W, H = 1080, 1920
FPS = 30

# Duración de cada sección (segundos)
SECTION_DURATIONS = {
    "hook": 8,
    "context": 12,
    "detail": 25,
    "cta": 13,
}
TOTAL = sum(SECTION_DURATIONS.values())  # 58s

# Colores
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
BLACK = (0, 0, 0)
OVERLAY_ALPHA = 128  # 50% negro


# ─── FONT ─────────────────────────────────────────────────────────────────────

def _get_bebas_neue(size: int) -> ImageFont.FreeTypeFont:
    """Descarga Bebas Neue o usa fallback."""
    cache_path = "/tmp/BebasNeue-Regular.ttf"
    
    if not os.path.exists(cache_path):
        urls = [
            # Strategy 1: Google Fonts API con UA antiguo
            ("https://fonts.googleapis.com/css?family=Bebas+Neue",
             "IE6"),
            # Strategy 2: GitHub raw
            ("https://github.com/dharmatype/Bebas-Neue/raw/master/Fonts/BN_TTF_1.002.zip",
             None),
        ]
        
        import requests, zipfile, io, re as re2
        
        # Strategy 1: Google Fonts CSS → extraer URL TTF
        try:
            r = requests.get(
                "https://fonts.googleapis.com/css?family=Bebas+Neue",
                headers={"User-Agent": "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)"},
                timeout=10,
            )
            ttf_urls = re2.findall(r'url\((https://[^)]+\.ttf)\)', r.text)
            if ttf_urls:
                fr = requests.get(ttf_urls[0], timeout=20)
                with open(cache_path, "wb") as f:
                    f.write(fr.content)
                log.info("Bebas Neue descargada via Google Fonts")
        except Exception as e:
            log.warning(f"Google Fonts falló: {e}")
        
        # Strategy 2: ZIP de GitHub
        if not os.path.exists(cache_path):
            try:
                r = requests.get(
                    "https://github.com/dharmatype/Bebas-Neue/raw/master/Fonts/BN_TTF_1.002.zip",
                    timeout=30,
                )
                with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                    for name in z.namelist():
                        if "BebasNeue-Regular" in name and name.endswith(".ttf"):
                            with z.open(name) as zf, open(cache_path, "wb") as f:
                                f.write(zf.read())
                            log.info("Bebas Neue descargada via GitHub ZIP")
                            break
            except Exception as e:
                log.warning(f"GitHub ZIP falló: {e}")
    
    try:
        return ImageFont.truetype(cache_path, size)
    except Exception:
        # Sistema fallbacks
        for fp in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                   "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                   "C:/Windows/Fonts/arialbd.ttf"]:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
        return ImageFont.load_default()


# ─── FRAME BUILDER ────────────────────────────────────────────────────────────

def _draw_shadow_text(draw, text, font, x, y, text_color, shadow_color=(0,0,0),
                      shadow_offset=3, max_width=None, align="center"):
    """Dibuja texto con sombra negra difusa."""
    if max_width:
        # Word wrap manual
        words = text.split()
        lines = []
        current = []
        for word in words:
            test = " ".join(current + [word])
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(" ".join(current))
                current = [word]
            else:
                current.append(word)
        if current:
            lines.append(" ".join(current))
    else:
        lines = [text]
    
    line_height = font.size + 8
    total_h = len(lines) * line_height
    cy = y
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        lw = bbox[2] - bbox[0]
        if align == "center":
            lx = x - lw // 2
        elif align == "left":
            lx = x
        else:
            lx = x - lw
        
        # Sombra (múltiples capas para efecto difuso)
        for dx in range(-shadow_offset, shadow_offset + 1, 1):
            for dy in range(-shadow_offset, shadow_offset + 1, 1):
                if dx != 0 or dy != 0:
                    alpha = max(0, 180 - (abs(dx) + abs(dy)) * 30)
                    draw.text((lx + dx, cy + dy), line, font=font,
                              fill=(*shadow_color, alpha))
        
        draw.text((lx, cy), line, font=font, fill=text_color)
        cy += line_height
    
    return cy  # Y final


def build_styled_frame(
    bg_image_path: str,
    section: str,
    script_data: dict,
    output_path: str,
) -> str:
    """
    Construye un frame PIL con:
    - Imagen histórica de fondo
    - Overlay negro 50%
    - Texto blanco con sombra según sección
    """
    # Cargar y preparar fondo
    bg = Image.open(bg_image_path).convert("RGBA")
    if bg.size != (W, H):
        bg = bg.resize((W, H), Image.LANCZOS)
    
    # Overlay negro 50%
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, OVERLAY_ALPHA))
    frame = Image.alpha_composite(bg, overlay).convert("RGBA")
    
    draw = ImageDraw.Draw(frame)
    cx = W // 2
    
    year = str(script_data.get("year", ""))
    title = script_data.get("title", "")
    hook = script_data.get("hook", "")
    narration = script_data.get("narration", "")
    cta = script_data.get("cta", "")
    
    # Limpiar marcadores SSML del texto visual
    def clean(t):
        t = re.sub(r'<[^>]+>', '', t)
        t = re.sub(r'\[.*?\]', '', t)
        return t.strip()
    
    if section == "hook":
        # ¿SABÍAS QUE EN {year}? + hook text
        f_label = _get_bebas_neue(72)
        f_hook = _get_bebas_neue(58)
        
        label = f"¿SABÍAS QUE EN {year}?"
        _draw_shadow_text(draw, label, f_label, cx, 280, GOLD, max_width=900, align="center")
        _draw_shadow_text(draw, clean(hook)[:120], f_hook, cx, 460, WHITE, max_width=880, align="center")
    
    elif section == "context":
        # Año gigante + título
        f_year = _get_bebas_neue(200)
        f_title = _get_bebas_neue(64)
        f_sub = _get_bebas_neue(48)
        
        _draw_shadow_text(draw, year, f_year, cx, 200, GOLD, align="center")
        _draw_shadow_text(draw, title[:60], f_title, cx, 520, WHITE, max_width=900, align="center")
        
        # Primeras 2 oraciones de narración
        sentences = re.split(r'[.!?]', clean(narration))
        context_text = ". ".join(s.strip() for s in sentences[:2] if s.strip())
        _draw_shadow_text(draw, context_text[:150], f_sub, cx, 720, (220, 220, 220),
                         max_width=880, align="center")
    
    elif section == "detail":
        # 3 bullets del cuerpo de la narración
        f_title = _get_bebas_neue(60)
        f_bullet = _get_bebas_neue(50)
        
        _draw_shadow_text(draw, "LO QUE NADIE TE CONTÓ", f_title, cx, 200, GOLD, align="center")
        
        sentences = [s.strip() for s in re.split(r'[.!?]', clean(narration)) if len(s.strip()) > 20]
        bullets = sentences[2:5] if len(sentences) > 2 else sentences
        
        y_pos = 400
        for i, bullet in enumerate(bullets[:3]):
            text = f"• {bullet[:80]}"
            y_pos = _draw_shadow_text(draw, text, f_bullet, 80, y_pos, WHITE,
                                      max_width=920, align="left") + 30
    
    elif section == "cta":
        # ¿LO SABÍAS? + CTA
        f_main = _get_bebas_neue(90)
        f_cta = _get_bebas_neue(60)
        f_channel = _get_bebas_neue(44)
        
        # Extra overlay más oscuro para CTA
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 80))
        frame = Image.alpha_composite(frame.convert("RGBA"), dark)
        draw = ImageDraw.Draw(frame)
        
        _draw_shadow_text(draw, "¿LO SABÍAS?", f_main, cx, 300, GOLD, align="center")
        _draw_shadow_text(draw, clean(cta)[:120], f_cta, cx, 520, WHITE, max_width=880, align="center")
        _draw_shadow_text(draw, "@BitacoraDelTiempo", f_channel, cx, 800, (180, 180, 180), align="center")
    
    # Guardar
    frame.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path


# ─── AMBIENT MUSIC ────────────────────────────────────────────────────────────

def _generate_ambient_music(duration: float, output_path: str) -> str:
    """Genera música ambiente épica con numpy (Am chord + tremolo)."""
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    
    # Acorde de Am: A2 (110Hz), E3 (165Hz), A3 (220Hz), C4 (261Hz)
    freqs = [110.0, 165.0, 220.0, 261.63]
    harmonics = [0.5, 0.35, 0.25, 0.2]
    
    audio = np.zeros_like(t)
    for freq, amp in zip(freqs, harmonics):
        audio += amp * np.sin(2 * np.pi * freq * t)
    
    # Tremolo lento (0.15Hz)
    tremolo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.15 * t)
    audio *= tremolo
    
    # Fade in/out
    fade = int(sr * 2.5)
    audio[:fade] *= np.linspace(0, 1, fade)
    audio[-fade:] *= np.linspace(1, 0, fade)
    
    # Normalizar al 15% del volumen
    audio = (audio / np.max(np.abs(audio))) * 0.15 * 32767
    stereo = np.column_stack([audio, audio]).astype(np.int16)
    
    import wave, struct
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        for sample in stereo:
            wf.writeframes(struct.pack('<hh', sample[0], sample[1]))
    
    return output_path


# ─── VIDEO ASSEMBLY ───────────────────────────────────────────────────────────

def create_short_video(
    image_path: str,
    audio_path: str,
    script_data: dict,
    output_path: str,
) -> str:
    """
    Ensambla el video final con:
    - 4 secciones (hook/context/detail/cta)
    - Ken Burns zoom 1.0→1.08 en cada sección
    - Overlay negro 50% con texto
    - Narración + música ambiente 15%
    """
    import tempfile
    work_dir = os.path.dirname(output_path)
    
    # Construir los 4 frames
    sections = ["hook", "context", "detail", "cta"]
    ken_burns_params = [
        (1.00, 1.06),  # hook: zoom in
        (1.06, 1.00),  # context: zoom out
        (1.00, 1.08),  # detail: zoom in más
        (1.08, 1.02),  # cta: ligero zoom out
    ]
    
    clips = []
    for i, (section, (z_start, z_end)) in enumerate(zip(sections, ken_burns_params)):
        dur = SECTION_DURATIONS[section]
        
        frame_path = os.path.join(work_dir, f"frame_{section}.jpg")
        build_styled_frame(image_path, section, script_data, frame_path)
        
        # Ken Burns effect
        clip = (
            ImageClip(frame_path, duration=dur)
            .resize(lambda t, zs=z_start, ze=z_end, d=max(dur, 0.01):
                    zs + (ze - zs) * (t / d))
            .set_position("center")
            .set_fps(FPS)
        )
        
        # Fade entre clips (0.3s)
        if i > 0:
            clip = clip.crossfadein(0.3)
        
        clips.append(clip)
    
    # Concatenar con crossfade
    video = concatenate_videoclips(clips, method="compose", padding=-0.3)
    video = video.set_fps(FPS)
    
    # Audio principal (narración)
    narration_audio = AudioFileClip(audio_path)
    
    # Música ambiente
    music_path = os.path.join(work_dir, "ambient.wav")
    _generate_ambient_music(TOTAL + 1, music_path)
    ambient_audio = AudioFileClip(music_path).volumex(0.15)
    
    # Mezclar audio
    final_audio = CompositeAudioClip([
        narration_audio,
        ambient_audio.set_duration(TOTAL),
    ])
    
    # Ajustar duración del video al audio
    final_duration = min(TOTAL, narration_audio.duration + 0.5)
    video = video.set_duration(final_duration)
    video = video.set_audio(final_audio.set_duration(final_duration))
    
    # Exportar
    log.info(f"Renderizando video {W}x{H} @ {FPS}fps → {output_path}")
    video.write_videofile(
        output_path,
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="5000k",
        audio_bitrate="192k",
        preset="fast",
        threads=2,
        logger=None,
    )
    
    # Generar thumbnail
    thumb_path = output_path.replace(".mp4", "_thumb.jpg")
    _generate_thumbnail(image_path, script_data, thumb_path)
    script_data["thumbnail_path"] = thumb_path
    
    log.info(f"Video OK: {os.path.getsize(output_path)/1024/1024:.1f}MB")
    return output_path


def _generate_thumbnail(image_path: str, script_data: dict, output_path: str) -> str:
    """Thumbnail 1280x720 para YouTube."""
    TW, TH = 1280, 720
    
    bg = Image.open(image_path).convert("RGBA")
    bg = bg.resize((TW, TH), Image.LANCZOS)
    
    overlay = Image.new("RGBA", (TW, TH), (0, 0, 0, 140))
    frame = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(frame)
    
    cx = TW // 2
    year = str(script_data.get("year", ""))
    title = script_data.get("title", "")[:50]
    
    f_year = _get_bebas_neue(180)
    f_title = _get_bebas_neue(70)
    
    _draw_shadow_text(draw, year, f_year, cx, 80, GOLD, align="center")
    _draw_shadow_text(draw, title, f_title, cx, 350, WHITE, max_width=1100, align="center")
    
    frame.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path
