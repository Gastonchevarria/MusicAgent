import os
import re
import html
import telegram
import structlog

log = structlog.get_logger()


def sanitize_html(text) -> str:
    if not text:
        return "N/A"
    return str(text)


def _clean(text: str) -> str:
    """Escape specific characters for HTML."""
    return html.escape(str(text))


def _build_message(track_result: dict) -> str:
    """Build daily notification for a single track using HTML."""
    msg = "🎵 <b>Arcadia Music - Daily Track</b>\n\n"

    msg += f"<b>Nicho:</b> {_clean(track_result.get('niche', 'N/A'))}\n"
    msg += f"<b>Titulo:</b> {_clean(track_result.get('title', 'N/A'))}\n"
    msg += f"<b>Provider:</b> {_clean(track_result.get('provider', 'N/A'))}\n"
    msg += f"<b>BPM:</b> {track_result.get('bpm', 'N/A')}\n\n"

    yt_url = track_result.get("yt_url", "N/A")
    if not isinstance(yt_url, str) or yt_url.startswith("ERROR"):
        msg += f"▶️ <b>YouTube:</b> {_clean(str(yt_url))}\n"
    else:
        msg += f"▶️ <b>YouTube:</b> <a href=\"{yt_url}\">{yt_url}</a>\n"

    yt_short = track_result.get("yt_short_url", "N/A")
    if not isinstance(yt_short, str) or yt_short.startswith("ERROR"):
        msg += f"📱 <b>Short:</b> {_clean(str(yt_short))}\n"
    else:
        msg += f"📱 <b>Short:</b> <a href=\"{yt_short}\">{yt_short}</a>\n"

    msg += f"💰 <b>Pond5:</b> {'OK' if track_result.get('pond5') else 'Fallo'}\n"

    return msg


def _build_batch_message(track_results: list) -> str:
    """Build notification for multiple tracks (used for pending retries)."""
    msg = "🎵 <b>Arcadia Music - Reporte Diario</b>\n\n"
    msg += f"📦 <b>Tracks publicados:</b> {len(track_results)}\n\n"
    for i, track in enumerate(track_results, 1):
        msg += f"<b>{i}.</b> {_clean(track.get('title', 'N/A'))}\n"
        yt_url = track.get("yt_url", "N/A")
        if isinstance(yt_url, str) and not yt_url.startswith("ERROR"):
            msg += f"   ▶️ <a href=\"{yt_url}\">{yt_url}</a>\n"
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
                parse_mode="HTML",
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
            f"⚠️ <b>Arcadia Music - Error</b>\n\n"
            f"<b>Tipo:</b> {_clean(error_type)}\n"
            f"<b>Detalle:</b> {details_clean[:500]}\n"
        )

        bot = telegram.Bot(token=token)
        async with bot:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
        log.info("telegram_error_notification_sent", error_type=error_type)

    except Exception as e:
        log.error("telegram_error_notification_failed", error=str(e))
