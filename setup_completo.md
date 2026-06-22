# 📋 Setup Completo — Bitácora del Tiempo
## Guía paso a paso para configurar todo sin ayuda

---

## CUENTAS NECESARIAS (todas gratuitas)

| Cuenta | URL | Para qué |
|--------|-----|----------|
| Google Cloud | console.cloud.google.com | YouTube API + Gemini |
| Google AI Studio | aistudio.google.com | Gemini API Key |
| Hugging Face | huggingface.co | Imágenes SDXL fallback |
| Render.com | render.com | Servidor 24/7 gratis |
| GitHub | github.com | Código + Actions |

---

## FASE 1: API KEYS (20 min)

### A. Gemini API Key
1. Ir a https://aistudio.google.com/app/apikey
2. Click **Create API Key**
3. Copiar → guardar en `.env` como `GEMINI_API_KEY=...`

### B. Hugging Face Token
1. Ir a https://huggingface.co/settings/tokens
2. Click **New token** → nombre: "bitacora" → tipo: **Read**
3. Copiar → guardar en `.env` como `HF_TOKEN=hf_...`

### C. YouTube OAuth (pasos exactos)
1. Ir a https://console.cloud.google.com
2. Click **Select project** → **New Project** → nombre: "BitacoraDelTiempo" → Create
3. Menu lateral → **APIs & Services** → **Library**
4. Buscar "YouTube Data API v3" → Click → **Enable**
5. Menu lateral → **APIs & Services** → **Credentials**
6. Click **+ Create Credentials** → **OAuth client ID**
7. Si pide configurar pantalla: **Configure Consent Screen** → External → Fill:
   - App name: "Bitácora del Tiempo"
   - User support email: tu email
   - Developer email: tu email
   - Save and Continue (skip todo lo demás)
   - Back to Dashboard
8. Volver a Create Credentials → OAuth client ID
9. Application type: **Desktop app** → nombre: "BitacoraDesktop" → Create
10. Copiar **Client ID** y **Client Secret** → guardar en `.env`

### D. Obtener Refresh Token (en tu Lenovo)
```bash
# En tu PC local con .env completo:
cd C:\Users\margs\OneDrive\Documents\Claude\Projects\yotube Bitacora del tiempo
pip install -r requirements.txt
python youtube_uploader.py
# Se abre Chrome → Seleccionar tu cuenta YouTube → Permitir
# Terminal muestra: YT_REFRESH_TOKEN=1//0...
# COPIA ESE TOKEN
```

---

## FASE 2: GITHUB (5 min)

### Subir código
```bash
cd C:\Users\margs\OneDrive\Documents\Claude\Projects\yotube Bitacora del tiempo
git init  # si no existe
git remote add origin https://github.com/Margi15/bitacora-del-tiempo.git
git add .
git commit -m "feat: Bitácora v2 — pipeline completo"
git push origin main --force
```

### Agregar Secrets en GitHub
1. Ir a https://github.com/Margi15/bitacora-del-tiempo
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** y agregar:
   - `RENDER_URL` → lo obtienes en Fase 3 (hacerlo después)

---

## FASE 3: RENDER.COM (10 min)

### Deploy del servidor
1. Ir a https://render.com → **Sign in with GitHub**
2. Click **New +** → **Web Service**
3. **Connect** el repo: `Margi15/bitacora-del-tiempo`
4. Configurar:
   - **Name**: `bitacora-del-tiempo`
   - **Runtime**: Docker
   - **Plan**: Free
   - **Region**: Oregon (US West)
5. Click **Advanced** → **Add Environment Variable** → agregar TODOS:

   ```
   GEMINI_API_KEY    = [tu key]
   HF_TOKEN          = [tu token]
   YT_CLIENT_ID      = [tu client id]
   YT_CLIENT_SECRET  = [tu secret]
   YT_REFRESH_TOKEN  = [tu refresh token]
   TTS_VOICE         = es-MX-JorgeNeural
   TTS_RATE          = +10%
   OUTPUT_DIR        = /tmp/bitacora
   PORT              = 8080
   ```

6. Click **Create Web Service** → esperar 5-8 minutos
7. Copiar tu URL: `https://bitacora-del-tiempo.onrender.com`

### Verificar que funciona
```bash
curl https://bitacora-del-tiempo.onrender.com/health
# Respuesta: {"status":"ok","version":"2.0.0",...}
```

### Agregar URL a GitHub Secrets
- Volver a GitHub Secrets → agregar `RENDER_URL` = `https://bitacora-del-tiempo.onrender.com`

---

## FASE 4: MAKE.COM (5 min)

1. Ir a https://make.com → tu cuenta existente
2. Click **Create a new scenario**
3. Click el ícono de los tres puntos (⋯) → **Import Blueprint**
4. Pegar el contenido completo de `make_scenario_blueprint.json`
5. Click **Save**
6. Hacer click en el módulo HTTP → cambiar URL a tu URL real de Render
7. Hacer click en el módulo Gmail → conectar tu cuenta Gmail
8. En el trigger: configurar horario (cada 2h24min para 10 diarios)
9. Click **Activate** (toggle verde)

---

## FASE 5: PRUEBA LOCAL EN LENOVO

```bash
# 1. Instalar ffmpeg (solo una vez)
winget install ffmpeg
# Si no funciona: https://ffmpeg.org/download.html → Windows build → copiar a C:\ffmpeg\bin → agregar al PATH

# 2. Instalar Python dependencies
cd "C:\Users\margs\OneDrive\Documents\Claude\Projects\yotube Bitacora del tiempo"
pip install -r requirements.txt

# 3. Crear .env con tus keys reales (copiar .env.example y editar)
copy .env.example .env
notepad .env

# 4. Iniciar servidor
python bitacora_server.py

# 5. En otra terminal, probar:
curl -X POST http://localhost:8080/generate_single
# Resultado esperado: {"status":"ok","youtube_url":"https://..."}
```

---

## VERIFICACIÓN FINAL

✅ `/health` responde en Render  
✅ GitHub Actions se ve en pestaña "Actions" del repo  
✅ Make.com escenario está Activo (verde)  
✅ El primer Short se generó correctamente  

---

## MANTENIMIENTO MENSUAL (5 minutos)

- Verificar que Render sigue activo (no pausado por inactividad)
- Render free pausa el servicio si tiene 0 deploys en 90 días → hacer un push vacío
- GitHub Actions free: 2,000 min/mes → 10 shorts × 30 días = ~300 min usados (seguro)

---

## SI ALGO FALLA

**Render muestra "Build failed":**
```bash
# Ver logs en Render Dashboard → Logs → buscar el error
# Más común: dependencia faltante en requirements.txt
```

**GitHub Actions falla:**
- Actions → ver el workflow → click en el paso que falla
- Más común: RENDER_URL secret no configurado

**Video sin imagen (fondo negro):**
- Wikimedia y HF fallaron → el gradiente oscuro se usa automáticamente
- No es un error crítico, el video igual se publica

**YouTube "quota exceeded":**
- La API YouTube tiene límite de 10,000 unidades/día
- Cada upload cuesta ~1,600 unidades → máximo 6 videos/día con cuenta nueva
- Solución: esperar 24h o crear proyecto nuevo en Google Cloud
