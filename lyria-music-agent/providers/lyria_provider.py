"""
Lyria 3 Clip + Pro con retry y logging estructurado.
"""
import os
from google import genai
from google.genai import types
from core.retry import music_api_retry
import structlog

log = structlog.get_logger()

class LyriaProvider:
    def __init__(self):
        # Inicializa cliente explicitamente con GEMINI_API_KEY
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
             log.warning("GEMINI_API_KEY is missing from environment!")
        self.client = genai.Client(api_key=api_key)

    @music_api_retry
    async def test_clip(self, clip_prompt: str, output_path: str) -> bool:
        log.info("lyria_clip_start", prompt_preview=clip_prompt[:80])
        
        response = self.client.models.generate_content(
            model="lyria-3-clip-preview",
            contents=clip_prompt,
        )
        
        parts = response.candidates[0].content.parts if hasattr(response, 'candidates') and response.candidates else (response.parts if hasattr(response, 'parts') else [])
        audio_data = next(
            (p.inline_data.data for p in parts if getattr(p, 'inline_data', None)),
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
        
        response = self.client.models.generate_content(
            model="lyria-3-pro-preview",
            contents=pro_prompt,
        )
        
        parts = response.candidates[0].content.parts if hasattr(response, 'candidates') and response.candidates else (response.parts if hasattr(response, 'parts') else [])
        lyrics = [p.text for p in parts if getattr(p, 'text', None)]
        audio_data = next(
            (p.inline_data.data for p in parts if getattr(p, 'inline_data', None)),
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
