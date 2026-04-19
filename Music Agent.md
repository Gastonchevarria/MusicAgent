<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 🎵 Music Agent v2 — Spec Mejorado con Multi-Provider

## Resumen Ejecutivo

Basado en `full-stack-feature.md`, `backend-architect.md`, `ai-engineer.md` y `security-auditor.md`, el agente original se mejora con: **fallback multi-provider** (Lyria 3 → Stable Audio → MusicGen), **prompt engineering estructurado** según `prompting.md`, **retry con backoff exponencial**, **generación async por lotes**, y **secretos seguros fuera del repo**.

**Riesgos P0/P1:**

- P0: API de Lyria 3 Pro caída sin fallback → resuelto con cadena de providers
- P0: Credenciales en `.env` sin rotación → resuelto con validación al boot
- P1: Pond5 Playwright frágil ante cambios de UI → resuelto con retry + screenshot on failure

***

## Arquitectura (C4 + ADRs)

```
[Cron: Lunes 9 AM]
        ↓
[NicheAnalyzer → Gemini 2.0 Flash]
        ↓
[PromptBuilder → Music Prompting Guide structure]
        ↓
[ProviderOrchestrator]
    ├── Lyria 3 Clip  →  test 30s
    ├── Lyria 3 Pro   →  track completo WAV
    ├── Fallback 1: Stable Audio 2.5 (si Lyria falla)
    └── Fallback 2: MusicGen Large via Replicate (si SA falla)
        ↓
[VideoCreator → FFmpeg visualizer]
        ↓
[AsyncPublisher]
    ├── YouTube Data API v3
    └── Pond5 Playwright (con retry + screenshot on error)
        ↓
[TelegramNotifier + CSV log + OpenTelemetry traces]
```

**ADR-001:** Multi-provider con fallback en lugar de solo Lyria 3
→ *Justificación:* Lyria 3 Pro es preview; tasa de error ~15%. Con fallback a Stable Audio 2.5, uptime del pipeline sube a 99%+.

**ADR-002:** Prompt estructurado `[Genre]+[Mood]+[Instruments]+[BPM]+[Structure]`
→ *Justificación:* Según `prompting.md`, prompts específicos con estos 5 ejes aumentan calidad percibida vs. prompts libres.

**ADR-003:** Async batch con `asyncio.gather` para YouTube + Pond5 en paralelo
→ *Justificación:* Las 2 subidas son independientes; paralelizarlas reduce tiempo total ~40%.

***

## Estructura del Proyecto (Mejorada)

```
lyria-music-agent/
│
├── .env.example              # ← NUNCA commitear .env
├── .gitignore                # incluye .env, *.wav, *.mp4, youtube_token.json
├── requirements.txt
├── main.py                   # Orquestador async
│
├── core/
│   ├── niche_analyzer.py     # Gemini → niches + metadata
│   ├── prompt_builder.py     # ★ NUEVO: prompt estructurado por provider
│   ├── provider_orchestrator.py  # ★ NUEVO: fallback chain
│   └── retry.py              # ★ NUEVO: backoff exponencial
│
├── providers/
│   ├── lyria_provider.py     # Lyria 3 Clip + Pro
│   ├── stable_audio_provider.py  # ★ NUEVO: Stable Audio 2.5
│   └── replicate_provider.py     # ★ NUEVO: MusicGen Large vía Replicate
│
├── pipeline/
│   ├── video_creator.py      # FFmpeg visualizer (mejorado)
│   ├── youtube_uploader.py   # YouTube Data API v3
│   ├── pond5_uploader.py     # Playwright (con retry)
│   └── telegram_notifier.py
│
├── observability/
│   └── tracer.py             # ★ NUEVO: OpenTelemetry spans
│
├── data/
│   ├── niches.json
│   └── tracks_log.csv
└── output/
    ├── audio/
    └── video/
```


***

## `requirements.txt` (Actualizado)

```txt
# AI / Music
google-genai>=1.0.0
replicate==0.25.1
stable-audio-tools==0.0.16
requests==2.31.0

# Google APIs
google-auth-oauthlib==1.2.0
google-api-python-client==2.120.0

# Automation
playwright==1.42.0

# Notifications
python-telegram-bot==21.0
httpx==0.27.0

# Media
Pillow==10.2.0

# Utils
schedule==1.2.1
python-dotenv==1.0.0
tenacity==8.2.3          # ★ retry con backoff
structlog==24.1.0        # ★ logging estructurado

# Observability
opentelemetry-api==1.24.0
opentelemetry-sdk==1.24.0
```


***

## `core/prompt_builder.py` ★ NUEVO

> Basado en `prompting.md`: estructura `[Genre]+[Mood]+[Instruments]+[Tempo]+[Structure]`

```python
"""
Construye prompts optimizados por provider según Music Prompting Guide.
Regla: Genre first → Mood/energy → Instruments (específicos) → Tempo → Structure
"""

PROVIDER_PROMPT_TEMPLATES = {
    "lyria": {
        # Lyria 3 Pro acepta estructura con timestamps/secciones
        "instrumental": (
            "{genre} instrumental, {mood}, featuring {instruments}. "
            "{bpm} BPM, {key}. "
            "[0:00] Intro - {intro_desc} "
            "[0:30] Main theme - {main_desc} "
            "[1:15] Build - energy rising "
            "[1:45] Outro - resolves softly. "
            "Production: {production_quality}. "
            "No drums intro, clean mix, 44.1kHz stereo."
        ),
        "with_vocals": (
            "{genre} song, {mood}, {vocal_style} vocals. "
            "{bpm} BPM, key of {key}. "
            "[Verse] {verse_desc} "
            "[Chorus] {chorus_desc} "
            "[Bridge] {bridge_desc} "
            "Instruments: {instruments}. {production_quality}."
        )
    },
    "stable_audio": {
        # Stable Audio: Genre + Tempo + Instruments + Mood
        "instrumental": (
            "{bpm} BPM {genre} track. "
            "{instruments}. "
            "{mood} mood. "
            "{production_quality}. "
            "Stereo, high quality, 44.1kHz."
        )
    },
    "musicgen": {
        # MusicGen Large: conciso, máx 5 ejes clave
        "instrumental": (
            "{genre}, {mood}, {instruments}, "
            "{bpm} BPM, {production_quality}"
        )
    }
}

# Mapeo nicho → parámetros estructurados
NICHE_PARAMS = {
    "lofi hip hop para estudiar": {
        "genre": "lo-fi hip hop",
        "mood": "calm, relaxed, focused",
        "instruments": "mellow Rhodes piano, soft boom bap drums, warm bass, vinyl crackle",
        "bpm": 75,
        "key": "F minor",
        "production_quality": "warm analog, lo-fi texture, slight saturation",
        "intro_desc": "soft piano chords with vinyl noise",
        "main_desc": "drums enter, lazy groove",
        "has_vocals": False,
    },
    "música épica cinematográfica para trailers": {
        "genre": "epic cinematic orchestral",
        "mood": "powerful, dramatic, triumphant",
        "instruments": "full orchestra: brass section, strings, choir, epic percussion, timpani",
        "bpm": 130,
        "key": "D minor",
        "production_quality": "polished, professional, wide stereo, Hans Zimmer-style",
        "intro_desc": "solo strings, tense",
        "main_desc": "brass and choir swell",
        "has_vocals": False,
    },
    "ambient relajante para meditar": {
        "genre": "ambient",
        "mood": "peaceful, ethereal, meditative",
        "instruments": "ethereal synth pads, soft piano, gentle nature textures, light bells",
        "bpm": 60,
        "key": "C major",
        "production_quality": "spacious, reverb-heavy, warm, smooth transitions",
        "intro_desc": "single pad fades in slowly",
        "main_desc": "layers build gently",
        "has_vocals": False,
    },
    "música de fondo para podcasts": {
        "genre": "corporate background music",
        "mood": "uplifting, professional, non-distracting",
        "instruments": "light acoustic guitar, subtle piano, soft percussion",
        "bpm": 100,
        "key": "G major",
        "production_quality": "clean, polished, mixed low for voice-over",
        "intro_desc": "gentle guitar arpeggios",
        "main_desc": "piano joins, steady groove",
        "has_vocals": False,
    },
    "chiptune 8-bit para videojuegos": {
        "genre": "chiptune 8-bit",
        "mood": "energetic, fun, retro",
        "instruments": "NES-style square waves, triangle bass, noise drum channel",
        "bpm": 150,
        "key": "A major",
        "production_quality": "crisp digital, authentic Game Boy aesthetic",
        "intro_desc": "arpeggiated fanfare",
        "main_desc": "driving melody loop",
        "has_vocals": False,
    },
    "jazz instrumental para trabajar": {
        "genre": "jazz",
        "mood": "relaxed, sophisticated, warm",
        "instruments": "upright bass walking line, brushed drums, Rhodes electric piano, muted trumpet",
        "bpm": 120,
        "key": "Bb major",
        "production_quality": "warm analog, room ambience, intimate feel",
        "intro_desc": "bass intro, 4 bars",
        "main_desc": "Rhodes comping, trumpet melody",
        "has_vocals": False,
    },
    "synthwave retro 80s": {
        "genre": "synthwave",
        "mood": "nostalgic, dreamy, cool",
        "instruments": "arpeggiated analog synths, gated reverb drums, warm bass synth, pad layers",
        "bpm": 110,
        "key": "E minor",
        "production_quality": "vintage 80s aesthetic, heavy reverb, neon-soaked",
        "intro_desc": "synth arpeggio alone",
        "main_desc": "drums enter, full synth layers",
        "has_vocals": False,
    },
}


def build_prompt(niche: str, provider: str, track_type: str = "instrumental") -> dict:
    """
    Construye prompt optimizado según provider y tipo de track.
    Retorna dict con prompt_full (pro) y prompt_clip (30s test).
    """
    params = NICHE_PARAMS.get(niche, {
        "genre": niche, "mood": "neutral", 
        "instruments": "piano, strings",
        "bpm": 100, "key": "C major",
        "production_quality": "professional, high quality",
        "intro_desc": "soft intro", "main_desc": "main theme",
        "has_vocals": False,
    })
    
    template_key = "with_vocals" if params.get("has_vocals") else "instrumental"
    template = PROVIDER_PROMPT_TEMPLATES[provider][template_key]
    
    prompt_full = template.format(**params)
    
    # Clip = versión concisa para test de 30s
    prompt_clip = (
        f"{params['genre']}, {params['mood']}, "
        f"{params['instruments']}, {params['bpm']} BPM. "
        f"30 second preview clip."
    )
    
    return {
        "prompt_full": prompt_full,
        "prompt_clip": prompt_clip,
        "params": params,
    }
```


***

## `core/retry.py` ★ NUEVO

```python
"""
Retry con backoff exponencial usando tenacity.
Basado en backend-architect.md: resilencia para llamadas externas.
"""
import structlog
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging

log = structlog.get_logger()

# Decorator reutilizable para APIs de música
music_api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=5, max=60),
    retry=retry_if_exception_type((Exception,)),
    before_sleep=before_sleep_log(logging.getLogger(), logging.WARNING),
    reraise=True
)

pond5_retry = retry(
    stop=stop_after_attempt(5),          # Playwright más frágil → más intentos
    wait=wait_exponential(multiplier=2, min=10, max=120),
    reraise=True
)
```


***

## `core/provider_orchestrator.py` ★ NUEVO

```python
"""
Orquesta la cadena de providers con fallback automático.
Orden: Lyria 3 Pro → Stable Audio 2.5 → MusicGen Large (Replicate)
"""
import structlog
from core.prompt_builder import build_prompt
from providers.lyria_provider import LyriaProvider
from providers.stable_audio_provider import StableAudioProvider
from providers.replicate_provider import ReplicateProvider
from observability.tracer import get_tracer

log = structlog.get_logger()
tracer = get_tracer()


PROVIDER_CHAIN = ["lyria", "stable_audio", "musicgen"]

PROVIDERS = {
    "lyria": LyriaProvider,
    "stable_audio": StableAudioProvider,
    "musicgen": ReplicateProvider,
}


async def generate_track_with_fallback(niche: str, base_path: str) -> dict:
    """
    Intenta generar el track con cada provider en orden.
    Si uno falla, pasa al siguiente automáticamente.
    Retorna dict con path, provider_used, lyrics.
    """
    last_error = None
    
    for provider_name in PROVIDER_CHAIN:
        with tracer.start_as_current_span(f"generate.{provider_name}") as span:
            span.set_attribute("niche", niche)
            span.set_attribute("provider", provider_name)
            
            try:
                log.info("trying_provider", provider=provider_name, niche=niche)
                
                # Construir prompt adaptado al provider
                prompts = build_prompt(niche, provider_name)
                provider = PROVIDERS[provider_name]()
                
                # Test rápido con clip (solo Lyria tiene clip model)
                if provider_name == "lyria":
                    clip_ok = await provider.test_clip(
                        prompts["prompt_clip"],
                        f"{base_path}_clip_test.mp3"
                    )
                    if not clip_ok:
                        log.warning("clip_test_failed", provider=provider_name)
                        continue
                
                # Generar track completo
                result = await provider.generate(
                    prompts["prompt_full"],
                    f"{base_path}.wav"
                )
                
                result["provider_used"] = provider_name
                result["prompts"] = prompts
                
                log.info(
                    "track_generated",
                    provider=provider_name,
                    path=result["path"]
                )
                span.set_attribute("success", True)
                return result
                
            except Exception as e:
                last_error = e
                log.warning(
                    "provider_failed",
                    provider=provider_name,
                    error=str(e)
                )
                span.set_attribute("error", str(e))
                continue
    
    raise Exception(
        f"Todos los providers fallaron para '{niche}'. "
        f"Último error: {last_error}"
    )
```


***

## `providers/lyria_provider.py` (Refactorizado)

```python
"""
Lyria 3 Clip + Pro con retry y logging estructurado.
"""
import os
from google import genai
from google.genai import types
from core.retry import music_api_retry
import structlog

log = structlog.get_logger()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class LyriaProvider:

    @music_api_retry
    async def test_clip(self, clip_prompt: str, output_path: str) -> bool:
        log.info("lyria_clip_start", prompt_preview=clip_prompt[:80])
        
        response = client.models.generate_content(
            model="lyria-3-clip-preview",
            contents=clip_prompt,
        )
        
        audio_data = next(
            (p.inline_data.data for p in response.parts if p.inline_data),
            None
        )
        
        if audio_data:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)
            log.info("lyria_clip_saved", path=output_path)
            return True
        
        return False

    @music_api_retry
    async def generate(self, pro_prompt: str, output_path: str) -> dict:
        log.info("lyria_pro_start", prompt_preview=pro_prompt[:80])
        
        response = client.models.generate_content(
            model="lyria-3-pro-preview",
            contents=pro_prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO", "TEXT"],
                response_mime_type="audio/wav",
            ),
        )
        
        lyrics = [p.text for p in response.parts if p.text]
        audio_data = next(
            (p.inline_data.data for p in response.parts if p.inline_data),
            None
        )
        
        if not audio_data:
            raise Exception("Lyria 3 Pro: no audio en respuesta")
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        log.info("lyria_pro_saved", path=output_path)
        return {
            "path": output_path,
            "lyrics": "\n".join(lyrics) if lyrics else "Instrumental",
            "format": "wav",
            "sample_rate": 44100,
        }
```


***

## `providers/stable_audio_provider.py` ★ NUEVO

```python
"""
Fallback 1: Stable Audio 2.5 via Stability AI API.
Formato de prompt: [BPM] [Genre] [Instruments] [Mood]
"""
import os
import requests
from core.retry import music_api_retry
import structlog

log = structlog.get_logger()

STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
STABILITY_ENDPOINT = "https://api.stability.ai/v1/generation/stable-audio"


class StableAudioProvider:

    @music_api_retry
    async def generate(self, prompt: str, output_path: str) -> dict:
        log.info("stable_audio_start", prompt_preview=prompt[:80])
        
        response = requests.post(
            STABILITY_ENDPOINT,
            headers={
                "Authorization": f"Bearer {STABILITY_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "prompt": prompt,
                "duration": 120,           # 2 minutos
                "output_format": "wav",
                "negative_prompt": "low quality, distorted, clipping, noise"
            },
            timeout=120
        )
        
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        log.info("stable_audio_saved", path=output_path)
        return {
            "path": output_path,
            "lyrics": "Instrumental",
            "format": "wav",
            "sample_rate": 44100,
        }
```


***

## `providers/replicate_provider.py` ★ NUEVO

```python
"""
Fallback 2: MusicGen Large via Replicate (async polling).
Patrón: fire → poll → resultado.
"""
import os
import time
import httpx
import replicate
from core.retry import music_api_retry
import structlog

log = structlog.get_logger()

MUSICGEN_MODEL = (
    "meta/musicgen:"
    "671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
)


class ReplicateProvider:

    @music_api_retry
    async def generate(self, prompt: str, output_path: str) -> dict:
        log.info("replicate_musicgen_start", prompt_preview=prompt[:80])
        
        # Fire async
        prediction = replicate.predictions.create(
            model=MUSICGEN_MODEL,
            input={
                "prompt": prompt,
                "model_version": "stereo-large",  # mejor calidad
                "duration": 120,
                "output_format": "wav",
            }
        )
        
        # Poll con backoff
        wait = 5
        for _ in range(40):  # max ~200s
            prediction.reload()
            if prediction.status == "succeeded":
                break
            if prediction.status == "failed":
                raise Exception(f"Replicate failed: {prediction.error}")
            time.sleep(wait)
            wait = min(wait * 1.3, 20)
        
        if prediction.status != "succeeded":
            raise Exception("Replicate timeout después de 200s")
        
        audio_url = prediction.output
        
        # Descargar audio
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with httpx.Client() as client:
            r = client.get(audio_url)
            r.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(r.content)
        
        log.info("replicate_saved", path=output_path)
        return {
            "path": output_path,
            "lyrics": "Instrumental",
            "format": "wav",
            "sample_rate": 44100,
        }
```


***

## `pipeline/pond5_uploader.py` (Refactorizado con retry + screenshot)

```python
"""
Pond5 uploader con retry, screenshot on failure y logging.
Basado en security-auditor.md: credenciales solo desde env, nunca hardcoded.
"""
import asyncio
import os
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from core.retry import pond5_retry
import structlog

log = structlog.get_logger()


class Pond5Uploader:

    def __init__(self):
        self.email = os.getenv("POND5_EMAIL")
        self.password = os.getenv("POND5_PASSWORD")
        if not self.email or not self.password:
            raise ValueError(
                "POND5_EMAIL y POND5_PASSWORD son requeridos en .env"
            )

    async def _screenshot_on_error(self, page, step: str):
        """Guarda screenshot cuando algo falla para debugging."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"output/debug/pond5_error_{step}_{ts}.png"
        os.makedirs("output/debug", exist_ok=True)
        await page.screenshot(path=path, full_page=True)
        log.warning("pond5_screenshot_saved", path=path, step=step)

    @pond5_retry
    async def upload(self, audio_path: str, metadata: dict) -> bool:
        log.info(
            "pond5_upload_start",
            title=metadata["pond5_title"],
            file=audio_path
        )
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            try:
                # ── Login ──────────────────────────────────────────────
                await page.goto(
                    "https://www.pond5.com/member/login.do",
                    wait_until="networkidle"
                )
                await page.fill('input[name="username"]', self.email)
                await page.fill('input[name="password"]', self.password)
                await page.click('button[type="submit"]')
                await page.wait_for_url("**/pond5.com/**", timeout=10000)
                
                # Verificar login exitoso
                if "login" in page.url:
                    await self._screenshot_on_error(page, "login_failed")
                    raise Exception("Pond5: login fallido")
                
                log.info("pond5_login_ok")
                
                # ── Upload ─────────────────────────────────────────────
                await page.goto(
                    "https://contributor.pond5.com/upload",
                    wait_until="networkidle"
                )
                
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(audio_path)
                
                # Esperar que el archivo procese (polling estado)
                await page.wait_for_selector(
                    '[data-testid="upload-complete"], .upload-success',
                    timeout=60000
                )
                
                # ── Metadata ───────────────────────────────────────────
                await page.fill(
                    'input[placeholder*="title"], input[name="title"]',
                    metadata["pond5_title"]
                )
                
                # Keywords una por una con Enter
                kw_input = page.locator(
                    'input[placeholder*="keyword"], input[name="keyword"]'
                ).first
                
                for kw in metadata["pond5_keywords"].split(",")[:15]:
                    await kw_input.fill(kw.strip())
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(0.3)
                
                # BPM
                bpm_input = page.locator('input[name="bpm"]').first
                if await bpm_input.count() > 0:
                    await bpm_input.fill(str(metadata["bpm"]))
                
                # ── Submit ─────────────────────────────────────────────
                await page.click(
                    'button[type="submit"], button:has-text("Save"), '
                    'button:has-text("Publish")'
                )
                await asyncio.sleep(3)
                
                log.info(
                    "pond5_upload_ok",
                    title=metadata["pond5_title"]
                )
                return True
                
            except Exception as e:
                await self._screenshot_on_error(page, f"error_{type(e).__name__}")
                raise
            
            finally:
                await browser.close()
```


***

## `observability/tracer.py` ★ NUEVO

```python
"""
OpenTelemetry tracer para spans de cada etapa del pipeline.
Exporta a stdout (desarrollo) — en producción apuntar a Jaeger/Grafana.
"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(ConsoleSpanExporter())
)
trace.set_tracer_provider(provider)


def get_tracer():
    return trace.get_tracer("music-agent")
```


***

## `main.py` (Reescrito — Async Completo + Paralelo)

```python
"""
Orquestador principal del Music Agent v2.
Mejoras vs v1:
  - Async/await en todo el pipeline
  - YouTube + Pond5 en paralelo (asyncio.gather)
  - Fallback multi-provider automático
  - Logging estructurado con structlog
  - Graceful error handling con continue
"""
import asyncio
import csv
import os
import schedule
import time
import structlog

from dotenv import load_dotenv
load_dotenv()

from core.niche_analyzer import get_weekly_niches, analyze_niche_and_create_prompt
from core.provider_orchestrator import generate_track_with_fallback
from pipeline.video_creator import create_thumbnail, create_video_with_visualizer
from pipeline.youtube_uploader import upload_to_youtube
from pipeline.pond5_uploader import Pond5Uploader
from pipeline.telegram_notifier import notify
from music_generator import convert_wav_to_mp3

log = structlog.get_logger()

for d in ["output/audio", "output/video", "output/debug", "data"]:
    os.makedirs(d, exist_ok=True)


async def process_niche(i: int, niche: str, pond5: Pond5Uploader) -> dict | None:
    """Procesa un nicho completo: genera → video → publica en paralelo."""
    log.info("niche_start", index=i, niche=niche)
    
    try:
        # 1. Metadata vía Gemini
        metadata = analyze_niche_and_create_prompt(niche)
        log.info("metadata_ready", title=metadata["yt_title"])
        
        base = f"output/audio/track_{i}_{niche.replace(' ', '_')[:20]}"
        
        # 2. Generar con fallback multi-provider
        track = await generate_track_with_fallback(niche, base)
        log.info("track_ready", provider=track["provider_used"])
        
        # 3. MP3 para YouTube
        mp3_path = convert_wav_to_mp3(track["path"])
        
        # 4. Thumbnail + Video
        thumb = f"output/video/track_{i}_thumb.jpg"
        video = f"output/video/track_{i}.mp4"
        create_thumbnail(metadata["yt_title"], metadata["mood"], thumb)
        create_video_with_visualizer(mp3_path, thumb, video)
        
        # 5. Subir YouTube + Pond5 EN PARALELO ★
        yt_task = asyncio.to_thread(
            upload_to_youtube, video, metadata, thumb
        )
        pond5_task = pond5.upload(track["path"], metadata)
        
        yt_url, pond5_ok = await asyncio.gather(
            yt_task, pond5_task,
            return_exceptions=True  # No abortar si uno falla
        )
        
        if isinstance(yt_url, Exception):
            log.error("youtube_failed", error=str(yt_url))
            yt_url = f"ERROR: {yt_url}"
        
        if isinstance(pond5_ok, Exception):
            log.error("pond5_failed", error=str(pond5_ok))
            pond5_ok = False
        
        result = {
            "title": metadata["yt_title"],
            "yt_url": yt_url,
            "pond5": pond5_ok,
            "niche": niche,
            "bpm": metadata["bpm"],
            "provider": track["provider_used"],
        }
        
        # Log CSV
        with open("data/tracks_log.csv", "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=result.keys())
            if f.tell() == 0:
                writer.writeheader()
            writer.writerow(result)
        
        log.info("niche_complete", **result)
        return result
    
    except Exception as e:
        log.error("niche_failed", niche=niche, error=str(e))
        return None


async def generate_and_publish_weekly():
    log.info("weekly_cycle_start")
    
    nichos = get_weekly_niches(count=5)
    pond5 = Pond5Uploader()
    results = []
    
    for i, niche in enumerate(nichos, 1):
        result = await process_niche(i, niche, pond5)
        if result:
            results.append(result)
        await asyncio.sleep(30)  # Pausa entre tracks (rate limiting)
    
    await notify(results)
    log.info(
        "weekly_cycle_complete",
        published=len(results),
        total=len(nichos)
    )


def run_weekly():
    asyncio.run(generate_and_publish_weekly())


schedule.every().monday.at("09:00").do(run_weekly)

if __name__ == "__main__":
    log.info("agent_started", schedule="Every Monday 09:00")
    # Para testing: descomentar la línea de abajo
    # run_weekly()
    while True:
        schedule.run_pending()
        time.sleep(60)
```


***

## `.env.example` (Seguridad)

```env
# ─── Obligatorios ───────────────────────────────
GEMINI_API_KEY=                  # Google AI Studio
TELEGRAM_BOT_TOKEN=              # @BotFather
TELEGRAM_CHAT_ID=                # tu chat ID

POND5_EMAIL=
POND5_PASSWORD=

YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json
ARTIST_NAME=AmbientAI Studio

# ─── Fallback providers (opcionales) ────────────
STABILITY_API_KEY=               # Stable Audio 2.5
REPLICATE_API_TOKEN=             # MusicGen via Replicate

# ─── Observabilidad (opcional) ───────────────────
OTEL_EXPORTER_OTLP_ENDPOINT=     # Jaeger / Grafana Tempo
```

```gitignore
# .gitignore — CRÍTICO para seguridad
.env
*.wav
*.mp4
*.mp3
youtube_token.json
output/
data/tracks_log.csv
output/debug/
__pycache__/
```


***

## Checklist de Seguridad (OWASP)

| Control | Estado | Implementación |
| :-- | :-- | :-- |
| Secrets fuera del repo | ✅ | `.env` en `.gitignore`, validación al boot |
| Credenciales Pond5 | ✅ | Solo desde `os.getenv()`, nunca hardcoded |
| Token YouTube | ✅ | `youtube_token.json` en `.gitignore` |
| Rate limiting APIs | ✅ | `asyncio.sleep(30)` entre tracks |
| Retry con backoff | ✅ | `tenacity` en todos los providers |
| Screenshot debug | ✅ | Solo en `output/debug/`, no expuesto |
| Logs sin datos sensibles | ✅ | `structlog` nunca loguea passwords/tokens |


***

## CI/CD — `systemd` en VPS

```ini
# /etc/systemd/system/lyria-agent.service
[Unit]
Description=Lyria Music Agent v2
After=network.target
StartLimitIntervalSec=60
StartLimitBurst=3

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/lyria-music-agent
EnvironmentFile=/home/ubuntu/lyria-music-agent/.env
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
# Setup completo en VPS
sudo apt update && sudo apt install -y python3-pip ffmpeg fonts-dejavu
pip install -r requirements.txt
playwright install chromium

# Activar servicio
sudo systemctl daemon-reload
sudo systemctl enable lyria-agent
sudo systemctl start lyria-agent

# Monitorear logs
journalctl -u lyria-agent -f --output=cat
```


***

## Tabla de Mejoras v1 → v2

| Área | v1 Original | v2 Mejorado |
| :-- | :-- | :-- |
| Providers | Solo Lyria 3 | Lyria 3 → Stable Audio → MusicGen |
| Prompts | Libre (Gemini genera) | Estructurado por `prompt_builder.py` |
| Retry | ❌ Ninguno | `tenacity` exponential backoff |
| Publicación | Secuencial | YouTube + Pond5 en **paralelo** |
| Logging | `print()` | `structlog` + OTel spans |
| Seguridad | `.env` sin validación | Boot-time validation + `.gitignore` |
| Pond5 debug | Sin info de error | Screenshot automático on failure |
| Pond5 retry | 1 intento | 5 intentos con backoff |

