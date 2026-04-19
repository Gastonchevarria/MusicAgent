# Arcadia Soundscapes — Daily Drip v2 Design Spec

**Fecha:** 2026-04-17
**Canal:** [Arcadia Soundscapes](https://www.youtube.com/@ArcadiaSoundscapes-ok)
**Enfoque elegido:** A — "Daily Drip" (1 track/dia)

---

## 1. Problema

El agente actual genera 5 tracks en batch semanal (miercoles 09:00). Esto causa:

1. **YouTube quota exceeded** — 5 tracks x 2 uploads (video + short) = 10 uploads = ~16,500 unidades. Limite diario: 10,000.
2. **Pond5 FTP auth failure** — `530 Failure to authenticate user`. Credenciales invalidas o expiradas.
3. **Telegram notification broken** — Errores de YouTube contienen HTML (`<a href>`) que rompe el parser de Telegram.
4. **Thumbnails inaceptables** — Texto cortado (sin word-wrap), fondos planos, emoji roto, sin branding.
5. **Videos basicos** — Imagen estatica + waveform blanco. Sin identidad visual.
6. **Sin Spotify trends** — Nichos solo de SEED_NICHES hardcoded, sin datos de tendencias reales.
7. **Schedule inconsistente** — Codigo: miercoles. Descripcion del canal: lunes.

## 2. Solucion: Daily Drip

Cambiar de batch semanal a **1 track por dia**, todos los dias a las 09:00 ART.

### 2.1 Quota math

| Operacion | Unidades YouTube API |
|---|---|
| Upload video largo | 1,600 |
| Set thumbnail (video) | 50 |
| Upload short | 1,600 |
| Set thumbnail (short) | 50 |
| **Total por dia** | **~3,300** |
| **Limite diario** | **10,000** |
| **Margen restante** | **~6,700 (para retries + pending queue)** |

### 2.2 Flujo diario (09:00 ART)

```
1. Chequear data/pending_uploads/ (retry de dias anteriores, max 2)
2. Subir pendientes si existen
3. Seleccionar nicho del dia (del pool semanal)
4. Generar track (Lyria -> Stable Audio -> MusicGen fallback)
5. Convertir WAV -> MP3
6. Crear thumbnail con branding Arcadia
7. Crear video largo (1280x720) con spectrum analyzer
8. Crear YouTube Short (1080x1920) con spectrum bars
9. Subir video + short a YouTube en paralelo
10. Subir WAV a Pond5 (1 intento, no bloqueante)
11. Notificar por Telegram
```

### 2.3 Pool semanal de nichos

Generado cada lunes a las 08:50 (antes del primer track de la semana):

- **4 nichos de Spotify trends** via `spotify_trend_analyzer.py`
- **3 nichos de SEED_NICHES** evergreen (rotacion sin repetir en 30 dias)
- **Total: 7 nichos** (1 por dia, lunes a domingo)
- Guardado en `data/weekly_pool.json`

Si Spotify Charts falla: se usan 7 de SEED_NICHES como fallback.

---

## 3. Archivo nuevo: `core/spotify_trend_analyzer.py`

**Responsabilidad:** Consultar Top 10 global de Spotify Charts (endpoint publico, sin auth) y usar Gemini para extraer generos instrumentales derivados.

**Funciones:**
- `get_spotify_top_tracks(region="global") -> list` — Extrae metadata del Top 10 (rank, titulo, artista). Retorna lista vacia si falla.
- `extract_niches_from_charts(tracks: list) -> list` — Gemini analiza Top 10 y devuelve 4 generos instrumentales puros.

**Regla legal critica:** Los prompts generados NUNCA incluyen nombres de artistas ni titulos de canciones. Solo generos puros: "trap instrumental 140 BPM", no "estilo Bad Bunny".

**Modelo:** `gemini-2.0-flash` (estable, no `-exp`).

**Endpoint Spotify:** `https://charts-spotify-com-service.spotify.com/public/v0/charts` — publico pero no oficial. Si retorna 403, fallback silencioso a SEED_NICHES.

---

## 4. Modificar: `core/competitor_analyzer.py`

**Cambios vs actual:**

| Aspecto | Actual | Nuevo |
|---|---|---|
| Frecuencia | Cada track (random 1 canal) | 1 vez por semana (lunes, cacheado) |
| Modelo | Claude Opus (caro) | Gemini Flash (rapido, barato) |
| Output | keywords, title_template | + thumbnail_style, top_tags |
| Canales | 3 (ChilledCow, EpicMusicVn, NCS) | + Lofi Girl (4 total) |
| Cache | No existe | `data/competitor_patterns.json`, valido 7 dias |

**Flujo:** Lunes 08:50 -> yt-dlp metadata de 4 canales -> Gemini analiza top 10 videos -> guarda patterns en JSON -> disponible para los 7 tracks de la semana.

---

## 5. Modificar: `core/niche_analyzer.py`

**Cambios:**

1. `get_weekly_niches(count=7)` — genera pool semanal combinando Spotify trends + SEED_NICHES
2. `get_daily_niche(day_index: int) -> str` — nueva funcion que retorna el nicho del dia desde el pool
3. `analyze_niche_and_create_prompt(niche, patterns=None)` — acepta `patterns` de competitor_analyzer como contexto adicional para mejorar SEO. **Eliminar** la llamada directa a `analyze_top_videos()` y `extract_winning_patterns()` que actualmente se ejecuta por cada track — los patterns ahora vienen pre-cacheados como parametro.
4. Pool persistido en `data/weekly_pool.json` con fecha de generacion

---

## 6. Modificar: `pipeline/video_creator.py` — Thumbnails

**Reescritura completa de `create_thumbnail()`.**

### Paleta cosmica por mood (familia Arcadia)

| Mood | Color primario | Color secundario |
|---|---|---|
| calm, peaceful, relaxing | #0a0e27 (azul profundo) | #1a3a5c (cyan oscuro) |
| epic, dramatic, powerful | #1a0a2e (purpura oscuro) | #2e0a1a (rojo profundo) |
| energetic, happy | #0a1a3e (azul) | #0a3e3e (teal) |
| dark, aggressive | #050510 (negro) | #1a0a2e (purpura) |
| cozy, warm | #0d1b2a (azul marino) | #2a1a0d (ambar oscuro) |

### Elementos del thumbnail

1. **Fondo:** Gradiente radial multi-capa desde el centro (mas claro) hacia bordes (mas oscuro). Simulado con circulos concentricos en Pillow.
2. **Particulas/estrellas:** Puntos blancos aleatorios con opacidad variable para efecto cosmico. Generados con `ImageDraw.ellipse()`.
3. **Titulo:** Auto-sizing + word-wrap. Maximo 3 lineas. Font DejaVuSans-Bold. Text shadow oscuro para profundidad. Centrado en el 70% central del canvas.
4. **Branding:** "Arcadia Soundscapes" fijo abajo, font pequena, color semi-transparente.
5. **Borde glow:** Rectangulo interior con bordes difuminados (efecto luminoso sutil).
6. **Sin emojis** — eliminados completamente.

---

## 7. Modificar: `pipeline/video_creator.py` — Videos

### Video largo (1280x720)

**Cambios en `create_video_with_visualizer()`:**

1. **Visualizer:** Reemplazar `showwaves` (linea basica) con `showfreqs=mode=bar` (spectrum analyzer barras). Colores: cyan (#00ccff) a purpura (#8800ff) gradient.
2. **Efecto breathing:** `zoompan` filter sutil (zoom 1.0 -> 1.02 -> 1.0) en loop sobre el thumbnail de fondo.
3. **Overlay de texto:** `drawtext` con "Arcadia Soundscapes" semi-transparente en la esquina inferior.
4. **Encoding:** Se mantiene libx264 + AAC 192k + yuv420p.

### YouTube Short (1080x1920)

**Cambios en `create_youtube_short()`:**

1. **Layout:** Thumbnail en mitad superior, visualizer en mitad inferior.
2. **Visualizer:** Spectrum bars verticales centradas, colores cyan/purpura.
3. **Texto:** Nombre del track arriba, "Arcadia Soundscapes" abajo.
4. **Duracion:** 59s — se mantiene.

---

## 8. Modificar: `main.py`

### Cambios estructurales

1. **Schedule:** `schedule.every().day.at("09:00")` (era `.wednesday`)
2. **Pool semanal:** Lunes 08:50 genera pool de 7 nichos + competitor patterns
3. **Retry queue:** Antes de generar, chequear `data/pending_uploads/` y subir pendientes (max 2/dia)
4. **process_niche():** Recibe `patterns` de competitor_analyzer
5. **Pond5:** 1 intento, si falla loguea y sigue (no bloqueante)
6. **Error handling:** Notificacion Telegram inmediata en fallos criticos

### Logica de seleccion de nicho diario

```python
import datetime

def get_today_niche_index():
    """Lunes=0, Martes=1, ..., Domingo=6"""
    return datetime.date.today().weekday()
```

El pool se regenera cada lunes. De martes a domingo se consume el pool existente.

### Retry queue

```
data/pending_uploads/
    track_20260415_epic_cinematic.json  # metadata + paths
    track_20260415_epic_cinematic.mp4   # video listo
    track_20260415_epic_cinematic_short.mp4
    track_20260415_epic_cinematic_thumb.jpg
```

Antes del track del dia:
1. Leer archivos en `data/pending_uploads/`
2. Subir max 2 (para dejar quota para el track nuevo)
3. Si el upload funciona, borrar de pending
4. Si falla de nuevo, dejar para manana

---

## 9. Modificar: `pipeline/telegram_notifier.py`

**Cambios:**
1. `sanitize_html(text)` — nueva funcion que stripea tags HTML de strings de error antes de construir el mensaje
2. `notify_error(error_type, details)` — nueva funcion para notificacion inmediata de fallos criticos (no esperar al final del ciclo)
3. El `notify()` existente se adapta para reporte diario (1 track) en vez de semanal (5 tracks)

---

## 10. Error handling y resiliencia

| Escenario | Comportamiento |
|---|---|
| Los 3 providers fallan | Logea + notifica Telegram + no publica nada hoy |
| YouTube quota exceeded | Guarda en pending_uploads/ + reintenta manana |
| YouTube 401 (token expirado) | Notifica Telegram: "Re-autenticar manualmente" |
| Pond5 FTP falla | 1 intento, logea, continua sin bloquear |
| Telegram falla | Solo logea (no bloquea nada) |
| Spotify Charts falla | Usa solo SEED_NICHES (fallback silencioso) |
| Competitor yt-dlp falla | Usa patterns cacheados o ninguno |

---

## 11. Acciones manuales requeridas

1. **OAuth Consent Screen -> "In production"** en Google Cloud Console. Sin esto, el refresh token expira cada 7 dias y los uploads fallan silenciosamente.
2. **Verificar credenciales Pond5 FTP** — `530 Failure to authenticate` indica credenciales invalidas.
3. **Rotar API keys** (recomendado) — el .env contiene credenciales que fueron leidas en texto plano.

---

## 12. Archivos — Resumen de cambios

### Crear
| Archivo | Descripcion |
|---|---|
| `core/spotify_trend_analyzer.py` | Spotify Charts + Gemini -> nichos trending |

### Modificar
| Archivo | Cambios |
|---|---|
| `main.py` | Schedule diario, retry queue, competitor patterns semanal |
| `core/niche_analyzer.py` | Pool semanal 7 nichos, seleccion diaria, patterns como contexto |
| `core/competitor_analyzer.py` | Gemini Flash, cache JSON semanal, +Lofi Girl, +thumbnail_style |
| `pipeline/video_creator.py` | Thumbnails Arcadia, spectrum analyzer, breathing effect, branding |
| `pipeline/telegram_notifier.py` | Sanitizar HTML, notify_error(), formato diario |

### No tocar
| Archivo | Razon |
|---|---|
| `providers/*` | Funcionan correctamente |
| `pipeline/youtube_uploader.py` | El upload funciona, problema era quota |
| `pipeline/pond5_uploader.py` | Solo cambia retry logic en main.py |
| `core/prompt_builder.py` | Prompts por provider estan bien |
| `core/retry.py` | Se mantiene |
| `core/trend_analyzer.py` | Se mantiene — `validate_tags_with_search_volume()` sigue en uso |
| `music_generator.py` | WAV->MP3 funciona |
| `requirements.txt` | Ya tiene yt-dlp y pytrends |
