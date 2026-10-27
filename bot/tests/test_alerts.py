from datetime import datetime, timedelta, timezone

from alerts import is_tle_stale, passes_to_alert, select_agenda

NOW = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)


def iso(minutes: int) -> str:
    return (NOW + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_pass(minutes: int, elevation: float = 50, **extra) -> dict:
    return {"aos": iso(minutes), "max_elevation_deg": elevation, **extra}


def test_alerts_only_inside_the_lead_window():
    passes = [make_pass(10), make_pass(20), make_pass(-1)]

    selected = passes_to_alert(passes, NOW, lead_min=15)

    assert [p["aos"] for p in selected] == [iso(10)]


def test_alerts_skip_a_pass_already_under_way():
    passes = [make_pass(5, aos_clipped=True), make_pass(5)]

    selected = passes_to_alert(passes, NOW, lead_min=15)

    assert len(selected) == 1
    assert selected[0].get("aos_clipped") is None


def test_alerts_are_sorted_by_aos():
    passes = [make_pass(10), make_pass(3)]

    selected = passes_to_alert(passes, NOW, lead_min=15)

    assert [p["aos"] for p in selected] == [iso(3), iso(10)]


def test_agenda_filters_by_elevation_and_limits():
    passes = [make_pass(10, 5), make_pass(20, 30), make_pass(30, 80), make_pass(40, 40)]

    selected = select_agenda(passes, min_elevation_deg=10, limit=2)

    assert [p["max_elevation_deg"] for p in selected] == [30, 80]


def test_tle_is_stale_only_above_the_threshold():
    assert is_tle_stale({"tle_age_days": 8}, 7)
    assert not is_tle_stale({"tle_age_days": 7}, 7)
    assert not is_tle_stale({"tle_age_days": None}, 7)
    assert not is_tle_stale({}, 7)
