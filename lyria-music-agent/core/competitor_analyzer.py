"""
Competitor video analyzer.
Uses yt-dlp to extract metadata (no downloads) from top royalty-free music
channels, then Gemini Flash to identify winning patterns.

Results are cached in data/competitor_patterns.json (valid 7 days).
"""
import os
import json
import datetime
from typing import Optional
import yt_dlp
import structlog
from google import genai

log = structlog.get_logger()

COMPETITOR_URLS = [
    "https://www.youtube.com/@LofiGirl/videos",
    "https://www.youtube.com/@EpicMusicVn/videos",
    "https://www.youtube.com/@NoCopyrightSounds/videos",
]

CACHE_FILE = "data/competitor_patterns.json"
CACHE_MAX_AGE_DAYS = 7


def _load_cache() -> Optional[dict]:
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
