"""
Arcadia Music — Daily Drip v2

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

async def process_daily_track(patterns: dict):
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
