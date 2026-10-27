from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from config import Settings
from runtime import Runtime

NOW = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        bot_token="token",
        chat_id=None,
        backend_url="http://backend",
        alert_lead_min=15,
        pass_scan_interval_min=5,
        agenda_hour_utc=9,
        tle_max_age_days=7.0,
        min_elevation_deg=10.0,
        timezone=ZoneInfo("UTC"),
        timezone_name="UTC",
        state_path=tmp_path / "state.json",
        chat_id_file=tmp_path / "chat_id.txt",
        test_scan_seconds=5,
        test_lead_min=1,
    )


def test_normal_mode_uses_the_configured_interval(tmp_path):
    runtime = Runtime(make_settings(tmp_path))

    assert runtime.interval_seconds == 300
    assert runtime.lead_min == 15
    assert runtime.due(NOW) is True

    runtime.mark_scan(NOW)
    assert runtime.due(NOW + timedelta(seconds=4)) is False
    assert runtime.due(NOW + timedelta(minutes=5)) is True


def test_test_mode_changes_scan_and_lead(tmp_path):
    runtime = Runtime(make_settings(tmp_path))
    runtime.mark_scan(NOW)

    runtime.enter_test(10)

    assert runtime.test_mode is True
    assert runtime.interval_seconds == 10
    assert runtime.lead_min == 1
    assert runtime.due(NOW) is True


def test_stop_restores_normal_mode(tmp_path):
    runtime = Runtime(make_settings(tmp_path))
    runtime.enter_test(5)

    runtime.stop_test()

    assert runtime.test_mode is False
    assert runtime.interval_seconds == 300
    assert runtime.lead_min == 15
