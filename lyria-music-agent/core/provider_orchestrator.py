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
