"""
video_generator.py — Genera YouTube Shorts 1080x1920, ~58s
Estilo: imagen histórica REAL + overlay negro 50% + texto blanco con sombra
Ensamblado con ffmpeg directo (sin moviepy) para bajo consumo de memoria.
"""

import os
import re
import wave
import logging
import subprocess
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

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
    """Descarga Bebas Neue o usa fallback de sistema."""
    cache_path = "/tmp/BebasNeue-Regular.ttf"

    if not os.path.exists(cache_path):
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
                if len(fr.content) > 10000:  # Sanity check: TTF debe ser >10KB
                    with open(cache_path, "wb") as f:
                        f.write(fr.content)
                    log.info("Bebas Neue descargada via Google Fonts")
        except Exception as e:
            log.warning(f"Google Fonts falló: {e}")

    try:
        return ImageFont.truetype(cache_path, size)
    except Exception:
        for fp in [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]:
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
        return ImageFont.load_default()


# ─── FRAME BUILDER ────────────────────────────────────────────────────────────

def _draw_shadow_text(draw, text, font, x, y, text_color, shadow_color=(0, 0, 0),
                      shadow_offset=3, max_width=None, align="center"):
    """Dibuja texto con sombra negra difusa."""
    if max_width:
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

        for dx in range(-shadow_offset, shadow_offset + 1, 1):
            for dy in range(-shadow_offset, shadow_offset + 1, 1):
                if dx != 0 or dy != 0:
                    alpha = max(0, 180 - (abs(dx) + abs(dy)) * 30)
                    draw.text((lx + dx, cy + dy), line, font=font,
                              fill=(*shadow_color, alpha))

        draw.text((lx, cy), line, font=font, fill=text_color)
        cy += line_height

    return cy


def build_styled_frame(
    bg_image_path: str,
    section: str,
    script_data: dict,
    output_path: str,
) -> str:
    """Construye un frame PIL con imagen histórica, overlay y texto."""
    bg = Image.open(bg_image_path).convert("RGBA")
    if bg.size != (W, H):
        bg = bg.resize((W, H), Image.LANCZOS)

    overlay = Image.new("RGBA", (W, H), (0, 0, 0, OVERLAY_ALPHA))
    frame = Image.alpha_composite(bg, overlay).convert("RGBA")
    draw = ImageDraw.Draw(frame)
    cx = W // 2

    year = str(script_data.get("year", ""))
    title = script_data.get("title", "")
    hook = script_data.get("hook", "")
    narration = script_data.get("narration", "")
    cta = script_data.get("cta", "")

    def clean(t):
        t = re.sub(r'<[^>]+>', '', t)
        t = re.sub(r'\[.*?\]', '', t)
        return t.strip()

    if section == "hook":
        f_label = _get_bebas_neue(72)
        f_hook = _get_bebas_neue(58)
        label = f"¿SABÍAS QUE EN {year}?"
        _draw_shadow_text(draw, label, f_label, cx, 280, GOLD, max_width=900, align="center")
        _draw_shadow_text(draw, clean(hook)[:120], f_hook, cx, 460, WHITE, max_width=880, align="center")

    elif section == "context":
        f_year = _get_bebas_neue(200)
        f_title = _get_bebas_neue(64)
        f_sub = _get_bebas_neue(48)
        _draw_shadow_text(draw, year, f_year, cx, 200, GOLD, align="center")
        _draw_shadow_text(draw, title[:60], f_title, cx, 520, WHITE, max_width=900, align="center")
        sentences = re.split(r'[.!?]', clean(narration))
        context_text = ". ".join(s.strip() for s in sentences[:2] if s.strip())
        _draw_shadow_text(draw, context_text[:150], f_sub, cx, 720, (220, 220, 220),
                          max_width=880, align="center")

    elif section == "detail":
        f_title = _get_bebas_neue(60)
        f_bullet = _get_bebas_neue(50)
        _draw_shadow_text(draw, "LO QUE NADIE TE CONTÓ", f_title, cx, 200, GOLD, align="center")
        sentences = [s.strip() for s in re.split(r'[.!?]', clean(narration)) if len(s.strip()) > 20]
        bullets = sentences[2:5] if len(sentences) > 2 else sentences
        y_pos = 400
        for bullet in bullets[:3]:
            text = f"• {bullet[:80]}"
            y_pos = _draw_shadow_text(draw, text, f_bullet, 80, y_pos, WHITE,
                                      max_width=920, align="left") + 30

    elif section == "cta":
        f_main = _get_bebas_neue(90)
        f_cta = _get_bebas_neue(60)
        f_channel = _get_bebas_neue(44)
        dark = Image.new("RGBA", (W, H), (0, 0, 0, 80))
        frame = Image.alpha_composite(frame.convert("RGBA"), dark)
        draw = ImageDraw.Draw(frame)
        _draw_shadow_text(draw, "¿LO SABÍAS?", f_main, cx, 300, GOLD, align="center")
        _draw_shadow_text(draw, clean(cta)[:120], f_cta, cx, 520, WHITE, max_width=880, align="center")
        _draw_shadow_text(draw, "@BitacoraDelTiempo", f_channel, cx, 800, (180, 180, 180), align="center")

    frame.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path


# ─── AMBIENT MUSIC ────────────────────────────────────────────────────────────

def _generate_ambient_music(duration: float, output_path: str) -> str:
    """Genera música ambiente épica con numpy (Am chord + tremolo)."""
    sr = 44100
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    freqs = [110.0, 165.0, 220.0, 261.63]
    harmonics = [0.5, 0.35, 0.25, 0.2]

    audio = np.zeros_like(t)
    for freq, amp in zip(freqs, harmonics):
        audio += amp * np.sin(2 * np.pi * freq * t)

    tremolo = 0.75 + 0.25 * np.sin(2 * np.pi * 0.15 * t)
    audio *= tremolo

    fade = int(sr * 2.5)
    audio[:fade] *= np.linspace(0, 1, fade)
    audio[-fade:] *= np.linspace(1, 0, fade)

    audio = (audio / np.max(np.abs(audio))) * 0.15 * 32767
    stereo = np.column_stack([audio, audio]).astype(np.int16)

    # Escribir WAV de una sola vez (no frame-by-frame)
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(stereo.tobytes())

    return output_path


# ─── VIDEO ASSEMBLY (ffmpeg directo — sin moviepy) ───────────────────────────

def _run_ffmpeg(cmd: list, timeout: int = 120, label: str = "") -> None:
    """Ejecuta ffmpeg y lanza excepción con stderr si falla."""
    result = subprocess.run(cmd, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        err = result.stderr.decode(errors="replace")[-1000:]
        raise RuntimeError(f"ffmpeg {label} falló (rc={result.returncode}): {err}")


def create_short_video(
    image_path: str,
    audio_path: str,
    script_data: dict,
    output_path: str,
) -> str:
    """
    Ensambla el video final con ffmpeg directo:
    - 4 secciones (hook/context/detail/cta) con Ken Burns zoom
    - Narración + música ambiente 15%
    Usa <50MB RAM (vs ~2GB con moviepy).
    """
    work_dir = os.path.dirname(output_path)

    sections = ["hook", "context", "detail", "cta"]
    # (z_start, z_end) para cada sección
    zoom_params = {
        "hook":    (1.00, 1.06),
        "context": (1.06, 1.00),
        "detail":  (1.00, 1.08),
        "cta":     (1.08, 1.02),
    }

    section_videos = []

    for section in sections:
        dur = SECTION_DURATIONS[section]
        nframes = dur * FPS
        frame_path = os.path.join(work_dir, f"frame_{section}.jpg")
        section_video = os.path.join(work_dir, f"section_{section}.mp4")

        # 1. Construir frame PIL
        build_styled_frame(image_path, section, script_data, frame_path)

        z_start, z_end = zoom_params[section]
        delta = z_end - z_start

        # 2. Convertir frame → video con Ken Burns via zoompan
        #    Pre-escalar a 110% para que zoompan tenga margen de recorte
        pad_w = int(W * 1.10)
        pad_h = int(H * 1.10)

        if delta >= 0:
            z_expr = f"min({z_start:.4f}+{delta:.6f}*on/{nframes-1},{z_end:.4f})"
        else:
            z_expr = f"max({z_end:.4f},{z_start:.4f}+{delta:.6f}*on/{nframes-1})"

        vf = (
            f"scale={pad_w}:{pad_h},"
            f"zoompan=z='{z_expr}'"
            f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={nframes}:fps={FPS}:s={W}x{H}"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", frame_path,
            "-vf", vf,
            "-t", str(dur),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-an",
            section_video,
        ]

        try:
            _run_ffmpeg(cmd, timeout=90, label=f"zoompan/{section}")
            log.info(f"Sección {section} OK (Ken Burns {z_start}→{z_end})")
        except Exception as e:
            log.warning(f"zoompan falló para {section}: {e} — usando clip estático")
            # Fallback: clip estático sin zoom
            cmd_static = [
                "ffmpeg", "-y",
                "-loop", "1", "-i", frame_path,
                "-t", str(dur),
                "-vf", f"scale={W}:{H}",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
                "-pix_fmt", "yuv420p",
                "-r", str(FPS),
                "-an",
                section_video,
            ]
            _run_ffmpeg(cmd_static, timeout=60, label=f"static/{section}")
            log.info(f"Sección {section} OK (estático)")

        section_videos.append(section_video)

    # 3. Concatenar secciones
    concat_list = os.path.join(work_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for v in section_videos:
            f.write(f"file '{v}'\n")

    concat_video = os.path.join(work_dir, "concat_silent.mp4")
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy",
        concat_video,
    ], timeout=60, label="concat")

    # 4. Generar música ambiente
    music_path = os.path.join(work_dir, "ambient.wav")
    _generate_ambient_music(TOTAL + 2, music_path)

    # 5. Mezclar audio + video → output final
    log.info(f"Renderizando video {W}x{H} @ {FPS}fps → {output_path}")
    _run_ffmpeg([
        "ffmpeg", "-y",
        "-i", concat_video,
        "-i", audio_path,
        "-i", music_path,
        "-filter_complex",
        "[1:a]volume=1.0[narr];[2:a]volume=0.15[mus];[narr][mus]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ], timeout=300, label="final mix")

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    log.info(f"Video OK: {size_mb:.1f}MB → {output_path}")

    # 6. Thumbnail
    thumb_path = output_path.replace(".mp4", "_thumb.jpg")
    _generate_thumbnail(image_path, script_data, thumb_path)
    script_data["thumbnail_path"] = thumb_path

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
