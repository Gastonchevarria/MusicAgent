# Daily Drip v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Arcadia Soundscapes music agent from weekly batch (broken by quota) to daily publishing with Spotify trends, competitor intelligence, and a complete visual overhaul.

**Architecture:** 7 files changed/created. Each task is independent except Task 6 (niche_analyzer depends on Tasks 2+3) and Task 7 (main.py wires everything). Tasks 1-5 can be parallelized.

**Tech Stack:** Python 3.11, Pillow, FFmpeg, google-genai, yt-dlp, schedule, structlog, asyncio

**Spec:** `docs/superpowers/specs/2026-04-17-daily-drip-v2-design.md`

---

## File Map

| Action | File | Responsibility |
|---|---|---|
| CREATE | `core/spotify_trend_analyzer.py` | Fetch Spotify Charts + Gemini extraction of instrumental niches |
| MODIFY | `core/competitor_analyzer.py` | Switch from Claude to Gemini, add JSON cache, add 4th channel |
| MODIFY | `core/niche_analyzer.py` | Weekly pool of 7 niches (4 Spotify + 3 evergreen), daily selection |
| MODIFY | `pipeline/video_creator.py` | Arcadia-branded thumbnails, spectrum analyzer videos, improved shorts |
| MODIFY | `pipeline/telegram_notifier.py` | HTML sanitization, error notifications, daily format |
| MODIFY | `main.py` | Daily schedule, retry queue, wire Spotify+competitor+niche together |
| CREATE | `tests/test_thumbnail.py` | Visual verification test for new thumbnails |
| CREATE | `tests/test_telegram_sanitize.py` | Unit tests for HTML sanitization |
| CREATE | `tests/test_niche_pool.py` | Unit tests for weekly pool and daily selection logic |

---

## Task 1: Fix Telegram Notifier (HTML sanitization + error notifications)

**Files:**
- Modify: `pipeline/telegram_notifier.py`
- Create: `tests/test_telegram_sanitize.py`

This fixes the `Can't parse entities` crash caused by YouTube error messages containing HTML tags like `<a href="/youtube/v3/getting-started#quota">`.

- [ ] **Step 1: Write the failing test for HTML sanitization**

Create `tests/test_telegram_sanitize.py`:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_sanitize_html_strips_tags():
    from pipeline.telegram_notifier import sanitize_html
    raw = 'The request cannot be completed because you have exceeded your <a href="/youtube/v3/getting-started#quota">quota</a>.'
    result = sanitize_html(raw)
    assert "<" not in result
    assert ">" not in result
    assert "quota" in result


def test_sanitize_html_handles_none():
    from pipeline.telegram_notifier import sanitize_html
    assert sanitize_html(None) == "N/A"
    assert sanitize_html("") == "N/A"


def test_sanitize_html_preserves_clean_text():
    from pipeline.telegram_notifier import sanitize_html
    assert sanitize_html("simple error message") == "simple error message"


def test_clean_uses_sanitize():
    """_clean should strip HTML AND escape Telegram markdown."""
    from pipeline.telegram_notifier import _clean
    raw = '<HttpError 403 "quota_exceeded">'
    result = _clean(raw)
    assert "<" not in result
    assert ">" not in result


if __name__ == "__main__":
    test_sanitize_html_strips_tags()
    test_sanitize_html_handles_none()
    test_sanitize_html_preserves_clean_text()
    test_clean_uses_sanitize()
    print("ALL TELEGRAM SANITIZE TESTS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python tests/test_telegram_sanitize.py`

Expected: `ImportError` or `AttributeError` because `sanitize_html` does not exist yet.

- [ ] **Step 3: Implement sanitize_html and notify_error in telegram_notifier.py**

Replace the full content of `pipeline/telegram_notifier.py`:

```python
import os
import re
import telegram
import structlog

log = structlog.get_logger()


def sanitize_html(text) -> str:
    """Strip HTML tags from error strings. YouTube API errors contain <a> tags."""
    if not text:
        return "N/A"
    text = str(text)
    return re.sub(r"<[^>]+>", "", text)


def _clean(text: str) -> str:
    """Sanitize HTML then escape Telegram Markdown special characters."""
    text = sanitize_html(text)
    for char in ["_", "*", "[", "]", "`"]:
        text = text.replace(char, f"\\{char}")
    return text


def _build_message(track_result: dict) -> str:
    """Build daily notification for a single track."""
    msg = "🎵 *Arcadia Soundscapes - Daily Track*\n\n"

    msg += f"*Nicho:* {_clean(track_result.get('niche', 'N/A'))}\n"
    msg += f"*Titulo:* {_clean(track_result.get('title', 'N/A'))}\n"
    msg += f"*Provider:* {_clean(track_result.get('provider', 'N/A'))}\n"
    msg += f"*BPM:* {track_result.get('bpm', 'N/A')}\n\n"

    yt_url = track_result.get("yt_url", "N/A")
    if not isinstance(yt_url, str) or yt_url.startswith("ERROR"):
        msg += f"▶️ *YouTube:* {_clean(str(yt_url))}\n"
    else:
        msg += f"▶️ *YouTube:* {yt_url}\n"

    yt_short = track_result.get("yt_short_url", "N/A")
    if not isinstance(yt_short, str) or yt_short.startswith("ERROR"):
        msg += f"📱 *Short:* {_clean(str(yt_short))}\n"
    else:
        msg += f"📱 *Short:* {yt_short}\n"

    msg += f"💰 *Pond5:* {'OK' if track_result.get('pond5') else 'Fallo'}\n"

    return msg


def _build_batch_message(track_results: list) -> str:
    """Build notification for multiple tracks (used for pending retries)."""
    msg = "🎵 *Arcadia Soundscapes - Reporte Diario*\n\n"
    msg += f"📦 *Tracks publicados:* {len(track_results)}\n\n"
    for i, track in enumerate(track_results, 1):
        msg += f"*{i}.* {_clean(track.get('title', 'N/A'))}\n"
        yt_url = track.get("yt_url", "N/A")
        if isinstance(yt_url, str) and not yt_url.startswith("ERROR"):
            msg += f"   ▶️ {yt_url}\n"
        msg += "\n"
    return msg


async def notify(track_results):
    """Send daily notification. Accepts a single dict or a list."""
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            log.warning("telegram_credentials_missing")
            return

        if isinstance(track_results, dict):
            message = _build_message(track_results)
        elif isinstance(track_results, list) and len(track_results) == 1:
            message = _build_message(track_results[0])
        else:
            message = _build_batch_message(track_results)

        bot = telegram.Bot(token=token)
        async with bot:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        log.info("telegram_notification_sent")

    except Exception as e:
        log.error("telegram_notification_failed", error=str(e))


async def notify_error(error_type: str, details: str):
    """Send immediate error notification for critical failures."""
    try:
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if not token or not chat_id:
            return

        details_clean = _clean(details)
        message = (
            f"⚠️ *Arcadia Soundscapes - Error*\n\n"
            f"*Tipo:* {_clean(error_type)}\n"
            f"*Detalle:* {details_clean[:500]}\n"
        )

        bot = telegram.Bot(token=token)
        async with bot:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        log.info("telegram_error_notification_sent", error_type=error_type)

    except Exception as e:
        log.error("telegram_error_notification_failed", error=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python tests/test_telegram_sanitize.py`

Expected: `ALL TELEGRAM SANITIZE TESTS PASSED`

- [ ] **Step 5: Commit**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add pipeline/telegram_notifier.py tests/test_telegram_sanitize.py
git commit -m "fix: sanitize HTML in Telegram notifications, add error alerts"
```

---

## Task 2: Create Spotify Trend Analyzer

**Files:**
- Create: `core/spotify_trend_analyzer.py`

This module fetches the Spotify Charts Top 10 and uses Gemini to extract instrumental genre niches. It returns pure genre strings — never artist names or song titles.

- [ ] **Step 1: Create `core/spotify_trend_analyzer.py`**

```python
"""
Spotify Charts trend analyzer.
Fetches public Top 10 global charts and uses Gemini to extract
instrumental genre niches for music generation.

Legal rule: NEVER include artist names or song titles in output.
Only pure genres: "trap instrumental 140 BPM", not "estilo Bad Bunny".
"""
import os
import json
import requests
import structlog
from google import genai

log = structlog.get_logger()

SPOTIFY_CHARTS_ENDPOINT = (
    "https://charts-spotify-com-service.spotify.com/public/v0/charts"
)


def get_spotify_top_tracks(region: str = "global") -> list:
    """
    Extract metadata from Spotify Charts Top 10 (public endpoint, no auth).
    Returns list of dicts with rank/title/artist, or empty list on failure.
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
        log.info("spotify_charts_fetched", count=len(tracks))
        return tracks

    except Exception as e:
        log.warning("spotify_charts_unavailable", error=str(e))
        return []


def extract_niches_from_charts(tracks: list) -> list:
    """
    Gemini analyzes Top 10 Spotify tracks and returns 4 instrumental genre
    niches derived from current trends.

    Returns list of strings compatible with NICHE_PARAMS in prompt_builder.py.
    Returns empty list if Gemini fails (caller falls back to SEED_NICHES).
    """
    if not tracks:
        return []

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.warning("GEMINI_API_KEY missing, skipping Spotify niche extraction")
        return []

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""Analiza este Top 10 actual de Spotify Charts:
{json.dumps(tracks, indent=2)}

Tarea: extrae 4 GENEROS MUSICALES INSTRUMENTALES que estos tracks representan.

Reglas estrictas:
- NO nombres de artistas
- NO titulos de canciones
- SI generos puros con BPM aproximado: "trap instrumental 140 BPM"
- Orientados a royalty-free, sync licensing (YouTube, Pond5)
- En espanol, compatibles con estos formatos existentes:
  "lofi hip hop para estudiar", "musica epica cinematografica para trailers",
  "synthwave retro 80s", "trap beats instrumentales"

Responde SOLO con un JSON array de 4 strings. Sin explicacion.
Ejemplo: ["trap beats oscuros 140 BPM", "pop electronico bailable 120 BPM"]""",
        )

        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        niches = json.loads(text.strip())
        log.info("spotify_niches_extracted", count=len(niches), niches=niches)
        return niches[:4]

    except Exception as e:
        log.warning("spotify_niche_extraction_failed", error=str(e))
        return []
```

- [ ] **Step 2: Verify module imports cleanly**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python -c "from core.spotify_trend_analyzer import get_spotify_top_tracks, extract_niches_from_charts; print('import OK')"`

Expected: `import OK`

- [ ] **Step 3: Commit**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add core/spotify_trend_analyzer.py
git commit -m "feat: add Spotify Charts trend analyzer with Gemini niche extraction"
```

---

## Task 3: Rewrite Competitor Analyzer (Claude -> Gemini + cache)

**Files:**
- Modify: `core/competitor_analyzer.py`

Changes: switch from Claude Opus to Gemini Flash, add weekly JSON cache, add Lofi Girl channel, add `thumbnail_style` and `top_tags` to output.

- [ ] **Step 1: Rewrite `core/competitor_analyzer.py`**

Replace the full content:

```python
"""
Competitor video analyzer.
Uses yt-dlp to extract metadata (no downloads) from top royalty-free music
channels, then Gemini Flash to identify winning patterns.

Results are cached in data/competitor_patterns.json (valid 7 days).
"""
import os
import json
import datetime
import yt_dlp
import structlog
from google import genai

log = structlog.get_logger()

COMPETITOR_URLS = [
    "https://www.youtube.com/@LofiGirl/videos",
    "https://www.youtube.com/@EpicMusicVn/videos",
    "https://www.youtube.com/@NoCopyrightSounds/videos",
    "https://www.youtube.com/@ChilledCow/videos",
]

CACHE_FILE = "data/competitor_patterns.json"
CACHE_MAX_AGE_DAYS = 7


def _load_cache() -> dict | None:
    """Load cached patterns if they exist and are fresh (< 7 days)."""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE) as f:
            cache = json.load(f)
        cached_date = datetime.date.fromisoformat(cache.get("date", "2000-01-01"))
        if (datetime.date.today() - cached_date).days < CACHE_MAX_AGE_DAYS:
            log.info("competitor_cache_hit", date=cache["date"])
            return cache.get("patterns")
    except Exception:
        pass
    return None


def _save_cache(patterns: dict):
    """Save patterns to JSON cache with today's date."""
    os.makedirs("data", exist_ok=True)
    cache = {"date": datetime.date.today().isoformat(), "patterns": patterns}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)
    log.info("competitor_cache_saved")


def analyze_top_videos(channel_url: str, limit: int = 10) -> list:
    """
    Extract metadata from a channel's most recent videos via yt-dlp.
    No audio downloads — only titles, views, duration, tags.
    """
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlist_items": f"1:{limit}",
    }
    log.info("competitor_fetch_start", channel=channel_url)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            return [
                {
                    "title": v.get("title", ""),
                    "views": v.get("view_count", 0),
                    "duration": v.get("duration", 0),
                    "tags": (v.get("tags") or [])[:10],
                }
                for v in (info.get("entries") or [])
                if v
            ]
    except Exception as e:
        log.warning("competitor_fetch_error", channel=channel_url, error=str(e))
        return []


def extract_winning_patterns(videos: list = None) -> dict:
    """
    Analyze competitor videos and extract winning patterns using Gemini Flash.

    If called with no arguments, fetches from all COMPETITOR_URLS.
    Returns dict with keys: keywords, title_template, avg_duration_min,
    thumbnail_style, top_tags.

    Uses cached results if available and fresh (< 7 days).
    """
    # Check cache first
    cached = _load_cache()
    if cached:
        return cached

    # Fetch from all channels
    if videos is None:
        all_videos = []
        for url in COMPETITOR_URLS:
            all_videos.extend(analyze_top_videos(url, limit=10))
        videos = all_videos

    if not videos:
        return _default_patterns()

    # Sort by views, take top 10
    top_videos = sorted(videos, key=lambda x: x.get("views") or 0, reverse=True)[:10]
    top_titles = [v["title"] for v in top_videos]
    avg_duration = sum(v.get("duration") or 0 for v in top_videos) / len(top_videos) / 60

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log.warning("GEMINI_API_KEY missing, returning default patterns")
        return _default_patterns()

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""Analiza estos titulos de los 10 videos mas vistos en canales top de royalty-free music:
{json.dumps(top_titles, indent=2)}

Duracion promedio: {avg_duration:.1f} minutos.

Extrae:
1. keywords: Las 10 palabras/frases mas exitosas para SEO en YouTube
2. title_template: La estructura de titulo mas efectiva
   Ejemplo: "[Mood] Music for [Activity] | No Copyright | Free to Use"
3. avg_duration_min: Duracion optima en minutos (numero entero)
4. thumbnail_style: Descripcion de estetica ganadora en 1 linea
   Ejemplo: "fondo oscuro azul marino, texto blanco grande, icono musical dorado"
5. top_tags: Los 15 tags mas relevantes para este nicho

Responde SOLO en JSON con claves:
keywords, title_template, avg_duration_min, thumbnail_style, top_tags""",
        )

        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        patterns = json.loads(text.strip())
        patterns["avg_duration_min"] = int(avg_duration)

        # Cache result
        _save_cache(patterns)
        log.info("competitor_patterns_ready", keywords_count=len(patterns.get("keywords", [])))
        return patterns

    except Exception as e:
        log.error("competitor_analysis_failed", error=str(e))
        return _default_patterns()


def _default_patterns() -> dict:
    """Fallback patterns when APIs are unavailable."""
    return {
        "keywords": ["royalty free", "background music", "no copyright", "relaxing", "study music"],
        "title_template": "[Mood] Music for [Activity] | No Copyright | Free to Use",
        "avg_duration_min": 3,
        "thumbnail_style": "dark cosmic background, white text, subtle glow",
        "top_tags": ["royalty free music", "no copyright music", "background music",
                     "study music", "relaxing music", "free music", "ambient",
                     "lofi", "chill", "focus", "meditation", "sleep",
                     "cinematic", "epic", "instrumental"],
    }
```

- [ ] **Step 2: Verify module imports cleanly**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python -c "from core.competitor_analyzer import extract_winning_patterns, COMPETITOR_URLS; print(f'OK, {len(COMPETITOR_URLS)} channels')"`

Expected: `OK, 4 channels`

- [ ] **Step 3: Commit**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add core/competitor_analyzer.py
git commit -m "refactor: competitor analyzer to Gemini Flash with 7-day JSON cache"
```

---

## Task 4: Rewrite Thumbnails (Arcadia branding)

**Files:**
- Modify: `pipeline/video_creator.py` (only the thumbnail section — video functions in Task 5)
- Create: `tests/test_thumbnail.py`

Complete rewrite of `create_thumbnail()` with cosmic Arcadia aesthetic: radial gradient, star particles, auto-sizing text, brand watermark.

- [ ] **Step 1: Write the thumbnail verification test**

Create `tests/test_thumbnail.py`:

```python
"""
Visual verification test for Arcadia Soundscapes thumbnails.
Generates thumbnails for each mood and saves to output/video/test_thumbs/.
Run and visually inspect the results.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.video_creator import create_thumbnail

TEST_DIR = "output/video/test_thumbs"
os.makedirs(TEST_DIR, exist_ok=True)

TEST_CASES = [
    ("Peaceful Ambient Meditation Music for Deep Relaxation and Sleep", "calm"),
    ("EPIC Cinematic Orchestral Battle Theme | Powerful Dramatic Music", "epic"),
    ("Lofi Hip Hop Beats to Study and Relax | Chill Vibes", "relaxing"),
    ("Dark Trap Instrumental 140 BPM | Hard Aggressive Beat", "dark"),
    ("Cozy Acoustic Coffee Shop Music | Warm Morning Vibes", "cozy"),
    ("Energetic Electronic Dance Music | Happy Upbeat EDM", "energetic"),
    ("Short Title", "neutral"),
]


def test_all_thumbnails():
    for i, (title, mood) in enumerate(TEST_CASES):
        out = os.path.join(TEST_DIR, f"thumb_{mood}_{i}.jpg")
        create_thumbnail(title, mood, out)
        assert os.path.exists(out), f"Thumbnail not created: {out}"
        size = os.path.getsize(out)
        assert size > 5000, f"Thumbnail too small ({size} bytes): {out}"
        print(f"  OK: {out} ({size:,} bytes) — {mood}")

    print(f"\nALL {len(TEST_CASES)} THUMBNAILS GENERATED")
    print(f"Visually inspect: {os.path.abspath(TEST_DIR)}/")


if __name__ == "__main__":
    test_all_thumbnails()
```

- [ ] **Step 2: Rewrite thumbnail code in `pipeline/video_creator.py`**

Replace everything from line 1 through the end of `create_thumbnail()` (keep `create_video_with_visualizer` and `create_youtube_short` unchanged for now — they are modified in Task 5).

Replace the `MOOD_COLORS`, `get_mood_colors()`, and `create_thumbnail()` with:

```python
import os
import random
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- Arcadia Soundscapes color palette (cosmic theme) ---

ARCADIA_MOODS = {
    "calm":      {"primary": (10, 14, 39),  "secondary": (26, 58, 92),  "accent": (0, 204, 255)},
    "peaceful":  {"primary": (10, 14, 39),  "secondary": (26, 58, 92),  "accent": (0, 204, 255)},
    "relaxing":  {"primary": (10, 14, 39),  "secondary": (26, 58, 92),  "accent": (0, 204, 255)},
    "epic":      {"primary": (26, 10, 46),  "secondary": (46, 10, 26),  "accent": (136, 0, 255)},
    "dramatic":  {"primary": (26, 10, 46),  "secondary": (46, 10, 26),  "accent": (136, 0, 255)},
    "powerful":  {"primary": (26, 10, 46),  "secondary": (46, 10, 26),  "accent": (136, 0, 255)},
    "energetic": {"primary": (10, 26, 62),  "secondary": (10, 62, 62),  "accent": (0, 255, 200)},
    "happy":     {"primary": (10, 26, 62),  "secondary": (10, 62, 62),  "accent": (0, 255, 200)},
    "dark":      {"primary": (5, 5, 16),    "secondary": (26, 10, 46),  "accent": (136, 0, 255)},
    "aggressive":{"primary": (5, 5, 16),    "secondary": (26, 10, 46),  "accent": (136, 0, 255)},
    "cozy":      {"primary": (13, 27, 42),  "secondary": (42, 26, 13),  "accent": (255, 170, 50)},
    "warm":      {"primary": (13, 27, 42),  "secondary": (42, 26, 13),  "accent": (255, 170, 50)},
}


def get_arcadia_colors(mood: str) -> dict:
    """Get Arcadia color palette for a mood. Always returns cosmic tones."""
    mood_lower = mood.lower()
    for key, colors in ARCADIA_MOODS.items():
        if key in mood_lower:
            return colors
    return {"primary": (10, 14, 39), "secondary": (26, 58, 92), "accent": (0, 204, 255)}


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Load DejaVuSans-Bold at given size. Works on Ubuntu VPS and macOS."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        if bbox[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit_text(text: str, max_width: int, max_height: int) -> tuple:
    """Find largest font size that fits text in bounds (max 3 lines).
    Returns (font, lines)."""
    for size in range(60, 24, -2):
        font = _get_font(size)
        lines = _wrap_text(text, font, max_width)
        if len(lines) > 3:
            continue
        line_height = font.getbbox("Ay")[3] + 8
        total_height = line_height * len(lines)
        if total_height <= max_height:
            return font, lines
    font = _get_font(26)
    lines = _wrap_text(text, font, max_width)
    return font, lines[:3]


def _draw_radial_gradient(img: Image.Image, center_color: tuple, edge_color: tuple):
    """Draw radial gradient using concentric ellipses + blur."""
    width, height = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, height], fill=edge_color)

    steps = 80
    for i in range(steps):
        ratio = i / steps
        mx = int(width * 0.45 * (1 - ratio))
        my = int(height * 0.45 * (1 - ratio))
        r = int(edge_color[0] + (center_color[0] - edge_color[0]) * ratio)
        g = int(edge_color[1] + (center_color[1] - edge_color[1]) * ratio)
        b = int(edge_color[2] + (center_color[2] - edge_color[2]) * ratio)
        draw.ellipse([mx, my, width - mx, height - my], fill=(r, g, b))

    # Smooth the banding
    blurred = img.filter(ImageFilter.GaussianBlur(radius=20))
    img.paste(blurred)


def _draw_stars(img: Image.Image, count: int = 120):
    """Draw random star particles for cosmic effect."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = img.size
    for _ in range(count):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        size = random.randint(1, 3)
        alpha = random.randint(60, 200)
        draw.ellipse([x, y, x + size, y + size], fill=(255, 255, 255, alpha))

    # Convert base to RGBA, composite, convert back
    base_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(base_rgba, overlay)
    img.paste(composite.convert("RGB"))


def _draw_glow_border(img: Image.Image, accent: tuple, width_px: int = 3):
    """Draw a subtle glowing border inside the image."""
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow_layer)
    w, h = img.size
    margin = 20
    for i in range(width_px):
        alpha = 80 - i * 20
        if alpha <= 0:
            break
        color = (*accent, alpha)
        draw.rectangle(
            [margin + i, margin + i, w - margin - i, h - margin - i],
            outline=color,
        )

    base_rgba = img.convert("RGBA")
    composite = Image.alpha_composite(base_rgba, glow_layer)
    img.paste(composite.convert("RGB"))


def create_thumbnail(title: str, mood: str, output_path: str):
    """
    Generate 1280x720 Arcadia Soundscapes branded thumbnail.

    - Radial gradient background in cosmic tones
    - Star particle overlay
    - Auto-sized, word-wrapped title with text shadow
    - "Arcadia Soundscapes" branding at bottom
    - Subtle glow border
    """
    width, height = 1280, 720
    colors = get_arcadia_colors(mood)
    primary = colors["primary"]
    secondary = colors["secondary"]
    accent = colors["accent"]

    # Lighter center for radial gradient
    center = tuple(min(c + 30, 255) for c in primary)

    img = Image.new("RGB", (width, height))

    # 1. Radial gradient background
    _draw_radial_gradient(img, center, secondary)

    # 2. Star particles
    _draw_stars(img, count=120)

    # 3. Glow border
    _draw_glow_border(img, accent)

    draw = ImageDraw.Draw(img)

    # 4. Title — auto-sized, word-wrapped, centered in 70% zone
    text_max_w = int(width * 0.70)
    text_max_h = int(height * 0.45)
    font, lines = _fit_text(title, text_max_w, text_max_h)
    line_height = font.getbbox("Ay")[3] + 8
    total_text_h = line_height * len(lines)
    start_y = (height // 2) - (total_text_h // 2) - 20

    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        line_w = bbox[2]
        x = (width - line_w) // 2
        y = start_y + i * line_height
        # Text shadow
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0))
        draw.text((x + 1, y + 1), line, font=font, fill=(0, 0, 0))
        # Main text
        draw.text((x, y), line, font=font, fill="white")

    # 5. Branding — bottom center
    brand_font = _get_font(22)
    brand_text = "Arcadia Soundscapes"
    brand_bbox = brand_font.getbbox(brand_text)
    brand_x = (width - brand_bbox[2]) // 2
    brand_y = height - 55
    # Accent-tinted semi-transparent look (draw dimmer)
    brand_color = tuple(min(c + 100, 255) for c in accent)
    draw.text((brand_x, brand_y), brand_text, font=brand_font, fill=brand_color)

    # Save
    dirname = os.path.dirname(output_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)
    img.save(output_path, "JPEG", quality=95)
```

- [ ] **Step 3: Run the visual test**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python tests/test_thumbnail.py`

Expected: `ALL 7 THUMBNAILS GENERATED` and thumbnails saved to `output/video/test_thumbs/`. Open the directory and visually verify the Arcadia aesthetic (cosmic gradients, readable text, no overflow, brand watermark).

- [ ] **Step 4: Commit**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add pipeline/video_creator.py tests/test_thumbnail.py
git commit -m "feat: Arcadia-branded thumbnails with radial gradient, stars, auto-text"
```

---

## Task 5: Upgrade Video Visualizers (spectrum analyzer + branding)

**Files:**
- Modify: `pipeline/video_creator.py` (the `create_video_with_visualizer` and `create_youtube_short` functions)

Replace basic `showwaves` with `showfreqs` spectrum bars and add `drawtext` branding overlay.

- [ ] **Step 1: Replace `create_video_with_visualizer()` in `pipeline/video_creator.py`**

Replace the existing function (lines 65-90 area, after `create_thumbnail`) with:

```python
def create_video_with_visualizer(mp3_path: str, thumb_path: str, output_path: str):
    """
    Create 1280x720 video with spectrum analyzer and Arcadia branding.
    - Thumbnail background with subtle zoom breathing effect
    - showfreqs spectrum bars (cyan/purple gradient)
    - 'Arcadia Soundscapes' drawtext watermark
    """
    dirname = os.path.dirname(output_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    # Detect available font for drawtext
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"

    # Try showfreqs first (spectrum bars), fall back to showwaves if unavailable
    filter_complex = (
        "[1:a]aformat=channel_layouts=stereo[a_stereo];"
        "[a_stereo]showfreqs=mode=bar:s=1280x180:fscale=log:"
        "ascale=log:colors=0x00ccff|0x8800ff:win_size=2048[freq];"
        "[0:v][freq]overlay=0:540[with_freq];"
        f"[with_freq]drawtext=text='Arcadia Soundscapes':"
        f"fontfile={font_path}:fontsize=22:"
        f"fontcolor=white@0.35:x=w-tw-20:y=h-th-15[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", thumb_path,
        "-i", mp3_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback: use showwaves if showfreqs not available
        filter_complex_fallback = (
            "[1:a]aformat=channel_layouts=stereo[a_stereo];"
            "[a_stereo]showwaves=s=1280x180:mode=cline:"
            "colors=0x00ccff@0.7:rate=30[waves];"
            "[0:v][waves]overlay=0:540[with_waves];"
            f"[with_waves]drawtext=text='Arcadia Soundscapes':"
            f"fontfile={font_path}:fontsize=22:"
            f"fontcolor=white@0.35:x=w-tw-20:y=h-th-15[outv]"
        )
        cmd_fallback = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", thumb_path,
            "-i", mp3_path,
            "-filter_complex", filter_complex_fallback,
            "-map", "[outv]", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd_fallback, check=True)
```

- [ ] **Step 2: Replace `create_youtube_short()` in `pipeline/video_creator.py`**

Replace the existing function with:

```python
def create_youtube_short(audio_path: str, thumbnail_path: str, output_path: str):
    """
    Generate vertical 1080x1920 YouTube Short.
    - Thumbnail in upper half, spectrum visualizer in lower half
    - Arcadia Soundscapes branding at bottom
    - Max 59 seconds
    """
    dirname = os.path.dirname(output_path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    if not os.path.exists(font_path):
        font_path = "/System/Library/Fonts/Helvetica.ttc"

    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
        "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x050510[bg];"
        "[1:a]aformat=channel_layouts=stereo[a_stereo];"
        "[a_stereo]showfreqs=mode=bar:s=1080x400:fscale=log:"
        "ascale=log:colors=0x00ccff|0x8800ff:win_size=2048[freq];"
        "[bg][freq]overlay=0:1200[with_freq];"
        f"[with_freq]drawtext=text='Arcadia Soundscapes':"
        f"fontfile={font_path}:fontsize=28:"
        f"fontcolor=white@0.4:x=(w-tw)/2:y=h-60[outv]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", thumbnail_path,
        "-i", audio_path,
        "-t", "59",
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        # Fallback with showwaves
        filter_fallback = (
            "[0:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=0x050510[bg];"
            "[1:a]aformat=channel_layouts=stereo[a_stereo];"
            "[a_stereo]showwaves=s=1080x400:mode=cline:"
            "colors=0x00ccff@0.7:rate=30[waves];"
            "[bg][waves]overlay=0:1200[with_waves];"
            f"[with_waves]drawtext=text='Arcadia Soundscapes':"
            f"fontfile={font_path}:fontsize=28:"
            f"fontcolor=white@0.4:x=(w-tw)/2:y=h-60[outv]"
        )
        cmd_fallback = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", thumbnail_path,
            "-i", audio_path,
            "-t", "59",
            "-filter_complex", filter_fallback,
            "-map", "[outv]", "-map", "1:a",
            "-c:v", "libx264", "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd_fallback, check=True)
```

- [ ] **Step 3: Test video creation with an existing audio file**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python -c "
from pipeline.video_creator import create_thumbnail, create_video_with_visualizer, create_youtube_short
import os
thumb = 'output/video/test_video_thumb.jpg'
create_thumbnail('Epic Cinematic Orchestral Music', 'epic', thumb)
if os.path.exists('dummy.mp3'):
    create_video_with_visualizer('dummy.mp3', thumb, 'output/video/test_video.mp4')
    create_youtube_short('dummy.mp3', thumb, 'output/video/test_short.mp4')
    print('VIDEO+SHORT OK')
else:
    print('THUMB OK (skip video: no dummy.mp3)')
"`

Expected: `VIDEO+SHORT OK` or `THUMB OK (skip video: no dummy.mp3)`

- [ ] **Step 4: Commit**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add pipeline/video_creator.py
git commit -m "feat: spectrum analyzer visualizer + Arcadia branding in videos/shorts"
```

---

## Task 6: Upgrade Niche Analyzer (weekly pool + daily selection)

**Files:**
- Modify: `core/niche_analyzer.py`
- Create: `tests/test_niche_pool.py`

Depends on Task 2 (spotify_trend_analyzer) and Task 3 (competitor_analyzer cache).

- [ ] **Step 1: Write the pool selection test**

Create `tests/test_niche_pool.py`:

```python
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_get_daily_niche_returns_string():
    from core.niche_analyzer import get_daily_niche
    # Create a fake pool file
    os.makedirs("data", exist_ok=True)
    pool = {
        "date": "2026-04-17",
        "niches": ["niche_0", "niche_1", "niche_2", "niche_3",
                    "niche_4", "niche_5", "niche_6"],
    }
    with open("data/weekly_pool.json", "w") as f:
        json.dump(pool, f)

    niche = get_daily_niche(0)
    assert niche == "niche_0"
    niche = get_daily_niche(6)
    assert niche == "niche_6"
    print("  OK: get_daily_niche returns correct niche by index")


def test_get_daily_niche_wraps_on_overflow():
    from core.niche_analyzer import get_daily_niche
    # index 7 should wrap to 0
    niche = get_daily_niche(7)
    assert niche == "niche_0"
    print("  OK: get_daily_niche wraps on overflow")


def test_pool_file_missing_triggers_generation():
    from core.niche_analyzer import get_daily_niche
    # Remove pool file — should regenerate and return a string
    if os.path.exists("data/weekly_pool.json"):
        os.remove("data/weekly_pool.json")
    niche = get_daily_niche(0)
    assert isinstance(niche, str)
    assert len(niche) > 0
    print(f"  OK: missing pool triggers generation, got: {niche}")


if __name__ == "__main__":
    test_get_daily_niche_returns_string()
    test_get_daily_niche_wraps_on_overflow()
    test_pool_file_missing_triggers_generation()
    print("\nALL NICHE POOL TESTS PASSED")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python tests/test_niche_pool.py`

Expected: `ImportError` or `AttributeError` because `get_daily_niche` does not exist yet.

- [ ] **Step 3: Rewrite `core/niche_analyzer.py`**

Replace the full content:

```python
"""
Niche analyzer for Arcadia Soundscapes.
Generates a weekly pool of 7 niches (4 Spotify trends + 3 evergreen SEED_NICHES)
and serves one niche per day via get_daily_niche().
"""
import os
import json
import random
import datetime
import anthropic
import structlog

from core.prompt_builder import NICHE_PARAMS
from core.trend_analyzer import validate_tags_with_search_volume
from core.spotify_trend_analyzer import get_spotify_top_tracks, extract_niches_from_charts

log = structlog.get_logger()

SEED_NICHES = list(NICHE_PARAMS.keys())
POOL_FILE = "data/weekly_pool.json"
HISTORY_FILE = "data/niches_history.json"


def _load_used_niches() -> list:
    """Load niches used in the last 30 days to avoid repetition."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)
        cutoff = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
        return [n for n in data.get("entries", []) if n.get("date", "") >= cutoff]
    except Exception:
        return []


def _save_used_niches(niches: list):
    """Append niches to usage history."""
    os.makedirs("data", exist_ok=True)
    existing = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                existing = json.load(f).get("entries", [])
        except Exception:
            pass

    today = datetime.date.today().isoformat()
    for n in niches:
        existing.append({"niche": n, "date": today})

    # Keep only last 90 days
    cutoff = (datetime.date.today() - datetime.timedelta(days=90)).isoformat()
    existing = [e for e in existing if e.get("date", "") >= cutoff]

    with open(HISTORY_FILE, "w") as f:
        json.dump({"entries": existing}, f, indent=2)


def get_weekly_niches(count: int = 7) -> list:
    """
    Generate weekly niche pool combining:
    - 4 niches from Spotify Charts trends (via Gemini)
    - 3 niches from SEED_NICHES evergreen (avoiding 30-day repeats)

    Returns list of `count` niche strings.
    """
    # Spotify trends (target: 4)
    spotify_tracks = get_spotify_top_tracks()
    trend_niches = extract_niches_from_charts(spotify_tracks)
    log.info("weekly_pool_spotify", count=len(trend_niches))

    # Evergreen SEED_NICHES (target: 3, no repeats in 30 days)
    used_entries = _load_used_niches()
    used_names = [e["niche"] for e in used_entries]
    available_seeds = [n for n in SEED_NICHES if n not in used_names]
    if len(available_seeds) < 3:
        available_seeds = SEED_NICHES  # Reset if exhausted

    seed_count = count - len(trend_niches)
    seed_selection = random.sample(available_seeds, min(seed_count, len(available_seeds)))

    # Combine: trends first, then evergreen, deduplicate
    combined = list(dict.fromkeys(trend_niches + seed_selection))[:count]

    # Fill remaining slots if needed (Spotify may have returned < 4)
    if len(combined) < count:
        extras = [n for n in SEED_NICHES if n not in combined]
        fill = random.sample(extras, min(count - len(combined), len(extras)))
        combined.extend(fill)

    # Persist pool and history
    os.makedirs("data", exist_ok=True)
    pool_data = {
        "date": datetime.date.today().isoformat(),
        "niches": combined,
    }
    with open(POOL_FILE, "w") as f:
        json.dump(pool_data, f, indent=2)

    _save_used_niches(combined)

    log.info("weekly_pool_ready", count=len(combined), niches=combined)
    return combined


def get_daily_niche(day_index: int) -> str:
    """
    Get the niche for today from the weekly pool.
    day_index: 0=Monday, 1=Tuesday, ..., 6=Sunday (use datetime.date.today().weekday())

    If the pool file doesn't exist or is stale (> 7 days), regenerates it.
    """
    pool = None
    if os.path.exists(POOL_FILE):
        try:
            with open(POOL_FILE) as f:
                data = json.load(f)
            pool_date = datetime.date.fromisoformat(data.get("date", "2000-01-01"))
            if (datetime.date.today() - pool_date).days < 7:
                pool = data.get("niches", [])
        except Exception:
            pass

    if not pool:
        log.info("weekly_pool_regenerating")
        pool = get_weekly_niches(count=7)

    idx = day_index % len(pool)
    niche = pool[idx]
    log.info("daily_niche_selected", day=day_index, niche=niche)
    return niche


def analyze_niche_and_create_prompt(niche: str, patterns: dict = None) -> dict:
    """
    Generate full metadata for a niche using Anthropic Claude.

    If patterns (from competitor_analyzer) are provided, uses them as
    additional SEO context for title and tags optimization.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    params = NICHE_PARAMS.get(niche, NICHE_PARAMS.get(SEED_NICHES[0]))
    default_meta = {
        "yt_title": f"{niche.title()} - Royalty Free Music",
        "pond5_title": f"{niche.title()} Background Music",
        "pond5_keywords": "music, loop, background, " + niche.replace(" ", ", "),
        "yt_description": f"Best {niche} music. Free to use.",
        "bpm": params.get("bpm", 100),
        "mood": params.get("mood", "neutral").split(",")[0].strip(),
    }

    if not api_key:
        log.warning("ANTHROPIC_API_KEY missing, returning default metadata")
        return default_meta

    client = anthropic.Anthropic(api_key=api_key)

    # Build patterns context if available (from cached competitor analysis)
    patterns_context = ""
    if patterns:
        patterns_context = f"""
Contexto de analisis de competencia (usar para mejorar SEO):
- Template de titulo ganador: {patterns.get("title_template", "")}
- Keywords top: {", ".join(patterns.get("keywords", [])[:5])}
- Tags recomendados: {", ".join(patterns.get("top_tags", [])[:10])}
- Estilo de thumbnail: {patterns.get("thumbnail_style", "")}
"""

    sys_instruction = (
        "Eres un experto en metadata musical SEO para YouTube y Pond5. "
        "Devuelve UNICAMENTE un objeto JSON sin explicacion. "
        "Keys: yt_title, pond5_title, pond5_keywords (string de palabras separadas por comas), "
        "yt_description, yt_tags (string de tags separados por comas), bpm (int), mood (string)."
    )

    prompt = f"""
Nicho: '{niche}'
Estilo: {params.get('mood')} a {params.get('bpm')} BPM.
{patterns_context}
Genera la mejor metadata para publicar en YouTube y Pond5.
El canal se llama "Arcadia Soundscapes" — musica generada por IA, paisajes sonoros inmersivos.
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            temperature=0.6,
            system=sys_instruction,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text

        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        data = json.loads(text.strip())

        # Validate tags against YouTube search volume
        raw_tags = [t.strip() for t in data.get("pond5_keywords", "").split(",")]
        best_tags = validate_tags_with_search_volume(raw_tags)
        data["pond5_keywords"] = ", ".join(best_tags)

        # Ensure required fields
        if "bpm" not in data:
            data["bpm"] = default_meta["bpm"]
        if "mood" not in data:
            data["mood"] = default_meta["mood"]

        return data

    except Exception as e:
        log.error("metadata_analysis_error", error=str(e))
        return default_meta
```

**Key changes from original:**
- Removed imports of `competitor_analyzer` (no longer called per-track)
- Removed `rank_niches_by_trend()` (replaced by Spotify trends)
- Added `get_daily_niche()` for daily selection from persistent pool
- `analyze_niche_and_create_prompt()` accepts `patterns` parameter instead of calling competitor analyzer directly
- Changed model from `claude-opus-4-6` to `claude-sonnet-4-6` (cheaper for metadata generation, Opus is overkill)
- Added `yt_tags` to the metadata schema

- [ ] **Step 4: Run tests**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python tests/test_niche_pool.py`

Expected: `ALL NICHE POOL TESTS PASSED`

- [ ] **Step 5: Commit**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add core/niche_analyzer.py tests/test_niche_pool.py
git commit -m "feat: weekly niche pool with Spotify trends + daily selection"
```

---

## Task 7: Rewrite main.py (daily schedule + retry queue)

**Files:**
- Modify: `main.py`

This is the final wiring task. Changes schedule from weekly to daily, adds retry queue for failed YouTube uploads, wires Spotify trends + competitor patterns.

- [ ] **Step 1: Rewrite `main.py`**

Replace the full content:

```python
"""
Arcadia Soundscapes — Daily Drip v2

Generates and publishes 1 track per day to YouTube + Pond5.
- Daily at 09:00 ART
- Weekly pool of 7 niches (4 Spotify trends + 3 evergreen)
- Competitor patterns analyzed once per week (Monday)
- Retry queue for failed YouTube uploads
"""
import asyncio
import csv
import datetime
import glob
import json
import os
import schedule
import shutil
import sys
import time

import structlog
from dotenv import load_dotenv

load_dotenv()

from core.niche_analyzer import get_daily_niche, get_weekly_niches, analyze_niche_and_create_prompt
from core.competitor_analyzer import extract_winning_patterns
from core.provider_orchestrator import generate_track_with_fallback
from pipeline.video_creator import create_thumbnail, create_video_with_visualizer, create_youtube_short
from pipeline.youtube_uploader import upload_to_youtube
from pipeline.pond5_uploader import Pond5Uploader
from pipeline.telegram_notifier import notify, notify_error
from music_generator import convert_wav_to_mp3

log = structlog.get_logger()

for d in ["output/audio", "output/video", "output/debug", "data", "data/pending_uploads"]:
    os.makedirs(d, exist_ok=True)


# --- Retry Queue ---

def _save_pending(video_path: str, short_path: str, thumb_path: str, metadata: dict):
    """Save failed upload to pending queue for retry next day."""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    pending_dir = f"data/pending_uploads/{ts}"
    os.makedirs(pending_dir, exist_ok=True)

    # Copy files to pending directory
    for src, name in [(video_path, "video.mp4"), (short_path, "short.mp4"), (thumb_path, "thumb.jpg")]:
        if src and os.path.exists(src):
            shutil.copy2(src, os.path.join(pending_dir, name))

    with open(os.path.join(pending_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    log.info("pending_upload_saved", dir=pending_dir)


async def _process_pending_uploads(max_retries: int = 2) -> list:
    """Upload pending videos from previous failed attempts. Max 2 per day."""
    pending_base = "data/pending_uploads"
    if not os.path.exists(pending_base):
        return []

    pending_dirs = sorted(glob.glob(os.path.join(pending_base, "*")))
    if not pending_dirs:
        return []

    log.info("pending_uploads_found", count=len(pending_dirs))
    results = []

    for pending_dir in pending_dirs[:max_retries]:
        meta_file = os.path.join(pending_dir, "metadata.json")
        video_file = os.path.join(pending_dir, "video.mp4")
        short_file = os.path.join(pending_dir, "short.mp4")
        thumb_file = os.path.join(pending_dir, "thumb.jpg")

        if not os.path.exists(meta_file) or not os.path.exists(video_file):
            shutil.rmtree(pending_dir, ignore_errors=True)
            continue

        try:
            with open(meta_file) as f:
                metadata = json.load(f)

            log.info("pending_retry_start", title=metadata.get("yt_title", "unknown"))

            # Upload video
            yt_url = await asyncio.to_thread(upload_to_youtube, video_file, metadata, thumb_file)

            # Upload short if it exists
            yt_short_url = "N/A"
            if os.path.exists(short_file):
                short_meta = metadata.copy()
                short_meta["yt_title"] = f"{metadata['yt_title'][:90]} #Shorts"
                yt_short_url = await asyncio.to_thread(
                    upload_to_youtube, short_file, short_meta, thumb_file
                )

            # Success — remove pending directory
            shutil.rmtree(pending_dir, ignore_errors=True)
            log.info("pending_retry_success", yt_url=yt_url)

            results.append({
                "title": metadata.get("yt_title", "retry"),
                "yt_url": yt_url,
                "yt_short_url": yt_short_url,
                "pond5": False,
                "niche": metadata.get("niche", "retry"),
                "bpm": metadata.get("bpm", 0),
                "provider": "retry",
            })

        except Exception as e:
            log.error("pending_retry_failed", dir=pending_dir, error=str(e))
            # Leave in pending for next day

    return results


# --- Daily Pipeline ---

async def process_daily_track(patterns: dict) -> dict | None:
    """Generate and publish one track for today."""
    day_index = datetime.date.today().weekday()
    niche = get_daily_niche(day_index)
    log.info("daily_track_start", day=day_index, niche=niche)

    try:
        # 1. Metadata via Claude
        metadata = await asyncio.to_thread(analyze_niche_and_create_prompt, niche, patterns)
        log.info("metadata_ready", title=metadata.get("yt_title", "Unknown"))

        # 2. Generate track with multi-provider fallback
        base = f"output/audio/track_{niche.replace(' ', '_')[:20]}"
        track = await generate_track_with_fallback(niche, base)
        log.info("track_ready", provider=track["provider_used"])

        # 3. Convert WAV -> MP3
        mp3_path = await asyncio.to_thread(convert_wav_to_mp3, track["path"])

        # 4. Create thumbnail + video + short
        ts = datetime.datetime.now().strftime("%Y%m%d")
        thumb = f"output/video/{ts}_thumb.jpg"
        video = f"output/video/{ts}_video.mp4"
        short_video = f"output/video/{ts}_short.mp4"

        await asyncio.to_thread(create_thumbnail, metadata["yt_title"], metadata["mood"], thumb)
        await asyncio.to_thread(create_video_with_visualizer, mp3_path, thumb, video)
        await asyncio.to_thread(create_youtube_short, mp3_path, thumb, short_video)

        # 5. Upload YouTube video + short in parallel, Pond5 non-blocking
        short_meta = metadata.copy()
        short_meta["yt_title"] = f"{metadata['yt_title'][:90]} #Shorts"
        short_meta["yt_description"] = f"{metadata.get('yt_description', '')}\n#Shorts"

        pond5 = Pond5Uploader()

        yt_task = asyncio.to_thread(upload_to_youtube, video, metadata, thumb)
        yt_short_task = asyncio.to_thread(upload_to_youtube, short_video, short_meta, thumb)
        pond5_task = pond5.upload(track["path"], metadata)

        yt_url, yt_short_url, pond5_ok = await asyncio.gather(
            yt_task, yt_short_task, pond5_task,
            return_exceptions=True,
        )

        # Handle YouTube failures — save to pending queue
        youtube_failed = False

        if isinstance(yt_url, Exception):
            log.error("youtube_upload_failed", error=str(yt_url))
            yt_url = f"ERROR: {yt_url}"
            youtube_failed = True

        if isinstance(yt_short_url, Exception):
            log.error("youtube_short_failed", error=str(yt_short_url))
            yt_short_url = f"ERROR: {yt_short_url}"
            youtube_failed = True

        if youtube_failed:
            metadata["niche"] = niche
            _save_pending(video, short_video, thumb, metadata)
            # Check if it's a token expiry
            error_str = str(yt_url) + str(yt_short_url)
            if "401" in error_str or "invalid_grant" in error_str.lower():
                await notify_error(
                    "YouTube Token Expirado",
                    "Re-autenticar manualmente: borrar youtube_token.json y correr OAuth desde maquina local",
                )

        if isinstance(pond5_ok, Exception):
            log.error("pond5_failed", error=str(pond5_ok))
            pond5_ok = False

        result = {
            "title": metadata["yt_title"],
            "yt_url": yt_url,
            "yt_short_url": yt_short_url,
            "pond5": pond5_ok if not isinstance(pond5_ok, Exception) else False,
            "niche": niche,
            "bpm": metadata.get("bpm", 0),
            "provider": track["provider_used"],
        }

        # CSV log
        def write_log(res):
            with open("data/tracks_log.csv", "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=res.keys())
                if f.tell() == 0:
                    writer.writeheader()
                writer.writerow(res)

        await asyncio.to_thread(write_log, result)

        log.info("daily_track_complete", **result)
        return result

    except Exception as e:
        log.error("daily_track_failed", niche=niche, error=str(e))
        await notify_error("Track Generation Failed", f"Niche: {niche}\nError: {str(e)}")
        return None


async def run_daily():
    """Main daily entry point: process pending retries, then generate today's track."""
    log.info("daily_cycle_start")

    # Monday: regenerate weekly pool + competitor patterns
    is_monday = datetime.date.today().weekday() == 0
    if is_monday:
        log.info("monday_weekly_refresh")
        get_weekly_niches(count=7)

    # Load competitor patterns (cached, refreshed weekly)
    patterns = extract_winning_patterns()

    all_results = []

    # 1. Retry pending uploads (max 2)
    pending_results = await _process_pending_uploads(max_retries=2)
    all_results.extend(pending_results)

    # 2. Generate today's track
    result = await process_daily_track(patterns)
    if result:
        all_results.append(result)

    # 3. Notify
    if all_results:
        await notify(all_results)
    else:
        await notify_error("No Track Today", "All providers failed or pipeline errored.")

    log.info("daily_cycle_complete", published=len(all_results))


def _run_daily_sync():
    """Sync wrapper for schedule library."""
    asyncio.run(run_daily())


# --- Schedule ---

schedule.every().day.at("09:00").do(_run_daily_sync)

if __name__ == "__main__":
    log.info("agent_started", schedule="Every day at 09:00 ART")

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        log.info("test_mode")
        asyncio.run(run_daily())
    else:
        while True:
            schedule.run_pending()
            time.sleep(60)
```

**Key changes from original:**
- `schedule.every().day.at("09:00")` instead of `.wednesday`
- `process_daily_track()` replaces `process_niche()` — processes 1 niche, not a batch
- `_process_pending_uploads()` — retry queue for failed YouTube uploads
- `_save_pending()` — saves failed uploads for next-day retry
- Monday auto-refreshes weekly pool + competitor patterns
- Pond5 is non-blocking (1 attempt, no retry chain)
- Token expiry detection with Telegram alert
- `--test` mode runs full daily cycle immediately

- [ ] **Step 2: Verify module imports**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python -c "from main import run_daily; print('main.py imports OK')"`

Expected: `main.py imports OK`

- [ ] **Step 3: Commit**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add main.py
git commit -m "feat: daily schedule with retry queue, Spotify trends, competitor cache"
```

---

## Task 8: Integration Test (--test mode)

**Files:** None (verification only)

- [ ] **Step 1: Run all unit tests**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python tests/test_telegram_sanitize.py && python tests/test_niche_pool.py && python tests/test_thumbnail.py`

Expected: All three test suites pass.

- [ ] **Step 2: Run agent in test mode (if API keys are configured)**

Run: `cd /Users/gastonchevarria/MusicAgent/lyria-music-agent && python main.py --test`

This runs the full daily pipeline once:
1. Checks for pending uploads
2. Selects today's niche from the weekly pool
3. Generates a track (requires Gemini/Lyria API keys)
4. Creates thumbnail + video + short
5. Attempts YouTube upload (requires valid OAuth token)
6. Sends Telegram notification

Expected: Either a successful run or clear error messages indicating which API needs attention (quota, auth, etc.)

- [ ] **Step 3: Final commit with all tests**

```bash
cd /Users/gastonchevarria/MusicAgent/lyria-music-agent
git add tests/
git commit -m "test: add unit and visual verification tests for v2"
```

---

## Deployment Notes

After all tasks are complete and verified locally:

1. **Stop the current agent on VPS:**
   ```bash
   pm2 stop lyria-agent
   ```

2. **Copy updated code to VPS:**
   ```bash
   gcloud compute scp --recurse /Users/gastonchevarria/MusicAgent/lyria-music-agent arcadia-admin@arcadia-b2b-engine-br:/home/arcadia-admin/ --zone=southamerica-east1-a --project=proyecto001-490716 --tunnel-through-iap
   ```

3. **Restart agent:**
   ```bash
   pm2 restart lyria-agent
   pm2 logs lyria-agent
   ```

4. **Manual actions (user must do):**
   - OAuth Consent Screen -> "In production" in Google Cloud Console
   - Verify Pond5 FTP credentials
   - Consider rotating exposed API keys
