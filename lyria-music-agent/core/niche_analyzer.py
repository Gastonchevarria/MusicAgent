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
        "yt_tags": "royalty free music, " + niche.replace(" ", ", "),
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
El canal se llama "Arcadia Soundscapes" -- musica generada por IA, paisajes sonoros inmersivos.
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
