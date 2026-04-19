# Music Agent v2 — Nuevas Skills: Spotify Trends + Competitor Intel + YouTube Growth

## Contexto

Este documento extiende el spec base de `lyria-music-agent` con 5 nuevas capacidades acordadas.
El agente ya está deployado y funcionando en VPS. Estos cambios se implementan **encima** de la arquitectura existente sin romper nada.

---

## Resumen de Cambios

| Archivo | Tipo | Prioridad |
|---|---|---|
| `core/spotify_trend_analyzer.py` | NUEVO | P0 |
| `core/competitor_analyzer.py` | NUEVO | P0 |
| `core/niche_analyzer.py` | MODIFICAR | P0 |
| `pipeline/video_creator.py` | MODIFICAR | P1 |
| `main.py` | MODIFICAR | P1 |
| `requirements.txt` | MODIFICAR | P0 |
| Google Cloud OAuth Consent | ACCIÓN MANUAL | P0 urgente |

---

## ⚠️ Acción Manual Urgente — Antes de Implementar Código

El OAuth Consent Screen de YouTube en modo **Testing** expira el refresh token cada **7 días**.
Si no se hace esto, el agente dejará de subir videos a YouTube silenciosamente.

**Pasos:**
1. Ir a [console.cloud.google.com](https://console.cloud.google.com)
2. APIs & Services → OAuth Consent Screen
3. Publishing status: **"In production"** → Confirm
4. Borrar `youtube_token.json` de la VPS y re-autenticar desde la máquina local

---

## `requirements.txt` — Agregar

```txt
yt-dlp==2024.12.23
pytrends==4.9.2
```

Estas dos líneas se suman a las existentes. No reemplaza nada.

---

## NUEVO: `core/spotify_trend_analyzer.py`

**Qué hace:** Consulta el Top 10 global de Spotify Charts (endpoint público, sin auth) y usa Gemini
para extraer 5 géneros instrumentales derivados. Nunca copia artistas ni canciones — solo lee tendencias.

**Regla legal crítica:** Los prompts que se generan desde aquí NO deben incluir nombres de artistas
ni títulos de canciones con copyright. Solo géneros puros: "trap instrumental 140 BPM", no
"en el estilo de Bad Bunny".

```python
# core/spotify_trend_analyzer.py
import requests
import json
import os
import google.generativeai as genai

SPOTIFY_CHARTS_ENDPOINT = (
    "https://charts-spotify-com-service.spotify.com/public/v0/charts"
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-exp")


def get_spotify_top_tracks(region: str = "global") -> list:
    """
    Extrae metadata del Top 10 global de Spotify Charts.
    No descarga audio. No viola copyright. Solo lee metadata pública.
    Retorna lista vacía si el endpoint falla (fallback a SEED_NICHES).
    """
    try:
        res = requests.get(SPOTIFY_CHARTS_ENDPOINT, timeout=10)
        res.raise_for_status()
        data = res.json()
        entries = data["chartEntryViewResponses"][0]["entries"]

        tracks = [
            {
                "rank": e["chartEntryData"]["currentRank"],
                "title": e["trackMetadata"]["trackName"],
                "artist": e["trackMetadata"]["artists"][0]["name"],
            }
            for e in entries[:10]
        ]
        return tracks

    except Exception as e:
        print(f"[spotify_trends] charts no disponible: {e}")
        return []


def extract_niches_from_charts(tracks: list) -> list:
    """
    Gemini analiza el Top 10 y devuelve 5 géneros instrumentales derivados.
    Output: lista de strings compatibles con NICHE_PARAMS de prompt_builder.py
    Si Gemini falla, retorna lista vacía (se usa SEED_NICHES como fallback).
    """
    if not tracks:
        return []

    try:
        response = model.generate_content(f"""
Analizá este Top 10 actual de Spotify Charts:
{json.dumps(tracks, indent=2)}

Tarea: extraé 5 GÉNEROS MUSICALES INSTRUMENTALES que estos tracks representan.

Reglas estrictas:
- NO nombres de artistas
- NO títulos de canciones
- SÍ géneros puros con BPM aproximado: "trap instrumental 140 BPM"
- Orientados a royalty-free, sync licensing (YouTube, Pond5)
- En español, compatibles con estos formatos existentes:
  "lofi hip hop para estudiar", "música épica cinematográfica para trailers",
  "synthwave retro 80s", "trap beats instrumentales"

Respondé SOLO con un JSON array de 5 strings. Sin explicación.
Ejemplo: ["trap beats oscuros 140 BPM", "pop electrónico bailable 120 BPM"]
""")

        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        niches = json.loads(text.strip())
        return niches[:5]

    except Exception as e:
        print(f"[spotify_trends] Gemini extracción falló: {e}")
        return []
```

---

## NUEVO: `core/competitor_analyzer.py`

**Qué hace:** Usa `yt-dlp` para extraer metadata (títulos, views, tags, duración) de los top videos
de canales competidores. Luego Gemini analiza patrones ganadores y los devuelve como instrucciones
para `niche_analyzer.py` y `prompt_builder.py`.

**Sin descargas de audio:** `skip_download: True` y `extract_flat: True` — solo lee metadata.

```python
# core/competitor_analyzer.py
import yt_dlp
import json
import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash-exp")

# Canales de referencia — los más grandes de royalty-free music en YouTube
COMPETITOR_CHANNELS = [
    "https://www.youtube.com/@ChilledCow/videos",
    "https://www.youtube.com/@EpicMusicVn/videos",
    "https://www.youtube.com/@NoCopyrightSounds/videos",
    "https://www.youtube.com/@Lofi-Girl/videos",
]


def analyze_top_videos(channel_url: str, limit: int = 10) -> list:
    """
    Extrae metadata de los videos más recientes de un canal.
    No descarga nada — solo lee títulos, views, tags, duración.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlist_items": f"1:{limit}",
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            return [
                {
                    "title": v.get("title", ""),
                    "views": v.get("view_count", 0),
                    "duration_sec": v.get("duration", 0),
                    "tags": v.get("tags", [])[:10],
                }
                for v in (info.get("entries") or [])
                if v
            ]
    except Exception as e:
        print(f"[competitor] Error en {channel_url}: {e}")
        return []


def extract_winning_patterns() -> dict:
    """
    Analiza todos los canales competidores y devuelve patrones ganadores:
    - keywords más frecuentes en títulos top
    - duración promedio de videos más vistos
    - template de título recomendado
    - estilo de thumbnail recomendado (oscuro, brillante, minimalista, etc.)

    Retorna dict con claves: keywords, title_template, avg_duration_min,
    thumbnail_style, top_tags
    """
    all_videos = []
    for channel in COMPETITOR_CHANNELS:
        videos = analyze_top_videos(channel, limit=10)
        all_videos.extend(videos)

    if not all_videos:
        return {}

    # Top 10 por views
    top_videos = sorted(
        all_videos,
        key=lambda x: x.get("views") or 0,
        reverse=True
    )[:10]

    top_titles = [v["title"] for v in top_videos]
    avg_duration = (
        sum(v.get("duration_sec", 0) for v in top_videos) / len(top_videos) / 60
    )

    try:
        response = model.generate_content(f"""
Analizá estos títulos de los 10 videos más vistos en canales top de royalty-free music:
{json.dumps(top_titles, indent=2)}

Duración promedio: {avg_duration:.1f} minutos.

Extraé:
1. keywords: Las 10 palabras/frases más exitosas para SEO en YouTube
2. title_template: La estructura de título más efectiva
   Ejemplo: "[Mood] Music for [Activity] | No Copyright | Free to Use"
3. avg_duration_min: Duración óptima en minutos (número entero)
4. thumbnail_style: Descripción de estética ganadora en 1 línea
   Ejemplo: "fondo oscuro azul marino, texto blanco grande, ícono musical dorado"
5. top_tags: Los 15 tags más relevantes para este nicho

Respondé en JSON con claves:
keywords, title_template, avg_duration_min, thumbnail_style, top_tags
""")

        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        patterns = json.loads(text.strip())
        patterns["avg_duration_min"] = int(avg_duration)
        return patterns

    except Exception as e:
        print(f"[competitor] Gemini análisis falló: {e}")
        return {"avg_duration_min": int(avg_duration)}
```

---

## MODIFICAR: `core/niche_analyzer.py`

**Cambios vs versión actual:**
1. `get_weekly_niches()` ahora acepta `count=10` por defecto
2. Combina 5 nichos de Spotify trends + 5 de SEED_NICHES evergreen
3. Integra `extract_winning_patterns()` para enriquecer la metadata generada
4. `analyze_niche_and_create_prompt()` recibe `patterns` como contexto adicional

```python
# core/niche_analyzer.py — DIFF de cambios (agregar a lo existente)

# 1. Nuevos imports al inicio del archivo:
from core.spotify_trend_analyzer import get_spotify_top_tracks, extract_niches_from_charts
from core.competitor_analyzer import extract_winning_patterns


# 2. Reemplazar get_weekly_niches() completo:
def get_weekly_niches(count: int = 10) -> list:
    """
    Combina:
    - 5 nichos derivados del Top 10 actual de Spotify (tendencias reales)
    - 5 nichos de SEED_NICHES (evergreen probados)
    Total por defecto: 10 tracks por semana
    """
    # Spotify trends (5 nichos)
    spotify_tracks = get_spotify_top_tracks()
    trend_niches = extract_niches_from_charts(spotify_tracks)
    print(f"  📊 Nichos de Spotify trends: {len(trend_niches)}")

    # SEED_NICHES evergreen (5 nichos)
    history_file = "data/niches.json"
    used = []
    if os.path.exists(history_file):
        with open(history_file) as f:
            used = json.load(f).get("used_last_30_days", [])

    available_seed = [n for n in SEED_NICHES if n not in used]
    if len(available_seed) < 5:
        available_seed = SEED_NICHES

    seed_selection = random.sample(available_seed, min(5, len(available_seed)))

    # Combinar — trends primero, luego evergreen, deduplicar
    combined = list(dict.fromkeys(trend_niches + seed_selection))[:count]

    # Si trends falló (Spotify endpoint caído), usar solo seed
    if len(combined) < count:
        extras = [n for n in SEED_NICHES if n not in combined]
        combined += random.sample(extras, min(count - len(combined), len(extras)))

    # Guardar historial
    os.makedirs("data", exist_ok=True)
    with open(history_file, "w") as f:
        json.dump({
            "used_last_30_days": used + combined,
            "last_run": __import__("datetime").datetime.now().isoformat()
        }, f, indent=2)

    print(f"  ✅ Total nichos seleccionados: {len(combined)}")
    return combined


# 3. Enriquecer analyze_niche_and_create_prompt() con patterns:
# Agregar parámetro opcional patterns al inicio de la función existente:
def analyze_niche_and_create_prompt(niche: str, patterns: dict = None) -> dict:
    """
    Genera metadata completa para un nicho.
    Si se pasan patterns (de competitor_analyzer), los usa para mejorar
    el título, tags y descripción del video.
    """
    patterns_context = ""
    if patterns:
        patterns_context = f"""
Contexto adicional del análisis de competencia:
- Template de título ganador: {patterns.get("title_template", "")}
- Keywords top: {", ".join(patterns.get("keywords", [])[:5])}
- Tags recomendados: {", ".join(patterns.get("top_tags", [])[:10])}
- Estilo de thumbnail: {patterns.get("thumbnail_style", "")}
Usá este contexto para mejorar el SEO del título y los tags.
"""
    # ... resto del prompt existente, agregando patterns_context al f-string
```

---

## MODIFICAR: `pipeline/video_creator.py`

**Cambios:** Agregar función `create_youtube_short()` al final del archivo existente.
No modifica nada de lo que ya funciona.

```python
# Agregar al final de pipeline/video_creator.py

def create_youtube_short(
    audio_path: str,
    thumbnail_path: str,
    output_path: str,
    duration_sec: int = 59
) -> str:
    """
    Genera versión vertical 1080x1920 para YouTube Shorts.
    - Mismo audio del track completo, cortado a 59s
    - Formato vertical con thumbnail escalado y centrado
    - Visualizer de ondas en la parte inferior
    - -ac 2 para compatibilidad mono/estéreo (igual que video horizontal)
    """
    print(f"  📱 Creando YouTube Short...")

    cmd = [
        "ffmpeg",
        "-loop", "1",
        "-i", thumbnail_path,
        "-i", audio_path,
        "-t", str(duration_sec),
        "-ac", "2",
        "-filter_complex",
        # Escalar thumbnail a vertical, pad con negro, overlay visualizer
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black[bg];"
        "[1:a]showwaves=s=1080x300:mode=cline:"
        "colors=0x00ff88|0x0088ff:rate=30[waves];"
        "[bg][waves]overlay=0:1580[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        output_path, "-y"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"  ✅ Short creado: {output_path}")
        return output_path
    else:
        raise Exception(f"FFmpeg Short error: {result.stderr[-500:]}")
```

---

## MODIFICAR: `main.py`

**Cambios vs versión actual:**
1. `count=10` en `get_weekly_niches()`
2. Generar Short además del video normal (un call extra a `create_youtube_short`)
3. Subir Short a YouTube como video separado con `#Shorts` en el título
4. Cron dividido: lunes + jueves para distribuir carga (5 tracks cada día)
5. `competitor_analyzer.extract_winning_patterns()` se llama una sola vez antes del loop

```python
# main.py — DIFF de cambios

# 1. Nuevo import al inicio:
from pipeline.video_creator import create_youtube_short
from core.competitor_analyzer import extract_winning_patterns
from core.niche_analyzer import get_weekly_niches, analyze_niche_and_create_prompt


# 2. Al inicio de generate_and_publish_weekly(), antes del loop:
async def generate_and_publish_weekly():
    log.info("weekly_cycle_start")

    nichos = get_weekly_niches(count=10)  # ← era count=5
    pond5 = Pond5Uploader()

    # Analizar competencia UNA vez por ciclo (no por cada track)
    log.info("analyzing_competitors")
    patterns = extract_winning_patterns()
    log.info("patterns_ready", thumbnail_style=patterns.get("thumbnail_style", ""))

    results = []

    for i, niche in enumerate(nichos, 1):
        result = await process_niche(i, niche, pond5, patterns)
        if result:
            results.append(result)
        await asyncio.sleep(30)

    await notify(results)
    log.info("weekly_cycle_complete", published=len(results), total=len(nichos))


# 3. process_niche() recibe patterns y genera Short adicional:
async def process_niche(
    i: int, niche: str, pond5: Pond5Uploader, patterns: dict = None
) -> dict | None:

    try:
        # Pasar patterns a analyze_niche_and_create_prompt
        metadata = await asyncio.to_thread(
            analyze_niche_and_create_prompt, niche, patterns
        )

        base = f"output/audio/track_{i}_{niche.replace(' ', '_')[:20]}"
        track = await generate_track_with_fallback(niche, base)
        mp3_path = convert_wav_to_mp3(track["path"])

        thumb = f"output/video/track_{i}_thumb.jpg"
        video = f"output/video/track_{i}.mp4"
        short = f"output/video/track_{i}_short.mp4"

        create_thumbnail(metadata["yt_title"], metadata["mood"], thumb)
        create_video_with_visualizer(mp3_path, thumb, video)
        create_youtube_short(mp3_path, thumb, short)   # ← NUEVO

        # Metadata del Short — agregar #Shorts al título
        short_metadata = {
            **metadata,
            "title": f"{metadata['yt_title'][:60]} #Shorts",
            "tags": metadata.get("yt_tags", "") + ",shorts,short video,música corta",
        }

        # Subir video normal + Short + Pond5 en paralelo
        yt_task = asyncio.to_thread(upload_to_youtube, video, metadata, thumb)
        yt_short_task = asyncio.to_thread(upload_to_youtube, short, short_metadata, thumb)
        pond5_task = pond5.upload(track["path"], metadata)

        yt_url, yt_short_url, pond5_ok = await asyncio.gather(
            yt_task, yt_short_task, pond5_task,
            return_exceptions=True
        )

        result = {
            "title": metadata["yt_title"],
            "yt_url": yt_url if not isinstance(yt_url, Exception) else f"ERROR: {yt_url}",
            "yt_short_url": yt_short_url if not isinstance(yt_short_url, Exception) else "ERROR",
            "pond5": pond5_ok if not isinstance(pond5_ok, Exception) else False,
            "niche": niche,
            "bpm": metadata["bpm"],
            "provider": track["provider_used"],
        }

        # CSV log
        with open("data/tracks_log.csv", "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=result.keys())
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(result)

        return result

    except Exception as e:
        log.error("niche_failed", niche=niche, error=str(e))
        return None


# 4. Cron dividido — reemplazar las líneas de schedule al final:
# Lunes 2 AM → 5 tracks (nichos 1–5)
# Jueves 2 AM → 5 tracks (nichos 6–10)
# Nota: get_weekly_niches() con count=5 cada vez,
# el historial evita repeticiones automáticamente

schedule.every().monday.at("02:00").do(
    lambda: asyncio.run(generate_and_publish_weekly_partial(0, 5))
)
schedule.every().thursday.at("02:00").do(
    lambda: asyncio.run(generate_and_publish_weekly_partial(5, 10))
)


async def generate_and_publish_weekly_partial(start: int, end: int):
    """Genera un subset de nichos (para dividir lunes/jueves)."""
    log.info("partial_cycle_start", start=start, end=end)
    nichos = get_weekly_niches(count=10)
    subset = nichos[start:end]
    pond5 = Pond5Uploader()
    patterns = extract_winning_patterns()
    results = []
    for i, niche in enumerate(subset, start + 1):
        result = await process_niche(i, niche, pond5, patterns)
        if result:
            results.append(result)
        await asyncio.sleep(30)
    await notify(results)
```

---

## Verification Plan

### Tests unitarios nuevos

**1. `test_spotify_trends.py`**
```python
# Verificar que Spotify Charts retorna datos o falla silenciosamente
from core.spotify_trend_analyzer import get_spotify_top_tracks, extract_niches_from_charts

tracks = get_spotify_top_tracks()
print(f"Tracks obtenidos: {len(tracks)}")  # Esperado: 10 o 0

niches = extract_niches_from_charts(tracks)
print(f"Nichos extraídos: {niches}")        # Esperado: 5 strings en español
assert all(isinstance(n, str) for n in niches)
assert len(niches) <= 5
print("✅ spotify_trend_analyzer OK")
```

**2. `test_competitor_analyzer.py`**
```python
# Verificar que yt-dlp extrae metadata sin descargar audio
from core.competitor_analyzer import analyze_top_videos, extract_winning_patterns

# Test de un solo canal (rápido)
videos = analyze_top_videos(
    "https://www.youtube.com/@ChilledCow/videos", limit=3
)
print(f"Videos obtenidos: {len(videos)}")
assert all("title" in v for v in videos)

patterns = extract_winning_patterns()
print(f"Patterns: {patterns}")
assert "title_template" in patterns or patterns == {}
print("✅ competitor_analyzer OK")
```

**3. `test_short_creation.py`**
```python
# Verificar que FFmpeg genera Short vertical correcto
from pipeline.video_creator import create_youtube_short
import os

# Requiere un MP3 y thumbnail de prueba existentes
short_path = "output/video/test_short.mp4"
create_youtube_short(
    "output/audio/test_track.mp3",
    "output/video/test_thumb.jpg",
    short_path,
    duration_sec=10  # 10s para el test, rápido
)
assert os.path.exists(short_path)
assert os.path.getsize(short_path) > 10000  # > 10KB
print("✅ YouTube Short creation OK")
```

**4. Test de integración `count=10`**
```python
# En main.py, ejecutar con 2 nichos (no 10) para validar pipeline completo
# Descomentar temporalmente:
# asyncio.run(generate_and_publish_weekly_partial(0, 2))
```

---

## Notas de Implementación

### Sobre el endpoint de Spotify Charts
El endpoint `charts-spotify-com-service.spotify.com/public/v0/charts` es público pero no oficial.
Si cambia o retorna error 403, el agente usa automáticamente `SEED_NICHES` como fallback.
**No agregar autenticación de Spotify API** — no es necesaria para este caso de uso.

### Sobre yt-dlp y rate limiting
Si YouTube bloquea el scraping de metadata (Error 429), agregar en `analyze_top_videos()`:
```python
opts = {
    ...
    "sleep_interval": 2,         # esperar 2s entre requests
    "max_sleep_interval": 5,
}
```

### Sobre los YouTube Shorts y monetización
Los Shorts tienen umbral separado de monetización: **10M views en 90 días** para AdSense.
Sin embargo generan suscriptores mucho más rápido que videos normales.
La estrategia es usar Shorts para crecer el canal y los videos normales para el watch time.

### Sobre `patterns` en thumbnail
Cuando `competitor_analyzer` devuelva un `thumbnail_style` como
"fondo oscuro azul marino, texto blanco, ícono dorado", ese string puede pasarse
a `create_thumbnail()` como contexto para que Gemini sugiera ajustes de color.
Implementación futura — por ahora `create_thumbnail()` sigue usando `MOOD_COLORS`.
