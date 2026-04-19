import os
import structlog
from googleapiclient.discovery import build

log = structlog.get_logger()

def get_youtube_service():
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return None
    return build("youtube", "v3", developerKey=api_key)

def get_trending_music_niches() -> list:
    """
    Usa YouTube Data API para encontrar nichos con alta demanda real.
    Reemplaza/complementa la lista hardcodeada de SEED_NICHES.
    """
    youtube = get_youtube_service()
    if not youtube:
        log.warning("YOUTUBE_API_KEY no encontrada. Omitiendo validacion de Search API.")
        return []
        
    searches = [
        "royalty free music 2025",
        "no copyright music",
        "lofi beats study",
        "epic cinematic music",
    ]
    
    trending = []
    log.info("trending_search_start", queries=len(searches))
    
    try:
        for query in searches:
            res = youtube.search().list(
                q=query, part="snippet",
                type="video", videoCategoryId="10",  # Music
                order="viewCount",
                publishedAfter="2024-01-01T00:00:00Z", # relajamos publishedAfter temporalmente a ultimo año
                maxResults=5
            ).execute()
            
            for item in res.get("items", []):
                trending.append(item["snippet"]["title"])
                
        return trending
    except Exception as e:
        log.error("trending_search_failed", error=str(e))
        return []


def validate_tags_with_search_volume(tags: list) -> list:
    """
    Ordena los tags según el totalResults de YouTube Search API.
    Devuelve los top 15 por relevancia real.
    """
    youtube = get_youtube_service()
    if not youtube:
        return tags[:15]
        
    scored = []
    log.info("validate_tags_start", total_tags=len(tags[:20]))
    try:
        for tag in tags[:20]:
            tag = tag.strip()
            if not tag:
                continue
            res = youtube.search().list(
                q=tag, part="snippet",
                type="video", videoCategoryId="10",
                maxResults=1
            ).execute()
            
            total = res.get("pageInfo", {}).get("totalResults", 0)
            scored.append((tag, total))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return [t[0] for t in scored[:15]]
    except Exception as e:
        log.error("validate_tags_failed", error=str(e))
        return tags[:15]
