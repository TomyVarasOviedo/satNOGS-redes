from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _chat_id(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class Settings:
    bot_token: str
    chat_id: int | None
    backend_url: str
    alert_lead_min: int
    pass_scan_interval_min: int
    agenda_hour_utc: int
    tle_max_age_days: float
    min_elevation_deg: float
    timezone: ZoneInfo
    timezone_name: str
    state_path: Path
    chat_id_file: Path
    test_scan_seconds: int
    test_lead_min: int

    @property
    def tz(self) -> ZoneInfo:
        return self.timezone


def load_settings(require_token: bool = True) -> Settings:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if require_token and not token:
        raise ValueError(
            "Falta TELEGRAM_BOT_TOKEN. Copiá bot/.env.example a bot/.env y completalo."
        )

    timezone_name = (os.getenv("TZ") or "America/Argentina/Buenos_Aires").strip() or "UTC"
    try:
        timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        timezone_name, timezone = "UTC", ZoneInfo("UTC")

    state_raw = (os.getenv("STATE_PATH") or "").strip()
    state_path = Path(state_raw) if state_raw else BASE_DIR / "state.json"

    chat_file_raw = (os.getenv("CHAT_ID_FILE") or "").strip()
    chat_id_file = Path(chat_file_raw) if chat_file_raw else BASE_DIR / "chat_id.txt"

    alert_lead_min = max(1, _int("ALERT_LEAD_MIN", 15))
    pass_scan_interval_min = min(
        max(1, _int("PASS_SCAN_INTERVAL_MIN", 5)),
        alert_lead_min,
    )

    return Settings(
        bot_token=token,
        chat_id=_chat_id(os.getenv("TELEGRAM_CHAT_ID")),
        backend_url=(os.getenv("BACKEND_URL") or "http://127.0.0.1:8000").rstrip("/"),
        alert_lead_min=alert_lead_min,
        pass_scan_interval_min=pass_scan_interval_min,
        agenda_hour_utc=max(0, min(23, _int("AGENDA_HOUR_UTC", 9))),
        tle_max_age_days=max(0.0, _float("TLE_MAX_AGE_DAYS", 7.0)),
        min_elevation_deg=max(0.0, min(90.0, _float("MIN_ELEVATION_DEG", 10.0))),
        timezone=timezone,
        timezone_name=timezone_name,
        state_path=state_path,
        chat_id_file=chat_id_file,
        test_scan_seconds=max(1, min(60, _int("TEST_SCAN_SECONDS", 5))),
        test_lead_min=max(1, _int("TEST_LEAD_MIN", alert_lead_min)),
    )
