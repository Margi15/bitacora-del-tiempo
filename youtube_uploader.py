"""
youtube_uploader.py — Sube Shorts a YouTube con OAuth2
Genera refresh_token la primera vez, reutiliza en producción.
"""

import os
import json
import time
import logging
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]

TOKEN_FILE = os.environ.get("YT_TOKEN_FILE", "/tmp/yt_token.json")


def _get_credentials() -> Credentials:
    """
    Obtiene credenciales OAuth2.
    En producción (Render/GitHub Actions): usa variables de entorno.
    En desarrollo local: abre browser para autorizar.
    """
    client_id = os.environ.get("YT_CLIENT_ID")
    client_secret = os.environ.get("YT_CLIENT_SECRET")
    refresh_token = os.environ.get("YT_REFRESH_TOKEN")
    
    if not client_id or not client_secret:
        raise ValueError("YT_CLIENT_ID y YT_CLIENT_SECRET son requeridos")
    
    if refresh_token:
        # Producción: usar refresh_token directamente
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=SCOPES,
        )
        creds.refresh(Request())
        return creds
    
    # Desarrollo local: OAuth flow interactivo
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
        }
    }
    
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8090)
    
    # Guardar token para reutilizar
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    
    log.info(f"Token guardado en {TOKEN_FILE}")
    log.info(f"REFRESH_TOKEN para copiar a variables de entorno:\n{creds.refresh_token}")
    
    return creds


def _build_description(description: str, tags: list) -> str:
    """Construye descripción optimizada para YouTube."""
    hashtags = " ".join(f"#{t.replace(' ', '')}" for t in tags[:15])
    
    return f"""{description}

━━━━━━━━━━━━━━━━━━━━━━━
🕰️ Bitácora del Tiempo
Historia que nadie te contó.
━━━━━━━━━━━━━━━━━━━━━━━

{hashtags}

#Shorts #Historia #Curiosidades #BitacoraDelTiempo #DatosHistoricos"""


def upload_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: list,
    thumbnail_path: str = None,
    category_id: str = "27",  # 27 = Education
    privacy: str = "public",
) -> dict:
    """
    Sube video a YouTube como Short.
    
    Returns:
        dict con 'video_id' y 'url'
    """
    creds = _get_credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    
    # Asegurar que el título tiene #Shorts para clasificarlo
    if "#Shorts" not in title and "#shorts" not in title:
        title = title[:90] + " #Shorts"
    
    full_description = _build_description(description, tags)
    
    body = {
        "snippet": {
            "title": title[:100],
            "description": full_description[:5000],
            "tags": tags[:500],  # Max 500 chars total
            "categoryId": category_id,
            "defaultLanguage": "es",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
            "madeForKids": False,
        },
    }
    
    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024,  # 5MB chunks
    )
    
    log.info(f"Iniciando upload: '{title[:60]}'")
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    
    # Upload con progreso
    response = None
    retry_count = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                log.info(f"Upload: {progress}%")
        except Exception as e:
            if retry_count < 5:
                retry_count += 1
                wait = 2 ** retry_count
                log.warning(f"Upload error (retry {retry_count}/5 en {wait}s): {e}")
                time.sleep(wait)
            else:
                raise
    
    video_id = response["id"]
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    
    log.info(f"Video subido: {video_url}")
    
    # Subir thumbnail si existe
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            log.info("Thumbnail subido OK")
        except Exception as e:
            log.warning(f"Thumbnail falló (no crítico): {e}")
    
    return {"video_id": video_id, "url": video_url}


def get_refresh_token_interactive():
    """
    Ejecutar este script localmente para obtener el refresh_token.
    Uso: python youtube_uploader.py
    """
    print("=== Obteniendo YouTube Refresh Token ===")
    print("Necesitas: YT_CLIENT_ID y YT_CLIENT_SECRET en tu .env")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    creds = _get_credentials()
    print(f"\n✅ REFRESH TOKEN OBTENIDO:")
    print(f"YT_REFRESH_TOKEN={creds.refresh_token}")
    print("\nCopia este valor a tus variables de entorno en Render y GitHub Secrets")


if __name__ == "__main__":
    get_refresh_token_interactive()
