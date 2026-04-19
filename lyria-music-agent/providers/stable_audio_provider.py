"""
Fallback 1: Stable Audio 2.5 via Stability AI API.
Formato de prompt: [BPM] [Genre] [Instruments] [Mood]
"""
import os
import requests
from core.retry import music_api_retry
import structlog

log = structlog.get_logger()

STABILITY_ENDPOINT = "https://api.stability.ai/v2beta/stable-audio/generate"

class StableAudioProvider:
    def __init__(self):
        self.api_key = os.getenv("STABILITY_API_KEY")

    @music_api_retry
    async def generate(self, prompt: str, output_path: str) -> dict:
        log.info("stable_audio_start", prompt_preview=prompt[:80])
        
        if not self.api_key:
            raise ValueError("STABILITY_API_KEY no configurado")

        response = requests.post(
            STABILITY_ENDPOINT,
            headers={
                "Authorization": f"Bearer {self.api_key}",
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
