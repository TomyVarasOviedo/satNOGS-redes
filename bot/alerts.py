from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from api import ApiError, NocApi
from chat_store import ChatStore
from config import Settings
from messages import (
    chunk,
    combine_sources,
    format_agenda,
    format_pass_alert,
    format_tle_warning,
)
from runtime import Runtime
from state import State

logger = logging.getLogger(__name__)


def parse_iso(value: str) -> datetime:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def passes_to_alert(passes: list[dict], now: datetime, lead_min: int) -> list[dict]:
    horizon = now + timedelta(minutes=lead_min)
    selected = []
    for satellite_pass in passes:
        if satellite_pass.get("aos_clipped"):
            continue
        try:
            aos = parse_iso(satellite_pass["aos"])
        except (KeyError, ValueError):
            continue
        if now < aos <= horizon:
            selected.append(satellite_pass)
    return sorted(selected, key=lambda satellite_pass: satellite_pass["aos"])


def select_agenda(
    passes: list[dict],
    min_elevation_deg: float,
    limit: int = 5,
) -> list[dict]:
    selected = [
        satellite_pass
        for satellite_pass in passes
        if satellite_pass.get("max_elevation_deg") is not None
        and satellite_pass["max_elevation_deg"] >= min_elevation_deg
    ]
    return sorted(selected, key=lambda satellite_pass: satellite_pass["aos"])[:limit]


def is_tle_stale(orbit: dict, max_age_days: float) -> bool:
    age = orbit.get("tle_age_days")
    return age is not None and age > max_age_days


async def send_chunks(bot, chat_id: int, text: str) -> None:
    from telegram.constants import ParseMode

    for part in chunk(text):
        await bot.send_message(
            chat_id=chat_id,
            text=part,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )


class AlertService:
    def __init__(
        self,
        api: NocApi,
        state: State,
        settings: Settings,
        chats: ChatStore,
        runtime: Runtime,
    ):
        self.api = api
        self.state = state
        self.settings = settings
        self.chats = chats
        self.runtime = runtime

    async def monitored_pairs(self) -> list[tuple[str, str]]:
        result = await self.api.monitored()
        pairs: list[tuple[str, str]] = []
        for item in result.data if isinstance(result.data, list) else []:
            name = (item.get("name") or "").strip()
            if not name:
                continue
            try:
                sat_id = await self.api.resolve_sat_id(name)
            except ApiError as exc:
                logger.warning("No se pudo resolver %s: %s", name, exc)
                continue
            pairs.append((name, sat_id))
        return pairs

    async def _passes(self, sat_id: str, days: float):
        return await self.api.passes(
            sat_id,
            days=days,
            horizon_deg=self.settings.min_elevation_deg,
        )

    async def scan_pass_alerts(self, bot, ignore_dedup: bool = False) -> int:
        chat_id = self.chats.chat_id
        if chat_id is None:
            return 0

        now = datetime.now(timezone.utc)
        lead_min = self.runtime.lead_min
        days = max(lead_min / 1440, 1 / 24)
        sent = 0
        for name, sat_id in await self.monitored_pairs():
            try:
                result = await self._passes(sat_id, days)
            except ApiError as exc:
                logger.warning("No se pudieron leer pases de %s: %s", name, exc)
                continue

            passes = result.data.get("passes", []) if isinstance(result.data, dict) else []
            for satellite_pass in passes_to_alert(passes, now, lead_min):
                key = f"pass:{sat_id}:{satellite_pass['aos']}"
                if not ignore_dedup and self.state.contains(key):
                    continue

                doppler = None
                try:
                    doppler = (await self.api.doppler(sat_id, start=satellite_pass["aos"])).data
                except ApiError as exc:
                    logger.info("Sin Doppler para %s: %s", name, exc)

                minutes = round((parse_iso(satellite_pass["aos"]) - now).total_seconds() / 60)
                text = format_pass_alert(
                    name,
                    satellite_pass,
                    doppler,
                    self.settings.tz,
                    result.source,
                    minutes,
                )
                await send_chunks(bot, chat_id, text)
                self.state.mark(key)
                sent += 1
                logger.info("Alerta de pase enviada: %s %s", name, satellite_pass["aos"])

        self.state.prune()
        logger.info("Escaneo de pases completado: %s alerta(s) enviada(s), T-%s min", sent, lead_min)
        return sent

    async def send_agenda(self, bot, chat_id: int, force: bool = False) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        key = f"agenda:{today}"
        if not force and self.state.contains(key):
            return 0

        entries: list[tuple[str, list[dict]]] = []
        sources: set[str] = set()
        for name, sat_id in await self.monitored_pairs():
            try:
                result = await self._passes(sat_id, 1)
            except ApiError as exc:
                logger.warning("No se pudieron leer pases de %s: %s", name, exc)
                continue
            passes = result.data.get("passes", []) if isinstance(result.data, dict) else []
            entries.append((name, select_agenda(passes, self.settings.min_elevation_deg)))
            sources.add(result.source)

        if not entries:
            return 0

        await send_chunks(
            bot,
            chat_id,
            format_agenda(entries, self.settings.tz, combine_sources(sources)),
        )
        if not force:
            self.state.mark(key)
        return len(entries)

    async def send_tle_warnings(self, bot, chat_id: int, force: bool = False) -> int:
        today = datetime.now(timezone.utc).date().isoformat()
        sent = 0
        for name, sat_id in await self.monitored_pairs():
            key = f"tle:{sat_id}:{today}"
            if not force and self.state.contains(key):
                continue
            try:
                result = await self.api.orbit(sat_id)
            except ApiError as exc:
                logger.warning("No se pudo leer la órbita de %s: %s", name, exc)
                continue
            if not is_tle_stale(result.data, self.settings.tle_max_age_days):
                continue

            text = format_tle_warning(
                name,
                result.data,
                self.settings.tle_max_age_days,
                result.source,
            )
            await send_chunks(bot, chat_id, text)
            if not force:
                self.state.mark(key)
            sent += 1
        return sent
