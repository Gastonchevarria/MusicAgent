import asyncio
import os
from core.provider_orchestrator import generate_track_with_fallback

async def main():
    # Aseguramos que no haya keys para forzar el fallo
    if "GEMINI_API_KEY" in os.environ:
        del os.environ["GEMINI_API_KEY"]
    if "STABILITY_API_KEY" in os.environ:
        del os.environ["STABILITY_API_KEY"]
    if "REPLICATE_API_TOKEN" in os.environ:
        del os.environ["REPLICATE_API_TOKEN"]

    niche = "jazz instrumental para trabajar"
    base_path = "output_test"
    try:
        res = await generate_track_with_fallback(niche, base_path)
        print("Éxito inesperado", res)
    except Exception as e:
        print("Fallback verificado, todos fallaron correctamente:")
        print(e)

if __name__ == "__main__":
    asyncio.run(main())
