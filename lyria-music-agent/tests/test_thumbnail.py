"""
Visual verification test for Arcadia Soundscapes thumbnails.
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
    ("Peaceful Ambient Meditation Music for Deep Relaxation and Sleep", "calm"),
    ("EPIC Cinematic Orchestral Battle Theme | Powerful Dramatic Music", "epic"),
    ("Lofi Hip Hop Beats to Study and Relax | Chill Vibes", "relaxing"),
    ("Dark Trap Instrumental 140 BPM | Hard Aggressive Beat", "dark"),
    ("Cozy Acoustic Coffee Shop Music | Warm Morning Vibes", "cozy"),
    ("Energetic Electronic Dance Music | Happy Upbeat EDM", "energetic"),
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
