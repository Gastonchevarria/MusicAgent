import unittest
from core.prompt_builder import build_prompt

class TestPromptBuilder(unittest.TestCase):
    def test_all_niches(self):
        niches = [
            "lofi hip hop para estudiar",
            "música épica cinematográfica para trailers",
            "ambient relajante para meditar",
            "música de fondo para podcasts",
            "chiptune 8-bit para videojuegos",
            "jazz instrumental para trabajar",
            "synthwave retro 80s",
            "música dramática para YouTube vlogs",
            "trap beats instrumentales",
            "música acústica para cafeterías",
            "unknown niche fallback"
        ]
        
        providers = ["lyria", "stable_audio", "musicgen"]
        
        for niche in niches:
            for provider in providers:
                res = build_prompt(niche, provider)
                self.assertIn("prompt_full", res)
                self.assertIn("prompt_clip", res)
                self.assertTrue(len(res["prompt_full"]) > 0)
                self.assertTrue(len(res["prompt_clip"]) > 0)

if __name__ == '__main__':
    unittest.main()
