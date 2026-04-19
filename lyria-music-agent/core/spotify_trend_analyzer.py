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
