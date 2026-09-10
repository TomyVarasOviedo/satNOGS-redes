import threading
import time
import asyncio
import logging
from typing import Optional
from utils.config import RESILIENCE_CONFIG, SATELLITES_TO_MONITOR, SATNOGS_CONFIG
from services.satnogs import fetch_with_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Refresher:
    def __init__(self, interval: Optional[int] = None):
        self.interval = interval or RESILIENCE_CONFIG["REFRESH_INTERVAL"]
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            logger.warning("Refresher already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info(f"Refresher started with interval {self.interval}s")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Refresher stopped")

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                asyncio.run(self._refresh_all())
            except Exception as e:
                logger.error(f"Error in refresher cycle: {e}")

            self._stop_event.wait(self.interval)

    async def _refresh_all(self) -> None:
        for sat in SATELLITES_TO_MONITOR:
            if self._stop_event.is_set():
                break

            norad_id = sat["norad_id"]
            name = sat["name"]

            try:
                await self._refresh_satellite(norad_id, name)
            except Exception as e:
                logger.error(f"Failed to refresh {name} (NORAD: {norad_id}): {e}")

    async def _refresh_satellite(self, norad_id: int, name: str) -> None:
        logger.info(f"Refreshing {name} (NORAD: {norad_id})")

        sat_id = await self._get_sat_id(norad_id)
        if not sat_id:
            logger.warning(f"Could not get sat_id for NORAD {norad_id}")
            return

        await self._refresh_metadata(sat_id, name)
        await self._refresh_observations(sat_id, name)

    async def _get_sat_id(self, norad_id: int) -> Optional[str]:
        import httpx

        try:
            async with httpx.AsyncClient(timeout=RESILIENCE_CONFIG["REQUEST_TIMEOUT"]) as client:
                response = await client.get(
                    f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?norad_cat_id={norad_id}",
                    headers={
                        "Accept": "application/json",
                        "Authorization": f"TOKEN {SATNOGS_CONFIG['DB_TOKEN_SATNOGS']}",
                    },
                )
                response.raise_for_status()
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return data[0].get("sat_id")
        except Exception as e:
            logger.error(f"Error getting sat_id for NORAD {norad_id}: {e}")
        return None

    async def _refresh_metadata(self, sat_id: str, name: str) -> None:
        try:
            await fetch_with_cache(
                endpoint="satellite_metadata",
                params={"sat_id": sat_id},
                ttl=RESILIENCE_CONFIG["DEFAULT_TTL_METADATA"],
                source="DB",
                url_builder=lambda p: f"{SATNOGS_CONFIG['DB_URL_SATNOGS']}/satellites/?sat_id={p['sat_id']}",
            )
            logger.info(f"Refreshed metadata for {name}")
        except Exception as e:
            logger.error(f"Failed to refresh metadata for {name}: {e}")

    async def _refresh_observations(self, sat_id: str, name: str) -> None:
        try:
            await fetch_with_cache(
                endpoint="observations",
                params={"sat_id": sat_id},
                ttl=RESILIENCE_CONFIG["DEFAULT_TTL_OBSERVATIONS"],
                source="NETWORK",
                url_builder=lambda p: f"{SATNOGS_CONFIG['NETWORK_URL']}/observations/?sat_id={p['sat_id']}",
            )
            logger.info(f"Refreshed observations for {name}")
        except Exception as e:
            logger.error(f"Failed to refresh observations for {name}: {e}")


refresher = Refresher()