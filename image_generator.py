"""
image_generator.py — Imágenes históricas para Bitácora del Tiempo
Fuentes: Wikimedia Commons → Hugging Face SDXL → gradiente épico
"""

import os
import io
import re
import time
import random
import logging
import requests
from pathlib import Path
from PIL import Image, ImageFilter, ImageDraw, ImageEnhance

log = logging.getLogger(__name__)

HF_TOKEN = os.environ.get("HF_TOKEN", "")
W, H = 1080, 1920  # Vertical Short
WIKI_HEADERS = {
    "User-Agent": "BitacoraBot/2.0 (kuralens.official@gmail.com)",
    "Accept": "application/json",
}

# Prompts cinematográficos por categoría
CINEMATIC_PROMPTS = {
    "space": "dramatic cinematic space photograph, nebula, stars, deep space, National Geographic style, ultra high quality, 8k",
    "war": "dramatic historical war photograph, dramatic lighting, cinematic, sepia tones, ultra realistic",
    "invention": "dramatic cinematic photograph of historical invention, dramatic studio lighting, vintage aesthetic",
    "revolution": "dramatic crowd historical photograph, cinematic lighting, black and white, iconic, photojournalism",
    "disaster": "dramatic cinematic natural disaster photograph, epic scale, dramatic clouds, golden hour",
    "science": "dramatic cinematic scientific discovery, laboratory, dramatic lighting, National Geographic",
    "default": "dramatic cinematic historical photograph, dramatic lighting, epic composition, ultra realistic, 8k",
}


def _smart_crop(img: Image.Image) -> Image.Image:
    """Recorta inteligentemente a 1080x1920 preservando el centro."""
    img = img.convert("RGB")
    src_w, src_h = img.size
    target_ratio = W / H
    src_ratio = src_w / src_h
    
    if src_ratio > target_ratio:
        # Imagen más ancha: recortar lados
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        # Imagen más alta: recortar arriba/abajo con sesgo hacia arriba (sujetos)
        new_h = int(src_w / target_ratio)
        top = max(0, int((src_h - new_h) * 0.3))
        img = img.crop((0, top, src_w, top + new_h))
    
    return img.resize((W, H), Image.LANCZOS)


def _apply_cinematic_filter(img: Image.Image) -> Image.Image:
    """Aplica filtro cinematográfico: contraste + viñeta."""
    # Boost contraste ligeramente
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.15)
    
    # Viñeta oscura en bordes
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    for i in range(200):
        alpha = int((i / 200) * 120)
        draw.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
    
    img_rgba = img.convert("RGBA")
    img_rgba = Image.alpha_composite(img_rgba, vignette)
    return img_rgba.convert("RGB")


def _wikimedia_search(query: str, year=None) -> list[str]:
    """Busca imágenes en Wikimedia Commons. Retorna lista de URLs."""
    search_query = query
    if year and int(year) > 1800:
        search_query = f"{query} {year}"
    
    # 1. Wikipedia 'On This Day' image (ya la tenemos en event_image_url pero por si acaso)
    # 2. Wikimedia Commons API search
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": f"{search_query} filetype:bitmap",
        "srnamespace": "6",  # File namespace
        "srlimit": "10",
        "format": "json",
    }
    
    r = requests.get(url, params=params, headers=WIKI_HEADERS, timeout=15)
    r.raise_for_status()
    data = r.json()
    
    results = data.get("query", {}).get("search", [])
    urls = []
    
    for item in results:
        title = item["title"]  # "File:Something.jpg"
        # Obtener URL directa
        info_url = "https://commons.wikimedia.org/w/api.php"
        info_params = {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|size|mediatype",
            "format": "json",
        }
        try:
            ir = requests.get(info_url, params=info_params, headers=WIKI_HEADERS, timeout=10)
            ir.raise_for_status()
            pages = ir.json().get("query", {}).get("pages", {})
            for page in pages.values():
                ii = page.get("imageinfo", [{}])[0]
                if ii.get("url") and ii.get("mediatype") in ("BITMAP", "DRAWING"):
                    w = ii.get("width", 0)
                    h = ii.get("height", 0)
                    if w >= 400 and h >= 400:
                        urls.append(ii["url"])
        except Exception:
            pass
    
    return urls


def _download_image(url: str, save_path: str) -> str:
    """Descarga imagen desde URL y la procesa."""
    r = requests.get(url, timeout=30, headers={"User-Agent": "BitacoraBot/2.0"})
    r.raise_for_status()
    
    img = Image.open(io.BytesIO(r.content))
    img = _smart_crop(img)
    img = _apply_cinematic_filter(img)
    img.save(save_path, "JPEG", quality=92)
    return save_path


def _hf_sdxl_image(prompt: str, save_path: str) -> str:
    """Genera imagen con Hugging Face SDXL (fallback)."""
    if not HF_TOKEN:
        raise ValueError("HF_TOKEN no configurado")
    
    api_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    
    # SDXL genera 1024x1024, luego recortamos
    payload = {
        "inputs": prompt,
        "parameters": {
            "width": 1024,
            "height": 1024,
            "num_inference_steps": 20,
            "guidance_scale": 7.5,
        },
    }
    
    # Reintentos por cold start
    for attempt in range(3):
        r = requests.post(api_url, headers=headers, json=payload, timeout=120)
        if r.status_code == 503:
            wait = 20 * (attempt + 1)
            log.info(f"HF model loading, esperando {wait}s...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        break
    
    img = Image.open(io.BytesIO(r.content))
    img = _smart_crop(img)
    img = _apply_cinematic_filter(img)
    img.save(save_path, "JPEG", quality=92)
    return save_path


def _dark_gradient_fallback(save_path: str, year=None) -> str:
    """Gradiente épico oscuro como último fallback."""
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    
    # Gradiente diagonal dramático
    for y in range(H):
        progress = y / H
        r = int(8 + 15 * progress)
        g = int(5 + 10 * progress)
        b = int(15 + 20 * progress)
        draw.line([(0, y), (W, y)], fill=(r, g, b))
    
    # Textura de ruido sutil
    import numpy as np
    arr = np.array(img)
    noise = np.random.randint(-8, 9, arr.shape, dtype=np.int16)
    arr = np.clip(arr.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    
    img.save(save_path, "JPEG", quality=92)
    return save_path


def get_historical_image(query: str, year=None, work_dir: str = "/tmp", event_image_url: str = None) -> str:
    """
    Obtiene la mejor imagen histórica disponible.
    Orden: URL directa de Wikipedia → Wikimedia search → HF SDXL → gradiente
    """
    save_path = os.path.join(work_dir, "background.jpg")
    
    # 1. URL directa desde Wikipedia (si viene en event_image_url)
    if event_image_url:
        try:
            log.info(f"Descargando imagen directa: {event_image_url[:80]}")
            return _download_image(event_image_url, save_path)
        except Exception as e:
            log.warning(f"URL directa falló: {e}")
    
    # 2. Búsqueda en Wikimedia Commons
    try:
        log.info(f"Buscando en Wikimedia: '{query}'")
        urls = _wikimedia_search(query, year)
        if urls:
            for url in urls[:5]:
                try:
                    return _download_image(url, save_path)
                except Exception:
                    continue
        log.warning("Wikimedia: sin resultados válidos")
    except Exception as e:
        log.warning(f"Wikimedia error: {e}")
    
    # 3. Hugging Face SDXL
    try:
        # Categorizar el query para elegir prompt cinematográfico
        q_lower = query.lower()
        category = "default"
        for cat, keywords in [
            ("space", ["space", "moon", "planet", "star", "nasa", "astronaut", "cosmos"]),
            ("war", ["war", "battle", "military", "army", "soldier", "conflict"]),
            ("invention", ["invention", "inventor", "machine", "patent", "discovery"]),
            ("revolution", ["revolution", "protest", "independence", "uprising", "freedom"]),
            ("disaster", ["earthquake", "flood", "fire", "disaster", "explosion", "disaster"]),
            ("science", ["science", "laboratory", "experiment", "physics", "chemistry"]),
        ]:
            if any(kw in q_lower for kw in keywords):
                category = cat
                break
        
        base_prompt = CINEMATIC_PROMPTS.get(category, CINEMATIC_PROMPTS["default"])
        full_prompt = f"{query}, {base_prompt}"
        
        log.info(f"Generando con HF SDXL: '{full_prompt[:80]}'")
        return _hf_sdxl_image(full_prompt, save_path)
    except Exception as e:
        log.warning(f"HF SDXL error: {e}")
    
    # 4. Gradiente épico fallback
    log.warning("Usando gradiente épico como fallback final")
    return _dark_gradient_fallback(save_path, year)
