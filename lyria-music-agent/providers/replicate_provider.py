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
    def __init__(self):
        self.api_token = os.getenv("REPLICATE_API_TOKEN")

    @music_api_retry
    async def generate(self, prompt: str, output_path: str) -> dict:
        log.info("replicate_musicgen_start", prompt_preview=prompt[:80])
        
        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN no configurado")

        os.environ["REPLICATE_API_TOKEN"] = self.api_token

        # Ejecutar y esperar asincronicamente
        output = replicate.run(
            MUSICGEN_MODEL,
            input={
                "prompt": prompt,
                "model_version": "stereo-large",  # mejor calidad
                "duration": 120,
                "output_format": "wav",
            }
        )
        
        # replicate.run returns the output straightforwardly
        audio_url = output
        
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
