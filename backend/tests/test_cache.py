from utils.cache import CacheManager

WINDOWS_INVALID = set('<>:"/\\|?*')


def test_cache_file_names_are_valid_on_windows(tmp_path):
    cache = CacheManager(str(tmp_path))

    cache.set("observations_good", {"start": "2026-10-14T00:00:00Z", "sat_id": "A/B"}, [1])

    names = [p.name for p in tmp_path.iterdir()]
    assert names and not any(set(name) & WINDOWS_INVALID for name in names)
    assert cache.get("observations_good", {"start": "2026-10-14T00:00:00Z", "sat_id": "A/B"}, 60)[0] == [1]
