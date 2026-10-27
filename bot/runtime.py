from __future__ import annotations

from datetime import datetime

from config import Settings


class Runtime:
    """Estado en memoria del modo prueba; un reinicio vuelve a la configuración normal."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.test_mode = False
        self.scan_seconds = settings.test_scan_seconds
        self.lead_min = settings.alert_lead_min
        self.last_scan: datetime | None = None

    @property
    def interval_seconds(self) -> int:
        if self.test_mode:
            return self.scan_seconds
        return self.settings.pass_scan_interval_min * 60

    def enter_test(self, scan_seconds: int | None = None) -> None:
        self.test_mode = True
        self.scan_seconds = scan_seconds or self.settings.test_scan_seconds
        self.lead_min = self.settings.test_lead_min
        self.last_scan = None

    def stop_test(self) -> None:
        self.test_mode = False
        self.scan_seconds = self.settings.test_scan_seconds
        self.lead_min = self.settings.alert_lead_min
        self.last_scan = None

    def due(self, now: datetime) -> bool:
        if self.last_scan is None:
            return True
        return (now - self.last_scan).total_seconds() >= self.interval_seconds

    def mark_scan(self, now: datetime) -> None:
        self.last_scan = now
