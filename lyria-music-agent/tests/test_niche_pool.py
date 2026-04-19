import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_get_daily_niche_returns_string():
    from core.niche_analyzer import get_daily_niche
    # Create a fake pool file
    os.makedirs("data", exist_ok=True)
    pool = {
        "date": "2026-04-17",
        "niches": ["niche_0", "niche_1", "niche_2", "niche_3",
                    "niche_4", "niche_5", "niche_6"],
    }
    with open("data/weekly_pool.json", "w") as f:
        json.dump(pool, f)

    niche = get_daily_niche(0)
    assert niche == "niche_0"
    niche = get_daily_niche(6)
    assert niche == "niche_6"
    print("  OK: get_daily_niche returns correct niche by index")


def test_get_daily_niche_wraps_on_overflow():
    from core.niche_analyzer import get_daily_niche
    # index 7 should wrap to 0
    niche = get_daily_niche(7)
    assert niche == "niche_0"
    print("  OK: get_daily_niche wraps on overflow")


def test_pool_file_missing_triggers_generation():
    from core.niche_analyzer import get_daily_niche
    # Remove pool file -- should regenerate and return a string
    if os.path.exists("data/weekly_pool.json"):
        os.remove("data/weekly_pool.json")
    niche = get_daily_niche(0)
    assert isinstance(niche, str)
    assert len(niche) > 0
    print(f"  OK: missing pool triggers generation, got: {niche}")


if __name__ == "__main__":
    test_get_daily_niche_returns_string()
    test_get_daily_niche_wraps_on_overflow()
    test_pool_file_missing_triggers_generation()
    print("\nALL NICHE POOL TESTS PASSED")
