from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from alerts import AlertService
from api import ApiResult
from chat_store import ChatStore
from config import Settings
from runtime import Runtime
from state import State

NOW = datetime.now(timezone.utc)
AOS = (NOW + timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
LOS = (NOW + timedelta(minutes=13)).strftime("%Y-%m-%dT%H:%M:%SZ")

PASS = {
    "aos": AOS,
    "tca": AOS,
    "los": LOS,
    "duration_s": 480,
    "max_elevation_deg": 60,
    "aos_azimuth_deg": 10,
    "los_azimuth_deg": 170,
    "aos_clipped": False,
    "los_clipped": False,
    "link": {
        "margin_at_aos_db": 10.0,
        "margin_at_tca_db": 20.0,
        "freq_hz": 437150000,
        "mode": "BPSK",
        "baud": 1200,
    },
}
DOPPLER = {"f0_hz": 437150000, "aos_frequency_hz": 437158000, "los_frequency_hz": 437142000}
ORBIT = {"orbit_type": "LEO", "period_min": 100.0, "altitude_km": 785, "tle_age_days": 9.0}


class FakeApi:
    async def monitored(self):
        return ApiResult([{"name": "LUSAT"}], "live", 0)

    async def resolve_sat_id(self, name):
        return "ZDPY"

    async def passes(self, sat_id, days=2, horizon_deg=None):
        return ApiResult({"passes": [PASS]}, "live", 0)

    async def doppler(self, sat_id, start=None, horizon_deg=None):
        return ApiResult(DOPPLER, "live", 0)

    async def orbit(self, sat_id):
        return ApiResult(ORBIT, "live", 0)


class FakeBot:
    def __init__(self):
        self.messages: list[str] = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append(text)


@pytest.fixture
def service(tmp_path) -> AlertService:
    settings = Settings(
        bot_token="token",
        chat_id=123,
        backend_url="http://backend",
        alert_lead_min=15,
        pass_scan_interval_min=5,
        agenda_hour_utc=9,
        tle_max_age_days=7.0,
        min_elevation_deg=10.0,
        timezone=ZoneInfo("UTC"),
        timezone_name="UTC",
        state_path=Path(tmp_path) / "state.json",
        chat_id_file=Path(tmp_path) / "chat_id.txt",
        test_scan_seconds=5,
        test_lead_min=15,
    )
    chats = ChatStore(settings.chat_id_file, settings.chat_id)
    runtime = Runtime(settings)
    return AlertService(FakeApi(), State(settings.state_path), settings, chats, runtime)


@pytest.mark.asyncio
async def test_pass_alert_is_sent_once(service):
    bot = FakeBot()

    assert await service.scan_pass_alerts(bot) == 1
    assert await service.scan_pass_alerts(bot) == 0

    assert len(bot.messages) == 1
    assert "pasa en" in bot.messages[0].lower()


@pytest.mark.asyncio
async def test_agenda_is_sent_once_unless_forced(service):
    bot = FakeBot()

    assert await service.send_agenda(bot, 123) == 1
    assert await service.send_agenda(bot, 123) == 0
    assert await service.send_agenda(bot, 123, force=True) == 1

    assert len(bot.messages) == 2


@pytest.mark.asyncio
async def test_test_scan_can_ignore_dedup_once(service):
    bot = FakeBot()

    assert await service.scan_pass_alerts(bot) == 1
    assert await service.scan_pass_alerts(bot) == 0
    assert await service.scan_pass_alerts(bot, ignore_dedup=True) == 1

    assert len(bot.messages) == 2


@pytest.mark.asyncio
async def test_stale_tle_warning_is_sent_once(service):
    bot = FakeBot()

    assert await service.send_tle_warnings(bot, 123) == 1
    assert await service.send_tle_warnings(bot, 123) == 0

    assert len(bot.messages) == 1
    assert "desactualizado" in bot.messages[0]
