# 🕰️ Bitácora del Tiempo — YouTube Shorts Automatizados

Pipeline 100% automático que publica 10 YouTube Shorts diarios sobre historia viral.

## Arquitectura

```
GitHub Actions (10x/día)
    ↓ HTTP POST
Render.com (Flask server)
    ↓
Wikipedia API → Gemini Flash → Wikimedia/HF SDXL → edge-tts → moviepy → YouTube
```

## Archivos del Proyecto

| Archivo | Función |
|---------|---------|
| `bitacora_server.py` | Servidor Flask principal |
| `script_writer.py` | Guiones virales con Gemini Flash |
| `image_generator.py` | Imágenes de Wikimedia + HF SDXL |
| `voice_generator.py` | Narración con edge-tts (JorgeNeural) |
| `video_generator.py` | Ensamblado moviepy 1080x1920 |
| `youtube_uploader.py` | Subida YouTube API v3 |

## Setup Rápido (30 minutos)

### 1. GitHub
```bash
git clone https://github.com/Margi15/bitacora-del-tiempo.git
cd bitacora-del-tiempo
# Sube todos estos archivos
git add .
git commit -m "feat: pipeline v2 completo"
git push origin main
```

**GitHub Secrets** (Settings → Secrets → Actions):
- `RENDER_URL` → tu URL de Render

### 2. Render.com
1. Ir a https://render.com → New → Web Service
2. Conectar repo GitHub: `Margi15/bitacora-del-tiempo`
3. Runtime: **Docker**
4. Plan: **Free**
5. Agregar variables de entorno (copiar de `.env.example`)
6. Deploy → esperar ~5 min

### 3. YouTube OAuth (solo una vez, en tu Lenovo)
```bash
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus credenciales de Google Cloud
python youtube_uploader.py
# Se abre browser → autorizar → copia YT_REFRESH_TOKEN
# Agrega YT_REFRESH_TOKEN a variables de Render y GitHub Secrets
```

### 4. Probar en Lenovo
```bash
# Instalar ffmpeg primero
# Windows: winget install ffmpeg
pip install -r requirements.txt
cp .env.example .env  # Editar con tus keys reales
python bitacora_server.py
# En otra terminal:
curl -X POST http://localhost:8080/generate_single
```

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/health` | GET | Estado del servidor |
| `/generate_single` | POST | Genera 1 Short |
| `/generate_daily_batch` | POST | Genera N Shorts (body: `{"count": 10}`) |

## Make.com

1. Crear nuevo escenario → **Import Blueprint**
2. Pegar contenido de `make_scenario_blueprint.json`
3. Reemplazar `{{YOUR_RENDER_URL}}` y `{{YOUR_EMAIL}}`
4. Conectar Gmail cuando lo pida
5. Activar escenario

## Estilo Visual

- **Fondo**: imagen histórica real de Wikimedia Commons
- **Overlay**: negro 50% (no azul plano)
- **Texto**: blanco #FFFFFF con sombra negra difusa
- **Acento**: dorado #FFD700 para año y labels
- **Fuente**: Bebas Neue Bold (descarga automática)
- **Formato**: 1080×1920 vertical
- **Duración**: 58 segundos
- **Efecto**: Ken Burns zoom 1.0→1.08

## Troubleshooting

**El servidor en Render se duerme (free tier):**
El primer request del día tarda ~30s en despertar. El GitHub Actions tiene `timeout-minutes: 20` para manejarlo.

**Gemini API quota exceeded:**
Normal en free tier. El pipeline genera guion de todas formas con fallback hardcoded.

**HF_TOKEN no configurado:**
Sin token, las imágenes AI no funcionan pero Wikimedia Commons sigue funcionando.

**edge-tts falla:**
Requiere conexión a internet. En Render siempre funciona.

**Video se renderiza lento:**
Normal en Render free (1 CPU). Cada video tarda ~3-5 minutos.

## Variables de Entorno Requeridas

| Variable | Dónde obtener |
|----------|--------------|
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `HF_TOKEN` | https://huggingface.co/settings/tokens |
| `YT_CLIENT_ID` | Google Cloud Console → OAuth 2.0 |
| `YT_CLIENT_SECRET` | Google Cloud Console → OAuth 2.0 |
| `YT_REFRESH_TOKEN` | `python youtube_uploader.py` (una vez) |
