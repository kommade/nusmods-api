import os
import time

from nusmods_api.cache import Cache


def test_cache_round_trip(tmp_path):
    cache = Cache(tmp_path)

    cache.set("modules", {"moduleCode": "CS1010"})

    assert cache.get("modules") == {"moduleCode": "CS1010"}


def test_cache_uses_distinct_files_for_keys(tmp_path):
    cache = Cache(tmp_path)

    cache.set("first", 1)
    cache.set("second", 2)

    assert cache.get("first") == 1
    assert cache.get("second") == 2
    assert len(list(tmp_path.glob("*.json"))) == 2


def test_missing_cache_entry_returns_none(tmp_path):
    assert Cache(tmp_path).get("missing") is None


def test_delete_removes_entry_and_is_idempotent(tmp_path):
    cache = Cache(tmp_path)
    cache.set("modules", [1, 2, 3])

    cache.delete("modules")
    cache.delete("modules")

    assert cache.get("modules") is None


def test_clear_removes_all_json_entries(tmp_path):
    cache = Cache(tmp_path)
    cache.set("first", 1)
    cache.set("second", 2)
    (tmp_path / "not-a-cache-file.txt").write_text("keep", encoding="utf-8")

    cache.clear()

    assert list(tmp_path.glob("*.json")) == []
    assert (tmp_path / "not-a-cache-file.txt").exists()


def test_expired_entry_is_removed(tmp_path):
    cache = Cache(tmp_path, expiration=1)
    cache.set("modules", {"value": 1})
    path = cache._path_for("modules")
    old_time = time.time() - 10
    os.utime(path, (old_time, old_time))

    assert cache.get("modules") is None
    assert not path.exists()


def test_malformed_json_is_treated_as_cache_miss(tmp_path):
    cache = Cache(tmp_path)
    path = cache._path_for("broken")
    path.write_text("{invalid", encoding="utf-8")

    assert cache.get("broken") is None


def test_cache_can_be_configured_without_expiration(tmp_path):
    cache = Cache(tmp_path, expiration=None)
    cache.set("modules", {"value": 1})
    path = cache._path_for("modules")
    old_time = time.time() - 100_000
    os.utime(path, (old_time, old_time))

    assert cache.get("modules") == {"value": 1}
