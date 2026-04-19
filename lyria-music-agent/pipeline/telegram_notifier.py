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
