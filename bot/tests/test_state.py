import time

from state import State


def test_mark_is_persisted(tmp_path):
    path = tmp_path / "state.json"
    state = State(path)

    assert not state.contains("pass:LUSAT:2026-10-27T18:30:00Z")
    state.mark("pass:LUSAT:2026-10-27T18:30:00Z")

    assert State(path).contains("pass:LUSAT:2026-10-27T18:30:00Z")


def test_prune_removes_old_entries(tmp_path):
    state = State(tmp_path / "state.json")
    state.mark("old", timestamp=time.time() - 10 * 86400)
    state.mark("new")

    state.prune(max_age_days=3)

    assert not state.contains("old")
    assert state.contains("new")


def test_a_corrupt_file_starts_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("not json", encoding="utf-8")

    state = State(path)

    assert not state.contains("anything")
    state.mark("anything")
    assert State(path).contains("anything")
