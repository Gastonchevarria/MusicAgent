"""
Visual verification test for Arcadia Music thumbnails.
Generates thumbnails for each mood and saves to output/video/test_thumbs/.
Run and visually inspect the results.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.video_creator import create_thumbnail

TEST_DIR = "output/video/test_thumbs"
os.makedirs(TEST_DIR, exist_ok=True)

TEST_CASES = [
    ("Neon Pulse Protocol | Melodic Techno", "hypnotic"),
    ("Shattered Horizon | Dark Melodic Techno", "dark"),
    ("Voltage In The Veins | Peak Time Techno", "aggressive"),
    ("Ghost Frequency | Industrial Techno", "dystopian"),
    ("Eclipse Protocol | Progressive Techno", "emotional"),
    ("Bad Angels Dance | Cyberpunk Electronic", "futuristic"),
    ("Acid Nerve | Acid Techno", "psychedelic"),
    ("Desert Mirage | Organic House", "warm"),
    ("Short Title", "neutral"),
]


def test_all_thumbnails():
    for i, (title, mood) in enumerate(TEST_CASES):
        out = os.path.join(TEST_DIR, f"thumb_{mood}_{i}.jpg")
        create_thumbnail(title, mood, out)
        assert os.path.exists(out), f"Thumbnail not created: {out}"
        size = os.path.getsize(out)
        assert size > 5000, f"Thumbnail too small ({size} bytes): {out}"
        print(f"  OK: {out} ({size:,} bytes) -- {mood}")

    print(f"\nALL {len(TEST_CASES)} THUMBNAILS GENERATED")
    print(f"Visually inspect: {os.path.abspath(TEST_DIR)}/")


if __name__ == "__main__":
    test_all_thumbnails()
